"""
업체 관리 탭 (vendor_manager.py)

업체 추가/삭제, 양식 파일 업로드/다운로드, 키워드 설정 UI를 통합 제공합니다.
"""
import streamlit as st
import pandas as pd
import os
from map import (
    get_all_vendors,
    get_vendor_by_id,
    get_vendor_by_name,
    add_vendor_to_config,
    remove_vendor_from_config,
    update_vendor_in_config,
    update_vendor_keywords,
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
    st.caption("등록된 업체를 클릭하면 키워드 편집, 양식 파일 변경, 삭제 등을 바로 처리할 수 있습니다.")

    vendors = get_all_vendors()

    st.markdown("### 📋 등록된 업체 목록")

    if vendors:
        for v in vendors:
            vendor_id = v["id"]
            vendor_name = v["name"]
            current_keywords = list(v.get("keywords", [vendor_name]))
            form_file = v.get("form_file", "")
            keywords_display = ", ".join(current_keywords)

            # ── 각 업체를 expander로 표시 ──
            label = f"**{vendor_name}** — 🏷️ {keywords_display}"
            if form_file:
                label += f"  |  📄 {form_file}"

            with st.expander(label, expanded=False):
                # ── 기본 정보 ──
                info_col1, info_col2 = st.columns(2)
                with info_col1:
                    st.metric("키워드 수", len(current_keywords))
                with info_col2:
                    st.metric("칼럼 수", len(v.get("target_columns", [])))

                # ── 키워드 편집 ──
                st.markdown("#### 🏷️ 키워드 관리")
                st.caption("키워드를 수정한 뒤 **💾 변경사항 저장** 버튼을 누르세요.")

                edit_df = pd.DataFrame({"키워드": current_keywords})
                edited_df = st.data_editor(
                    edit_df,
                    num_rows="dynamic",
                    use_container_width=True,
                    hide_index=True,
                    key=f"kw_editor_{vendor_id}",
                    column_config={
                        "키워드": st.column_config.TextColumn(
                            "키워드",
                            help="주문서의 상품약어에 이 문자열이 포함되면 해당 업체로 분류됩니다.",
                            required=True,
                        ),
                    },
                )

                new_keywords = [
                    str(kw).strip()
                    for kw in edited_df["키워드"].tolist()
                    if pd.notna(kw) and str(kw).strip()
                ]
                has_kw_changes = new_keywords != current_keywords

                if has_kw_changes:
                    st.info("✏️ 키워드가 수정되었습니다. 저장 버튼을 눌러 적용하세요.")

                kw_save_col, kw_reset_col = st.columns([2, 1])
                with kw_save_col:
                    save_disabled = not has_kw_changes or len(new_keywords) == 0
                    if st.button(
                        "💾 변경사항 저장",
                        type="primary",
                        use_container_width=True,
                        disabled=save_disabled,
                        key=f"kw_save_{vendor_id}",
                    ):
                        if not new_keywords:
                            st.error("⚠️ 최소 1개 이상의 키워드가 필요합니다.")
                        else:
                            try:
                                update_vendor_keywords(vendor_id, new_keywords)
                                reload_config()
                                st.success(f"✅ **{vendor_name}**의 키워드가 저장되었습니다. ({len(new_keywords)}개)")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 저장 실패: {e}")
                with kw_reset_col:
                    if st.button("↩️ 초기화", use_container_width=True, key=f"kw_reset_{vendor_id}"):
                        st.rerun()

                if not has_kw_changes:
                    st.caption("변경사항이 없습니다.")

                st.divider()

                # ── 양식 파일 관리 ──
                st.markdown("#### 📂 양식 파일 관리")

                # 현재 양식 파일 다운로드
                if form_file:
                    form_path = _get_form_file_path(form_file)
                    if form_path:
                        with open(form_path, "rb") as f:
                            file_bytes = f.read()
                        st.download_button(
                            label=f"📥 현재 양식 다운로드 ({form_file})",
                            data=file_bytes,
                            file_name=form_file,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_form_{vendor_id}",
                            use_container_width=True,
                        )

                        # 양식 파일 미리보기
                        form_df, _ = _load_existing_form(vendor_name)
                        if form_df is not None:
                            with st.expander("📄 양식 파일 미리보기", expanded=False):
                                st.dataframe(form_df, use_container_width=True, height=200)
                    else:
                        st.caption(f"⚠️ {form_file} (파일을 찾을 수 없습니다)")
                else:
                    st.caption("양식 파일이 설정되지 않았습니다.")

                # 양식 파일 업로드/변경
                update_form = st.file_uploader(
                    "새 양식 파일 업로드 (변경)",
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
                                form_fn = _save_form_file(update_form, vendor_name)
                                update_vendor_in_config(vendor_id, {
                                    "target_columns": new_cols,
                                    "form_file": form_fn,
                                })
                                reload_config()
                                st.success("✅ 양식이 업데이트되었습니다!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 양식 업데이트 실패: {e}")

                st.divider()

                # ── 상세 정보 ──
                with st.expander("📋 상세 설정 보기", expanded=False):
                    # target_columns 표시
                    target_cols = v.get("target_columns", [])
                    if target_cols:
                        st.markdown("**대상 칼럼 목록:**")
                        for i, col in enumerate(target_cols, 1):
                            st.text(f"  {i}. {col}")
                    else:
                        st.caption("칼럼이 설정되지 않았습니다.")

                    # rename_map 표시
                    rename_map = v.get("rename_map", {})
                    if rename_map:
                        st.markdown("**칼럼명 매핑 (rename_map):**")
                        for old, new in rename_map.items():
                            st.text(f"  {old} → {new}")

                st.divider()

                # ── 업체 삭제 ──
                st.markdown("#### ⚠️ 위험 영역")

                delete_key = f"confirm_delete_vendor_{vendor_id}"
                if delete_key not in st.session_state:
                    st.session_state[delete_key] = False

                if not st.session_state[delete_key]:
                    if st.button(
                        f"🗑️ '{vendor_name}' 업체 삭제",
                        key=f"delete_vendor_{vendor_id}",
                        type="secondary",
                    ):
                        st.session_state[delete_key] = True
                        st.rerun()
                else:
                    st.warning(f"정말 '{vendor_name}' 업체를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")
                    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 3])
                    with btn_col1:
                        if st.button("✅ 네, 삭제합니다", key=f"confirm_yes_{vendor_id}"):
                            try:
                                remove_vendor_from_config(vendor_id)
                                reload_config()
                                st.session_state[delete_key] = False
                                st.success(f"✅ '{vendor_name}' 업체가 삭제되었습니다.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 삭제 실패: {e}")
                    with btn_col2:
                        if st.button("❌ 취소", key=f"confirm_no_{vendor_id}"):
                            st.session_state[delete_key] = False
                            st.rerun()
    else:
        st.info("등록된 업체가 없습니다. 아래에서 업체를 추가하세요.")

    st.divider()

    # ── 새 업체 추가 ──
    with st.expander("➕ 새 업체 추가", expanded=False):
        with st.form("add_vendor_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input(
                    "업체명 *",
                    placeholder="예: 강화군농협",
                    help="등록할 업체의 이름을 입력하세요."
                )
            with col2:
                new_kw_input = st.text_input(
                    "분류 키워드 *",
                    placeholder="예: 강화 (쉼표로 여러 개 입력 가능)",
                    help="주문서의 '상품약어' 칼럼에서 이 키워드가 포함되면 해당 업체로 분류됩니다."
                )

            form_file = st.file_uploader(
                "📂 주문 양식 엑셀 파일 (선택)",
                type=["xlsx", "xls"],
                help="업체의 고유 주문 양식 파일을 업로드하세요. 칼럼 구조가 자동으로 추출됩니다.",
                key="add_vendor_form_file",
            )

            # 양식 파일 미리보기
            form_columns = []
            if form_file is not None:
                columns, preview_df = _read_form_columns(form_file)
                if columns:
                    form_columns = columns
                    st.markdown("**📊 양식 파일 미리보기:**")
                    st.dataframe(preview_df, use_container_width=True, height=200)
                    st.caption(f"감지된 칼럼 ({len(columns)}개): {', '.join(columns)}")

            submitted = st.form_submit_button(
                "✅ 업체 추가",
                type="primary",
                use_container_width=True,
            )

            if submitted:
                if not new_name or not new_name.strip():
                    st.error("⚠️ 업체명을 입력해주세요.")
                elif not new_kw_input or not new_kw_input.strip():
                    st.error("⚠️ 분류 키워드를 입력해주세요.")
                else:
                    try:
                        keywords_list = [k.strip() for k in new_kw_input.split(",") if k.strip()]

                        form_filename = None
                        target_cols = None
                        if form_file is not None:
                            form_filename = _save_form_file(form_file, new_name.strip())
                            if form_columns:
                                target_cols = form_columns

                        new_id = add_vendor_to_config(
                            name=new_name.strip(),
                            keywords=keywords_list,
                            target_columns=target_cols,
                            form_file=form_filename,
                        )
                        reload_config()
                        st.success(f"✅ '{new_name.strip()}' 업체가 추가되었습니다! (ID: {new_id})")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"⚠️ {e}")
                    except Exception as e:
                        st.error(f"❌ 업체 추가 중 오류 발생: {e}")
