"""
인증 모듈 (auth.py)

st.secrets 기반 로그인/로그아웃 처리.
비밀번호는 SHA-256 해시로 저장·비교합니다.
"""
import hashlib
import streamlit as st


def _hash_password(password: str) -> str:
    """비밀번호를 SHA-256 해시로 변환합니다."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    """입력 비밀번호와 저장된 해시를 비교합니다."""
    return _hash_password(password) == hashed


def _get_users() -> dict:
    """st.secrets에서 사용자 목록을 로드합니다.

    secrets.toml 예시:
        [users.admin]
        password_hash = "..."
        display_name = "365건강농산"
        role = "admin"
    """
    try:
        return dict(st.secrets["users"])
    except (KeyError, FileNotFoundError):
        return {}


def check_auth() -> bool:
    """현재 세션이 인증되었는지 확인합니다."""
    return st.session_state.get("authenticated", False)


def get_current_user() -> dict:
    """현재 로그인한 사용자 정보를 반환합니다.

    Returns:
        {"user_id": str, "display_name": str, "role": str}
    """
    return st.session_state.get("user_info", {})


def logout():
    """세션을 클리어하고 로그인 페이지로 복귀합니다."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def render_login_page():
    """로그인 폼 UI를 렌더링합니다."""
    # 로그인 페이지 전용 스타일
    st.markdown("""
    <style>
    /* 로그인 페이지 - 사이드바 숨김 */
    section[data-testid="stSidebar"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    .login-container {
        max-width: 400px;
        margin: 80px auto;
        padding: 2rem;
        background: #fff;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
    .login-title {
        text-align: center;
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e2128;
        margin-bottom: 0.5rem;
    }
    .login-subtitle {
        text-align: center;
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-title">주문서 변환 시스템</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">로그인하여 시작하세요</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            user_id = st.text_input("아이디", placeholder="아이디를 입력하세요")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
            submitted = st.form_submit_button("로그인", use_container_width=True, type="primary")

            if submitted:
                if not user_id or not password:
                    st.error("아이디와 비밀번호를 입력해 주세요.")
                    return

                users = _get_users()
                user_config = users.get(user_id)

                if user_config is None:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
                    return

                stored_hash = user_config.get("password_hash", "")
                if not _verify_password(password, stored_hash):
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
                    return

                # 인증 성공
                st.session_state["authenticated"] = True
                st.session_state["user_info"] = {
                    "user_id": user_id,
                    "display_name": str(user_config.get("display_name", user_id)),
                    "role": str(user_config.get("role", "user")),
                }
                st.rerun()
