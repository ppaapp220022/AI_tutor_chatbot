"""Batch API 평가 경로 검사. 가짜 클라이언트로 OpenAI를 호출하지 않는다."""

import json
from types import SimpleNamespace

from app.backend.service.ai_client_service import chat_request
from app.evaluation import batch
from app.evaluation.judge import Verdict, judge_request
from app.evaluation.run import load_cases, load_document, tutor_messages

CASES = load_cases()[:4]
PASS = {"correct": True, "unsupported_claim": False, "persona_violation": False, "reason": "맞음"}


def ok(content: str) -> dict:
    return {"status_code": 200, "body": {"choices": [{"message": {"content": content}}]}}


class FakeClient:
    """올린 JSONL을 받아 respond(custom_id, body)가 돌려준 응답으로 배치 결과를 만든다"""

    def __init__(self, respond):
        self.respond = respond
        self.sent: list[list[dict]] = []
        self.outputs: dict[str, str] = {}
        self.files = SimpleNamespace(create=self._upload, content=self._content)
        self.batches = SimpleNamespace(create=self._create, retrieve=self._retrieve)

    def _upload(self, file, purpose):
        assert purpose == "batch"
        lines = [json.loads(line) for line in file[1].read().decode().splitlines()]
        self.sent.append(lines)
        return SimpleNamespace(id=f"file-{len(self.sent)}")

    def _create(self, input_file_id, endpoint, completion_window):
        lines = self.sent[-1]
        out, err = [], []
        for line in lines:
            response = self.respond(line["custom_id"], line["body"])
            item = {"custom_id": line["custom_id"], "response": response, "error": None}
            (out if response and response["status_code"] == 200 else err).append(json.dumps(item))
        batch_id = f"batch-{len(self.sent)}"
        self.outputs[f"{batch_id}-out"] = "\n".join(out)
        self.outputs[f"{batch_id}-err"] = "\n".join(err)
        return SimpleNamespace(id=batch_id)

    def _retrieve(self, batch_id):
        return SimpleNamespace(
            status="completed", output_file_id=f"{batch_id}-out", error_file_id=f"{batch_id}-err", request_counts=None
        )

    def _content(self, file_id):
        return SimpleNamespace(text=self.outputs[file_id])


def test_batch_sends_same_requests_as_direct_run(monkeypatch):
    def respond(case_id, body):
        return ok(json.dumps(PASS)) if body.get("response_format") else ok(f"{case_id} 답변")

    client = FakeClient(respond)
    monkeypatch.setattr(batch, "OpenAI", lambda: client)

    results = batch.run_batch(CASES, poll_seconds=0)

    answers, judges = client.sent
    assert [line["body"] for line in answers] == [chat_request(tutor_messages(case)) for case in CASES]
    assert [line["body"] for line in judges] == [
        judge_request(case, load_document(case), f"{case['id']} 답변") for case in CASES
    ]
    assert all(line["url"] == batch.ENDPOINT for line in answers + judges)
    assert [r.status for r in results] == ["pass"] * len(CASES)
    assert [r.id for r in results] == [case["id"] for case in CASES]


def test_batch_statuses(monkeypatch):
    first, second, third, fourth = (case["id"] for case in CASES)
    fail = {**PASS, "unsupported_claim": True, "reason": "문서에 없는 내용"}

    def respond(case_id, body):
        if not body.get("response_format"):
            if case_id == first:
                return {"status_code": 429, "body": {"error": {"message": "rate limit"}}}
            return ok("" if case_id == second else "답변")
        return ok(json.dumps(fail) if case_id == third else "판정 못함")

    client = FakeClient(respond)
    monkeypatch.setattr(batch, "OpenAI", lambda: client)
    retried: list[str] = []

    def fake_judge(case, document, answer):
        retried.append(case["id"])
        return None

    monkeypatch.setattr(batch, "judge", fake_judge)

    results = {r.id: r for r in batch.run_batch(CASES, poll_seconds=0)}

    assert (results[first].status, results[first].error) == ("generation_error", "rate limit")
    assert (results[second].status, results[second].error) == ("generation_error", "빈 응답")
    assert (results[third].status, results[third].unsupported_claim) == ("fail", True)
    # 해석하지 못한 판정은 바로 돌릴 때처럼 한 번 더 채점한다
    assert retried == [fourth]
    assert results[fourth].status == "judge_error"
    # 답을 못 만든 문항은 채점 배치에 넣지 않는다
    assert [line["custom_id"] for line in client.sent[1]] == [third, fourth]


def test_batch_retry_verdict_is_used(monkeypatch):
    def respond(case_id, body):
        return ok("판정 못함") if body.get("response_format") else ok("답변")

    monkeypatch.setattr(batch, "OpenAI", lambda: FakeClient(respond))
    monkeypatch.setattr(batch, "judge", lambda c, d, a: Verdict(True, False, False, "맞음"))

    assert {r.status for r in batch.run_batch(CASES[:1], poll_seconds=0)} == {"pass"}
