"""Batch API로 평가를 돌린다. 결과는 늦게 오지만 요청 비용이 절반이다.

답변을 한 배치로 만들고, 끝나면 그 답변을 채점하는 judge 배치를 하나 더 보낸다.
요청 본문은 바로 돌릴 때와 같은 chat_request()·judge_request()를 써서 두 방식의 점수를 비교할 수 있게 한다.
"""

import io
import json
import sys
import time
from typing import Any, Final

from openai import OpenAI

from app.backend.service.ai_client_service import chat_request
from app.evaluation.judge import judge, judge_request, parse_verdict
from app.evaluation.run import Result, apply_verdict, load_document, tutor_messages

ENDPOINT: Final = "/v1/chat/completions"
DONE_STATUSES = {"completed", "failed", "expired", "cancelled"}


def submit(client: OpenAI, bodies: dict[str, dict[str, Any]], label: str) -> str:
    """
    요청들을 JSONL로 올리고 배치를 만든다
    :param client: OpenAI 클라이언트
    :param bodies: 문항 id별 요청 본문
    :param label: 진행 표시에 쓸 이름
    :return: 배치 id
    """
    lines = [
        json.dumps({"custom_id": case_id, "method": "POST", "url": ENDPOINT, "body": body}, ensure_ascii=False)
        for case_id, body in bodies.items()
    ]
    upload = client.files.create(file=(f"{label}.jsonl", io.BytesIO("\n".join(lines).encode())), purpose="batch")
    batch = client.batches.create(input_file_id=upload.id, endpoint=ENDPOINT, completion_window="24h")
    print(f"{label} 배치 {batch.id} ({len(lines)}건) 보냄", file=sys.stderr)
    return batch.id


def wait(client: OpenAI, batch_id: str, label: str, poll_seconds: float) -> dict[str, dict | str]:
    """
    배치가 끝날 때까지 기다린 뒤 문항 id별 응답을 모은다
    :param client: OpenAI 클라이언트
    :param batch_id: 배치 id
    :param label: 진행 표시에 쓸 이름
    :param poll_seconds: 상태를 다시 볼 간격(초)
    :return: 문항 id별 응답 본문(성공) 또는 오류 메시지(실패)
    """
    while True:
        batch = client.batches.retrieve(batch_id)
        if batch.status in DONE_STATUSES:
            break
        counts = batch.request_counts
        done = f"{counts.completed + counts.failed}/{counts.total}" if counts else "-"
        print(f"{label} 배치 {batch.status} {done}", file=sys.stderr)
        time.sleep(poll_seconds)
    if batch.status != "completed":
        print(f"{label} 배치가 {batch.status} 상태로 끝남", file=sys.stderr)

    responses: dict[str, dict | str] = {}
    for file_id in (batch.output_file_id, batch.error_file_id):
        if not file_id:
            continue
        for line in client.files.content(file_id).text.splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            response = item.get("response") or {}
            if item.get("error") or response.get("status_code") != 200:
                error = item.get("error") or response.get("body", {}).get("error") or "요청 실패"
                responses[item["custom_id"]] = error.get("message", str(error)) if isinstance(error, dict) else str(error)
            else:
                responses[item["custom_id"]] = response["body"]
    return responses


def message_text(body: dict) -> str:
    """
    chat.completions 응답 본문의 답변 텍스트
    :param body: 응답 본문
    :return: 답변 텍스트. 없으면 빈 문자열
    """
    choices = body.get("choices") or [{}]
    return (choices[0].get("message") or {}).get("content") or ""


def run_batch(cases: list[dict], poll_seconds: float = 30) -> list[Result]:
    """
    답변 배치와 judge 배치를 차례로 돌려 채점한다
    judge 응답을 해석하지 못한 문항은 바로 돌릴 때처럼 한 번 더 채점하되, 그건 일반 요청으로 보낸다
    :param cases: 평가 문항
    :param poll_seconds: 배치 상태를 다시 볼 간격(초)
    :return: 문항 순서대로 채점 결과
    """
    client = OpenAI()
    results = {
        case["id"]: Result(id=case["id"], kind=case["kind"], persona=case["persona"], status="fail")
        for case in cases
    }

    answer_batch = submit(client, {case["id"]: chat_request(tutor_messages(case)) for case in cases}, "답변")
    answers = wait(client, answer_batch, "답변", poll_seconds)
    for case_id, result in results.items():
        response = answers.get(case_id, "배치 결과에 없음")
        if isinstance(response, str):
            result.status, result.error = "generation_error", response
        elif not (answer := message_text(response)):
            result.status, result.error = "generation_error", "빈 응답"
        else:
            result.answer = answer

    to_judge = [case for case in cases if results[case["id"]].answer]
    if to_judge:
        judge_batch = submit(
            client,
            {case["id"]: judge_request(case, load_document(case), results[case["id"]].answer or "") for case in to_judge},
            "judge",
        )
        verdicts = wait(client, judge_batch, "judge", poll_seconds)
        for case in to_judge:
            result = results[case["id"]]
            response = verdicts.get(case["id"], "배치 결과에 없음")
            verdict = None if isinstance(response, str) else parse_verdict(message_text(response))
            if verdict is None:
                verdict = judge(case, load_document(case), result.answer or "")
            if verdict is None:
                result.status = "judge_error"
                result.error = response if isinstance(response, str) else "judge 응답을 해석하지 못함"
            else:
                apply_verdict(result, verdict)
    return [results[case["id"]] for case in cases]
