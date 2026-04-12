"""
정산 탭 (settlement_tab.py)

주문 데이터에 농협 매입가와 누계 칼럼을 추가하여 정산용 Excel 파일을 생성합니다.
"""
import streamlit as st
import pandas as pd
import io
import os
import glob as glob_mod

# ── 상수 ──
REFERENCE_DIR = os.path.join("data", "정산", "참조")
SHEET_NAME = "365건강농산"
PRICE_CODE_COL = "품번코드"
PRICE_VALUE_COL = "매입가"
INPUT_CODE_COL = "품번코드(필수)"
INPUT_QTY_COL = "수량"
OUTPUT_PRICE_COL = "농협 매입가"
OUTPUT_TOTAL_COL = "누계"


def _normalize_code(val):
    """품번코드를 정수 문자열로 통일"""
    if pd.isna(val):
        return None
    try:
        return str(int(float(val)))
    except (ValueError, TypeError):
        return str(val).strip()


def _find_reference_file():
    """data/정산/참조/ 폴더에서 .xlsx/.xls 파일을 탐색하여 반환.

    Returns:
        str | None: 참조 파일 경로, 없으면 None
    """
    if not os.path.isdir(REFERENCE_DIR):
        return None
    files = glob_mod.glob(os.path.join(REFERENCE_DIR, "*.xlsx")) + \
            glob_mod.glob(os.path.join(REFERENCE_DIR, "*.xls"))
    # ~$로 시작하는 임시 파일 제외
    files = [f for f in files if not os.path.basename(f).startswith("~$")]
    return files[0] if files else None


def _load_price_map(file_data, sheet_name=SHEET_NAME):
    """참조 파일에서 품번코드 -> 매입가 딕셔너리를 생성.

    Args:
        file_data: 파일 경로(str) 또는 바이트 데이터(bytes)
        sheet_name: 읽을 시트명

    Returns:
        dict: {품번코드(str): 매입가(float)} 매핑

    Raises:
        ValueError: 시트가 없거나 필수 칼럼이 없을 때
    """
    try:
        if isinstance(file_data, bytes):
            raw = pd.read_excel(io.BytesIO(file_data), sheet_name=sheet_name, header=None, nrows=5)
        else:
            raw = pd.read_excel(file_data, sheet_name=sheet_name, header=None, nrows=5)
    except ValueError:
        raise ValueError(f"'{sheet_name}' 시트를 찾을 수 없습니다.")

    # 헤더 행 자동 감지: 품번코드가 포함된 행 찾기
    header_row = 0
    for idx in range(len(raw)):
        row_vals = [str(v).strip() for v in raw.iloc[idx] if pd.notna(v)]
        if PRICE_CODE_COL in row_vals:
            header_row = idx
            break

    if isinstance(file_data, bytes):
        df = pd.read_excel(io.BytesIO(file_data), sheet_name=sheet_name, header=header_row)
    else:
        df = pd.read_excel(file_data, sheet_name=sheet_name, header=header_row)

    if PRICE_CODE_COL not in df.columns or PRICE_VALUE_COL not in df.columns:
        raise ValueError(f"'{PRICE_CODE_COL}' 또는 '{PRICE_VALUE_COL}' 칼럼이 없습니다.")

    # NaN 행 제거 후 딕셔너리 생성
    valid = df[[PRICE_CODE_COL, PRICE_VALUE_COL]].dropna(subset=[PRICE_CODE_COL])
    price_map = {}
    for _, row in valid.iterrows():
        code = _normalize_code(row[PRICE_CODE_COL])
        if code is not None:
            price_map[code] = row[PRICE_VALUE_COL]

    return price_map


def _process_settlement(df, price_map):
    """입력 DataFrame에 농협 매입가, 누계 칼럼을 추가.

    Returns:
        tuple: (result_df, stats_dict)
    """
    result = df.copy()

    price_values = []
    total_values = []
    matched = 0
    unmatched = 0
    unmatched_codes = []

    for idx, row in result.iterrows():
        # 빈 행 (업체 구분선) 체크
        if row.isna().all():
            price_values.append(None)
            total_values.append(None)
            continue

        code = _normalize_code(row.get(INPUT_CODE_COL))
        qty = pd.to_numeric(row.get(INPUT_QTY_COL), errors="coerce")

        if code is None:
            price_values.append(None)
            total_values.append(None)
            continue

        if code in price_map:
            price = price_map[code]
            price_values.append(price)
            if pd.notna(qty) and pd.notna(price):
                total_values.append(qty * price)
            else:
                total_values.append(None)
            matched += 1
        else:
            price_values.append(None)
            total_values.append(None)
            unmatched += 1
            if code not in unmatched_codes:
                unmatched_codes.append(code)

    # 수량 칼럼 바로 뒤에 삽입
    qty_idx = list(result.columns).index(INPUT_QTY_COL)
    result.insert(qty_idx + 1, OUTPUT_PRICE_COL, price_values)
    result.insert(qty_idx + 2, OUTPUT_TOTAL_COL, total_values)

    total_amount = pd.to_numeric(pd.Series(total_values), errors="coerce").sum()

    stats = {
        "total": matched + unmatched,
        "matched": matched,
        "unmatched": unmatched,
        "unmatched_codes": unmatched_codes,
        "total_amount": total_amount,
    }

    return result, stats


