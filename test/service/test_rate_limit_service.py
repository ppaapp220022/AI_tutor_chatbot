import pytest
from redis import RedisError

from app.backend.exception.app_exceptions import TooManyRequestsException
from app.backend.service.rate_limit_service import check_ai_chat_rate_limit


class FakePipeline:
    def __init__(self, store: dict[str, int], fail: bool):
        self.store = store
        self.fail = fail
        self.keys: list[str] = []

    def incr(self, key: str) -> None:
        self.keys.append(key)

    def expire(self, key: str, seconds: int) -> None:
        pass

    def execute(self) -> list[int]:
        if self.fail:
            raise RedisError("connection refused")
        key = self.keys[0]
        self.store[key] = self.store.get(key, 0) + 1
        return [self.store[key], True]


class FakeRedis:
    def __init__(self, fail: bool = False):
        self.store: dict[str, int] = {}
        self.fail = fail

    def pipeline(self) -> FakePipeline:
        return FakePipeline(self.store, self.fail)


@pytest.fixture(autouse=True)
def limits(monkeypatch):
    monkeypatch.setenv("AI_CHAT_LIMIT_PER_MINUTE", "2")
    monkeypatch.setenv("AI_CHAT_LIMIT_PER_DAY", "3")


def test_blocks_after_minute_limit():
    client = FakeRedis()
    for _ in range(2):
        check_ai_chat_rate_limit(client, "user1", now=0)

    with pytest.raises(TooManyRequestsException) as exc:
        check_ai_chat_rate_limit(client, "user1", now=10)
    assert exc.value.status_code == 429
    assert "1분" in exc.value.detail


def test_minute_limit_resets_in_next_window():
    client = FakeRedis()
    for _ in range(2):
        check_ai_chat_rate_limit(client, "user1", now=0)

    check_ai_chat_rate_limit(client, "user1", now=60)


def test_blocks_after_day_limit():
    client = FakeRedis()
    for minute in range(3):
        check_ai_chat_rate_limit(client, "user1", now=minute * 60)

    with pytest.raises(TooManyRequestsException) as exc:
        check_ai_chat_rate_limit(client, "user1", now=3 * 60)
    assert "오늘" in exc.value.detail


def test_users_are_counted_separately():
    client = FakeRedis()
    for _ in range(2):
        check_ai_chat_rate_limit(client, "user1", now=0)

    check_ai_chat_rate_limit(client, "user2", now=0)


def test_zero_disables_limit(monkeypatch):
    monkeypatch.setenv("AI_CHAT_LIMIT_PER_MINUTE", "0")
    monkeypatch.setenv("AI_CHAT_LIMIT_PER_DAY", "0")
    client = FakeRedis()

    for _ in range(10):
        check_ai_chat_rate_limit(client, "user1", now=0)


def test_invalid_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("AI_CHAT_LIMIT_PER_MINUTE", "abc")
    client = FakeRedis()

    for _ in range(3):
        check_ai_chat_rate_limit(client, "user1", now=0)


def test_redis_failure_does_not_block_chat():
    check_ai_chat_rate_limit(FakeRedis(fail=True), "user1", now=0)
