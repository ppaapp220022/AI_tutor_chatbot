from pathlib import Path
from typing import Literal

from loguru import logger
from openai import OpenAIError
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from sqlalchemy.exc import SQLAlchemyError

from app.backend.exception import (
    BadRequestException,
    DatabaseException,
    ExternalServiceException,
    NotFoundException,
)
from app.backend.model.messages import Messages
from app.backend.model.messages import Role
from app.backend.repository.chat_room_repository import find_chat_room
from app.backend.service.ai_client_service import request_chat_completion
from app.backend.service.document_context_service import select_document_context
from app.backend.service.file_parser_service import extract_text_from_file
from app.backend.service.messages_service import (
    get_message_history_service,
    post_messages_service,
)
from app.backend.service.uploaded_files_service import (
    get_latest_uploaded_file_service,
    resolve_upload_path,
    save_upload_file_service,
)

DEFAULT_PERSONA = "일반 튜터"

BASE_SYSTEM_PROMPT = (
    "당신은 업로드된 PDF 문서와 대화 문맥을 바탕으로 답변하는 AI 튜터입니다. "
    "당신은 전문적인 지식을 사용자가 이해하기 쉽게 설명해야 하고, "
    "사용자가 원하는 지식을 습득하기 위해 최선의 노력을 해야합니다. "
    "필요하다면 추가적인 질문을 계속 사용자에게 요구하세요. "
    "업로드된 문서가 있으면 문서 내용을 답변의 근거로 삼으세요. "
    "질문한 내용이 문서에 없으면 먼저 '문서에는 해당 내용이 없다'고 분명히 밝히세요. "
    "그 뒤 일반 지식으로 보충할 때는 문서 내용이 아니라는 것을 구분해서 말하고, "
    "확실하지 않은 인물·연도·수치는 지어내지 말고 모른다고 답하세요."
)

PERSONA_PROMPT_MAP: dict[str, str] = {
    DEFAULT_PERSONA: (
        f"{BASE_SYSTEM_PROMPT} "
        "특정 과목에 치우치지 말고, 학습자의 수준을 먼저 파악한 뒤 차분하고 균형 있게 설명하세요."
    ),
    "수학 전문가": (
        f"{BASE_SYSTEM_PROMPT} "
        "수학 개념, 공식, 풀이 과정을 단계별로 설명하고 계산 근거를 분명히 제시하세요. "
        "정답만 주지 말고 왜 그런 풀이를 선택했는지 함께 설명하세요."
    ),
    "영어 전문가": (
        f"{BASE_SYSTEM_PROMPT} "
        "영어 문법, 어휘, 독해, 작문을 중심으로 설명하고 필요한 경우 예문과 자연스러운 표현을 함께 제시하세요. "
        "틀린 표현은 부드럽게 교정하고, 한국어 설명과 영어 예문을 균형 있게 사용하세요. "
        "교정할 때는 고친 문장, 같은 문법을 쓴 새 영어 예문 하나 이상(고친 문장을 다시 쓴 것은 예문이 아니다), "
        "한국어 설명을 빠짐없이 모두 넣으세요."
    ),
    "과학 전문가": (
        f"{BASE_SYSTEM_PROMPT} "
        "과학 개념과 현상을 원리 중심으로 설명하고, 실생활 예시와 함께 오개념을 바로잡아 주세요. "
        "과정과 인과관계를 분명하게 풀어 설명하세요."
    ),
    "역사 전문가": (
        f"{BASE_SYSTEM_PROMPT} "
        "역사적 사건의 배경, 전개, 결과를 시간 흐름에 맞춰 설명하고 문서에 나온 주요 인물과 맥락을 함께 연결해 주세요. "
        "단편 암기보다 흐름 이해를 돕는 방식으로 답변하세요. "
        "문서에 나온 용어나 목록의 각 항목에 문서에 없는 뜻풀이·한자·세부 설명을 덧붙이지 말고, "
        "사용자가 따로 물으면 그때 '일반 지식'이라고 밝힌 뒤 설명하세요. "
        "사건의 원인·목적·제도의 내용도 문서에 적힌 만큼만 말하세요. "
        "문서가 '어떤 제도를 실시하여 무엇을 이루었다'고만 쓰면, 그 제도가 무엇인지·왜 실시했는지·누구에게 무엇을 주었는지를 짐작해 덧붙이지 마세요. "
        "문서에 없는 인물 이름은 목록으로 늘어놓지 말고, 교과서나 선생님께 확인하도록 안내하세요."
    ),
}