def _create_settlement_excel(df):
    """정산 결과 DataFrame을 Excel 바이너리로 변환."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        ws = writer.sheets["Sheet1"]

        ws.protection.sheet = False

        # 자동 너비 조절 (한글 보정 포함)
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    val = str(cell.value)
                    kor_count = sum(1 for c in val if "\uac00" <= c <= "\ud7a3")
                    adj_len = len(val) + int(kor_count * 0.7)
                    max_length = max(max_length, adj_len)
            ws.column_dimensions[col_letter].width = max_length + 2

        # AutoFilter 적용
        if len(df.columns) > 0 and len(df) > 0:
            last_col_letter = ws.cell(row=1, column=len(df.columns)).column_letter
            ws.auto_filter.ref = f"A1:{last_col_letter}{len(df) + 1}"

        # 농협 매입가, 누계 칼럼에 숫자 서식 적용
        col_list = list(df.columns)
        for col_name in [OUTPUT_PRICE_COL, OUTPUT_TOTAL_COL]:
            if col_name in col_list:
                col_idx = col_list.index(col_name) + 1  # 1-based
                for row_num in range(2, len(df) + 2):
                    cell = ws.cell(row=row_num, column=col_idx)
                    if cell.value is not None:
                        cell.number_format = "#,##0"

    return buf.getvalue()


def render_settlement_tab():
    """정산 탭 메인 UI"""
    st.subheader("정산")
    st.caption("주문 데이터에 매입가를 추가하여 정산 파일을 생성합니다")

    # ── 참조 파일 영역 ──
    ref_file_path = _find_reference_file()
    ref_ready = False
    ref_source = None  # 참조 파일 소스 (경로 또는 bytes)

    with st.expander("참조 파일 (상품리스트)", expanded=(ref_file_path is None)):
        if ref_file_path:
            st.success(f"로드됨: {os.path.basename(ref_file_path)}")
            ref_source = ref_file_path
            ref_ready = True

        uploaded_ref = st.file_uploader(
            "다른 참조 파일로 교체" if ref_file_path else "참조 파일 업로드 (필수)",
            type=["xlsx", "xls"],
            key="_settlement_ref_upload",
        )
        if uploaded_ref:
            ref_source = uploaded_ref.getvalue()
            ref_ready = True
            st.success(f"업로드됨: {uploaded_ref.name}")

    if not ref_ready:
        st.warning("참조 파일을 업로드해 주세요.")

    # ── 입력 파일 업로드 ──
    input_file = st.file_uploader(
        "정산용 주문 파일 업로드",
        type=["xlsx", "xls"],
        key="_settlement_input_upload",
    )

    if not input_file:
        return

    input_df = pd.read_excel(input_file)

    # 필수 칼럼 체크
    missing = []
    if INPUT_CODE_COL not in input_df.columns:
        missing.append(INPUT_CODE_COL)
    if INPUT_QTY_COL not in input_df.columns:
        missing.append(INPUT_QTY_COL)
    if missing:
        st.error(f"필수 칼럼이 없습니다: {', '.join(missing)}")
        return

    st.markdown("**입력 데이터 미리보기**")
    st.dataframe(input_df.head(10), use_container_width=True)

    # ── 정산 처리 ──
    if not ref_ready:
        st.button("정산 처리", disabled=True)
        return

    if not st.button("정산 처리", type="primary"):
        return

    # 매입가 맵 로드
    try:
        price_map = _load_price_map(ref_source)
    except ValueError as e:
        st.error(str(e))
        return

    if not price_map:
        st.error("참조 파일에서 매입가 데이터를 읽을 수 없습니다.")
        return

    st.info(f"참조 데이터: 상품 {len(price_map)}건의 매입가 정보 로드 완료")

    # 정산 처리
    result_df, stats = _process_settlement(input_df, price_map)

    # ── 결과 표시 ──
    st.markdown("---")
    st.markdown("**정산 결과**")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("전체", f"{stats['total']}건")
    col2.metric("매칭 성공", f"{stats['matched']}건")
    col3.metric("미매칭", f"{stats['unmatched']}건")
    col4.metric("합계", f"{stats['total_amount']:,.0f}원")

    if stats["unmatched_codes"]:
        st.warning(f"미매칭 품번코드: {', '.join(stats['unmatched_codes'])}")

    st.dataframe(result_df, use_container_width=True)

    # ── 다운로드 ──
    excel_data = _create_settlement_excel(result_df)
    # 입력 파일명에서 날짜 추출하여 출력 파일명 생성
    base_name = os.path.splitext(input_file.name)[0]
    if base_name.endswith("_input"):
        output_name = base_name.replace("_input", "") + ".xlsx"
    else:
        output_name = base_name + "_정산.xlsx"

    st.download_button(
        label="정산 파일 다운로드",
        data=excel_data,
        file_name=output_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
