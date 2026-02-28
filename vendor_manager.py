"""
업체 관리 탭 (vendor_manager.py)

업체 추가/삭제, 양식 파일 업로드/다운로드, 키워드 설정 UI를 통합 제공합니다.
"""
import streamlit as st
import pandas as pd
import os
from map import (
    get_all_vendors,
    get_vendor_by_name,
    add_vendor_to_config,
    remove_vendor_from_config,
    update_vendor_in_config,
    reload_config,
    _FORM_DIR,
)


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
    # form_file 필드로 시도
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
    st.subheader("🏭 업체 관리")
    st.caption("테이블에서 직접 업체를 추가·수정·삭제할 수 있습니다. 변경 후 **💾 변경사항 저장** 버튼을 누르세요.")

    vendors = get_all_vendors()

    st.markdown("### 📋 등록된 업체 목록")

    # ── 원본 데이터 구성 ──
    original_rows = []
    vendor_id_map = {}  # 행 인덱스 → vendor_id 매핑
    for i, v in enumerate(vendors):
        keywords = ", ".join(v.get("keywords", [v["name"]]))
        form_file = v.get("form_file", "")
        original_rows.append({
            "업체명": v["name"],
            "키워드": keywords,
            "양식 파일": form_file if form_file else "",
        })
        vendor_id_map[i] = v["id"]

    original_df = pd.DataFrame(
        original_rows,
        columns=["업체명", "키워드", "양식 파일"],
    )

    # ── data_editor: 추가/수정/삭제 가능한 통합 테이블 ──
    edited_df = st.data_editor(
        original_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="vendor_table_editor",
        column_config={
            "업체명": st.column_config.TextColumn(
                "업체명",
                help="업체의 이름입니다.",
                required=True,
                width="medium",
            ),
            "키워드": st.column_config.TextColumn(
                "키워드",
                help="쉼표로 구분된 분류 키워드입니다. 주문서의 상품약어에 이 문자열이 포함되면 해당 업체로 분류됩니다.",
                required=True,
                width="large",
            ),
            "양식 파일": st.column_config.TextColumn(
                "양식 파일",
                help="양식 파일명입니다. 아래 '양식 파일 관리' 영역에서 업로드/변경할 수 있습니다.",
                disabled=True,
                width="medium",
            ),
        },
    )

    # ── 변경 감지 ──
    # st.data_editor의 session_state에서 변경 정보 가져오기
    editor_state = st.session_state.get("vendor_table_editor", {})
    edited_rows = editor_state.get("edited_rows", {})
    added_rows = editor_state.get("added_rows", [])
    deleted_rows = editor_state.get("deleted_rows", [])

    has_changes = bool(edited_rows) or bool(added_rows) or bool(deleted_rows)

    # 변경 요약 표시
    if has_changes:
        changes_parts = []
        if edited_rows:
            changes_parts.append(f"수정 {len(edited_rows)}건")
        if added_rows:
            changes_parts.append(f"추가 {len(added_rows)}건")
        if deleted_rows:
            changes_parts.append(f"삭제 {len(deleted_rows)}건")
        st.info(f"✏️ 변경사항이 있습니다: {', '.join(changes_parts)}")

    # ── 저장 / 초기화 버튼 ──
    save_col, reset_col = st.columns([2, 1])
    with save_col:
        if st.button(
            "💾 변경사항 저장",
            type="primary",
            use_container_width=True,
            disabled=not has_changes,
            key="vendor_save_all",
        ):
            errors = []
            success_msgs = []

            # 1) 삭제 처리 (역순으로 — 인덱스 밀림 방지)
            for row_idx in sorted(deleted_rows, reverse=True):
                if row_idx in vendor_id_map:
                    vid = vendor_id_map[row_idx]
                    vname = original_rows[row_idx]["업체명"]
                    try:
                        remove_vendor_from_config(vid)
                        success_msgs.append(f"🗑️ '{vname}' 삭제됨")
                    except Exception as e:
                        errors.append(f"'{vname}' 삭제 실패: {e}")

            # 2) 수정 처리
            for row_idx_str, changes in edited_rows.items():
                row_idx = int(row_idx_str)
                if row_idx in vendor_id_map:
                    vid = vendor_id_map[row_idx]
                    updates = {}

                    if "업체명" in changes:
                        new_name = str(changes["업체명"]).strip()
                        if new_name:
                            updates["name"] = new_name

                    if "키워드" in changes:
                        kw_str = str(changes["키워드"]).strip()
                        if kw_str:
                            new_kw = [k.strip() for k in kw_str.split(",") if k.strip()]
                            if new_kw:
                                updates["keywords"] = new_kw

                    if updates:
                        try:
                            update_vendor_in_config(vid, updates)
                            vname = updates.get("name", original_rows[row_idx]["업체명"])
                            success_msgs.append(f"✏️ '{vname}' 수정됨")
                        except Exception as e:
                            errors.append(f"수정 실패 (행 {row_idx + 1}): {e}")

            # 3) 추가 처리
            for added in added_rows:
                name = str(added.get("업체명", "")).strip()
                kw_str = str(added.get("키워드", "")).strip()
                if not name:
                    errors.append("업체명이 비어있는 행은 추가할 수 없습니다.")
                    continue
                keywords = [k.strip() for k in kw_str.split(",") if k.strip()] if kw_str else [name]
                try:
                    add_vendor_to_config(name=name, keywords=keywords)
                    success_msgs.append(f"➕ '{name}' 추가됨")
                except Exception as e:
                    errors.append(f"'{name}' 추가 실패: {e}")

            # 결과 표시 및 갱신
            reload_config()
            for msg in success_msgs:
                st.success(msg)
            for err in errors:
                st.error(f"⚠️ {err}")
            if success_msgs:
                st.rerun()

    with reset_col:
        if st.button("↩️ 초기화", use_container_width=True, key="vendor_reset_all"):
            st.rerun()

    if not has_changes:
        st.caption(f"총 {len(vendors)}개 업체 등록됨. 변경사항이 없습니다.")

    st.divider()

    # ── 양식 파일 관리 ──
    st.markdown("### 📂 양식 파일 관리")
    st.caption("양식 파일을 업로드하거나 변경할 업체를 선택하세요.")

    if not vendors:
        st.info("등록된 업체가 없습니다. 위 테이블에서 업체를 먼저 추가하세요.")
        return

    vendor_names = [v["name"] for v in vendors]
    selected_vendor = st.selectbox(
        "업체 선택",
        options=vendor_names,
        key="form_vendor_select",
    )

    if selected_vendor:
        vendor = get_vendor_by_name(selected_vendor)
        if vendor:
            vendor_id = vendor["id"]
            form_file = vendor.get("form_file", "")

            # 현재 양식 파일 다운로드
            if form_file:
                form_path = _get_form_file_path(form_file)
                if form_path:
                    dl_col, info_col = st.columns([1, 2])
                    with dl_col:
                        with open(form_path, "rb") as f:
                            file_bytes = f.read()
                        st.download_button(
                            label=f"📥 {form_file}",
                            data=file_bytes,
                            file_name=form_file,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_form_{vendor_id}",
                            use_container_width=True,
                        )
                    with info_col:
                        st.caption(f"현재 양식: {form_file}")
                else:
                    st.caption(f"⚠️ {form_file} (파일을 찾을 수 없습니다)")
            else:
                st.caption("양식 파일이 설정되지 않았습니다.")

            # 양식 파일 업로드/변경
            update_form = st.file_uploader(
                "새 양식 파일 업로드",
                type=["xlsx", "xls"],
                key=f"update_form_{vendor_id}",
            )
            if update_form is not None:
                new_cols, preview = _read_form_columns(update_form)
                if new_cols:
                    st.dataframe(preview, use_container_width=True, height=150)
                    st.caption(f"감지된 칼럼 ({len(new_cols)}개): {', '.join(new_cols)}")

                    if st.button("📥 양식 적용", key=f"apply_form_{vendor_id}"):
                        try:
                            form_fn = _save_form_file(update_form, selected_vendor)
                            update_vendor_in_config(vendor_id, {
                                "target_columns": new_cols,
                                "form_file": form_fn,
                            })
                            reload_config()
                            st.success("✅ 양식이 업데이트되었습니다!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 양식 업데이트 실패: {e}")
