from io import BytesIO

import pytest

from app.backend.exception.app_exceptions import ExternalServiceException
from app.backend.model.users import Users, Role
from app.backend.repository.messages_repository import list_messages_by_room
from app.backend.repository.uploaded_files_repository import list_uploaded_files
from app.backend.repository.user_repository import create_users
from app.backend.service.ai_chat_service import handle_chat_request_service
from app.backend.service.chat_room_service import post_chat_room_service


def make_user(login_id: str, password: str, email: str) -> Users:
    return Users(login_id=login_id, password=password, email=email, role=Role.USER)


class DummyUploadFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.file = BytesIO(content)


def test_handle_chat_request_service_without_real_pdf(db, monkeypatch):
    user = create_users(db, make_user("user1", "1234", "user1@example.com"))
    room = post_chat_room_service(db, user.id, "test", "test persona")

    dummy_file = DummyUploadFile("fake.pdf", b"not a real pdf")

    def fake_extract_text_from_file(file_path: str) -> str:
        return "이 문서는 파이썬 기초 문서입니다."

    def fake_request_chat_completion(messages: list[dict]) -> str:
        return "문서 요약 결과입니다."

    monkeypatch.setattr(
        "app.backend.service.ai_chat_service.extract_text_from_file",
        fake_extract_text_from_file,
    )
    monkeypatch.setattr(
        "app.backend.service.ai_chat_service.request_chat_completion",
        fake_request_chat_completion,
    )

    result = handle_chat_request_service(
        db,
        room.id,
        "이 문서를 요약해줘.",
        dummy_file,
    )

    assert result["room_id"] == room.id
    assert result["user_message"] == "이 문서를 요약해줘."
    assert result["uploaded_file_id"] is not None
    assert result["file_name"] == "fake.pdf"
    assert result["assistant_message"] == "문서 요약 결과입니다."
    messages = list_messages_by_room(db, room.id, offset=0, limit=100)
    assert len(messages) == 2


def test_handle_chat_request_service_rolls_back_when_ai_fails(db, monkeypatch, upload_dir):
    user = create_users(db, make_user("user1", "1234", "user1@example.com"))
    room = post_chat_room_service(db, user.id, "test", "test persona")

    dummy_file = DummyUploadFile("fake.pdf", b"not a real pdf")

    def fake_extract_text_from_file(file_path: str) -> str:
        return "이 문서는 파이썬 기초 문서입니다."

    def fake_request_chat_completion(messages: list[dict]) -> str:
        raise RuntimeError("openai failure")

    monkeypatch.setattr(
        "app.backend.service.ai_chat_service.extract_text_from_file",
        fake_extract_text_from_file,
    )
    monkeypatch.setattr(
        "app.backend.service.ai_chat_service.request_chat_completion",
        fake_request_chat_completion,
    )

    # RuntimeError → ExternalServiceException 으로 변환됨
    with pytest.raises(ExternalServiceException):
        handle_chat_request_service(
            db,
            room.id,
            "이 문서를 요약해줘.",
            dummy_file,
        )

    assert list_messages_by_room(db, room.id, offset=0, limit=100) == []
    assert list_uploaded_files(db, room.id, offset=0, limit=100) == []
    assert list(upload_dir.rglob("*")) == []


def test_follow_up_without_file_uses_room_document(db, monkeypatch, upload_dir):
    user = create_users(db, make_user("user1", "1234", "user1@example.com"))
    room = post_chat_room_service(db, user.id, "test", "test persona")
    sent: list[list[dict]] = []

    monkeypatch.setattr(
        "app.backend.service.ai_chat_service.extract_text_from_file",
        lambda file_path: "수행평가 제출 기한은 11월 28일입니다.",
    )

    def fake_request_chat_completion(messages: list[dict]) -> str:
        sent.append(messages)
        return "답변입니다."

    monkeypatch.setattr(
        "app.backend.service.ai_chat_service.request_chat_completion",
        fake_request_chat_completion,
    )

    handle_chat_request_service(db, room.id, "이 문서를 요약해줘.", DummyUploadFile("fake.pdf", b"pdf"))
    result = handle_chat_request_service(db, room.id, "제출 기한이 언제야?")

    assert result["uploaded_file_id"] is None
    contents = [str(m["content"]) for m in sent[-1]]
    assert any("수행평가 제출 기한은 11월 28일입니다." in content for content in contents)


def test_follow_up_without_file_uses_latest_room_document(db, monkeypatch, upload_dir):
    user = create_users(db, make_user("user1", "1234", "user1@example.com"))
    room = post_chat_room_service(db, user.id, "test", "test persona")
    sent: list[list[dict]] = []

    monkeypatch.setattr(
        "app.backend.service.ai_chat_service.extract_text_from_file",
        lambda file_path: f"{file_path.rsplit('_', 1)[-1]} 내용",
    )

    def fake_request_chat_completion(messages: list[dict]) -> str:
        sent.append(messages)
        return "답변입니다."

    monkeypatch.setattr(
        "app.backend.service.ai_chat_service.request_chat_completion",
        fake_request_chat_completion,
    )

    handle_chat_request_service(db, room.id, "첫 문서야.", DummyUploadFile("old.pdf", b"pdf"))
    handle_chat_request_service(db, room.id, "새 문서야.", DummyUploadFile("new.pdf", b"pdf"))
    handle_chat_request_service(db, room.id, "요약해줘.")

    contents = "\n".join(str(m["content"]) for m in sent[-1] if m["role"] == "system")
    assert "new.pdf 내용" in contents
    assert "old.pdf 내용" not in contents


def test_follow_up_without_file_skips_unreadable_room_document(db, monkeypatch, upload_dir):
    user = create_users(db, make_user("user1", "1234", "user1@example.com"))
    room = post_chat_room_service(db, user.id, "test", "test persona")
    sent: list[list[dict]] = []
    texts = iter(["첫 업로드 문서 내용"])

    def fake_extract_text_from_file(file_path: str) -> str:
        # 업로드 때는 읽히고, 이후에는 파일이 사라진 상황
        try:
            return next(texts)
        except StopIteration:
            raise ValueError("파일이 존재하지 않습니다.")

    def fake_request_chat_completion(messages: list[dict]) -> str:
        sent.append(messages)
        return "답변입니다."

    monkeypatch.setattr(
        "app.backend.service.ai_chat_service.extract_text_from_file",
        fake_extract_text_from_file,
    )
    monkeypatch.setattr(
        "app.backend.service.ai_chat_service.request_chat_completion",
        fake_request_chat_completion,
    )

    handle_chat_request_service(db, room.id, "이 문서를 요약해줘.", DummyUploadFile("fake.pdf", b"pdf"))
    result = handle_chat_request_service(db, room.id, "다음 질문이야.")

    assert result["assistant_message"] == "답변입니다."
    assert [m["role"] for m in sent[-1]].count("system") == 1
    assert len(list_messages_by_room(db, room.id, offset=0, limit=100)) == 4
