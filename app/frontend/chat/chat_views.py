import streamlit as st

from app.frontend.api.http_client import FrontendApiError
from .chat_composer import render_chat_composer
from .chat_modals import create_room_modal, leave_room_modal
from .chat_state import get_total_room_pages, go_to_home, load_messages


def render_sidebar(personas: list[str]) -> None:
    # 공통 사이드바를 렌더링하고 채팅방 목록과 계정 액션을 노출
    with st.sidebar:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:8px; padding:4px 0">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#cdd6f4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 1 0-16 0"/></svg>
                <span style="font-size:16px; font-weight:600; color:#cdd6f4">{st.session_state.get('login_id', '')}님</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#cdd6f4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <span style="font-size:15px; font-weight:600; color:#cdd6f4">채팅방 목록</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not st.session_state["chat_rooms"]:
            st.caption("채팅방이 없습니다")
        else:
            _render_sidebar_room_buttons()
            _render_sidebar_pager()

        st.divider()
        _render_sidebar_actions(personas)


def _render_sidebar_room_buttons() -> None:
    # 현재 페이지에 속한 채팅방 버튼과 삭제 버튼을 노출 시킨다.
    for room in st.session_state["chat_rooms"]:
        col1, col2 = st.columns([4, 1])
        with col1:
            is_selected = (
                st.session_state["current_room"]
                and st.session_state["current_room"]["id"] == room["id"]
            )
            btn_label = f"✓ {room['title']}" if is_selected else f"  {room['title']}"
            if st.button(btn_label, key=f"room_{room['id']}", use_container_width=True):
                st.session_state["current_room"] = room
                if room.get("member_id"):
                    st.session_state["member_id"] = room["member_id"]
                try:
                    load_messages(room["id"])
                    st.rerun()
                except FrontendApiError as exc:
                    st.error(exc.message)
        with col2:
            if st.button("×", key=f"leave_{room['id']}", help="채팅방 나가기"):
                leave_room_modal(room)


def _render_sidebar_pager() -> None:
    # 사이드바 하단에 채팅방 이전/다음 페이지 이동 버튼
    total_room_pages = get_total_room_pages()
    st.markdown('<div class="sidebar-pager">', unsafe_allow_html=True)
    prev_col, next_col = st.columns(2)
    with prev_col:
        if st.button(
            "이전",
            key="room_page_prev",
            use_container_width=True,
            disabled=st.session_state["room_page"] <= 1,
        ):
            st.session_state["room_page"] -= 1
            st.rerun()
    with next_col:
        if st.button(
            "다음",
            key="room_page_next",
            use_container_width=True,
            disabled=st.session_state["room_page"] >= total_room_pages,
        ):
            st.session_state["room_page"] += 1
            st.rerun()
    st.markdown(
        f'<div class="pager-label">채팅방 페이지 {st.session_state["room_page"]} / {total_room_pages}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_sidebar_actions(personas: list[str]) -> None:
    # 관리자 이동과 로그아웃처럼 계정 성격의 액션 버튼을 렌더링
    if st.session_state.get("role") == "ADMIN":
        if st.button("관리자 페이지", use_container_width=True):
            st.switch_page("pages/admin.py")
        st.write("")

    if st.button("마이페이지", use_container_width=True):
        st.switch_page("pages/mypage.py")
    st.write("")

    if st.button("로그아웃", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("pages/login.py")


def render_lobby_view(personas: list[str]) -> None:
    # 채팅방 입장 전 메인 로비 화면과 카드형 채팅방 목록을 렌더링한
    if not st.session_state["chat_rooms"]:
        _render_empty_lobby(personas)
        return

    col1, col2 = st.columns([8, 1])
    with col1:
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:10px">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#89b4fa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
                <h2 style="margin:0">AI Tutor Chatbot</h2>
            </div>
            <p style="color:#888; margin-top:4px">채팅방을 선택하세요</p>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.write("")
        st.write("")
        if st.button("+ 새 채팅방", help="새 채팅방 만들기", use_container_width=True):
            create_room_modal(personas)

    st.divider()
    cols = st.columns(3)
    for i, room in enumerate(st.session_state["chat_rooms"]):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#89b4fa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                        <strong>{room['title']}</strong>
                    </div>
                    <p style="color:#888; font-size:13px; margin:0">페르소나 : {room['persona']}</p>
                    """,
                    unsafe_allow_html=True,
                )
                st.write("")
                if st.button(
                    "입장하기",
                    key=f"enter_{room['id']}",
                    use_container_width=True,
                    type="primary",
                ):
                    st.session_state["current_room"] = room
                    if room.get("member_id"):
                        st.session_state["member_id"] = room["member_id"]
                    try:
                        load_messages(room["id"])
                        st.rerun()
                    except FrontendApiError as exc:
                        st.error(exc.message)

    total_room_pages = get_total_room_pages()
    st.markdown(
        f'<div class="lobby-page-info">현재 페이지 {st.session_state["room_page"]} / {total_room_pages}</div>',
        unsafe_allow_html=True,
    )


def _render_empty_lobby(personas: list[str]) -> None:
    # 채팅방이 하나도 없을 때 비어 있는 로비 상태 화면을 출력
    st.markdown("<br>" * 3, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style="text-align:center; margin-bottom:16px">
                <svg xmlns="http://www.w3.org/2000/svg" width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="#89b4fa" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
                <h2 style="margin-top:8px">AI Tutor Chatbot</h2>
                <p style="color:#888">학습을 도와주는 AI 튜터입니다</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()
        st.info("채팅방이 없습니다. 새 채팅방을 만들어보세요!")
        st.write("")
        if st.button("+ 새 채팅방 만들기", use_container_width=True, type="primary"):
            create_room_modal(personas)


def render_room_view(personas: list[str]) -> None:
    # 현재 선택된 채팅방의 헤더, 메시지 목록, 입력창을 렌더링
    room = st.session_state["current_room"]
    if room is None:
        return

    if not st.session_state["messages"]:
        try:
            load_messages(room["id"])
        except FrontendApiError as exc:
            st.error(exc.message)

    top_action_col, col1, col2 = st.columns([1.2, 7.8, 1])
    with top_action_col:
        st.write("")
        st.write("")
        if st.button("← 메인", use_container_width=True):
            go_to_home()
            st.rerun()
    with col1:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:10px">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#89b4fa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <h2 style="margin:0">{room['title']}</h2>
            </div>
            <p style="color:#888; margin-top:4px; margin-left:38px">페르소나 : {room['persona']}</p>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.write("")
        st.write("")
        if st.button("+ 새 채팅방", use_container_width=True):
            create_room_modal(personas)

    st.divider()
    _render_messages()
    render_chat_composer(room["id"])


def _render_messages() -> None:
    # 세션에 적재된 메시지를 순서대로 채팅 UI에 출력
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message.get("notice"):
                st.warning(message["notice"])
            if message.get("file"):
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; gap:6px; color:#888; font-size:13px; margin-top:4px">
                        <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#888" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
                        {message['file']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
