from sqlalchemy import func
from sqlalchemy.orm import Session

from app.backend.model.uploaded_files import UploadedFiles
from loguru import logger

def create_uploaded_files(db: Session, room_id: int, file_name: str, file_path: str) -> UploadedFiles:
    """
    업로드 파일 생성
    :param db: DB 세션
    :param room_id: 대화방 번호
    :param file_name: 파일명
    :param file_path: 파일 경로
    :return: 생성된 업로드 파일
    """
    logger.info(f"업로드 파일 생성 요청 - room_id: {room_id}, file_name: {file_name}, file_path: {file_path}")
    uploaded = UploadedFiles(room_id=room_id, file_name=file_name, file_path=file_path)
    db.add(uploaded)
    db.flush()
    db.refresh(uploaded)
    logger.info(f"파일 업로드 완료 - id: {uploaded.id}, room_id: {uploaded.room_id}")
    return uploaded

def list_uploaded_files(db: Session, room_id: int, offset: int, limit: int) -> list[UploadedFiles]:
    """
    대화방별 업로드 파일 목록 조회
    :param db: DB 세션
    :param room_id: 대화방 번호
    :param offset: 조회 시작 위치
    :param limit: 조회 건수
    :return: 업로드 파일 목록
    """
    logger.info(f"업로드 파일 목록 조회 요청 - room_id: {room_id}")
    uploaded = (
        db.query(UploadedFiles)
        .filter(UploadedFiles.room_id == room_id)
        .order_by(UploadedFiles.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    logger.info(f"업로드 파일 목록 조회 완료 - room_id: {room_id}, count: {len(uploaded)}")
    return uploaded

def count_uploaded_files_by_room(db: Session, room_id: int) -> int:
    """
    대화방별 업로드 파일 전체 건수 카운트(페이징)
    :param db: DB 세션
    :param room_id: 대화방 번호
    :return: 업로드 파일 전체 건수
    """
    return db.query(func.count(UploadedFiles.id)).filter(UploadedFiles.room_id == room_id).scalar() or 0

def find_latest_uploaded_file(db: Session, room_id: int) -> UploadedFiles | None:
    """
    대화방에 가장 최근 업로드된 파일 조회
    :param db: DB 세션
    :param room_id: 대화방 번호
    :return: 가장 최근 업로드 파일. 없으면 None
    """
    return (
        db.query(UploadedFiles)
        .filter(UploadedFiles.room_id == room_id)
        .order_by(UploadedFiles.id.desc())
        .first()
    )

def find_uploaded_files(db: Session, uploaded_id: int) -> UploadedFiles | None:
    """
    업로드 파일 단건 조회
    :param db: DB 세션
    :param uploaded_id: 업로드 파일 번호
    :return: 업로드 파일
    """
    logger.info(f"업로드 파일 단건 조회 요청 - uploaded_id: {uploaded_id}")
    uploaded = db.query(UploadedFiles).filter(UploadedFiles.id == uploaded_id).first()

    if not uploaded:
        logger.warning(f"업로드 파일이 조회되지 않습니다. uploaded_id: {uploaded_id}")
        return None

    logger.info(f"업로드 파일 단건 조회 완료 - id: {uploaded.id}, room_id: {uploaded.room_id}")
    return uploaded

def update_uploaded_files(db: Session, uploaded_id: int, new_file_name: str, new_file_path: str) -> UploadedFiles | None:
    """
    업로드 파일 정보 수정
    :param db: DB 세션
    :param uploaded_id: 업로드 파일 번호
    :param new_file_name: 변경할 파일명
    :param new_file_path: 변경할 파일 경로
    :return: 변경된 업로드 파일
    """
    logger.info(f"업로드 파일 수정 요청 - uploaded_id: {uploaded_id}")
    uploaded = find_uploaded_files(db, uploaded_id)

    if not uploaded:
        logger.warning(f"수정할 업로드 파일이 없습니다. uploaded_id: {uploaded_id}")
        return None

    if new_file_name:
        uploaded.file_name = new_file_name

    if new_file_path:
        uploaded.file_path = new_file_path

    db.flush()
    db.refresh(uploaded)
    logger.info(f"업로드 파일 수정 완료 - "
                f"id: {uploaded.id}, "
                f"file_name: {uploaded.file_name}, "
                f"file_path: {uploaded.file_path}")
    return uploaded

def delete_uploaded_files(db: Session, uploaded_id: int) -> bool:
    """
    업로드 파일 삭제
    :param db: DB 세션
    :param uploaded_id: 업로드 파일 번호
    :return: 삭제 성공 여부
    """
    logger.info(f"업로드 파일 삭제 요청 - uploaded_id: {uploaded_id}")
    uploaded = find_uploaded_files(db, uploaded_id)

    if not uploaded:
        logger.warning(f"삭제할 업로드 파일이 없습니다. uploaded_id: {uploaded_id}")
        return False

    db.delete(uploaded)
    db.flush()
    logger.info(f"업로드 파일 삭제 완료 - uploaded_id: {uploaded_id}")
    return True