MAX_FILE_CONTEXT_LENGTH = 12000
FILE_CONTEXT_HEADER = "[업로드된 PDF 문서 내용]"
# 문서가 길어 일부만 넣었을 때 모델이 '문서에 없다'고 단정하지 않게 알린다
PARTIAL_FILE_CONTEXT_HEADER = (
    "[업로드된 PDF 문서 내용 — 문서가 길어 질문과 관련된 부분만 담았고, 빠진 부분은 '…(중략)…'으로 표시했다]"
)
MAX_HISTORY_COUNT = 20
# 대화방 문서를 읽지 못했을 때 모델에게 알린다. 없으면 '문서에 없다'고 단정하거나 내용을 짐작해 답한다
DOCUMENT_UNREADABLE_PROMPT = (
    "[업로드된 PDF 문서를 읽지 못함] 이 대화방에 올린 문서를 지금 읽을 수 없어 문서 내용을 보내지 못했다. "
    "그래서 이번 답변에는 '문서에는 해당 내용이 없다'는 규칙을 쓰지 않는다. 문서에 없는지 알 수 없기 때문이다. "
    "이 대화방에서 나오는 학습·과제·평가에 관한 질문은 올린 문서에 관한 질문으로 본다. "
    "그런 질문이면 '올린 문서를 지금 읽지 못해 확인할 수 없다'고 먼저 밝히고 문서를 다시 올려 달라고 안내하라. "
    "일반적인 예시나 목록으로 답을 대신하지 마라. "
    "문서 내용을 짐작해서 지어내지 마라. 이전 대화에서 이미 답한 문서 내용은 다시 말해도 된다."
)
ROOM_DOCUMENT_UNREADABLE_NOTICE = "이 대화방에 올린 문서({file_name})를 읽지 못해 문서 없이 답했습니다. 문서를 다시 올려 주세요."


def get_available_personas() -> list[str]:
    """
    현재 페르소나 목록 반환
    :return: 페르소나 이름 목록
    """
    return list(PERSONA_PROMPT_MAP.keys())

def _cleanup_uploaded_file(uploaded) -> None:
    """
    업로드 실패 시 저장된 파일과 빈 부모 폴더를 정리
    :param uploaded: 저장된 업로드 파일 정보
    :return: 없음
    """
    if not uploaded or not uploaded.file_path:
        return

    uploaded_path = Path(uploaded.file_path)
    if uploaded_path.exists():
        uploaded_path.unlink()

    parent_dir = uploaded_path.parent
    if parent_dir.exists() and not any(parent_dir.iterdir()):
        parent_dir.rmdir()

def _load_room_file_text(db, room_id: int, login_id: str | None) -> tuple[str, str | None]:
    """
    파일 없이 온 질문에 쓸 대화방 문서 텍스트. 가장 최근 업로드 파일만 쓴다
    (파일을 올린 요청도 그 파일 하나만 쓰므로 이어지는 질문도 같은 문서를 보게 한다)
    :param db: 세션
    :param room_id: 대화방 PK
    :param login_id: 로그인 아이디
    :return: (문서 텍스트, 사용자 안내). 파일이 없으면 ("", None), 읽지 못하면 ("", 안내 문구)
    """
    latest = get_latest_uploaded_file_service(db, room_id, login_id=login_id)
    if not latest or not latest.file_path:
        return "", None
    try:
        return extract_text_from_file(str(resolve_upload_path(room_id, latest.file_path))), None
    except ValueError as exc:
        # 이번 요청에 올린 파일이 아니므로 질문 자체는 막지 않고 문서 없이 답하되, 사용자에게 알린다
        logger.warning(f"대화방 문서를 읽지 못함 - room_id: {room_id}, uploaded_id: {latest.id}, {exc}")
        return "", ROOM_DOCUMENT_UNREADABLE_NOTICE.format(file_name=latest.file_name)

def _to_openai_role(role: Role) -> Literal["user", "assistant"]: # 반환값은 user, assistent 만 가질 수 있도록 명시
    """
    메시지 역할을 OpenAI 역할 형식으로 변환
    :param role: 메시지 역할
    :return: OpenAI 역할 문자열
    """
    if role == Role.USER:
        return "user"
    return "assistant"

def _build_system_prompt(persona: str | None) -> str:
    """
    채팅방 페르소나에 맞는 시스템 프롬프트를 생성
    :param persona: 채팅방에 저장된 페르소나
    :return: 시스템 프롬프트
    """
    normalized_persona = (persona or DEFAULT_PERSONA).strip() or DEFAULT_PERSONA
    prompt = PERSONA_PROMPT_MAP.get(normalized_persona)
    if prompt:
        return prompt
    return (
        f"{PERSONA_PROMPT_MAP[DEFAULT_PERSONA]} "
        f"현재 페르소나는 '{normalized_persona}'이며, 그 성격에 맞는 말투와 설명 방식을 최대한 반영하세요."
    )

