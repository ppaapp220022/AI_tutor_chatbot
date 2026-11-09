import os
from pathlib import Path
from uuid import uuid4
from sqlalchemy.exc import SQLAlchemyError

from app.backend.exception import BadRequestException, DatabaseException, NotFoundException
from app.backend.repository.uploaded_files_repository import (
    count_uploaded_files_by_room,
    create_uploaded_files,
    list_uploaded_files,
    find_latest_uploaded_file,
    find_uploaded_files,
    update_uploaded_files,
    delete_uploaded_files
)
from app.backend.repository.chat_room_repository import find_chat_room
from app.backend.schema.base_schema import PaginationRequest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
# 실행 위치(cwd)와 상관없이 같은 폴더를 쓰도록 절대 경로로 고정한다. 상대 경로를 주면 프로젝트 루트 기준이다
UPLOAD_DIR = (PROJECT_ROOT / os.getenv("UPLOAD_DIR", "uploads")).resolve()


def resolve_upload_path(room_id: int, file_path: str) -> Path:
    """
    DB에 저장된 업로드 경로를 실제 파일 경로로 바꾼다
    예전 행은 'uploads/13/...'처럼 상대 경로라 프로젝트 루트 기준으로 해석한다
    :param room_id: 대화방 PK
    :param file_path: 저장된 파일 경로
    :return: 해당 대화방 업로드 폴더 안의 절대 경로
    """
    room_dir = UPLOAD_DIR / str(room_id)
    path = (PROJECT_ROOT / file_path).resolve()  # file_path가 절대 경로면 그대로 쓰인다
    if not path.is_relative_to(room_dir):
        # 다른 대화방이나 업로드 폴더 밖의 파일을 읽지 못하게 막는다
        raise ValueError("대화방 업로드 폴더 밖의 파일입니다.")
    return path

# 파일 업로드 저장소 생성
def post_uploaded_files_service(
    db,
    room_id: int,
    file_name: str,
    file_path: str,
    commit: bool = True,
    login_id: str | None = None,
):
    """
    업로드 파일 메타데이터 생성 서비스
    :param db: 세션
    :param room_id: 대화방 PK
    :param file_name: 파일명
    :param file_path: 파일 경로
    :param commit: db 업로드 여부
    :param login_id: 로그인 아이디
    :return: 생성된 업로드 파일 정보
    """
    if not room_id:
        raise BadRequestException("채팅방을 확인 할 수 없습니다.")

    room = find_chat_room(db, room_id, login_id=login_id)
    if not room:
        raise NotFoundException("채팅방이 존재하지 않습니다.")

    try:
        uploaded = create_uploaded_files(db, room_id, file_name, file_path)

        if commit:
            db.commit()
            db.refresh(uploaded)

        return uploaded
    except SQLAlchemyError:
        db.rollback()
        raise DatabaseException("업로드 파일 정보 저장 중 데이터베이스 오류가 발생했습니다.")

def save_upload_file_service(db, room_id: int, upload_file, commit: bool = True, login_id: str | None = None):
    """
    업로드 파일 저장 서비스
    :param db: 세션
    :param room_id: 대화방 PK
    :param upload_file: 업로드 파일
    :param commit: db 업로드
    :param login_id: 로그인 아이디
    :return: 저장된 업로드 파일 정보
    """
    if not room_id:
        raise BadRequestException("채팅방을 확인할 수 없습니다.")

    room = find_chat_room(db, room_id, login_id=login_id)
    if not room:
        raise NotFoundException("채팅방이 존재하지 않습니다.")

    if not upload_file or not getattr(upload_file, "filename", None):
        raise BadRequestException("업로드 파일이 없습니다.")

    original_name = upload_file.filename
    if not original_name.lower().endswith(".pdf"):
        raise BadRequestException("pdf 파일만 업로드할 수 있습니다.")

    file_bytes = upload_file.file.read()
    if not file_bytes:
        raise BadRequestException("업로드 파일 내용이 비어 있습니다.")

    room_dir = UPLOAD_DIR / str(room_id)
    room_dir.mkdir(parents=True, exist_ok=True)

    # 파일명에 섞인 폴더 경로('../' 등)는 버린다
    stored_name = f"{uuid4()}_{Path(original_name).name}"
    stored_path = room_dir / stored_name

    try:
        with open(stored_path, "wb") as file_object:
            file_object.write(file_bytes)

        uploaded = post_uploaded_files_service(
            db,
            room_id=room_id,
            file_name=original_name,
            file_path=str(stored_path),
            commit=commit,
            login_id=login_id,
        )
        return uploaded
    except Exception:
        if stored_path.exists():
            stored_path.unlink()
        raise

