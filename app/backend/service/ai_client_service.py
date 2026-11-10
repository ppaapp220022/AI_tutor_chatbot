import os
from typing import Any

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

DEFAULT_CHAT_MODEL = "gpt-4.1-mini"


def chat_model() -> str:
    """
    채팅 응답에 쓸 모델 (OPENAI_CHAT_MODEL, 없으면 기본 모델)
    :return: OpenAI 모델 이름
    """
    return os.getenv("OPENAI_CHAT_MODEL") or DEFAULT_CHAT_MODEL


def chat_request(messages: list[ChatCompletionMessageParam]) -> dict[str, Any]:
    """
    채팅 요청 본문. 서비스와 평가(Batch API 포함)가 같은 요청을 쓴다
    :param messages: OpenAI 요청 메시지 목록
    :return: chat.completions 요청 인자
    """
    return {"model": chat_model(), "messages": messages}


def request_chat_completion(messages: list[ChatCompletionMessageParam]) -> str:
    """
    OpenAI 활용 채팅 요청건 응답 처리
    :param messages: OpenAI 요청 메시지 목록
    :return: 생성된 응답 텍스트
    """
    client = OpenAI()
    response = client.chat.completions.create(**chat_request(messages))
    return response.choices[0].message.content or ""