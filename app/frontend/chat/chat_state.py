from typing import Any

import streamlit as st

from app.frontend.api.http_client import FrontendApiError

from .chat_api import fetch_all_messages, fetch_chat_rooms_page, fetch_personas, send_ai_chat

def init_chat_session_state() -> None:
    # 채팅 화면이 사용하는 session_state 기본값을 한 번만 세팅
    defaults: dict[str, object] = {
        "chat_rooms": [],
        "current_room": None,
        "messages": [],
        "personas": [],
        "file_uploader_key": 0,
        "room_page": 1,
        "room_total": 0,
        "room_page_size": 5,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def load_chat_rooms(select_room_id: int | None = None) -> None:
    # 현재 페이지의 채팅방 목록을 불러오고 선택 상태를 가능한 범위에서 유지
    room_page = st.session_state.get("room_page", 1)
    payload = fetch_chat_rooms_page(room_page)
    rooms = payload["items"]
    st.session_state["chat_rooms"] = rooms
    st.session_state["room_total"] = payload["total"]
    st.session_state["room_page"] = payload["page"]
    st.session_state["room_page_size"] = payload["size"]

    current_room = st.session_state.get("current_room")
    if select_room_id is not None:
        _select_room_from_any_page(select_room_id, rooms)
        return

    if not current_room:
        return

    refreshed_room = next((room for room in rooms if room["id"] == current_room["id"]), None)
    if refreshed_room is not None:
        st.session_state["current_room"] = refreshed_room


def load_personas() -> list[str]:
    # 현재 기준의 페르소나 목록을 세션에 반영한다.
    personas = fetch_personas()
    st.session_state["personas"] = personas
    return personas


def _select_room_from_any_page(select_room_id: int, current_page_rooms: list[dict[str, Any]]) -> None:
    # 새로 만든 방처럼 현재 페이지에 없는 채팅방도 전체 페이지를 훑어 선택
    selected = next((room for room in current_page_rooms if room["id"] == select_room_id), None)
    if selected is None:
        target_page = 1
        total_pages = get_total_room_pages()
        for page in range(1, total_pages + 1):
            payload = fetch_chat_rooms_page(page)
            selected = next((room for room in payload["items"] if room["id"] == select_room_id), None)
            if selected is not None:
                st.session_state["chat_rooms"] = payload["items"]
                st.session_state["room_total"] = payload["total"]
                st.session_state["room_page"] = payload["page"]
                st.session_state["room_page_size"] = payload["size"]
                target_page = page
                break
        st.session_state["room_page"] = target_page
    st.session_state["current_room"] = selected


def load_messages(room_id: int) -> None:
    # 선택된 채팅방의 메시지를 전부 세션에 적재
    st.session_state["messages"] = fetch_all_messages(room_id)


def get_member_id_for_new_room() -> int | None:
    # 새 채팅방 생성에 쓸 회원 ID를 세션이나 현재 방 정보에서 찾아온다.
    member_id = st.session_state.get("member_id")
    if isinstance(member_id, int) and member_id > 0:
        return member_id

    current_room = st.session_state.get("current_room")
    if current_room and current_room.get("member_id"):
        return int(current_room["member_id"])
    return None


def go_to_home() -> None:
    # 현재 방과 메시지 상태를 비워 로비 화면으로 되돌린다.
    st.session_state["current_room"] = None
    st.session_state["messages"] = []


def handle_send_message(room_id: int, prompt: str, uploaded_file: Any | None) -> None:
    # AI 응답을 요청하고 사용자/어시스턴트 메시지를 세션에 함께 반영
    try:
        with st.spinner("AI가 답변을 생성하고 있습니다..."):
            result = send_ai_chat(room_id, prompt, uploaded_file)
    except FrontendApiError as exc:
        st.error(exc.message)
        return

    user_message = {
        "role": "user",
        "content": result.get("user_message", prompt),
    }
    if result.get("file_name"):
        user_message["file"] = result["file_name"]

    assistant_message = {
        "role": "assistant",
        "content": result.get("assistant_message", ""),
    }
    if result.get("document_notice"):
        assistant_message["notice"] = result["document_notice"]

    st.session_state["messages"].append(user_message)
    st.session_state["messages"].append(assistant_message)
    st.session_state["file_uploader_key"] += 1
    st.rerun()


def get_total_room_pages() -> int:
    # 전체 채팅방 수와 페이지 크기를 기준으로 마지막 페이지 번호를 계산
    total = st.session_state.get("room_total", 0)
    size = st.session_state.get("room_page_size", 5)
    return max(1, -(-total // size))
