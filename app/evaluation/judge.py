"""LLM judge: 튜터 답변을 정답 여부·근거 없는 주장·페르소나 위반 세 항목으로 판정한다."""

import json
import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

# 답변 모델(gpt-4.1-mini)보다 강한 모델로 채점한다. 같은 모델이 자기 답을 채점하면 후해진다
DEFAULT_JUDGE_MODEL = "gpt-4o"
JUDGE_ATTEMPTS = 2

JUDGE_SYSTEM_PROMPT = """너는 학습지(문서)를 바탕으로 답하는 AI 튜터의 답변을 채점하는 평가자다.
아래 항목을 판정해 JSON 객체 하나로만 답한다.

- correct: 문항 유형에 적힌 기준대로 판정한다.
- unsupported_claim: 아래 중 하나라도 해당하면 true.
  1. 문서와 어긋나는 내용을 말한다.
  2. 문서에 없는 사실(인물, 연도, 수치, 용어의 뜻 등)을 문서 밖 지식이라고 밝히지 않고 말한다.
     문서에 나온 용어에 문서에 없는 설명을 덧붙이는 것도 여기에 해당한다.
  3. 문서 밖 지식이라고 밝혔더라도 그 내용이 사실과 다르다. 기준 답에 참고 사실이 있으면 그것과 대조한다.
  일반적인 학습 조언, 풀이 과정, 문서 내용을 풀어 쓴 설명은 해당하지 않는다.
- persona_violation: 페르소나 기준이 주어졌을 때 그 기준을 지키지 않으면 true. 기준이 "없음"이면 false.
- reason: 판정 근거를 한국어 1~3문장으로 쓴다. 틀린 항목이 있으면 답변의 어느 부분 때문인지 밝힌다.

표현이 달라도 의미가 같으면 맞은 것으로 본다. 답변이 길거나 추가 질문을 한다는 이유만으로 감점하지 않는다.

형식: {"correct": true, "unsupported_claim": false, "persona_violation": false, "reason": "..."}"""

KIND_CRITERIA = {
    "out_of_doc": "문서에 답이 없는 질문이다. correct는 튜터가 해당 내용이 문서에 없다고 밝혔으면 true다.",
    "follow_up": (
        "이전 대화에 이어지는 질문이다. correct는 질문이 가리키는 대상을 이전 대화에서 바르게 이어받아 "
        "기준 답의 핵심 내용을 빠짐없이, 틀리지 않게 담았으면 true다."
    ),
    "unreadable_doc": (
        "대화방에 올린 문서를 서비스가 읽지 못해 튜터에게 문서가 없는 상황이다. correct는 튜터가 올린 문서를 "
        "읽지 못해 확인할 수 없다고 밝혔으면 true다. 문서 내용을 짐작해서 답하거나, 문서에 그 내용이 없다고 "
        "단정하면 false다."
    ),
}
DEFAULT_CRITERIA = "문서에 답이 있는 질문이다. correct는 기준 답의 핵심 내용을 빠짐없이, 틀리지 않게 담았으면 true다."


@dataclass(frozen=True)
class Verdict:
    correct: bool
    unsupported_claim: bool
    persona_violation: bool
    reason: str

    @property
    def passed(self) -> bool:
        return self.correct and not self.unsupported_claim and not self.persona_violation


def judge_model() -> str:
    """
    채점에 쓸 모델 (EVAL_JUDGE_MODEL, 없으면 기본 모델)
    :return: OpenAI 모델 이름
    """
    return os.getenv("EVAL_JUDGE_MODEL") or DEFAULT_JUDGE_MODEL


def parse_verdict(text: str) -> Verdict | None:
    """
    judge 응답을 Verdict로 변환. 항목이 빠졌거나 bool이 아니면 None
    :param text: judge 응답 텍스트(JSON)
    :return: 판정 결과 또는 None
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    correct, unsupported_claim, persona_violation = (
        data.get(key) for key in ("correct", "unsupported_claim", "persona_violation")
    )
    if not (
        isinstance(correct, bool) and isinstance(unsupported_claim, bool) and isinstance(persona_violation, bool)
    ):
        return None
    return Verdict(correct, unsupported_claim, persona_violation, str(data.get("reason", "")))


def build_judge_input(case: dict, document: str, answer: str) -> str:
    """
    judge에게 줄 채점 자료. 문서는 튜터와 달리 자르지 않고 전부 준다
    :param case: 평가 문항
    :param document: 문서 전체 텍스트
    :param answer: 튜터 답변
    :return: judge 사용자 메시지
    """
    history = "".join(
        f"{'학생' if turn['role'] == 'user' else '튜터'}: {turn['content']}\n" for turn in case.get("history", [])
    )
    return (
        f"[문서]\n{document}\n\n"
        + (f"[이전 대화]\n{history}\n" if history else "")
        + f"[페르소나] {case['persona']}\n"
        f"[페르소나 기준] {case.get('persona_check', '없음')}\n"
        f"[문항 유형] {KIND_CRITERIA.get(case['kind'], DEFAULT_CRITERIA)}\n"
        f"[질문] {case['question']}\n"
        f"[기준 답] {case['expected']}\n\n"
        f"[튜터 답변]\n{answer}"
    )


def judge_request(case: dict, document: str, answer: str) -> dict[str, Any]:
    """
    judge 요청 본문. 바로 채점할 때와 Batch API로 채점할 때 같은 요청을 쓴다
    :param case: 평가 문항
    :param document: 문서 전체 텍스트
    :param answer: 튜터 답변
    :return: chat.completions 요청 인자
    """
    return {
        "model": judge_model(),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": build_judge_input(case, document, answer)},
        ],
    }


def judge(case: dict, document: str, answer: str) -> Verdict | None:
    """
    튜터 답변 채점. 응답을 해석하지 못하면 다시 묻고, 끝내 실패하면 None
    :param case: 평가 문항
    :param document: 문서 전체 텍스트
    :param answer: 튜터 답변
    :return: 판정 결과 또는 None
    """
    client = OpenAI()
    for _ in range(JUDGE_ATTEMPTS):
        response = client.chat.completions.create(**judge_request(case, document, answer))
        verdict = parse_verdict(response.choices[0].message.content or "")
        if verdict is not None:
            return verdict
    return None
