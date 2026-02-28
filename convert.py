import pandas as pd
import streamlit as st
import io
import zipfile
import re
import os
from map import (
    get_ganghwagun_rename_map,
    get_ganghwagun_target_columns,
    sort_data,
    get_constant_values,
    get_copy_map,
    get_split_config,
    nh_list,
    get_nh_list,
)
from customize_file import get_customize_config, apply_customization
from vendor_manager import render_vendor_tab
from order_mapping import render_mapping_tab
from preview_tab import render_preview_tab

def create_excel_buffer(df, company_name):
    """엑셀 파일을 생성하고 스타일을 적용하여 바이너리 데이터를 반환하는 공통 함수"""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        # 데이터는 2행부터 시작 (startrow=1)
        df.to_excel(writer, index=False, startrow=1, sheet_name='Sheet1')
        ws = writer.sheets['Sheet1']
        
        # 시트 보호 해제 (수정 가능 모드)
        ws.protection.sheet = False
        
        # 상단 수신/발신 정보 기입
        ws.cell(row=1, column=2, value=f"수신: {company_name}")
        # 발신 정보 위치를 마지막 컬럼 쪽으로 자동 조정
        ws.cell(row=1, column=max(2, len(df.columns)), value="발신: 365건강농산")
        
        # 자동 너비 조절 (한글 너비 보정 포함)
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    val = str(cell.value)
                    # 한글 문자를 찾아 너비를 추가로 계산
                    kor_count = sum(1 for c in val if ord(c) >= 0xAC00 and ord(c) <= 0xD7A3)
                    adj_len = len(val) + int(kor_count * 0.7)
                    max_length = max(max_length, adj_len)
            ws.column_dimensions[col_letter].width = max_length + 2
        
        # 엑셀 AutoFilter 적용 (컬럼 헤더에 필터/정렬 드롭다운)
        if len(df.columns) > 0 and len(df) > 0:
            last_col_letter = ws.cell(row=2, column=len(df.columns)).column_letter
            ws.auto_filter.ref = f"A2:{last_col_letter}{len(df) + 2}"
            
    return buf.getvalue()

def create_text_buffer(df):
    """엑셀의 '텍스트(탭 구분)' 내보내기와 동일한 TSV 형식 텍스트 파일 생성"""
    buf = io.StringIO()
    df.to_csv(buf, sep='\t', index=False, encoding='utf-8')
    return buf.getvalue().encode('utf-8-sig')  # BOM 포함 (엑셀 호환)

def create_sort_info_file(raw_df):
    """원본 데이터에 분류 정보를 추가한 엑셀 파일 생성"""
    current_nh_list = get_nh_list()
    # 원본 데이터 복사
    df_with_sort = raw_df.copy()

    # nh_id 초기화
    df_with_sort['nh_id'] = -1

    # 업체명 매핑 (sort_data와 동일한 로직)
    for i, name in enumerate(current_nh_list):
        df_with_sort.loc[df_with_sort['상품약어'].str.contains(name, na=False, regex=False), 'nh_id'] = i

    # sort_value 칼럼 생성
    df_with_sort['sort_value'] = df_with_sort['nh_id'].apply(
        lambda x: current_nh_list[int(x)] if x != -1 and int(x) < len(current_nh_list) else "분류되지 않음"
    )

    # nh_id 칼럼 제거 (임시로만 사용)
    df_with_sort = df_with_sort.drop(columns=['nh_id'])

    # sort_value 칼럼을 맨 앞으로 이동
    cols = ['sort_value'] + [col for col in df_with_sort.columns if col != 'sort_value']
    df_with_sort = df_with_sort[cols]

    # 엑셀 파일 생성
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df_with_sort.to_excel(writer, index=False, sheet_name='분류정보')
        ws = writer.sheets['분류정보']

        # 자동 너비 조절
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    val = str(cell.value)
                    kor_count = sum(1 for c in val if ord(c) >= 0xAC00 and ord(c) <= 0xD7A3)
                    adj_len = len(val) + int(kor_count * 0.7)
                    max_length = max(max_length, adj_len)
            ws.column_dimensions[col_letter].width = max_length + 2

    return buf.getvalue()


# ──────────────────────────────────── 커스텀 스타일 ────────────────────────────────────

