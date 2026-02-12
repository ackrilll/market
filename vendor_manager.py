"""
업체 관리 탭 (vendor_manager.py)

업체 추가/삭제, 양식 파일 업로드, 키워드 설정 UI를 제공합니다.
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


def render_vendor_tab():
    """업체 관리 탭 UI를 렌더링합니다."""
    st.subheader("🏭 업체 관리")
    st.caption("업체를 추가/삭제하고, 주문 양식을 업로드하여 칼럼을 설정합니다.")

    # ── 업체 목록 테이블 ──
    vendors = get_all_vendors()

    if vendors:
        st.markdown("### 📋 등록된 업체 목록")
        
        vendor_table_data = []
        for v in vendors:
            keywords = ", ".join(v.get("keywords", [v["name"]]))
            col_count = len(v.get("target_columns", []))
            has_form = v.get("form_file", "")
            vendor_table_data.append({
                "ID": v["id"],
                "업체명": v["name"],
                "키워드": keywords,
                "칼럼 수": col_count,
                "양식 파일": has_form if has_form else "미설정",
            })

        st.dataframe(
            pd.DataFrame(vendor_table_data),
            use_container_width=True,
            hide_index=True,
            height=min(400, len(vendor_table_data) * 40 + 40),
        )
    else:
        st.info("등록된 업체가 없습니다. 아래에서 업체를 추가하세요.")

    st.divider()

    # ── 업체 추가 섹션 ──
    st.markdown("### ➕ 새 업체 추가")

    with st.form("add_vendor_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input(
                "업체명 *",
                placeholder="예: 강화군농협",
                help="등록할 업체의 이름을 입력하세요."
            )
        with col2:
            new_keywords = st.text_input(
                "분류 키워드 *",
                placeholder="예: 강화 (쉼표로 여러 개 입력 가능)",
                help="주문서의 '상품약어' 칼럼에서 이 키워드가 포함되면 해당 업체로 분류됩니다."
            )

        form_file = st.file_uploader(
            "📂 주문 양식 엑셀 파일 (선택)",
            type=["xlsx", "xls"],
            help="업체의 고유 주문 양식 파일을 업로드하세요. 칼럼 구조가 자동으로 추출됩니다."
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
            elif not new_keywords or not new_keywords.strip():
                st.error("⚠️ 분류 키워드를 입력해주세요.")
            else:
                try:
                    # 키워드 파싱 (쉼표 구분)
                    keywords_list = [k.strip() for k in new_keywords.split(",") if k.strip()]
                    
                    # 양식 파일 저장
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

    st.divider()

    # ── 업체 상세 / 삭제 섹션 ──
    if vendors:
        st.markdown("### 🔧 업체 상세 관리")

        vendor_names = [v["name"] for v in vendors]
        selected_name = st.selectbox(
            "관리할 업체 선택",
            options=vendor_names,
            key="vendor_detail_select"
        )

        if selected_name:
            vendor = get_vendor_by_name(selected_name)
            if vendor:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("ID", vendor["id"])
                with col2:
                    st.metric("칼럼 수", len(vendor.get("target_columns", [])))
                with col3:
                    keywords = vendor.get("keywords", [vendor["name"]])
                    st.metric("키워드 수", len(keywords))

                # 키워드 목록
                st.markdown(f"**키워드:** {', '.join(vendor.get('keywords', [vendor['name']]))}")

                # target_columns 표시
                with st.expander("📋 대상 칼럼 목록", expanded=False):
                    target_cols = vendor.get("target_columns", [])
                    if target_cols:
                        for i, col in enumerate(target_cols, 1):
                            st.text(f"  {i}. {col}")
                    else:
                        st.caption("칼럼이 설정되지 않았습니다.")

                # rename_map 표시
                rename_map = vendor.get("rename_map", {})
                if rename_map:
                    with st.expander("🔄 칼럼명 매핑 (rename_map)", expanded=False):
                        for old, new in rename_map.items():
                            st.text(f"  {old} → {new}")

                # 양식 파일 미리보기
                form_df, form_path = _load_existing_form(selected_name)
                if form_df is not None:
                    with st.expander("📄 양식 파일 미리보기", expanded=False):
                        st.dataframe(form_df, use_container_width=True, height=200)
                        st.caption(f"파일: {form_path}")

                # 양식 파일 재업로드
                with st.expander("📤 양식 파일 업데이트", expanded=False):
                    update_form = st.file_uploader(
                        "새 양식 파일 업로드",
                        type=["xlsx", "xls"],
                        key=f"update_form_{vendor['id']}",
                    )
                    if update_form is not None:
                        new_cols, preview = _read_form_columns(update_form)
                        if new_cols:
                            st.dataframe(preview, use_container_width=True, height=150)
                            st.caption(f"감지된 칼럼: {', '.join(new_cols)}")
                            
                            if st.button("📥 양식 적용", key=f"apply_form_{vendor['id']}"):
                                try:
                                    form_fn = _save_form_file(update_form, selected_name)
                                    update_vendor_in_config(vendor["id"], {
                                        "target_columns": new_cols,
                                        "form_file": form_fn,
                                    })
                                    reload_config()
                                    st.success("✅ 양식이 업데이트되었습니다!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 양식 업데이트 실패: {e}")

                # 삭제 버튼
                st.divider()
                st.markdown("#### ⚠️ 위험 영역")
                
                delete_key = f"confirm_delete_vendor_{vendor['id']}"
                if delete_key not in st.session_state:
                    st.session_state[delete_key] = False

                if not st.session_state[delete_key]:
                    if st.button(
                        f"🗑️ '{selected_name}' 업체 삭제",
                        key=f"delete_vendor_{vendor['id']}",
                        type="secondary",
                    ):
                        st.session_state[delete_key] = True
                        st.rerun()
                else:
                    st.warning(f"정말 '{selected_name}' 업체를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")
                    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 3])
                    with btn_col1:
                        if st.button("✅ 네, 삭제합니다", key=f"confirm_yes_{vendor['id']}"):
                            try:
                                remove_vendor_from_config(vendor["id"])
                                reload_config()
                                st.session_state[delete_key] = False
                                st.success(f"✅ '{selected_name}' 업체가 삭제되었습니다.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 삭제 실패: {e}")
                    with btn_col2:
                        if st.button("❌ 취소", key=f"confirm_no_{vendor['id']}"):
                            st.session_state[delete_key] = False
                            st.rerun()
