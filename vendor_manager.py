"""
업체 관리 탭 (vendor_manager.py)

업체 추가/삭제, 양식 파일 업로드/다운로드, 키워드 설정 UI를 통합 제공합니다.
"""
import streamlit as st
import pandas as pd
import os
import base64
import io
import re
import logging
import streamlit.components.v1 as stc

logger = logging.getLogger(__name__)

# ── 보안 상수 ──
_ALLOWED_EXTENSIONS = {'.xlsx', '.xls'}
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
_MAX_VENDOR_NAME_LENGTH = 100
from map import (
    get_all_vendors,
    get_vendor_by_name,
    add_vendor_to_config,
    remove_vendor_from_config,
    update_vendor_in_config,
    reload_config,
    _FORM_DIR,
)
from components.vendor_table import vendor_table


def _validate_vendor_name(name):
    """업체명을 검증하고 안전한 문자열로 반환합니다."""
    if not name or len(name.strip()) < 1:
        return None
    if len(name) > _MAX_VENDOR_NAME_LENGTH:
        return None
    # 위험 문자 제거 (XSS, 코드 삽입 방지)
    sanitized = re.sub(r'[<>"\';\\]', '', name).strip()
    return sanitized if sanitized else None


def _validate_file_upload(file_bytes, original_filename):
    """업로드된 파일의 크기, 확장자, 내용을 검증합니다."""
    # 1. 파일 크기 검증
    if len(file_bytes) > _MAX_FILE_SIZE:
        raise ValueError("파일 크기가 10MB를 초과합니다")
    # 2. 확장자 화이트리스트 검증
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValueError(f"허용되지 않는 파일 형식: {ext}")
    # 3. 파일 내용이 실제 Excel인지 검증
    try:
        pd.read_excel(io.BytesIO(file_bytes), nrows=0)
    except Exception:
        raise ValueError("유효한 Excel 파일이 아닙니다")


def _save_form_file_from_bytes(file_bytes, vendor_name, original_filename):
    """바이트 데이터로부터 양식 파일을 data/target_form/에 저장합니다."""
    # 파일 검증
    _validate_file_upload(file_bytes, original_filename)

    os.makedirs(_FORM_DIR, exist_ok=True)
    ext = os.path.splitext(original_filename)[1].lower()
    # 안전한 파일명 생성
    safe_name = re.sub(r'[^\w\s\-()]', '', vendor_name).strip()
    if not safe_name:
        raise ValueError("유효하지 않은 업체명입니다")
    filename = f"{safe_name}{ext}"
    filepath = os.path.join(_FORM_DIR, filename)

    # Path traversal 방어
    if not os.path.realpath(filepath).startswith(os.path.realpath(_FORM_DIR)):
        raise ValueError("잘못된 파일 경로입니다")

    import time
    for attempt in range(3):
        try:
            with open(filepath, "wb") as f:
                f.write(file_bytes)
            return filename
        except PermissionError:
            if attempt < 2:
                time.sleep(0.5)
            else:
                raise


def _read_form_columns_from_bytes(file_bytes):
    """바이트 데이터에서 엑셀 칼럼 헤더를 추출합니다."""
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), nrows=5)
        return list(df.columns)
    except Exception:
        return []


def _save_form_file(uploaded_file, vendor_name):
    """업로드된 양식 파일을 data/target_form/에 저장합니다."""
    file_bytes = uploaded_file.getbuffer().tobytes()
    return _save_form_file_from_bytes(file_bytes, vendor_name, uploaded_file.name)


def _read_form_columns(uploaded_file):
    """업로드된 엑셀 파일에서 칼럼 헤더를 추출합니다."""
    try:
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file, nrows=5)
        return list(df.columns), df
    except Exception as e:
        st.error(f"양식 파일 읽기 실패: {e}")
        return [], pd.DataFrame()


def _load_existing_form(vendor_name):
    """기존 업체의 양식 파일을 로드합니다."""
    for ext in ['.xlsx', '.xls']:
        filepath = os.path.join(_FORM_DIR, f"{vendor_name}{ext}")
        if os.path.exists(filepath):
            try:
                df = pd.read_excel(filepath, nrows=5)
                return df, filepath
            except Exception:
                pass
    return None, None


def _get_form_file_path(form_filename):
    """양식 파일의 전체 경로를 반환합니다."""
    if not form_filename:
        return None
    # Path traversal 방어: 경로 구분자 및 상위 디렉토리 참조 차단
    if '/' in form_filename or '\\' in form_filename or '..' in form_filename:
        logger.warning(f"Path traversal 시도 차단: {form_filename}")
        return None
    filepath = os.path.join(_FORM_DIR, form_filename)
    # 실제 경로가 _FORM_DIR 내부인지 검증
    if not os.path.realpath(filepath).startswith(os.path.realpath(_FORM_DIR)):
        logger.warning(f"Path traversal 시도 차단 (realpath): {form_filename}")
        return None
    if os.path.exists(filepath):
        return filepath
    return None


