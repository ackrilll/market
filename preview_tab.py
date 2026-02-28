"""
변환 미리보기 탭 (preview_tab.py)

엑셀 파일을 업로드하고 목표 업체를 선택하면,
해당 업체 양식에 맞게 변환된 데이터를 미리보기로 표시합니다.
"""
import streamlit as st
import pandas as pd
from map import (
    get_all_vendors,
    get_vendor_by_name,
    get_vendor_by_id,
    sort_data,
    get_ganghwagun_rename_map,
    get_ganghwagun_target_columns,
    get_constant_values,
    get_copy_map,
    get_split_config,
)


def _apply_conversion_pipeline(source_df, vendor_id, vendor_name):
    """업체 설정을 적용하여 변환된 DataFrame을 반환합니다.

    convert.py의 변환 로직과 동일한 파이프라인을 수행합니다.
    """
    rename_map = get_ganghwagun_rename_map(vendor_id)
    target_columns = get_ganghwagun_target_columns(vendor_id)
    constant_map = get_constant_values(vendor_id)
    copy_map = get_copy_map(vendor_id)

    # 1. 중복 컬럼 제거
    working_df = source_df.loc[:, ~source_df.columns.duplicated()].copy()

    # 2. 이름 변경 (중복 제거 포함)
    for old_col, new_col in rename_map.items():
        if new_col in working_df.columns and old_col != new_col:
            working_df = working_df.drop(columns=[new_col])

    renamed_df = working_df.rename(columns=rename_map)

    # 3. 누락 컬럼 빈 값으로 생성
    for col in target_columns:
        if col not in renamed_df.columns:
            renamed_df[col] = ""

    # 중복 컬럼 재제거 (안전장치)
    renamed_df = renamed_df.loc[:, ~renamed_df.columns.duplicated()].copy()

    # 4. 고정값 적용
    for col, value in constant_map.items():
        if col in renamed_df.columns:
            renamed_df[col] = value

    # 5. 컬럼 값 복제
    for origin_col, new_col in copy_map.items():
        if origin_col in renamed_df.columns and new_col in renamed_df.columns:
            renamed_df[new_col] = renamed_df[origin_col].values

    # 6. 최종 컬럼 선택
    result_df = renamed_df[target_columns].copy()

    # 7. 상품약어 기준 정렬
    if '상품약어' in result_df.columns:
        result_df = result_df.sort_values(
            by='상품약어', ascending=True, na_position='last'
        ).reset_index(drop=True)

    return result_df


