"""
인증 모듈 (auth.py)

st.secrets 기반 로그인/로그아웃 처리.
비밀번호는 bcrypt 해시로 저장·비교합니다.
SHA-256 레거시 해시도 호환 지원합니다.
"""
import hashlib
import time
import bcrypt
import streamlit as st

_MAX_LOGIN_ATTEMPTS = 5
_LOCKOUT_SECONDS = 30
_SESSION_TIMEOUT_SECONDS = 3600  # 1시간


def _hash_password_bcrypt(password: str) -> str:
    """비밀번호를 bcrypt 해시로 변환합니다."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, stored_hash: str) -> bool:
    """입력 비밀번호와 저장된 해시를 비교합니다. bcrypt와 SHA-256 레거시 모두 지원."""
    if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    # SHA-256 레거시 호환
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == stored_hash


def _get_users() -> dict:
    """st.secrets에서 사용자 목록을 로드합니다."""
    try:
        return dict(st.secrets["users"])
    except (KeyError, FileNotFoundError):
        return {}


def check_auth() -> bool:
    """현재 세션이 인증되었는지 확인합니다. 세션 타임아웃도 체크."""
    if not st.session_state.get("authenticated", False):
        return False
    login_time = st.session_state.get("login_time", 0)
    if time.time() - login_time > _SESSION_TIMEOUT_SECONDS:
        logout()
        return False
    return True


def get_current_user() -> dict:
    """현재 로그인한 사용자 정보를 반환합니다."""
    return st.session_state.get("user_info", {})


def logout():
    """세션을 클리어하고 로그인 페이지로 복귀합니다."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def _check_lockout() -> bool:
    """브루트포스 잠금 상태를 확인합니다. 잠금 중이면 True."""
    attempts = st.session_state.get("_login_attempts", 0)
    if attempts >= _MAX_LOGIN_ATTEMPTS:
        lockout_until = st.session_state.get("_lockout_until", 0)
        if time.time() < lockout_until:
            remaining = int(lockout_until - time.time())
            st.error(f"로그인 시도가 너무 많습니다. {remaining}초 후 다시 시도하세요.")
            return True
        # 잠금 해제
        st.session_state["_login_attempts"] = 0
    return False


def _record_failed_attempt():
    """실패한 로그인 시도를 기록합니다."""
    attempts = st.session_state.get("_login_attempts", 0) + 1
    st.session_state["_login_attempts"] = attempts
    if attempts >= _MAX_LOGIN_ATTEMPTS:
        st.session_state["_lockout_until"] = time.time() + _LOCKOUT_SECONDS


def render_login_page():
    """로그인 폼 UI를 렌더링합니다."""
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
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
                if _check_lockout():
                    return

                if not user_id or not password:
                    st.error("아이디와 비밀번호를 입력해 주세요.")
                    return

                users = _get_users()
                user_config = users.get(user_id)

                if user_config is None:
                    _record_failed_attempt()
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
                    return

                stored_hash = user_config.get("password_hash", "")
                if not _verify_password(password, stored_hash):
                    _record_failed_attempt()
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
                    return

                # 인증 성공
                st.session_state["authenticated"] = True
                st.session_state["login_time"] = time.time()
                st.session_state["_login_attempts"] = 0
                st.session_state["user_info"] = {
                    "user_id": user_id,
                    "display_name": str(user_config.get("display_name", user_id)),
                    "role": str(user_config.get("role", "user")),
                }
                st.rerun()
