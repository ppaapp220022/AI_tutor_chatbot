from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.backend.database import get_db
from app.backend.dependencies import get_current_users
from app.backend.exception import NotFoundException
from app.backend.repository.chat_room_repository import find_chat_room
from app.backend.schema.base_schema import PaginationRequest
from app.backend.schema.uploaded_files_schema import (
    UploadedFilePageResponse,
    UploadedFileUpdateRequest,
    UploadedFileResponse,
)
from app.backend.service.uploaded_files_service import (
    delete_uploaded_files_service,
    get_one_uploaded_files_service,
    get_all_uploaded_files_service,
    patch_uploaded_files_service,
    save_upload_file_service,
)

router = APIRouter(
    prefix="/chat-rooms/{room_id}/uploaded",
    tags=["uploaded_files"],
)

@router.post("",
             response_model=UploadedFileResponse,
             status_code=status.HTTP_201_CREATED,
             summary="파일 업로드 생성",
             description="파일 업로드 객체를 생성합니다."
             )
def create_uploaded_files(
    room_id: int,
    file: UploadFile = File(...),
    login_id: str = Depends(get_current_users),
    db: Session = Depends(get_db),
):
    """
    파일업로드 생성 API
    :param room_id: 대화방 PK
    :param file: 업로드 파일
    :param login_id: 현재 로그인 아이디
    :param db: 세션
    :return: 생성된 파일업로드
    """
    return save_upload_file_service(db, room_id, file, login_id=login_id)

@router.get("",
            response_model=UploadedFilePageResponse,
            summary="파일 목록 조회",
            description="업로드된 파일 목록을 조회 합니다."
            )
def get_all_uploaded_files(
    room_id: int,
    pagination: PaginationRequest = Depends(),
    login_id: str = Depends(get_current_users),
    db: Session = Depends(get_db)
):
    """
    파일업로드 목록 조회 API
    :param room_id: 대화방 PK
    :param pagination: 페이징 정보
    :param login_id: 현재 로그인 아이디
    :param db: 세션
    :return: 파일업로드 목록
    """
    return get_all_uploaded_files_service(db, room_id, pagination, login_id=login_id)

@router.get("/{uploaded_id}",
            response_model=UploadedFileResponse,
            summary="업로드 파일 조회",
            description="업로드 된 파일을 조회합니다."
            )
def get_one_uploaded_file(
    room_id: int,
    uploaded_id: int,
    login_id: str = Depends(get_current_users),
    db: Session = Depends(get_db),
):
    """
    파일 업로드 단건 조회 API
    :param room_id: 대화방 PK
    :param uploaded_id: 파일업로드 PK
    :param login_id: 현재 로그인 아이디
    :param db: 세션
    :return: 조회된 파일
    """
    room = find_chat_room(db, room_id, login_id=login_id)
    if not room:
        raise NotFoundException("채팅방이 존재하지 않습니다.")
    uploaded = get_one_uploaded_files_service(db, uploaded_id)
    if uploaded.room_id != room_id:
        raise NotFoundException("업로드된 파일이 해당 채팅방에 존재하지 않습니다.")
    return uploaded

@router.patch("/{uploaded_id}",
              response_model=UploadedFileResponse,
              summary="업로드 파일 수정",
              description="업로드 된 파일을 수정합니다."
              )
def update_uploaded_file(
    room_id: int,
    uploaded_id: int,
    request: UploadedFileUpdateRequest,
    login_id: str = Depends(get_current_users),
    db: Session = Depends(get_db),
):
    """
    파일업로드 수정 API
    :param room_id: 대화방 PK
    :param uploaded_id: 파일업로드 PK
    :param request: 파일 업로드 수정 요청
    :param login_id: 현재 로그인 아이디
    :param db: 세션
    :return: 수정된 파일
    """
    room = find_chat_room(db, room_id, login_id=login_id)
    if not room:
        raise NotFoundException("채팅방이 존재하지 않습니다.")
    uploaded = get_one_uploaded_files_service(db, uploaded_id)
    if uploaded.room_id != room_id:
        raise NotFoundException("수정할 파일 대상이 해당 채팅방에 존재하지 않습니다.")
    if not request.file_name or not request.file_path:
        raise ValueError('파일 이름과 경로는 필수 값입니다.')
    return patch_uploaded_files_service(db, room_id, uploaded_id, request.file_name, request.file_path)

@router.delete("/{uploaded_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="업로드 파일 삭제",
               description="업로드 된 파일을 삭제합니다."
               )
def delete_uploaded_file(
    room_id: int,
    uploaded_id: int,
    login_id: str = Depends(get_current_users),
    db: Session = Depends(get_db),
):
    """
    파일업로드 삭제 API
    :param room_id: 대화방 PK
    :param uploaded_id: 파일업로드 PK
    :param login_id: 현재 로그인 아이디
    :param db: 세션
    :return: 없음
    """
    room = find_chat_room(db, room_id, login_id=login_id)
    if not room:
        raise NotFoundException("채팅방이 존재하지 않습니다.")
    uploaded = get_one_uploaded_files_service(db, uploaded_id)
    if uploaded.room_id != room_id:
        raise NotFoundException("해당 채팅방에 업로드된 파일이 존재하지 않습니다.")
    delete_uploaded_files_service(db, uploaded_id)