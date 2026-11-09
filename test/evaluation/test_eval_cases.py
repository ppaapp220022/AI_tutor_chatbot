"""평가 문항(eval/cases.jsonl)과 채점 로직 검사. OpenAI를 호출하지 않는다."""

import json

from openai import OpenAIError

from app.backend.service.ai_chat_service import (
    MAX_FILE_CONTEXT_LENGTH,
    PERSONA_PROMPT_MAP,
    build_openai_messages,
)
from app.evaluation import run
from app.evaluation.judge import Verdict, parse_verdict
from app.evaluation.run import DOCUMENTS, KINDS, load_cases, load_document, run_one

CASES = load_cases()


def test_cases_are_well_formed():
    ids = [case["id"] for case in CASES]
    assert len(ids) == len(set(ids))
    for case in CASES:
        assert case["kind"] in KINDS, case["id"]
        assert case["persona"] in PERSONA_PROMPT_MAP, case["id"]
        assert case["question"].strip() and case["expected"].strip(), case["id"]
        assert all((DOCUMENTS / name).is_file() for name in case["documents"]), case["id"]
        if case["kind"] == "persona":
            assert case.get("persona_check"), case["id"]


def test_only_long_doc_cases_exceed_context_limit():
    # 짧은 문항은 문서가 잘리지 않아야 그 유형만 잴 수 있다
    for case in CASES:
        length = len(load_document(case))
        if case["kind"] == "long_doc":
            assert length > MAX_FILE_CONTEXT_LENGTH, case["id"]
        else:
            assert length <= MAX_FILE_CONTEXT_LENGTH, case["id"]


def test_long_doc_answer_reaches_tutor_context():
    # 긴 문서 문항의 답(anchor)은 12,000자 뒤에 있지만, 질문과 관련된 부분을 골라 넣으므로 튜터에게 간다
    for case in (c for c in CASES if c["kind"] == "long_doc"):
        document = load_document(case)
        assert document.index(case["anchor"]) > MAX_FILE_CONTEXT_LENGTH, case["id"]
        sent = "\n".join(str(m["content"]) for m in build_openai_messages([], case["question"], document))
        assert case["anchor"] in sent, case["id"]


def test_parse_verdict():
    text = json.dumps({"correct": True, "unsupported_claim": False, "persona_violation": False, "reason": "맞음"})
    assert parse_verdict(text) == Verdict(True, False, False, "맞음")
    assert parse_verdict('{"correct": true, "unsupported_claim": false}') is None
    assert parse_verdict('{"correct": "true", "unsupported_claim": false, "persona_violation": false}') is None
    assert parse_verdict("판정: 맞음") is None
    assert parse_verdict("[]") is None


def test_verdict_passes_only_when_all_checks_pass():
    assert Verdict(True, False, False, "").passed
    assert not Verdict(False, False, False, "").passed
    assert not Verdict(True, True, False, "").passed
    assert not Verdict(True, False, True, "").passed


def test_run_one_statuses(monkeypatch):
    case = CASES[0]
    monkeypatch.setattr(run, "request_chat_completion", lambda messages: "답변")

    monkeypatch.setattr(run, "judge", lambda c, d, a: Verdict(True, False, False, "맞음"))
    assert run_one(case).status == "pass"

    monkeypatch.setattr(run, "judge", lambda c, d, a: Verdict(True, True, False, "문서에 없는 내용"))
    result = run_one(case)
    assert (result.status, result.unsupported_claim) == ("fail", True)

    monkeypatch.setattr(run, "judge", lambda c, d, a: None)
    assert run_one(case).status == "judge_error"

    monkeypatch.setattr(run, "request_chat_completion", lambda messages: "")
    assert run_one(case).status == "generation_error"

    def raise_openai_error(messages):
        raise OpenAIError("요청 실패")

    monkeypatch.setattr(run, "request_chat_completion", raise_openai_error)
    result = run_one(case)
    assert (result.status, result.error) == ("generation_error", "요청 실패")
