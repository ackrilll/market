"""
엑셀 파일 읽기 유틸리티 (excel_utils.py)

양식 파일의 실제 헤더 행을 자동 감지하여 "Unnamed" 칼럼 문제를 해결합니다.
"""
import pandas as pd
import io


def _detect_header_row(filepath_or_bytes, max_scan=10):
    """엑셀 파일에서 실제 헤더 행 번호를 감지합니다.

    첫 행이 제목/라벨 행(대부분 빈 셀)인 경우를 처리합니다.
    비어있지 않은 셀이 가장 많은 첫 번째 행을 헤더로 판단합니다.
    """
    try:
        if isinstance(filepath_or_bytes, bytes):
            df_raw = pd.read_excel(io.BytesIO(filepath_or_bytes), header=None, nrows=max_scan)
        else:
            df_raw = pd.read_excel(filepath_or_bytes, header=None, nrows=max_scan)
    except Exception:
        return 0

    if df_raw.empty:
        return 0

    total_cols = len(df_raw.columns)
    best_row = 0
    best_count = 0

    for idx in range(len(df_raw)):
        row = df_raw.iloc[idx]
        non_empty = row.dropna().count()
        # 문자열 셀만 카운트 (헤더는 보통 문자열)
        str_count = sum(1 for v in row if isinstance(v, str) and v.strip())
        score = non_empty + str_count  # 문자열이 많을수록 가산점
        if score > best_count:
            best_count = score
            best_row = idx

    # 첫 행이 이미 최고 점수이면 기본값 사용
    if best_row == 0:
        return 0

    # 최고 행의 비어있지 않은 셀이 전체 칼럼의 30% 이상이어야 헤더로 인정
    row = df_raw.iloc[best_row]
    if row.dropna().count() >= total_cols * 0.3:
        return best_row

    return 0


def read_excel_with_header_detection(filepath_or_bytes, nrows=None):
    """헤더 행을 자동 감지하여 엑셀 파일을 읽습니다.

    Args:
        filepath_or_bytes: 파일 경로(str) 또는 바이트 데이터(bytes)
        nrows: 읽을 데이터 행 수 (None이면 전체)

    Returns:
        pandas DataFrame
    """
    header_row = _detect_header_row(filepath_or_bytes)

    kwargs = {"header": header_row}
    if nrows is not None:
        kwargs["nrows"] = nrows

    if isinstance(filepath_or_bytes, bytes):
        return pd.read_excel(io.BytesIO(filepath_or_bytes), **kwargs)
    else:
        return pd.read_excel(filepath_or_bytes, **kwargs)