def inject_custom_css():
    """Streamlit 앱에 네이버 스마트스토어센터 스타일 CSS를 주입합니다."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap');

    /* ── 전역 폰트 ── */
    html, body, [class*="css"], .stMarkdown, .stRadio label,
    .stButton button, .stCaption, input, textarea, select {
        font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* ── 상단 헤더 바 ── */
    .top-header-bar {
        background: #03C75A;
        padding: 10px 24px;
        margin: -80px -80px 20px -80px;
        display: flex;
        align-items: center;
    }
    .top-header-title {
        font-size: 17px;
        font-weight: 700;
        color: #fff;
        letter-spacing: -0.3px;
    }

    /* Streamlit 기본 헤더 숨김 */
    header[data-testid="stHeader"] {
        display: none !important;
    }

    /* ── 사이드바 스타일 ── */
    section[data-testid="stSidebar"] {
        background: #2b2f3a;
        border-right: 1px solid #3a3e4a;
    }
    section[data-testid="stSidebar"] .stRadio > div {
        gap: 0 !important;
    }
    section[data-testid="stSidebar"] .stRadio > div > label {
        display: flex !important;
        align-items: center;
        padding: 10px 16px !important;
        margin: 0 !important;
        border-radius: 0 !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        color: #b0b8c1 !important;
        cursor: pointer;
        transition: background 0.15s;
        border-left: 3px solid transparent;
    }
    section[data-testid="stSidebar"] .stRadio > div > label:hover {
        background: #363b48 !important;
        color: #e0e0e0 !important;
    }
    section[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"],
    section[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) {
        background: #363b48 !important;
        color: #fff !important;
        font-weight: 600 !important;
        border-left: 3px solid #03C75A;
    }
    /* 라디오 버튼 원형 숨김 */
    section[data-testid="stSidebar"] .stRadio > div > label > div:first-child {
        display: none !important;
    }
    /* 사이드바 내 캐프션/디바이더 색상 */
    section[data-testid="stSidebar"] .stCaption, section[data-testid="stSidebar"] small {
        color: #8a919a !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #3a3e4a !important;
    }

    /* ── 메인 헤더 (기존 카드 타입) ── */
    .main-header {
        background: linear-gradient(135deg, #03C75A 0%, #2DB400 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(3, 199, 90, 0.3);
    }
    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 0.95rem;
    }
    
    /* 파일 정보 카드 */
    .file-info-card {
        background: #f9fafb;
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #03C75A;
        border: 1px solid #e8e8e8;
    }

    /* 결과 메트릭 카드 */
    .metric-card {
        background: white;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        border-top: 3px solid #03C75A;
    }
    .metric-card .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #03C75A;
        line-height: 1.2;
    }
    .metric-card .metric-label {
        font-size: 0.85rem;
        color: #666;
        margin-top: 0.3rem;
    }
    
    /* 실패 메트릭 카드 */
    .metric-card-danger {
        border-top-color: #d32f2f;
    }
    .metric-card-danger .metric-value {
        color: #d32f2f;
    }
    
    /* 진행 상태 텍스트 */
    .progress-text {
        font-size: 0.9rem;
        color: #555;
        margin-bottom: 0.3rem;
    }
    
    /* 사이드바 정보 */
    .sidebar-info {
        background: rgba(3, 199, 90, 0.08);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        font-size: 0.85rem;
    }

    /* ── Streamlit 기본 버튼 색상 오버라이드 ── */
    .stButton > button[kind="primary"],
    button[data-testid="stBaseButton-primary"] {
        background-color: #03C75A !important;
        border-color: #03C75A !important;
    }
    .stButton > button[kind="primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover {
        background-color: #02b350 !important;
        border-color: #02b350 !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ──────────────────────────────────── 주문서 변환 탭 ────────────────────────────────────

def render_convert_tab():
    """주문서 변환 탭 UI를 렌더링합니다."""
    current_nh_list = get_nh_list()

    uploaded_file = st.file_uploader(
        " 사방넷 통합 주문내역 엑셀 파일 (.xlsx)",
        type=["xlsx"],
        help="파일명에 날짜가 포함된 경우 (예: 주문내역_20250126.xlsx) 자동으로 추출합니다."
    )

    if uploaded_file is not None:
        # 1. 파일명에서 날짜 추출 및 형식 변환 (예: 20250126 -> 2025-01-26)
        file_name_str = uploaded_file.name
        date_match = re.search(r'\d{8}', file_name_str)
        
        if date_match:
            raw_date = date_match.group()
            formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
        else:
            formatted_date = "날짜미상"
        
        # 파일 미리보기 정보
        raw_df_preview = pd.read_excel(uploaded_file)
        uploaded_file.seek(0)  # 커서 리셋 (나중에 다시 읽기 위해)
        
        st.markdown(f"""
        <div class="file-info-card">
             <strong>{file_name_str}</strong>&nbsp;&nbsp;│&nbsp;&nbsp;
             날짜: <strong>{formatted_date}</strong>&nbsp;&nbsp;│&nbsp;&nbsp;
             주문 <strong>{len(raw_df_preview):,}건</strong>&nbsp;&nbsp;│&nbsp;&nbsp;
             컬럼 <strong>{len(raw_df_preview.columns)}개</strong>
        </div>
        """, unsafe_allow_html=True)
        
        # 데이터 미리보기 (접기/펴기)
        with st.expander(" 원본 데이터 미리보기", expanded=False):
            st.dataframe(raw_df_preview.head(10), use_container_width=True, height=300)
            if len(raw_df_preview) > 10:
                st.caption(f"상위 10건만 표시 (전체 {len(raw_df_preview):,}건)")
        
        # ── 업체 선택 ──
        with st.expander(" 업체 선택", expanded=True):
            
            # 우선 배치 업체 (관인농협, 오덕쌀, 영광군농협, 한국라이스텍)
            priority_names = ['관인농협', '오덕쌀', '영광군농협', '한국라이스텍']
            priority_indices = [i for i, name in enumerate(current_nh_list) if name in priority_names]
            other_indices = [i for i in range(len(current_nh_list)) if i not in priority_indices]
            ordered_indices = priority_indices + other_indices
            
            # 전체 선택/해제 버튼
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 3])
            with btn_col1:
                if st.button(" 전체 선택", key="btn_select_all", use_container_width=True):
                    for i in ordered_indices:
                        st.session_state[f'vendor_chk_{i}'] = True
                    st.rerun()
            with btn_col2:
                if st.button(" 전체 해제", key="btn_deselect_all", use_container_width=True):
                    for i in ordered_indices:
                        st.session_state[f'vendor_chk_{i}'] = False
                    st.rerun()
            with btn_col3:
                st.caption(f"총 {len(current_nh_list)}개 업체 등록")
            
            # 가로 체크박스 그리드 (5열)
            NUM_COLS = 5
            selected_vendors = []
            cols = st.columns(NUM_COLS)
            for col_idx, vendor_idx in enumerate(ordered_indices):
                name = current_nh_list[vendor_idx]
                
                # 세션 상태에 기본값이 없으면 True로 초기화
                if f'vendor_chk_{vendor_idx}' not in st.session_state:
                    st.session_state[f'vendor_chk_{vendor_idx}'] = True
                
                with cols[col_idx % NUM_COLS]:
                    checked = st.checkbox(
                        name,
                        key=f'vendor_chk_{vendor_idx}',
                    )
                    if checked:
                        selected_vendors.append(name)
        
        # 선택 현황 안내
        if not selected_vendors:
            st.warning(" 선택된 업체가 없습니다. 선택되지 않은 업체의 데이터는 처리되지 않습니다.")
        else:
            st.info(f" **{len(selected_vendors)}개** 업체가 선택되었습니다.")
        

        # ── 변환 실행 ──
        if st.button(" 변환 및 압축파일 생성", type="primary", use_container_width=True):
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            OUTPUT_DIR = os.path.join(BASE_DIR, "data", "converted")
            try:
                # 출력 디렉토리 생성
                if not os.path.exists(OUTPUT_DIR):
                    os.makedirs(OUTPUT_DIR)

                raw_df = pd.read_excel(uploaded_file)
                
                # 1. 원본 데이터 분류
                sorted_data_list = sort_data(raw_df)
                
                # 진행 상태 추적 변수
                processed_files_count = 0
                failed_vendors = []
                total_orders_processed = 0
                
                # 프로그레스 바 초기화
                total_steps = len(sorted_data_list) + 1  # +1 for 분류 정보 파일
                progress_bar = st.progress(0, text="변환 준비 중...")
                status_container = st.empty()
                
                zip_buffer = io.BytesIO()

                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    # 분류 정보 파일 생성
                    progress_bar.progress(0, text=" 분류 정보 파일 생성 중...")
                    try:
                        sort_info_bytes = create_sort_info_file(raw_df)
                        sort_info_filename = f"00_원본파일_분류정보_{formatted_date}.xlsx"
                        zip_file.writestr(sort_info_filename, sort_info_bytes)
                        with open(os.path.join(OUTPUT_DIR, sort_info_filename), "wb") as f:
                            f.write(sort_info_bytes)
                    except Exception as e:
                        st.warning(f" 분류 정보 파일 생성 실패 (변환은 계속됩니다): {e}")

                    for step_idx, (idx, company_name, sorted_data) in enumerate(sorted_data_list):
                        # 프로그레스 바 업데이트
                        progress = (step_idx + 1) / total_steps
                        progress_bar.progress(progress, text=f" {company_name} 처리 중... ({step_idx + 1}/{len(sorted_data_list)})")
                        
                        # [분기 처리]
                        if company_name not in selected_vendors:
                            # 선택되지 않음 → 건너뜀
                            continue
                        
                        # 선택됨 → 변환 프로세스 (업체별 개별 에러 핸들링)
                        try:
                            if sorted_data.empty:
                                continue

                            # 설정 로드
                            rename_map = get_ganghwagun_rename_map(idx)
                            target_columns = get_ganghwagun_target_columns(idx)
                            constant_map = get_constant_values(idx)
                            copy_map = get_copy_map(idx)
                            split_config = get_split_config(idx)
                            
                            # [오류 방지] 원본 데이터의 중복 컬럼 제거
                            sorted_data = sorted_data.loc[:, ~sorted_data.columns.duplicated()].copy()
                            
                            # 2. 이름 변경 (중복 제거 포함)
                            for old_col, new_col in rename_map.items():
                                if new_col in sorted_data.columns and old_col != new_col:
                                    sorted_data = sorted_data.drop(columns=[new_col])
                            
                            renamed_df = sorted_data.rename(columns=rename_map)
                            
                            # 3. 필요한 컬럼 생성 (누락된 경우 빈 값으로 채움)
                            for col in target_columns:
                                if col not in renamed_df.columns:
                                    renamed_df[col] = ""
                            
                            # 생성 후 다시 한번 중복 컬럼 제거 (안전장치)
                            renamed_df = renamed_df.loc[:, ~renamed_df.columns.duplicated()].copy()

                            # 4. [날짜 유실 방지] 파일명 날짜 주입
                            if '날짜' in renamed_df.columns:
                                renamed_df['날짜'] = formatted_date

                            # 5. 고정값(Hardcoding) 일괄 적용
                            for col, value in constant_map.items():
                                if col in renamed_df.columns:
                                    renamed_df[col] = value

                            # 6. 컬럼 값 복제
                            for origin_col, new_col in copy_map.items():
                                if origin_col in renamed_df.columns and new_col in renamed_df.columns:
                                    renamed_df[new_col] = renamed_df[origin_col].values

                            # 최종 데이터프레임 확정
                            full_df = renamed_df[target_columns].copy()
                            
                            # 6.3. 상품약어 기본 오름차순 정렬 + 엑셀 내 AutoFilter는 create_excel_buffer에서 적용
                            if '상품약어' in full_df.columns:
                                full_df = full_df.sort_values(by='상품약어', ascending=True, na_position='last').reset_index(drop=True)

                            # 6.5. 업체별 커스터마이징 적용
                            customize_types = get_customize_config(idx)
                            for customize_type in customize_types:
                                full_df = apply_customization(full_df, idx, customize_type)

                            # 7. 설정 기반 파일 분할 처리 (청수굴비 등)
                            if split_config:
                                end_a, start_b = split_config
                                
                                df_delivery = full_df.loc[:, :end_a].copy()
                                delivery_bytes = create_excel_buffer(df_delivery, company_name)
                                delivery_filename = f"{idx}_{company_name}_롯데출력창.xlsx"
                                zip_file.writestr(delivery_filename, delivery_bytes)
                                with open(os.path.join(OUTPUT_DIR, delivery_filename), "wb") as f:
                                    f.write(delivery_bytes)
                                
                                df_settlement = full_df.loc[:, start_b:].copy()
                                settlement_bytes = create_excel_buffer(df_settlement, company_name)
                                settlement_filename = f"{idx}_{company_name}_메일양식.xlsx"
                                zip_file.writestr(settlement_filename, settlement_bytes)
                                with open(os.path.join(OUTPUT_DIR, settlement_filename), "wb") as f:
                                    f.write(settlement_bytes)
                            else:
                                normal_bytes = create_excel_buffer(full_df, company_name)
                                normal_filename = f"{idx}_{company_name}_양식.xlsx"
                                zip_file.writestr(normal_filename, normal_bytes)
                                with open(os.path.join(OUTPUT_DIR, normal_filename), "wb") as f:
                                    f.write(normal_bytes)
                                
                                # 동송농협(id=23): 텍스트 파일 추가 생성
                                if idx == 23:
                                    txt_bytes = create_text_buffer(full_df)
                                    txt_filename = f"{idx}_{company_name}_양식.txt"
                                    zip_file.writestr(txt_filename, txt_bytes)
                                    with open(os.path.join(OUTPUT_DIR, txt_filename), "wb") as f:
                                        f.write(txt_bytes)
                            
                            processed_files_count += 1
                            total_orders_processed += len(full_df)
                        
                        except Exception as e:
                            failed_vendors.append((company_name, str(e)))
                            continue

                # 프로그레스 완료
                progress_bar.progress(1.0, text=" 변환 완료!")
                
                # ── 결과 대시보드 ──
                st.divider()
                st.subheader(" 변환 결과")
                
                # 결과 메트릭 카드
                m_col1, m_col2, m_col3 = st.columns(3)
                with m_col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{processed_files_count}</div>
                        <div class="metric-label">변환 완료 업체</div>
                    </div>
                    """, unsafe_allow_html=True)
                with m_col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{total_orders_processed:,}</div>
                        <div class="metric-label">처리된 주문건</div>
                    </div>
                    """, unsafe_allow_html=True)
                with m_col3:
                    danger_class = " metric-card-danger" if len(failed_vendors) > 0 else ""
                    st.markdown(f"""
                    <div class="metric-card{danger_class}">
                        <div class="metric-value">{len(failed_vendors)}</div>
                        <div class="metric-label">변환 실패</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # 실패한 업체가 있으면 상세 경고
                if failed_vendors:
                    st.error(f" {len(failed_vendors)}개 업체 변환 실패:")
                    for vendor_name, error_msg in failed_vendors:
                        st.caption(f"  • **{vendor_name}**: {error_msg}")
                
                # 다운로드 버튼
                if processed_files_count > 0:
                    st.divider()
                    dl_col1, dl_col2 = st.columns([2, 1])
                    with dl_col1:
                        st.download_button(
                            label=f" {formatted_date} 결과물 다운로드 (ZIP)",
                            data=zip_buffer.getvalue(),
                            file_name=f"365_주문서_결과물_{formatted_date}.zip",
                            mime="application/zip",
                            use_container_width=True,
                            type="primary"
                        )
                    with dl_col2:
                        st.caption(f" 로컬 저장 완료\n\n`{OUTPUT_DIR}`")
                    st.balloons()
                else:
                    st.info(" 생성된 파일이 없습니다. (선택된 업체에 데이터가 없습니다)")

            except Exception as e:
                st.error(f"치명적 오류 발생: {e}")
                st.exception(e)


