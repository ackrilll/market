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
    st.caption("테이블에서 직접 업체를 추가·수정할 수 있습니다. 변경사항은 자동으로 저장됩니다.")

    vendors = get_all_vendors()

    st.markdown("### 📋 등록된 업체 목록")

    # ── 원본 데이터 구성 ──
    original_rows = []
    vendor_id_map = {}  # 행 인덱스 → vendor_id 매핑
    for i, v in enumerate(vendors):
        keywords = ", ".join(v.get("keywords", [v["name"]]))
        form_file = v.get("form_file", "")
        original_rows.append({
            "선택": False,
            "업체명": v["name"],
            "분류키워드": keywords,
            "양식 파일": form_file if form_file else "",
        })
        vendor_id_map[i] = v["id"]

    original_df = pd.DataFrame(
        original_rows,
        columns=["선택", "업체명", "분류키워드", "양식 파일"],
    )

    # ── data_editor: 추가/수정 가능한 통합 테이블 ──
    edited_df = st.data_editor(
        original_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="vendor_table_editor",
        column_config={
            "선택": st.column_config.CheckboxColumn(
                "선택",
                help="삭제할 업체를 선택하세요.",
                default=False,
            ),
            "업체명": st.column_config.TextColumn(
                "업체명",
                help="업체의 이름입니다.",
                required=True,
                width="medium",
            ),
            "분류키워드": st.column_config.TextColumn(
                "분류키워드",
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

    # ── 선택된 업체 삭제 버튼 ──
    selected_existing = [
        idx for idx in range(len(original_rows))
        if idx < len(edited_df) and edited_df.iloc[idx].get("선택", False)
        and idx in vendor_id_map
    ]

    if selected_existing:
        vendor_names_to_delete = [original_rows[idx]["업체명"] for idx in selected_existing]
        if st.button(
            f"🗑️ 선택한 {len(selected_existing)}개 업체 삭제 ({', '.join(vendor_names_to_delete)})",
            type="secondary",
            use_container_width=True,
            key="vendor_delete_selected",
        ):
            for idx in sorted(selected_existing, reverse=True):
                vid = vendor_id_map[idx]
                try:
                    remove_vendor_from_config(vid)
                except Exception as e:
                    st.error(f"⚠️ '{original_rows[idx]['업체명']}' 삭제 실패: {e}")
            reload_config()
            st.success(f"✅ {len(selected_existing)}개 업체가 삭제되었습니다.")
            st.rerun()

    # ── 자동 저장 ──
    editor_state = st.session_state.get("vendor_table_editor", {})
    edited_rows = editor_state.get("edited_rows", {})
    added_rows = editor_state.get("added_rows", [])
    deleted_rows = editor_state.get("deleted_rows", [])

    changes_applied = False

    # 1) 내장 행 삭제 처리
    for row_idx in sorted(deleted_rows, reverse=True):
        if row_idx in vendor_id_map:
            vid = vendor_id_map[row_idx]
            try:
                remove_vendor_from_config(vid)
                changes_applied = True
            except Exception as e:
                st.error(f"⚠️ 삭제 실패: {e}")

    # 2) 수정된 행 자동 저장
    for row_idx_str, changes in edited_rows.items():
        row_idx = int(row_idx_str)
        if row_idx in vendor_id_map:
            # "선택" 체크박스 변경은 저장 대상이 아님
            data_changes = {k: v for k, v in changes.items() if k != "선택"}
            if not data_changes:
                continue

            vid = vendor_id_map[row_idx]
            updates = {}

            if "업체명" in data_changes:
                new_name = str(data_changes["업체명"]).strip()
                if new_name:
                    updates["name"] = new_name

            if "분류키워드" in data_changes:
                kw_str = str(data_changes["분류키워드"]).strip()
                if kw_str:
                    new_kw = [k.strip() for k in kw_str.split(",") if k.strip()]
                    if new_kw:
                        updates["keywords"] = new_kw

            if updates:
                try:
                    update_vendor_in_config(vid, updates)
                    changes_applied = True
                except Exception as e:
                    st.error(f"⚠️ 수정 실패: {e}")

    # 3) 추가된 행 자동 저장
    for added in added_rows:
        name = str(added.get("업체명", "")).strip()
        kw_str = str(added.get("분류키워드", "")).strip()
        if not name:
            continue  # 업체명 없으면 무시
        keywords = [k.strip() for k in kw_str.split(",") if k.strip()] if kw_str else [name]
        try:
            add_vendor_to_config(name=name, keywords=keywords)
            changes_applied = True
        except Exception as e:
            st.error(f"⚠️ '{name}' 추가 실패: {e}")

    if changes_applied:
        reload_config()
        st.rerun()

    st.caption(f"총 {len(vendors)}개 업체 등록됨")

    st.divider()

    # ── 양식 파일 관리 ──
    st.markdown("### 📂 양식 파일 관리")

    if not vendors:
        st.info("등록된 업체가 없습니다. 위 테이블에서 업체를 먼저 추가하세요.")
        return

    # ── 양식 파일 바로 열기 (다운로드 그리드) ──
    vendors_with_files = [v for v in vendors if v.get("form_file")]
    if vendors_with_files:
        st.caption("📥 양식 파일을 클릭하면 다운로드하여 열어볼 수 있습니다.")
        NUM_COLS = 4
        cols = st.columns(NUM_COLS)
        for i, v in enumerate(vendors_with_files):
            form_file = v["form_file"]
            form_path = _get_form_file_path(form_file)
            with cols[i % NUM_COLS]:
                if form_path:
                    with open(form_path, "rb") as f:
                        file_bytes = f.read()
                    st.download_button(
                        label=f"📄 {v['name']}",
                        data=file_bytes,
                        file_name=form_file,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_form_{v['id']}",
                        use_container_width=True,
                    )
                else:
                    st.button(
                        f"⚠️ {v['name']}",
                        disabled=True,
                        key=f"dl_form_missing_{v['id']}",
                        use_container_width=True,
                    )
    else:
        st.caption("양식 파일이 등록된 업체가 없습니다.")

    st.divider()

    # ── 양식 파일 업로드 (드래그 앤 드롭) ──
    st.caption("🔄 양식 파일을 변경할 업체를 선택한 뒤, 파일을 드래그 앤 드롭하세요. 업로드 즉시 자동 적용됩니다.")

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

            # 양식 파일 업로드 (드래그 앤 드롭 지원)
            update_form = st.file_uploader(
                f"📂 {selected_vendor} 양식 파일 (드래그 앤 드롭 또는 클릭하여 업로드)",
                type=["xlsx", "xls"],
                key=f"update_form_{vendor_id}",
            )

            # 업로드 즉시 자동 적용
            if update_form is not None:
                new_cols, preview = _read_form_columns(update_form)
                if new_cols:
                    st.dataframe(preview, use_container_width=True, height=150)
                    st.caption(f"감지된 칼럼 ({len(new_cols)}개): {', '.join(new_cols)}")

                    try:
                        form_fn = _save_form_file(update_form, selected_vendor)
                        update_vendor_in_config(vendor_id, {
                            "target_columns": new_cols,
                            "form_file": form_fn,
                        })
                        reload_config()
                        st.success(f"✅ '{selected_vendor}' 양식이 자동 적용되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 양식 업데이트 실패: {e}")
