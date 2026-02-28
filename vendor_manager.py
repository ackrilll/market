"""
업체 관리 탭 (vendor_manager.py)

업체 추가/삭제, 양식 파일 업로드/다운로드, 키워드 설정 UI를 통합 제공합니다.
"""
import streamlit as st
import pandas as pd
import os
import base64
import io
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


def _save_form_file_from_bytes(file_bytes, vendor_name, original_filename):
    """바이트 데이터로부터 양식 파일을 data/target_form/에 저장합니다."""
    os.makedirs(_FORM_DIR, exist_ok=True)
    ext = os.path.splitext(original_filename)[1]
    filename = f"{vendor_name}{ext}"
    filepath = os.path.join(_FORM_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(file_bytes)
    return filename


def _read_form_columns_from_bytes(file_bytes):
    """바이트 데이터에서 엑셀 칼럼 헤더를 추출합니다."""
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), nrows=5)
        return list(df.columns)
    except Exception:
        return []


def _save_form_file(uploaded_file, vendor_name):
    """업로드된 양식 파일을 data/target_form/에 저장합니다."""
    os.makedirs(_FORM_DIR, exist_ok=True)
    ext = os.path.splitext(uploaded_file.name)[1]
    filename = f"{vendor_name}{ext}"
    filepath = os.path.join(_FORM_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return filename


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
    filepath = os.path.join(_FORM_DIR, form_filename)
    if os.path.exists(filepath):
        return filepath
    return None


def render_vendor_tab():
    """업체 관리 탭 UI를 렌더링합니다."""
    st.subheader("업체 관리")
    st.caption("테이블에서 직접 업체를 추가·수정하고, 양식 파일을 셀에 드래그 앤 드롭할 수 있습니다.")

    vendors = get_all_vendors()

    # ── 다운로드 버튼 (테이블 위에 표시) ──
    if "_vendor_dl_file" in st.session_state:
        st.markdown("""<style>
        button[data-testid="stDownloadButton"] {
            background-color: #1a73e8 !important;
            border-color: #1a73e8 !important;
            color: white !important;
        }
        button[data-testid="stDownloadButton"]:hover {
            background-color: #1557b0 !important;
            border-color: #1557b0 !important;
        }
        </style>""", unsafe_allow_html=True)
        dl_file = st.session_state["_vendor_dl_file"]
        filepath = _get_form_file_path(dl_file)
        if filepath:
            with open(filepath, "rb") as f:
                file_bytes = f.read()
            ext = os.path.splitext(dl_file)[1].lower()
            mime = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    if ext == ".xlsx"
                    else "application/vnd.ms-excel")
            col1, col2 = st.columns([4, 1])
            with col1:
                st.download_button(
                    label=f"{dl_file} 다운로드",
                    data=file_bytes,
                    file_name=dl_file,
                    mime=mime,
                    key="dl_form_active",
                    type="primary",
                )
            with col2:
                if st.button("닫기", key="dl_close"):
                    del st.session_state["_vendor_dl_file"]
                    st.rerun()

    # ── 커스텀 테이블 컴포넌트 ──
    result = vendor_table(vendors=vendors, key="vendor_table_component")

    # ── 컴포넌트 반환값 처리 ──
    if result is not None:
        # 다운로드 요청이 있으면 우선 처리 (rows 변경과 분리)
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
            st.rerun()