# 파일 업로드 목록
def get_all_uploaded_files_service(db, room_id: int, pagination: PaginationRequest, login_id: str | None = None):
    """
    업로드 파일 목록 조회 서비스
    :param db: 세션
    :param room_id: 대화방 PK
    :param pagination: 페이징 정보
    :param login_id: 로그인 아이디
    :return: 업로드 파일 목록
    """
    room = find_chat_room(db, room_id, login_id=login_id)
    if not room:
        raise NotFoundException("채팅방이 존재하지 않습니다.")

    total = count_uploaded_files_by_room(db, room_id)
    items = list_uploaded_files(db, room_id, pagination.offset, pagination.size)

    return {
        "items": items,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
    }

# 대화방의 가장 최근 업로드 파일
def get_latest_uploaded_file_service(db, room_id: int, login_id: str | None = None):
    """
    대화방에 가장 최근 업로드된 파일 조회 서비스
    :param db: 세션
    :param room_id: 대화방 PK
    :param login_id: 로그인 아이디
    :return: 가장 최근 업로드 파일 정보. 없으면 None
    """
    room = find_chat_room(db, room_id, login_id=login_id)
    if not room:
        raise NotFoundException("채팅방이 존재하지 않습니다.")

    return find_latest_uploaded_file(db, room_id)

# 파일 업로드 단건 검색
def get_one_uploaded_files_service(db, uploaded_id: int):
    """
    업로드 파일 단건 조회 서비스
    :param db: 세션
    :param uploaded_id: 업로드 파일 PK
    :return: 조회된 업로드 파일 정보
    """
    uploaded = find_uploaded_files(db, uploaded_id)

    if not uploaded:
        raise NotFoundException("업로드한 파일이 1건도 확인되지 않습니다.")

    return uploaded

# 파일 업로드 수정
def patch_uploaded_files_service(db, room_id: int, uploaded_id: int, new_file_name: str, new_file_path: str):
    """
    업로드 파일 수정 서비스
    :param db: 세션
    :param room_id: 대화방 PK
    :param uploaded_id: 업로드 파일 PK
    :param new_file_name: 수정할 파일명
    :param new_file_path: 수정할 파일 경로
    :return: 수정된 업로드 파일 정보
    """
    try:
        resolved_path = resolve_upload_path(room_id, new_file_path)
    except ValueError as exc:
        raise BadRequestException(str(exc)) from exc

    try:
        uploaded = update_uploaded_files(db, uploaded_id, new_file_name, str(resolved_path))

        if not uploaded:
            raise NotFoundException("수정할 업로드 파일이 존재하지 않습니다.")

        db.commit()
        db.refresh(uploaded)
        return uploaded
    except NotFoundException:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise DatabaseException("업로드 파일 수정 중 데이터베이스 오류가 발생했습니다.")

# 파일 업로드 삭제
def delete_uploaded_files_service(db, uploaded_id: int):
    """
    업로드 파일 삭제 서비스
    :param db: 세션
    :param uploaded_id: 업로드 파일 PK
    :return: 삭제 여부
    """
    try:
        uploaded = find_uploaded_files(db, uploaded_id)

        if not uploaded:
            raise NotFoundException("삭제할 업로드 파일이 존재하지 않습니다.")

        delete_uploaded_files(db, uploaded_id)
        db.commit()
        return True
    except NotFoundException:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise DatabaseException("업로드 파일 삭제 중 데이터베이스 오류가 발생했습니다.")
