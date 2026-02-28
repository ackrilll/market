"""
키워드 관리 탭 (keyword_manager.py)

등록된 업체들의 분류 키워드를 st.data_editor 인라인 편집으로 관리합니다.
행 추가/삭제/수정이 테이블 내에서 직접 이루어집니다.
"""
import streamlit as st
import pandas as pd
from map import (
    get_all_vendors,
    update_vendor_keywords,
    reload_config,
)


def render_keyword_tab():
    """키워드 관리 탭 UI를 렌더링합니다."""
    st.subheader(" 키워드 관리")
    st.caption("업체별 분류 키워드를 인라인으로 편집합니다. 키워드를 수정한 뒤 ** 변경사항 저장** 버튼을 누르세요.")

    vendors = get_all_vendors()
    if not vendors:
        st.info("등록된 업체가 없습니다. 먼저 업체 관리 탭에서 업체를 추가하세요.")
        return

    # ── 업체 선택 ──
    vendor_names = [v["name"] for v in vendors]
    selected_name = st.selectbox(
        " 업체 선택",
        options=vendor_names,
        key="kw_vendor_select",
    )

    if not selected_name:
        return

    # 선택된 업체 정보 조회
    vendor = None
    for v in vendors:
        if v["name"] == selected_name:
            vendor = v
            break

    if vendor is None:
        st.error("업체 정보를 찾을 수 없습니다.")
        return

    vendor_id = vendor["id"]
    current_keywords = list(vendor.get("keywords", [vendor["name"]]))

    st.markdown(f"**{selected_name}** — 현재 키워드 **{len(current_keywords)}개**")

    # ── data_editor 기반 인라인 편집 ──
    edit_df = pd.DataFrame({"키워드": current_keywords})

    edited_df = st.data_editor(
        edit_df,
        num_rows="fixed",             # 키워드 1개 고정 — 행 추가/삭제 불가
        use_container_width=True,
        hide_index=True,
        key=f"kw_editor_{vendor_id}",
        column_config={
            "키워드": st.column_config.TextColumn(
                "키워드",
                help="업체 분류에 사용되는 키워드입니다. 주문서의 상품약어에 이 문자열이 포함되면 해당 업체로 분류됩니다.",
                required=True,
            ),
        },
    )

    # ── 변경 감지 및 저장 ──
    # 편집된 키워드 추출 (빈 값 제거)
    new_keywords = [
        str(kw).strip()
        for kw in edited_df["키워드"].tolist()
        if pd.notna(kw) and str(kw).strip()
    ]

    # 변경 여부 체크
    has_changes = new_keywords != current_keywords

    if has_changes:
        st.info(" 키워드가 수정되었습니다. 저장 버튼을 눌러 적용하세요.")

    # 저장 버튼
    save_col, reset_col = st.columns([2, 1])
    with save_col:
        save_disabled = not has_changes or len(new_keywords) == 0
        if st.button(
            " 변경사항 저장",
            type="primary",
            use_container_width=True,
            disabled=save_disabled,
            key=f"kw_save_{vendor_id}",
        ):
            if not new_keywords:
                st.error(" 최소 1개 이상의 키워드가 필요합니다.")
            else:
                try:
                    update_vendor_keywords(vendor_id, new_keywords)
                    reload_config()
                    st.success(f" **{selected_name}**의 키워드가 저장되었습니다. ({len(new_keywords)}개)")
                    st.rerun()
                except Exception as e:
                    st.error(f" 저장 실패: {e}")

    with reset_col:
        if st.button("↩ 초기화", use_container_width=True, key=f"kw_reset_{vendor_id}"):
            st.rerun()

    if not has_changes:
        st.caption("변경사항이 없습니다.")

    # ── 전체 키워드 현황 (읽기 전용) ──
    st.divider()
    with st.expander(" 전체 업체 키워드 현황", expanded=False):
        all_data = []
        for v in vendors:
            keywords = v.get("keywords", [v["name"]])
            all_data.append({
                "업체명": v["name"],
                "키워드": ", ".join(keywords),
                "키워드 수": len(keywords),
            })

        overview_df = pd.DataFrame(all_data)
        st.dataframe(
            overview_df,
            use_container_width=True,
            hide_index=True,
            height=min(500, len(overview_df) * 40 + 40),
        )
        st.caption(f"총 {len(vendors)}개 업체, {sum(d['키워드 수'] for d in all_data)}개 키워드")
