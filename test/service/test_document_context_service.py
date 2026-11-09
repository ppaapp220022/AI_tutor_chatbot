from app.backend.model.messages import Messages, Role
from app.backend.service.ai_chat_service import (
    FILE_CONTEXT_HEADER,
    MAX_FILE_CONTEXT_LENGTH,
    PARTIAL_FILE_CONTEXT_HEADER,
    build_openai_messages,
)
from app.backend.service.document_context_service import OMITTED_MARK, select_document_context


def make_long_document() -> str:
    filler = "\n".join(f"{i}번째 줄은 단원 개요와 일반 설명을 담은 문장입니다." for i in range(2000))
    return (
        "학습지 제목: 2학기 통합 학습지\n"
        f"{filler}\n"
        "동아리 발표회는 12월 5일 강당에서 열린다.\n"
        f"{filler}"
    )


def test_short_document_is_returned_as_is():
    text = "짧은 문서입니다."

    assert select_document_context(text, "질문", 100) == text


def test_long_document_keeps_relevant_part_within_limit():
    text = make_long_document()

    selected = select_document_context(text, "동아리 발표회는 언제 어디서 해?", 3000)

    assert len(selected) <= 3000
    assert "동아리 발표회는 12월 5일 강당에서 열린다." in selected
    assert selected.startswith("학습지 제목: 2학기 통합 학습지")
    assert OMITTED_MARK in selected


def test_selected_chunks_keep_original_order():
    text = "\n".join(f"{i}장: " + "가" * 900 for i in range(30)) + "\n마지막장: 축제 일정은 10월이다."

    selected = select_document_context(text, "축제 일정", 3000)

    assert selected.index("0장:") < selected.index("마지막장: 축제 일정은 10월이다.")


def test_build_openai_messages_uses_previous_question_for_long_document():
    text = make_long_document()
    history = [
        Messages(role=Role.USER, content="동아리 발표회 알려줘"),
        Messages(role=Role.Assistant, content="어떤 점이 궁금한가요?"),
    ]

    messages = build_openai_messages(history, "그거 언제야?", text)

    file_message = str(messages[1]["content"])
    assert file_message.startswith(PARTIAL_FILE_CONTEXT_HEADER)
    assert "12월 5일" in file_message
    assert len(file_message) <= MAX_FILE_CONTEXT_LENGTH + len(PARTIAL_FILE_CONTEXT_HEADER) + 1


def test_build_openai_messages_keeps_short_document_whole():
    messages = build_openai_messages([], "질문", "짧은 문서")

    assert messages[1]["content"] == f"{FILE_CONTEXT_HEADER}\n짧은 문서"
