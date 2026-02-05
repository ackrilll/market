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
    get_split_config
)
from customize_file import get_customize_config, apply_customization

def create_excel_buffer(df, company_name):
    """엑셀 파일을 생성하고 스타일을 적용하여 바이너리 데이터를 반환하는 공통 함수"""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        # 데이터는 2행부터 시작 (startrow=1)
        df.to_excel(writer, index=False, startrow=1, sheet_name='Sheet1')
        ws = writer.sheets['Sheet1']
        
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
            
    return buf.getvalue()

def create_sort_info_file(raw_df):
    """원본 데이터에 분류 정보를 추가한 엑셀 파일 생성"""
    # map.py의 업체 리스트 (sort_data 함수와 동일)
    nh_list = [
        '강화군농협', '강화라이스', '관인농협', '담양', '당진시농협', '대명엠씨', '더끌림', '독정',
        '무안군농협', '보성군농협', '석곡농협', '신김포농협', '안중농협', '양구군농협', '양구친환경',
        '양구해안지점', '양평군농협', '연천', '영광군농협', '오덕쌀', '오병이어', '율목',
        '이천남부농협', '동송농협', '청수굴비', '파주', '팔탄농협', '한국라이스텍'
    ]

    # 원본 데이터 복사
    df_with_sort = raw_df.copy()

    # nh_id 초기화
    df_with_sort['nh_id'] = -1

    # 업체명 매핑 (sort_data와 동일한 로직)
    for i, name in enumerate(nh_list):
        df_with_sort.loc[df_with_sort['상품약어'].str.contains(name, na=False, regex=False), 'nh_id'] = i

    # sort_value 칼럼 생성
    df_with_sort['sort_value'] = df_with_sort['nh_id'].apply(
        lambda x: nh_list[int(x)] if x != -1 else "분류되지 않음"
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

def main():
    st.set_page_config(page_title="365 건강농산 데이터 도구", layout="wide")
    
    st.title("🌾 365 건강농산 주문서 변환기")
    st.info("파일을 업로드하면 업체별 분류, 컬럼 변환, 파일 분할을 자동으로 수행합니다.")

    uploaded_file = st.file_uploader("샤방넷 통합 주문내역 엑셀 파일을 선택하세요.", type=["xlsx"])

    if uploaded_file is not None:
        # 1. 파일명에서 날짜 추출 및 형식 변환 (예: 20250126 -> 2025-01-26)
        file_name_str = uploaded_file.name
        date_match = re.search(r'\d{8}', file_name_str)
        
        if date_match:
            raw_date = date_match.group()
            formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
        else:
            formatted_date = "날짜미상"
        
        if st.button("🚀 변환 및 압축파일 생성"):
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            OUTPUT_DIR = os.path.join(BASE_DIR, "data", "coverted")
            try:
                # 출력 디렉토리 생성
                if not os.path.exists(OUTPUT_DIR):
                    os.makedirs(OUTPUT_DIR)
                    st.toast(f"📁 폴더 생성됨: {OUTPUT_DIR}")

                raw_df = pd.read_excel(uploaded_file)
                sorted_data_list = sort_data(raw_df)

                zip_buffer = io.BytesIO()

                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    # 분류 정보 파일을 ZIP에 먼저 추가
                    sort_info_bytes = create_sort_info_file(raw_df)
                    sort_info_filename = f"00_원본파일_분류정보_{formatted_date}.xlsx"
                    
                    zip_file.writestr(sort_info_filename, sort_info_bytes)
                    
                    # 로컬 저장
                    with open(os.path.join(OUTPUT_DIR, sort_info_filename), "wb") as f:
                        f.write(sort_info_bytes)

                    for idx, company_name, sorted_data in sorted_data_list:
                        
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

                        # 6. 컬럼 값 복제 (값 복사 시 .values를 사용하여 길이 오류 방지)
                        for origin_col, new_col in copy_map.items():
                            if origin_col in renamed_df.columns and new_col in renamed_df.columns:
                                renamed_df[new_col] = renamed_df[origin_col].values

                        # 최종 데이터프레임 확정
                        full_df = renamed_df[target_columns].copy()

                        # 6.5. 업체별 커스터마이징 적용
                        customize_types = get_customize_config(idx)
                        for customize_type in customize_types:
                            full_df = apply_customization(full_df, idx, customize_type)

                        # 7. 설정 기반 파일 분할 처리 (청수굴비 등)
                        if split_config:
                            end_a, start_b = split_config
                            
                            # 배송용 파일 (시작부터 end_a까지)
                            df_delivery = full_df.loc[:, :end_a].copy()
                            delivery_bytes = create_excel_buffer(df_delivery, company_name)
                            delivery_filename = f"{idx}_{company_name}_롯데출력창.xlsx"
                            
                            zip_file.writestr(delivery_filename, delivery_bytes)
                            
                            # 로컬 저장
                            with open(os.path.join(OUTPUT_DIR, delivery_filename), "wb") as f:
                                f.write(delivery_bytes)
                            
                            # 정산용 파일 (start_b부터 끝까지)
                            df_settlement = full_df.loc[:, start_b:].copy()
                            settlement_bytes = create_excel_buffer(df_settlement, company_name)
                            settlement_filename = f"{idx}_{company_name}_메일양식.xlsx"
                            
                            zip_file.writestr(settlement_filename, settlement_bytes)
                            
                            # 로컬 저장
                            with open(os.path.join(OUTPUT_DIR, settlement_filename), "wb") as f:
                                f.write(settlement_bytes)
                        else:
                            # 일반 단일 파일 생성
                            normal_bytes = create_excel_buffer(full_df, company_name)
                            normal_filename = f"{idx}_{company_name}_양식.xlsx"
                            
                            zip_file.writestr(normal_filename, normal_bytes)
                            
                            # 로컬 저장
                            with open(os.path.join(OUTPUT_DIR, normal_filename), "wb") as f:
                                f.write(normal_bytes)

                # 최종 다운로드 버튼 생성
                st.divider()
                st.success(f"💾 모든 파일이 '{OUTPUT_DIR}' 경로에 저장되었습니다.")
                st.subheader("✅ 변환 완료!")
                st.download_button(
                    label=f"🎁 {formatted_date} 결과물 다운로드 (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=f"365_주문서_결과물_{formatted_date}.zip",
                    mime="application/zip"
                )
                st.balloons()

            except Exception as e:
                st.error(f"오류 발생: {e}")
                st.exception(e) # 상세 오류 내용 출력

if __name__ == "__main__":
    main()