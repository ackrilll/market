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
    nh_list
)
from customize_file import get_customize_config, apply_customization
import db_manager  # DB 매니저 모듈 추가

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
    # map.py의 업체 리스트 사용 (import됨)
    # nh_list is imported from map


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
        
        # DB 초기화 및 보류 건수 확인
        db_manager.init_db()
        pending_counts = db_manager.get_pending_counts()
        
        # --- 업체 선택 기능 추가 ---
        with st.expander("🏭 업체 선택 (Target Vendor Selection)", expanded=True):
            # 업체 리스트 준비 (보류 데이터 정보 포함)
            pending_counts = db_manager.get_pending_counts()
            
            vendor_options = []
            option_map = {} # 레이블 -> 실제 이름 매핑을 위해 추가
            for i, name in enumerate(nh_list):
                label = name
                if i in pending_counts and pending_counts[i] > 0:
                    label = f"{name} (보류: {pending_counts[i]}건)"
                vendor_options.append(label)
                option_map[label] = name # 매핑 저장

            # 세션 상태 초기화 (처음 한 번만 실행)
            if 'selected_vendors_state' not in st.session_state:
                st.session_state['selected_vendors_state'] = vendor_options

            # 일괄 선택/해제 버튼
            col1, col2, _ = st.columns([1, 1, 3])
            with col1:
                if st.button("✅ 전체 선택"):
                    st.session_state['selected_vendors_state'] = vendor_options
            with col2:
                if st.button("❌ 전체 해제"):
                    st.session_state['selected_vendors_state'] = []
                    
            # 멀티 셀렉트 위젯 (key를 사용하여 session_state와 연동)
            selected_labels = st.multiselect(
                "변환할 업체를 선택하세요:",
                options=vendor_options,
                key='selected_vendors_state',
                help="체크 해제된 업체 데이터는 DB에 저장되었다가, 추후 선택 시 자동으로 합쳐집니다."
            )
            
            # 레이블 -> 실제 이름 변환
            selected_vendors = [option_map[label] for label in selected_labels]
        
        # 아무것도 선택 안 하면 -> 모두 선택한 것으로 간주 (혹은 빈 리스트일 때 처리)
        if not selected_vendors:
            st.warning("선택된 업체가 없습니다. 변환 시 선택되지 않은 업체의 데이터는 모두 '보류' 상태로 저장됩니다.")
        
        if st.button("🚀 변환 및 압축파일 생성"):
            # 선택 여부와 관계없이 프로세스 시작 (저장만 하는 경우도 있으므로)
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            OUTPUT_DIR = os.path.join(BASE_DIR, "data", "coverted")
            try:
                # 출력 디렉토리 생성
                if not os.path.exists(OUTPUT_DIR):
                    os.makedirs(OUTPUT_DIR)
                    st.toast(f"📁 폴더 생성됨: {OUTPUT_DIR}")

                raw_df = pd.read_excel(uploaded_file)
                
                # 1. 원본 데이터 분류 (nh_id 부여) - 이제 모듈 내장 함수가 아니라 convert.py에서 호출
                # sort_data 함수 내부에서 df에 nh_id를 부여함
                sorted_data_list = sort_data(raw_df)
                
                # 원본 데이터프레임에는 nh_id가 없으므로(함수 내부 복사본에서만 작업), 
                # 저장 로직을 위해 다시 한 번 원본에 id 매핑 (혹은 sort_data 리턴값 활용)
                # sort_data가 리스트를 반환하므로, 이를 다시 하나의 DF로 합치거나 각각 처리해야 함.
                # 보류 데이터 저장을 위해 '선택되지 않은' 업체들의 데이터를 수집
                
                # 전체 데이터를 순회하며 저장 vs 처리 분기
                processed_files_count = 0
                
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
                        
                        # [분기 처리]
                        if company_name not in selected_vendors:
                            # A. 선택되지 않음 -> DB에 저장 (Deferred)
                            if not sorted_data.empty:
                                count = db_manager.save_deferred_data(sorted_data, [idx])
                                if count > 0:
                                    st.info(f"💾 {company_name}: {count}건 보류 저장됨")
                            continue
                        
                        else:
                            # B. 선택됨 -> 처리 프로세스
                            
                            # B-1. DB에서 기존 보류 데이터 로드
                            pending_df = db_manager.load_pending_data(idx)
                            
                            if not pending_df.empty:
                                st.toast(f"📥 {company_name}: 보류 데이터 {len(pending_df)}건 로드 및 병합")
                                # 병합 (새 데이터 + 보류 데이터)
                                sorted_data = pd.concat([sorted_data, pending_df], ignore_index=True)
                                
                                # 중복 제거 로직 삭제 (사용자 요청: 중복 허용)
                                # before_dedup = len(sorted_data)
                                # sorted_data = sorted_data.drop_duplicates()
                                # ...
                            
                            if sorted_data.empty:
                                continue

                            # 설정 로드
                            rename_map = get_ganghwagun_rename_map(idx)
                            target_columns = get_ganghwagun_target_columns(idx)
                            constant_map = get_constant_values(idx)
                            copy_map = get_copy_map(idx)
                            split_config = get_split_config(idx)
                            
                            # ... (기존 변환 로직 계속) ...
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

                            # 4. [날짜 유실 방지] 파일명 날짜 주입 (보류 데이터에는 날짜가 이미 있을 수 있음)
                            # 날짜 컬럼이 비어있는 행만 채우거나, 현재 파일 날짜로 덮어쓰거나 정책 결정 필요.
                            # 여기서는 '현재 돌리는 시점'의 파일 날짜로 통일 (요청사항에 따름)
                            if '날짜' in renamed_df.columns:
                                # 기존 값이 없는 경우에만 채우거나, 덮어쓰기
                                # renamed_df['날짜'] = renamed_df['날짜'].replace("", formatted_date) # 빈값만 채우기
                                renamed_df['날짜'] = formatted_date # 일괄 적용 (기존 로직 유지)

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
                            
                            processed_files_count += 1
                            
                            # [완료 후 삭제] 처리가 끝났으므로 보류 데이터 삭제
                            db_manager.delete_pending_data(idx)

                # 최종 다운로드 버튼 생성
                st.divider()
                
                if processed_files_count > 0:
                    st.success(f"💾 {processed_files_count}개 업체 파일 변환 완료! ('{OUTPUT_DIR}')")
                    st.subheader("✅ 변환 완료!")
                    st.download_button(
                        label=f"🎁 {formatted_date} 결과물 다운로드 (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name=f"365_주문서_결과물_{formatted_date}.zip",
                        mime="application/zip"
                    )
                    st.balloons()
                else:
                    st.info("⚠️ 생성된 파일이 없습니다. (선택된 업체에 데이터가 없거나 모두 보류 저장됨)")

            except Exception as e:
                st.error(f"오류 발생: {e}")
                st.exception(e) # 상세 오류 내용 출력
    
    # --- 보류 데이터 관리 및 초기화 섹션 ---
    st.divider()
    with st.expander("🗑️ 보류 데이터 관리 (Manage Pending Data)"):
        # 현재 보류 데이터 다시 확인 (UI 업데이트 후 갱신된 정보가 필요할 수 있음)
        current_pending_counts = db_manager.get_pending_counts()
        
        if not current_pending_counts:
            st.info("현재 보류 중인 데이터가 없습니다.")
        else:
            st.write("초기화(삭제)할 업체를 선택하세요:")
            
            # 보류 데이터가 있는 업체만 필터링하여 옵션 생성
            pending_options = []
            pending_option_map = {}
            
            for idx, count in current_pending_counts.items():
                if count > 0:
                    name = nh_list[idx]
                    label = f"{name} ({count}건)"
                    pending_options.append(label)
                    pending_option_map[label] = idx
            
            # 세션 상태 초기화 (보류 데이터 관리용)
            if 'pending_delete_selection' not in st.session_state:
                st.session_state['pending_delete_selection'] = []

            # 일괄 선택/해제 버튼
            p_col1, p_col2, _ = st.columns([1, 1, 3])
            with p_col1:
                if st.button("✅ 전체 선택", key="btn_select_all_pending"):
                    st.session_state['pending_delete_selection'] = pending_options
            with p_col2:
                if st.button("❌ 전체 해제", key="btn_deselect_all_pending"):
                    st.session_state['pending_delete_selection'] = []

            # 삭제 대상 선택
            selected_to_delete = st.multiselect(
                "삭제할 업체 선택:",
                options=pending_options,
                key='pending_delete_selection',
                help="선택한 업체의 보류 데이터가 영구적으로 삭제됩니다."
            )
            
            if st.button("선택한 업체의 데이터 영구 삭제", type="primary"):
                if not selected_to_delete:
                    st.warning("삭제할 업체를 선택해주세요.")
                else:
                    deleted_count = 0
                    for label in selected_to_delete:
                        idx = pending_option_map[label]
                        db_manager.delete_pending_data(idx)
                        deleted_count += 1
                        
                    st.success(f"{deleted_count}개 업체의 보류 데이터가 삭제되었습니다.")
                    import time
                    time.sleep(1) # 사용자가 메시지를 볼 수 있게 잠시 대기
                    st.rerun() # 페이지 새로고침하여 상태 반영

if __name__ == "__main__":
    main()