def render_vendor_tab():
    """업체 관리 탭 UI를 렌더링합니다."""
    st.subheader("업체 관리")
    st.markdown('<p style="font-size:16px; color:#888; margin-top:-10px;">샤방넷 통합파일에서 데이터를 추출할 분류 키워드를 지정하고, 해당 데이터를 출력할 업체별 양식 파일을 등록해 주세요.</p>', unsafe_allow_html=True)
    st.markdown("""<style>
    .stCustomComponentV1 { margin-top: -16px; }
    </style>""", unsafe_allow_html=True)

    vendors = get_all_vendors()

    # ── 양식 파일 다운로드 처리 ──
    if "_vendor_dl_file" in st.session_state:
        dl_file = st.session_state.pop("_vendor_dl_file")
        filepath = _get_form_file_path(dl_file)
        if filepath:
            with open(filepath, "rb") as f:
                file_bytes = f.read()
            ext = os.path.splitext(dl_file)[1].lower()
            mime = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    if ext == ".xlsx"
                    else "application/vnd.ms-excel")
            st.download_button(
                label=f"{dl_file} 다운로드",
                data=file_bytes,
                file_name=dl_file,
                mime=mime,
                key="dl_form_auto",
                type="primary",
                use_container_width=True,
            )

    # ── 커스텀 테이블 컴포넌트 ──
    result = vendor_table(vendors=vendors, key="vendor_table_component")

    # ── 컴포넌트 반환값 처리 ──
    if result is not None:
        # 다운로드 요청이 있으면 session_state에 저장 후 rerun
        dl_req = result.get("download_request")
        if dl_req:
            form_file = dl_req.get("form_file", "")
            if form_file:
                st.session_state["_vendor_dl_file"] = form_file
                st.rerun()
            return

        changes_applied = False

        # 1) 삭제 처리 (이미 삭제된 ID는 무시)
        deleted_ids = result.get("deleted_ids", [])
        for vid in deleted_ids:
            try:
                remove_vendor_from_config(vid)
                changes_applied = True
            except ValueError:
                pass  # 이미 삭제된 ID — 무시
            except Exception as e:
                st.error(f"삭제 실패: {e}")

        # 2) 행 데이터 처리 (수정/추가/파일 업로드)
        result_rows = result.get("rows", [])
        for row in result_rows:
            row_id = row.get("id")
            name = str(row.get("name", "")).strip()
            kw_str = str(row.get("keywords", "")).strip()
            file_data = row.get("_file_data")
            file_name = row.get("_file_name")
            is_new = row.get("_is_new", False)

            if not name:
                continue

            # 입력값 검증: 업체명 sanitize
            name = _validate_vendor_name(name)
            if not name:
                continue

            # 새 업체 추가
            if is_new and row_id is None:
                keywords = [k.strip() for k in kw_str.split(",") if k.strip()] if kw_str else [name]
                try:
                    new_id = add_vendor_to_config(name=name, keywords=keywords)
                    changes_applied = True

                    # 파일이 첨부된 경우
                    if file_data and file_name:
                        try:
                            raw = base64.b64decode(file_data)
                            form_fn = _save_form_file_from_bytes(raw, name, file_name)
                            cols = _read_form_columns_from_bytes(raw)
                            updates = {"form_file": form_fn}
                            if cols:
                                updates["target_columns"] = cols
                            update_vendor_in_config(new_id, updates)
                        except Exception:
                            pass
                except ValueError:
                    pass  # 이미 존재하는 업체 — 무시
                except Exception as e:
                    st.error(f"'{name}' 추가 실패: {e}")
                continue

            # 기존 업체 수정
            if row_id is not None:
                vendor = next((v for v in vendors if v["id"] == row_id), None)
                if vendor is None:
                    continue

                updates = {}
                if name != vendor["name"]:
                    updates["name"] = name
                current_kw = ", ".join(vendor.get("keywords", [vendor["name"]]))
                if kw_str != current_kw:
                    new_kw = [k.strip() for k in kw_str.split(",") if k.strip()]
                    if new_kw:
                        updates["keywords"] = new_kw

                # 파일 업로드 처리
                if file_data and file_name:
                    try:
                        raw = base64.b64decode(file_data)
                        vname = name if name else vendor["name"]
                        form_fn = _save_form_file_from_bytes(raw, vname, file_name)
                        cols = _read_form_columns_from_bytes(raw)
                        updates["form_file"] = form_fn
                        if cols:
                            updates["target_columns"] = cols
                    except Exception as e:
                        st.error(f"파일 저장 실패: {e}")

                # 파일 제거 처리
                file_removed = row.get("_file_removed", False)
                if file_removed and not file_data:
                    updates["form_file"] = ""

                if updates:
                    try:
                        update_vendor_in_config(row_id, updates)
                        changes_applied = True
                    except Exception as e:
                        st.error(f"수정 실패: {e}")

        if changes_applied:
            reload_config()
            st.warning("⚠️ 변경 사항은 현재 세션에서만 유효합니다. 앱 재시작 시 초기 설정으로 복원됩니다.")
            st.rerun()
