"""
키워드 관리 탭 (keyword_manager.py)

등록된 업체들의 분류 키워드를 조회/수정/삭제하는 UI를 제공합니다.
키워드 최초 생성은 업체 관리 탭에서만 가능합니다.
"""
import streamlit as st
import pandas as pd
from map import (
    get_all_vendors,
    get_vendor_by_id,
    update_vendor_keywords,
    reload_config,
)


def render_keyword_tab():
    """키워드 관리 탭 UI를 렌더링합니다."""
    st.subheader("🏷️ 키워드 관리")
    st.caption("업체별 분류 키워드를 조회하고 수정/삭제할 수 있습니다. 키워드 최초 생성은 업체 관리 탭에서 합니다.")

    vendors = get_all_vendors()
    if not vendors:
        st.info("등록된 업체가 없습니다. 먼저 업체 관리 탭에서 업체를 추가하세요.")
        return

    # ── 키워드 전체 조회 테이블 ──
    st.markdown("### 📋 전체 키워드 목록")

    # 검색 필터
    search_query = st.text_input(
        "🔍 키워드 검색",
        placeholder="업체명이나 키워드를 입력하세요...",
        key="keyword_search"
    )

    keyword_data = []
    for v in vendors:
        keywords = v.get("keywords", [v["name"]])
        for kw in keywords:
            keyword_data.append({
                "업체 ID": v["id"],
                "업체명": v["name"],
                "키워드": kw,
                "키워드 순서": keywords.index(kw) + 1,
            })

    keyword_df = pd.DataFrame(keyword_data)

    # 검색 필터 적용
    if search_query and search_query.strip():
        query = search_query.strip().lower()
        mask = (
            keyword_df["업체명"].str.lower().str.contains(query, na=False) |
            keyword_df["키워드"].str.lower().str.contains(query, na=False)
        )
        keyword_df = keyword_df[mask]

    if keyword_df.empty:
        st.info("검색 결과가 없습니다.")
    else:
        st.dataframe(
            keyword_df[["업체명", "키워드", "키워드 순서"]],
            use_container_width=True,
            hide_index=True,
            height=min(400, len(keyword_df) * 40 + 40),
        )
        st.caption(f"총 {len(keyword_df)}개 키워드 (검색 필터 적용됨)" if search_query else f"총 {len(keyword_df)}개 키워드")

    st.divider()

    # ── 키워드 수정/삭제 섹션 ──
    st.markdown("### ✏️ 키워드 수정")

    vendor_names = [v["name"] for v in vendors]
    selected_vendor_name = st.selectbox(
        "업체 선택",
        options=vendor_names,
        key="keyword_vendor_select"
    )

    if selected_vendor_name:
        vendor = None
        for v in vendors:
            if v["name"] == selected_vendor_name:
                vendor = v
                break

        if vendor:
            current_keywords = list(vendor.get("keywords", [vendor["name"]]))

            st.markdown(f"**현재 키워드 ({len(current_keywords)}개):**")

            # 각 키워드 표시 + 삭제 버튼
            keywords_to_remove = []
            for i, keyword in enumerate(current_keywords):
                kw_col1, kw_col2 = st.columns([4, 1])
                with kw_col1:
                    st.text(f"  {i+1}. {keyword}")
                with kw_col2:
                    if len(current_keywords) > 1:  # 최소 1개 유지
                        if st.button("🗑️", key=f"delete_kw_{vendor['id']}_{i}", help=f"'{keyword}' 키워드 삭제"):
                            keywords_to_remove.append(keyword)
                    else:
                        st.caption("삭제 불가")

            # 키워드 삭제 처리
            if keywords_to_remove:
                new_keywords = [kw for kw in current_keywords if kw not in keywords_to_remove]
                if new_keywords:
                    try:
                        update_vendor_keywords(vendor["id"], new_keywords)
                        reload_config()
                        st.success(f"✅ 키워드가 삭제되었습니다: {', '.join(keywords_to_remove)}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 키워드 삭제 실패: {e}")

            # 키워드 추가 (기존 업체에)
            st.markdown("---")
            add_col1, add_col2 = st.columns([3, 1])
            with add_col1:
                new_keyword = st.text_input(
                    "추가할 키워드",
                    placeholder="새 키워드 입력",
                    key=f"add_kw_input_{vendor['id']}"
                )
            with add_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("➕ 추가", key=f"add_kw_btn_{vendor['id']}"):
                    if new_keyword and new_keyword.strip():
                        new_kw = new_keyword.strip()
                        if new_kw in current_keywords:
                            st.warning(f"⚠️ '{new_kw}' 키워드는 이미 존재합니다.")
                        else:
                            try:
                                updated = current_keywords + [new_kw]
                                update_vendor_keywords(vendor["id"], updated)
                                reload_config()
                                st.success(f"✅ '{new_kw}' 키워드가 추가되었습니다.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 키워드 추가 실패: {e}")
                    else:
                        st.warning("⚠️ 키워드를 입력해주세요.")

            # 키워드 일괄 수정
            with st.expander("📝 키워드 일괄 수정", expanded=False):
                st.caption("쉼표로 구분하여 키워드를 입력하세요. 기존 키워드가 모두 대체됩니다.")
                bulk_keywords = st.text_input(
                    "키워드 목록",
                    value=", ".join(current_keywords),
                    key=f"bulk_kw_{vendor['id']}"
                )
                if st.button("💾 일괄 저장", key=f"bulk_save_{vendor['id']}"):
                    parsed = [k.strip() for k in bulk_keywords.split(",") if k.strip()]
                    if not parsed:
                        st.error("⚠️ 최소 1개 이상의 키워드가 필요합니다.")
                    else:
                        try:
                            update_vendor_keywords(vendor["id"], parsed)
                            reload_config()
                            st.success(f"✅ 키워드가 업데이트되었습니다: {', '.join(parsed)}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 업데이트 실패: {e}")