# ──────────────────────────────────── 메인 앱 ────────────────────────────────────

def main():
    st.set_page_config(
        page_title="365 건강농산 주문서 변환 시스템",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    inject_custom_css()

    # ── 상단 헤더 바 (네이버 스마트스토어센터 스타일) ──
    st.markdown("""
    <div class="top-header-bar">
        <span class="top-header-title">365건강농산 주문서 변환 시스템</span>
    </div>
    """, unsafe_allow_html=True)
    
    # ── 사이드바: 네비게이션 ──
    current_nh_list = get_nh_list()
    with st.sidebar:
        st.markdown("""
        <div style="padding:16px 0 8px 0;">
            <span style="font-size:22px; font-weight:700; color:#fff;">365 건강농산</span>
        </div>
        """, unsafe_allow_html=True)
        st.caption("주문서 변환 시스템 v3.0")
        st.divider()

        # 네비게이션 메뉴
        menu = st.radio(
            "메뉴",
            ["주문서 변환", "업체 관리", "주문 변환 매핑", "변환 미리보기"],
            label_visibility="collapsed",
        )

        st.caption("v3.0.0 | 2026-02-12")

    # ── 메인 콘텐츠 ──
    if menu == "주문서 변환":
        render_convert_tab()
    elif menu == "업체 관리":
        render_vendor_tab()
    elif menu == "주문 변환 매핑":
        render_mapping_tab()
    elif menu == "변환 미리보기":
        render_preview_tab()



if __name__ == "__main__":
    main()