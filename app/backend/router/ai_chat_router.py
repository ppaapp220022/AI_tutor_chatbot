from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.backend.database import get_db, redis_client
from app.backend.dependencies import get_current_users
from app.backend.schema.ai_chat_schema import AiChatResponse
from app.backend.service.ai_chat_service import handle_chat_request_service
from app.backend.service.rate_limit_service import check_ai_chat_rate_limit

router = APIRouter(
    prefix="/chat-rooms/{room_id}/AiChat",
    tags=["ai_chat"],
)

@router.post("",
             response_model=AiChatResponse,
             status_code=status.HTTP_200_OK,
             summary="AI 채팅 시작",
             description="AI 채팅 객체를 생성합니다. 사용자별 요청 횟수를 넘으면 429를 돌려줍니다."
             )
def chat_with_ai(
    room_id: int,
    message: str = Form(...),
    file: UploadFile | None = File(None),
    login_id: str = Depends(get_current_users),
    db: Session = Depends(get_db),
):
    """
    AI 채팅 요청 API
    :param room_id: 대화방 PK
    :param message: 사용자 메시지
    :param file: 업로드 파일
    :param login_id: 현재 로그인 아이디
    :param db: 세션
    :return: AI 응답 결과
    """
    check_ai_chat_rate_limit(redis_client, login_id)
    return handle_chat_request_service(db, room_id, message, file, login_id=login_id)