def build_openai_messages(
    history: list[Messages],
    user_message: str,
    file_text: str = "",
    persona: str | None = None,
    document_unreadable: bool = False,
) -> list[ChatCompletionMessageParam]: # OpenAI에서 채팅타입을 명시 해줌
    """
    OpenAI 요청용 메시지 배열 생성
    :param history: 기존 대화 이력
    :param user_message: 현재 사용자 메시지
    :param file_text: 업로드 파일 텍스트
    :param persona: 채팅방 페르소나
    :param document_unreadable: 대화방 문서를 읽지 못했는지 여부
    :return: OpenAI 요청 메시지 목록
    """
    messages: list[ChatCompletionMessageParam] = []

    system_prompt = _build_system_prompt(persona)

    system_message: ChatCompletionSystemMessageParam = {
        "role": "system",
        "content": system_prompt,
    }
    messages.append(system_message)

    if file_text:
        # 이어지는 질문('그건 언제까지야?')도 찾을 수 있게 직전 사용자 질문을 함께 쓴다
        previous_questions = [m.content for m in history if _to_openai_role(m.role) == "user"][-1:]
        query = "\n".join([*previous_questions, user_message])
        document = select_document_context(file_text, query, MAX_FILE_CONTEXT_LENGTH)
        header = FILE_CONTEXT_HEADER if document == file_text else PARTIAL_FILE_CONTEXT_HEADER
        file_message: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": f"{header}\n{document}",
        }
        messages.append(file_message)

    for history_message in history[-MAX_HISTORY_COUNT:]:
        if _to_openai_role(history_message.role) == "user":
            user_chat_message: ChatCompletionUserMessageParam = {
                "role": "user",
                "content": history_message.content,
            }
            messages.append(user_chat_message)
        else:
            assistant_chat_message: ChatCompletionAssistantMessageParam = {
                "role": "assistant",
                "content": history_message.content,
            }
            messages.append(assistant_chat_message)

    if document_unreadable and not file_text:
        # 이전 대화에서 문서로 답한 흐름을 이어 가지 않도록, 지금 질문 바로 앞에 둔다
        unreadable_message: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": DOCUMENT_UNREADABLE_PROMPT,
        }
        messages.append(unreadable_message)

    user_message_param: ChatCompletionUserMessageParam = {
        "role": "user",
        "content": user_message,
    }
    messages.append(user_message_param)
    return messages

def handle_chat_request_service(
    db,
    room_id: int,
    user_message: str,
    upload_file=None,
    login_id: str | None = None,
) -> dict:
    """
    채팅 요청 처리 서비스
    :param db: 세션
    :param room_id: 대화방 PK
    :param user_message: 사용자 메시지
    :param upload_file: 업로드 파일
    :param login_id: 로그인 아이디
    :return: AI 응답 결과
    """
    if not room_id:
        raise BadRequestException("채팅방을 확인할 수 없습니다.")

    if not user_message or not user_message.strip():
        raise BadRequestException("사용자 메시지가 비어 있습니다.")

    room = find_chat_room(db, room_id, login_id=login_id)
    if not room:
        raise NotFoundException("채팅방이 존재하지 않습니다.")

    uploaded = None
    file_text = ""
    document_notice = None

    try:
        if upload_file is not None:
            uploaded = save_upload_file_service(db, room_id, upload_file, commit=False, login_id=login_id)
            try:
                file_text = extract_text_from_file(str(resolve_upload_path(room_id, uploaded.file_path)))
            except ValueError as exc:
                raise BadRequestException(str(exc)) from exc
        else:
            file_text, document_notice = _load_room_file_text(db, room_id, login_id)

        history = get_message_history_service(db, room_id, MAX_HISTORY_COUNT, login_id=login_id)

        openai_messages = build_openai_messages(
            history, user_message.strip(), file_text, room.persona, document_unreadable=document_notice is not None
        )

        post_messages_service(db, room_id, Role.USER, user_message.strip(), commit=False, login_id=login_id)

        assistant_message = request_chat_completion(openai_messages)

        if not assistant_message:
            raise ExternalServiceException("AI 응답을 생성하지 못했습니다.")

        post_messages_service(db, room_id, Role.Assistant, assistant_message, commit=False, login_id=login_id)
        db.commit()
    except (BadRequestException, NotFoundException):
        db.rollback()
        _cleanup_uploaded_file(uploaded)
        raise
    except OpenAIError as exc:
        db.rollback()
        _cleanup_uploaded_file(uploaded)
        raise ExternalServiceException(str(exc)) from exc
    except ExternalServiceException:
        db.rollback()
        _cleanup_uploaded_file(uploaded)
        raise
    except SQLAlchemyError:
        db.rollback()
        _cleanup_uploaded_file(uploaded)
        raise DatabaseException("채팅 처리 중 데이터베이스 오류가 발생했습니다.")
    except Exception:
        db.rollback()
        _cleanup_uploaded_file(uploaded)
        raise ExternalServiceException("AI 응답 처리 중 서버 오류가 발생했습니다.")

    return {
        "room_id": room_id,
        "user_message": user_message.strip(),
        "assistant_message": assistant_message,
        "uploaded_file_id": uploaded.id if uploaded else None,
        "file_name": uploaded.file_name if uploaded else None,
        "document_notice": document_notice,
    }
