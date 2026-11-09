from io import BytesIO
from pathlib import Path

import pytest

from app.backend.exception import BadRequestException
from app.backend.model.users import Users, Role
from app.backend.service.uploaded_files_service import (
    patch_uploaded_files_service,
    post_uploaded_files_service,
    resolve_upload_path,
    save_upload_file_service,
)
from app.backend.service.chat_room_service import post_chat_room_service
from app.backend.repository.user_repository import create_users


def make_user(login_id: str, password: str, email: str) -> Users:
    return Users(login_id=login_id, password=password, email=email, role=Role.USER)


def test_post_uploaded_files_service(db):
    user = create_users(db, make_user('user1', '1234', 'user1@example.com'))
    room = post_chat_room_service(db, user.id, 'test', 'test persona')

    file_name = 'test.pdf'
    file_path = r'C:\dev'
    upload = post_uploaded_files_service(db, room.id, file_name, file_path)

    assert upload.id is not None
    assert upload.room_id == room.id
    assert upload.file_name == 'test.pdf'
    assert upload.file_path == r'C:\dev'


class DummyUploadFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.file = BytesIO(content)


def test_save_upload_file_service(db, upload_dir):
    user = create_users(db, make_user('user1', '1234', 'user1@example.com'))
    room = post_chat_room_service(db, user.id, 'test', 'test persona')

    dummy_file = DummyUploadFile("test.pdf", b"%PDF-1.4 test content")

    saved = save_upload_file_service(db, room.id, dummy_file)

    assert saved.id is not None
    assert saved.room_id == room.id
    assert saved.file_name == "test.pdf"
    assert saved.file_path is not None
    assert Path(saved.file_path).exists()
    # 실행 위치(cwd)와 상관없이 읽히도록 절대 경로로 저장한다
    assert Path(saved.file_path).is_absolute()
    assert Path(saved.file_path).parent == upload_dir / str(room.id)


def test_save_upload_file_service_strips_folder_from_file_name(db, upload_dir):
    user = create_users(db, make_user('user1', '1234', 'user1@example.com'))
    room = post_chat_room_service(db, user.id, 'test', 'test persona')

    saved = save_upload_file_service(db, room.id, DummyUploadFile("../../evil.pdf", b"%PDF-1.4"))

    assert Path(saved.file_path).parent == upload_dir / str(room.id)
    assert saved.file_path.endswith("_evil.pdf")


def test_resolve_upload_path_reads_legacy_relative_path(upload_dir, monkeypatch):
    # 예전 행은 프로젝트 루트 기준 'uploads/13/...'로 저장돼 있다
    monkeypatch.setattr("app.backend.service.uploaded_files_service.PROJECT_ROOT", upload_dir.parent)

    assert resolve_upload_path(13, "uploads/13/old.pdf") == upload_dir / "13" / "old.pdf"


@pytest.mark.parametrize("file_path", [
    "/etc/passwd",
    "uploads/14/other_room.pdf",
    "uploads/13/../14/other_room.pdf",
])
def test_resolve_upload_path_rejects_outside_room(file_path):
    with pytest.raises(ValueError):
        resolve_upload_path(13, file_path)


def test_patch_uploaded_files_service_rejects_outside_room(db, upload_dir):
    user = create_users(db, make_user('user1', '1234', 'user1@example.com'))
    room = post_chat_room_service(db, user.id, 'test', 'test persona')
    saved = save_upload_file_service(db, room.id, DummyUploadFile("test.pdf", b"%PDF-1.4"))

    with pytest.raises(BadRequestException):
        patch_uploaded_files_service(db, room.id, saved.id, "x.pdf", str(upload_dir / "999" / "x.pdf"))