def render_preview_tab():
    """변환 미리보기 탭 UI를 렌더링합니다."""
    st.subheader(" 변환 미리보기")
    st.caption("엑셀 파일을 업로드하고 업체를 선택하면, 해당 업체 양식으로 변환된 결과를 미리 확인할 수 있습니다.")

    vendors = get_all_vendors()
    if not vendors:
        st.info("등록된 업체가 없습니다. 먼저 업체 관리 탭에서 업체를 추가하세요.")
        return

    # ── 1. 파일 업로드 ──
    st.markdown("###  원본 주문서 업로드")
    uploaded_file = st.file_uploader(
        "원본 주문서 엑셀 파일 (.xlsx)",
        type=["xlsx", "xls"],
        help="사방넷 통합 주문내역 등 변환할 원본 파일을 업로드하세요.",
        key="preview_file_upload",
    )

    if uploaded_file is None:
        st.info(" 원본 주문서 파일을 업로드하세요.")
        return

    # 파일 읽기
    try:
        uploaded_file.seek(0)
        raw_df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f" 파일 읽기 실패: {e}")
        return

    st.success(f" 파일 로드 완료 — {len(raw_df)}행 × {len(raw_df.columns)}열")

    # ── 2. 업체 선택 ──
    st.markdown("###  목표 업체 선택")

    # 분류 실행하여 어떤 업체 데이터가 있는지 확인
    try:
        sorted_data_list = sort_data(raw_df.copy())
    except Exception as e:
        st.error(f" 분류 실패: {e}")
        return

    if not sorted_data_list:
        st.warning(" 원본 파일에서 분류할 수 있는 업체 데이터가 없습니다. "
                   "분류 기준 칼럼과 키워드 설정을 확인하세요.")
        # 파일 컬럼 정보 표시
        with st.expander(" 원본 파일 칼럼 확인"):
            st.write(list(raw_df.columns))
        return

    # 분류된 업체 목록
    available_vendors = [(vid, vname, vdf) for vid, vname, vdf in sorted_data_list]
    vendor_display = [f"{vname} ({len(vdf)}건)" for _, vname, vdf in available_vendors]

    selected_idx = st.selectbox(
        "업체 선택 (분류된 데이터가 있는 업체만 표시)",
        options=range(len(vendor_display)),
        format_func=lambda i: vendor_display[i],
        key="preview_vendor_select",
    )

    if selected_idx is None:
        return

    vendor_id, vendor_name, vendor_df = available_vendors[selected_idx]

    # ── 3. 원본 데이터 (분류된 것) 표시 ──
    st.markdown("###  미리보기")

    col_before, col_after = st.columns(2)

    with col_before:
        st.markdown(f"** 원본 데이터 ({vendor_name}, {len(vendor_df)}건)**")
        st.dataframe(
            vendor_df.head(20),
            use_container_width=True,
            height=400,
        )
        if len(vendor_df) > 20:
            st.caption(f"상위 20건만 표시 (전체 {len(vendor_df)}건)")

    # ── 4. 변환 실행 ──
    try:
        converted_df = _apply_conversion_pipeline(vendor_df, vendor_id, vendor_name)
    except Exception as e:
        with col_after:
            st.error(f" 변환 실패: {e}")
        return

    with col_after:
        st.markdown(f"** 변환 결과 ({vendor_name} 양식, {len(converted_df)}건)**")
        st.dataframe(
            converted_df.head(20),
            use_container_width=True,
            height=400,
        )
        if len(converted_df) > 20:
            st.caption(f"상위 20건만 표시 (전체 {len(converted_df)}건)")

    # ── 5. 변환 요약 ──
    st.divider()
    st.markdown("###  변환 요약")

    rename_map = get_ganghwagun_rename_map(vendor_id)
    target_columns = get_ganghwagun_target_columns(vendor_id)
    constant_map = get_constant_values(vendor_id)
    copy_map = get_copy_map(vendor_id)

    summary_col1, summary_col2, summary_col3 = st.columns(3)

    with summary_col1:
        st.metric(" 데이터 건수", f"{len(converted_df)}건")
        st.metric(" 출력 칼럼 수", f"{len(target_columns)}개")

    with summary_col2:
        st.metric(" 칼럼 매핑", f"{len(rename_map)}개")
        st.metric(" 값 복제", f"{len(copy_map)}개")

    with summary_col3:
        st.metric(" 고정값", f"{len(constant_map)}개")
        if constant_map:
            const_items = [f"`{k}` = `{v}`" for k, v in constant_map.items()]
            st.caption(" · ".join(const_items))

    # ── 6. 상세 설정 확인 (접히는 영역) ──
    with st.expander(" 적용된 설정 상세", expanded=False):
        detail_col1, detail_col2 = st.columns(2)

        with detail_col1:
            st.markdown("**칼럼 매핑 (rename_map)**")
            if rename_map:
                map_data = [{"원본": k, "→": "→", "변환": v} for k, v in rename_map.items()]
                st.dataframe(pd.DataFrame(map_data), hide_index=True, use_container_width=True)
            else:
                st.caption("설정 없음")

        with detail_col2:
            st.markdown("**출력 칼럼 순서 (target_columns)**")
            if target_columns:
                st.dataframe(
                    pd.DataFrame({"순서": range(1, len(target_columns)+1), "칼럼명": target_columns}),
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.caption("설정 없음")
