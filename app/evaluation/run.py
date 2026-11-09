"""평가 문항(eval/cases.jsonl)으로 AI 튜터 답변을 채점한다.

    uv run python -m app.evaluation.run                        # 전체
    uv run python -m app.evaluation.run sci-in-001 long-001    # 일부만
    uv run python -m app.evaluation.run --model gpt-4o         # 답변 모델 (기본: OPENAI_CHAT_MODEL, 없으면 gpt-4o-mini)
    uv run python -m app.evaluation.run --judge-model gpt-4.1  # judge 모델 (기본: EVAL_JUDGE_MODEL, 없으면 gpt-4o)

문항마다 서비스와 같은 build_openai_messages()와 request_chat_completion()으로 답을 만들고(DB는 쓰지 않는다),
judge가 정답 여부·근거 없는 주장·페르소나 위반을 판정한다. 셋 다 통과해야 pass다. judge 응답 오류는 통과로 치지 않는다.
결과는 eval/results/에 JSON으로 남긴다(git 제외). 답변 모델·judge 모델·프롬프트 버전이 다른 점수끼리 섞지 않는다.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from openai import OpenAIError

from app.backend.service.ai_chat_service import (
    MAX_FILE_CONTEXT_LENGTH,
    PERSONA_PROMPT_MAP,
    build_openai_messages,
)
from app.backend.service.ai_client_service import chat_model, request_chat_completion
from app.evaluation.judge import judge, judge_model

EVAL_DIR = Path(__file__).resolve().parents[2] / "eval"
CASES = EVAL_DIR / "cases.jsonl"
DOCUMENTS = EVAL_DIR / "documents"
RESULTS = EVAL_DIR / "results"
KINDS = {"in_doc": "문서 안", "out_of_doc": "문서 밖", "persona": "페르소나", "long_doc": "긴 문서"}


@dataclass
class Result:
    id: str
    kind: str
    persona: str
    # pass | fail | judge_error | generation_error
    status: str
    answer: str | None = None
    correct: bool | None = None
    unsupported_claim: bool | None = None
    persona_violation: bool | None = None
    reason: str | None = None
    error: str | None = None
    seconds: float = 0.0


def load_cases(ids: list[str] | None = None) -> list[dict]:
    """
    평가 문항 로드
    :param ids: 돌릴 문항 id. 없으면 전체
    :return: 평가 문항 목록
    """
    cases = [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]
    if ids:
        missing = set(ids) - {case["id"] for case in cases}
        if missing:
            raise SystemExit(f"없는 문항: {', '.join(sorted(missing))}")
        cases = [case for case in cases if case["id"] in ids]
    return cases


def load_document(case: dict) -> str:
    """
    문항의 문서를 이어 붙여 업로드된 PDF 텍스트 대신 쓴다
    :param case: 평가 문항
    :return: 문서 텍스트
    """
    return "\n\n".join((DOCUMENTS / name).read_text() for name in case["documents"])


def run_one(case: dict) -> Result:
    """
    문항 하나 실행 후 채점
    :param case: 평가 문항
    :return: 채점 결과
    """
    start = time.monotonic()
    result = Result(id=case["id"], kind=case["kind"], persona=case["persona"], status="fail")
    document = load_document(case)
    messages = build_openai_messages([], case["question"], document, case["persona"])
    try:
        result.answer = request_chat_completion(messages)
    except OpenAIError as exc:
        result.status, result.error = "generation_error", str(exc)
    if result.status != "generation_error" and not result.answer:
        result.status, result.error = "generation_error", "빈 응답"
    if result.status == "generation_error":
        result.seconds = round(time.monotonic() - start, 1)
        return result

    try:
        verdict = judge(case, document, result.answer or "")
    except OpenAIError as exc:
        verdict, result.error = None, str(exc)
    if verdict is None:
        result.status = "judge_error"
        result.error = result.error or "judge 응답을 해석하지 못함"
    else:
        result.status = "pass" if verdict.passed else "fail"
        result.correct = verdict.correct
        result.unsupported_claim = verdict.unsupported_claim
        result.persona_violation = verdict.persona_violation
        result.reason = verdict.reason
    result.seconds = round(time.monotonic() - start, 1)
    return result


def summarize(results: list[Result]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in results:
        for key in (r.kind, "전체"):
            summary[key]["total"] += 1
            summary[key][r.status] += 1
            summary[key]["wrong"] += r.correct is False
            summary[key]["unsupported_claim"] += bool(r.unsupported_claim)
            summary[key]["persona_violation"] += bool(r.persona_violation)
    return {k: dict(v) for k, v in summary.items()}


def format_summary(summary: dict[str, dict[str, int]]) -> str:
    lines = [
        "| 유형 | 통과 | 문항 | 통과율 | 정답 아님 | 근거 없는 주장 | 페르소나 위반 | judge 오류 | 생성 오류 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for kind in [k for k in KINDS if k in summary] + ["전체"]:
        s = summary[kind]
        n, ok = s["total"], s.get("pass", 0)
        lines.append(
            f"| {KINDS.get(kind, kind)} | {ok} | {n} | {ok / n:.0%} | {s['wrong']} | {s['unsupported_claim']} "
            f"| {s['persona_violation']} | {s.get('judge_error', 0)} | {s.get('generation_error', 0)} |"
        )
    return "\n".join(lines)


def prompt_version() -> str:
    # 페르소나 프롬프트나 문서 자르는 길이가 바뀌면 버전이 바뀐다
    text = json.dumps(PERSONA_PROMPT_MAP, ensure_ascii=False, sort_keys=True) + str(MAX_FILE_CONTEXT_LENGTH)
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def cases_version() -> str:
    text = CASES.read_text() + "".join(p.read_text() for p in sorted(DOCUMENTS.glob("*.md")))
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.evaluation.run", description="AI 튜터 평가 문항 채점")
    parser.add_argument("ids", nargs="*", help="돌릴 문항 id. 없으면 전체")
    parser.add_argument("--model", help="답변 모델 (기본: OPENAI_CHAT_MODEL, 없으면 gpt-4o-mini)")
    parser.add_argument("--judge-model", help="judge 모델 (기본: EVAL_JUDGE_MODEL, 없으면 gpt-4o)")
    parser.add_argument("--jobs", type=int, default=4, help="동시에 돌릴 문항 수")
    args = parser.parse_args(argv)

    if args.model:
        os.environ["OPENAI_CHAT_MODEL"] = args.model
    if args.judge_model:
        os.environ["EVAL_JUDGE_MODEL"] = args.judge_model
    cases = load_cases(args.ids)
    print(
        f"답변 모델 {chat_model()}, judge {judge_model()}, 프롬프트 {prompt_version()}, "
        f"문항 {cases_version()}, {len(cases)}개",
        file=sys.stderr,
    )

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(run_one, cases))
    for r in results:
        detail = f"  {r.error}" if r.error else ""
        if r.status == "fail":
            detail = f"  {r.reason}"
        print(f"{r.id:<16} {r.status:<17} {r.seconds:>5}s{detail}", file=sys.stderr)

    summary = summarize(results)
    record = {
        "model": chat_model(),
        "judge_model": judge_model(),
        "prompt_version": prompt_version(),
        "cases_version": cases_version(),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "results": [asdict(r) for r in results],
    }
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"{datetime.now():%Y%m%d-%H%M%S}-{chat_model()}-judge-{judge_model()}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2))
    print(format_summary(summary))
    print(f"\n결과: {path.relative_to(EVAL_DIR.parent)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
