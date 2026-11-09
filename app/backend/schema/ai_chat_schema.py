from pydantic import BaseModel

# Ai 채팅 응답 스키마
class AiChatResponse(BaseModel):
    room_id: int
    user_message: str
    assistant_message: str
    uploaded_file_id: int | None = None
    file_name: str | None = None
    # 대화방 문서를 읽지 못해 문서 없이 답했을 때 사용자에게 보여 줄 안내
    document_notice: str | None = None