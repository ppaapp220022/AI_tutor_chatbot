"""AI 채팅 요청 횟수 제한. 공개 배포에서 한 사용자가 OpenAI 비용을 몰아 쓰지 못하게 막는다."""

import os
import time

from loguru import logger
from redis import Redis, RedisError

from app.backend.exception.app_exceptions import TooManyRequestsException

DEFAULT_LIMIT_PER_MINUTE = 5
DEFAULT_LIMIT_PER_DAY = 100
MINUTE_SECONDS = 60
DAY_SECONDS = 24 * 60 * 60


def _limit_from_env(name: str, default: int) -> int:
    """
    환경변수의 제한 횟수. 비었거나 숫자가 아니면 기본값
    :param name: 환경변수 이름
    :param default: 기본값
    :return: 제한 횟수 (0 이하면 제한 없음)
    """
    value = os.getenv(name, "").strip()
    try:
        return int(value) if value else default
    except ValueError:
        logger.warning(f"{name} 값이 숫자가 아니어서 기본값 {default}을 쓴다")
        return default


def limits() -> list[tuple[str, int, int]]:
    """
    적용할 제한 목록 (이름, 허용 횟수, 구간 초)
    :return: 제한 목록
    """
    return [
        ("minute", _limit_from_env("AI_CHAT_LIMIT_PER_MINUTE", DEFAULT_LIMIT_PER_MINUTE), MINUTE_SECONDS),
        ("day", _limit_from_env("AI_CHAT_LIMIT_PER_DAY", DEFAULT_LIMIT_PER_DAY), DAY_SECONDS),
    ]


def check_ai_chat_rate_limit(client: Redis, login_id: str, now: float | None = None) -> None:
    """
    사용자의 AI 채팅 요청을 1건 세고, 구간별 허용 횟수를 넘으면 막는다 (고정 구간 방식)
    Redis에 닿지 못하면 채팅 자체를 막지 않고 경고만 남긴다. 비용 상한은 OpenAI 프로젝트 사용 한도가 맡는다
    :param client: Redis 클라이언트
    :param login_id: 로그인 아이디
    :param now: 현재 시각(초). 테스트용
    :raises TooManyRequestsException: 허용 횟수를 넘었을 때
    """
    current = time.time() if now is None else now
    for name, limit, window in limits():
        if limit <= 0:
            continue
        key = f"ai_chat_rate:{name}:{login_id}:{int(current // window)}"
        try:
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            count = int(pipe.execute()[0])
        except RedisError as exc:
            logger.warning(f"AI 채팅 요청 제한을 확인하지 못해 그대로 진행한다: {exc}")
            return
        if count > limit:
            message = "요청이 너무 잦아요. 1분 뒤에 다시 시도해 주세요." if name == "minute" else (
                "오늘 사용할 수 있는 AI 채팅 횟수를 모두 썼어요. 내일 다시 시도해 주세요."
            )
            raise TooManyRequestsException(message)
