# Design: 정산 탭 기능

> **Feature**: settlement-tab
> **Plan**: [settlement-tab.plan.md](../../01-plan/features/settlement-tab.plan.md)
> **Created**: 2026-04-12
> **Status**: Draft

---

## 1. 아키텍처 개요

```
convert.py (메인 앱)
  ├── 주문서 변환    → render_convert_tab()
  ├── 업체 관리      → render_vendor_tab()       (vendor_manager.py)
  ├── 매핑 관리      → render_mapping_tab()      (order_mapping.py)
  ├── 변환 미리보기  → render_preview_tab()      (preview_tab.py)
  └── 정산 [NEW]    → render_settlement_tab()   (settlement_tab.py)
```

기존 탭 패턴(별도 파일에 `render_*_tab()` 함수 → convert.py에서 import & 라우팅)을 동일하게 따른다.

## 2. 파일 변경 목록

| 파일 | 작업 | 변경 내용 |
|------|------|-----------|
| `settlement_tab.py` | **신규** | 정산 탭 전체 UI 및 로직 |
| `convert.py` | **수정** | import 추가, 메뉴 라디오 항목 추가, elif 라우팅 추가 |

## 3. settlement_tab.py 상세 설계

### 3.1 모듈 구조

```python
"""
정산 탭 (settlement_tab.py)

주문 데이터에 농협 매입가와 누계 칼럼을 추가하여 정산용 Excel 파일을 생성합니다.
"""
import streamlit as st
import pandas as pd
import io
import os
import glob


# ── 상수 ──
REFERENCE_DIR = os.path.join("data", "정산", "참조")
SHEET_NAME = "365건강농산"
PRICE_CODE_COL = "품번코드"          # 참조 파일 조회 키
PRICE_VALUE_COL = "매입가"           # 참조 파일 가격 칼럼
INPUT_CODE_COL = "품번코드(필수)"    # 입력 파일 조회 키
INPUT_QTY_COL = "수량"              # 입력 파일 수량 칼럼
OUTPUT_PRICE_COL = "농협 매입가"     # 출력 추가 칼럼 1
OUTPUT_TOTAL_COL = "누계"           # 출력 추가 칼럼 2


def render_settlement_tab():
    ...

def _find_reference_file():
    ...

def _load_price_map(file_data, sheet_name=SHEET_NAME):
    ...

def _process_settlement(df, price_map):
    ...

def _create_settlement_excel(df):
    ...
```

### 3.2 함수별 상세 설계

#### `render_settlement_tab()`

메인 UI 함수. 기존 탭들의 패턴을 따른다.

```
Flow:
1. st.subheader("정산")
2. 참조 파일 영역 (expander)
   - _find_reference_file()로 기존 파일 자동 탐색
   - 있으면 파일명 표시 + 교체 업로드 옵션
   - 없으면 업로드 필수 안내
   - 업로드 시 session_state에 저장 (세션 내 임시 교체)
3. 입력 파일 업로드 (st.file_uploader, type=["xlsx", "xls"])
4. 업로드 완료 시:
   a. 입력 데이터 미리보기 (상위 10행)
   b. "정산 처리" 버튼
5. 버튼 클릭 시:
   a. _load_price_map() → 매입가 딕셔너리
   b. _process_settlement() → 결과 DataFrame + 통계
   c. 결과 통계 표시 (metric cards)
   d. 결과 데이터 미리보기
   e. 미매칭 품번 경고
   f. _create_settlement_excel() → 다운로드 버튼
```

#### `_find_reference_file()`

```python
def _find_reference_file():
    """data/정산/참조/ 폴더에서 .xlsx/.xls 파일을 탐색하여 반환.

    Returns:
        str | None: 참조 파일 경로, 없으면 None
    """
    # glob으로 xlsx/xls 파일 탐색
    # ~$로 시작하는 임시 파일 제외
    # 첫 번째 파일 반환 (보통 1개만 존재)
```

#### `_load_price_map(file_data, sheet_name)`

```python
def _load_price_map(file_data, sheet_name=SHEET_NAME):
    """참조 파일에서 품번코드 → 매입가 딕셔너리를 생성.

    Args:
        file_data: 파일 경로(str) 또는 바이트 데이터(bytes)
        sheet_name: 읽을 시트명 (기본: "365건강농산")

    Returns:
        dict: {품번코드(int/str): 매입가(float)} 매핑

    Raises:
        ValueError: 시트가 없거나 필수 칼럼이 없을 때
    """
    # 1. 시트 읽기 (header 자동 감지 필요 - 참조 파일은 멀티헤더 가능)
    # 2. 품번코드, 매입가 칼럼 존재 확인
    # 3. NaN 행 제거
    # 4. 품번코드를 키, 매입가를 값으로 딕셔너리 생성
    # 5. 품번코드를 정수로 통일 (float→int 변환, 문자열 대응)
```

**참조 파일 시트 구조 (365건강농산)**:
- 행 0: 타이틀/빈 행 (헤더 아님)
- 행 1: 실제 칼럼 헤더 (`품번코드`, `약어`, `상품`, `매입가`, ...)
- 행 2~: 데이터

#### `_process_settlement(df, price_map)`

```python
def _process_settlement(df, price_map):
    """입력 DataFrame에 농협 매입가, 누계 칼럼을 추가.

    Args:
        df: 입력 DataFrame (18열)
        price_map: {품번코드: 매입가} 딕셔너리

    Returns:
        tuple: (result_df, stats_dict)
        - result_df: 20열 DataFrame (농협 매입가, 누계 추가)
        - stats_dict: {
            "total": 전체 데이터 행 수 (빈 행 제외),
            "matched": 매칭 성공 건수,
            "unmatched": 미매칭 건수,
            "unmatched_codes": 미매칭 품번코드 리스트,
            "total_amount": 누계 합산
          }
    """
    # 1. DataFrame 복사
    # 2. 농협 매입가 칼럼 생성:
    #    - 각 행의 품번코드(필수)로 price_map 조회
    #    - 빈 행(all NaN)은 스킵
    #    - 미매칭 시 빈값 처리
    # 3. 누계 칼럼 생성:
    #    - 수량 × 농협 매입가 (둘 다 숫자일 때만)
    # 4. 칼럼 삽입 위치: 수량 칼럼 바로 뒤
    #    - df.columns에서 수량 칼럼 인덱스 찾기
    #    - insert()로 농협 매입가, 누계 순서대로 삽입
    # 5. 통계 계산 및 반환
```

**칼럼 삽입 로직 상세**:
```python
qty_idx = list(result.columns).index(INPUT_QTY_COL)
# 수량 바로 뒤에 삽입 (insert 시 기존 칼럼이 밀림)
result.insert(qty_idx + 1, OUTPUT_PRICE_COL, price_values)
result.insert(qty_idx + 2, OUTPUT_TOTAL_COL, total_values)
```

#### `_create_settlement_excel(df)`

```python
def _create_settlement_excel(df):
    """정산 결과 DataFrame을 Excel 바이너리로 변환.

    기존 convert.py의 create_excel_buffer()와 유사한 스타일 적용.

    Args:
        df: 정산 완료 DataFrame (20열)

    Returns:
        bytes: Excel 파일 바이너리 데이터
    """
    # 1. BytesIO + pd.ExcelWriter
    # 2. 데이터는 1행부터 시작 (헤더만, 수신/발신 행 없음)
    # 3. 자동 너비 조절 (한글 보정 포함 - convert.py 패턴 재사용)
    # 4. AutoFilter 적용
    # 5. 농협 매입가, 누계 칼럼에 숫자 서식 적용 (천단위 콤마)
```

## 4. convert.py 변경 상세

### 4.1 import 추가 (line 25 부근)

```python
from settlement_tab import render_settlement_tab
```

### 4.2 메뉴 항목 추가 (line 911~915)

```python
menu = st.radio(
    "메뉴",
    ["주문서 변환", "업체 관리", "매핑 관리", "변환 미리보기", "정산"],
    label_visibility="collapsed",
)
```

### 4.3 라우팅 추가 (line 927 뒤)

```python
elif menu == "정산":
    render_settlement_tab()
```

## 5. 데이터 흐름도

```
사용자
  │
  ├─ [1] 참조 파일 확인/교체
  │     │
  │     ▼
  │   data/정산/참조/*.xlsx ──┐
  │   또는 업로드 파일 ────────┤
  │                           ▼
  │                    _load_price_map()
  │                    {품번코드: 매입가} dict
  │                           │
  ├─ [2] 입력 파일 업로드      │
  │     │                     │
  │     ▼                     │
  │   pd.read_excel()         │
  │   DataFrame (18열)        │
  │     │                     │
  │     ▼                     │
  │   _process_settlement() ◄─┘
  │     │
  │     ├─ 품번코드(필수) → price_map 조회
  │     ├─ 농협 매입가 칼럼 삽입
  │     ├─ 누계 = 수량 × 농협 매입가
  │     │
  │     ▼
  │   DataFrame (20열) + 통계
  │     │
  │     ├─ [3] 결과 미리보기 (st.dataframe)
  │     ├─ [4] 통계 표시 (metric cards)
  │     └─ [5] Excel 다운로드 (st.download_button)
  │
  ▼
```

## 6. UI 상세 설계

### 6.1 레이아웃

```
┌─────────────────────────────────────────────────────┐
│ 정산                                                 │
│ 주문 데이터에 매입가를 추가하여 정산 파일을 생성합니다    │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ▶ 참조 파일 (상품리스트)  [expander - 기본 닫힘]       │
│ ┌─────────────────────────────────────────────────┐ │
│ │ ✅ 로드됨: 0330_365건강농산 및 직코드...xlsx       │ │
│ │ 상품 329건의 매입가 정보                          │ │
│ │                                                 │ │
│ │ [📁 다른 참조 파일로 교체] (file_uploader)        │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ [📁 정산용 주문 파일 업로드] (.xlsx, .xls)            │
│                                                     │
│ ── 입력 데이터 미리보기 ──  (파일 업로드 후 표시)       │
│ ┌──────────────────────────────────────────────┐    │
│ │ dataframe (상위 10행)                         │    │
│ └──────────────────────────────────────────────┘    │
│                                                     │
│ [🔄 정산 처리]                                      │
│                                                     │
│ ── 정산 결과 ──  (처리 완료 후 표시)                   │
│                                                     │
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│ │ 전체   │ │ 매칭   │ │ 미매칭  │ │ 합계   │        │
│ │  87건  │ │  84건  │ │   3건  │ │ 2,450원│        │
│ └────────┘ └────────┘ └────────┘ └────────┘        │
│                                                     │
│ ⚠️ 미매칭 품번코드: 100059, 100171, ...              │
│                                                     │
│ ┌──────────────────────────────────────────────┐    │
│ │ 결과 dataframe (전체)                         │    │
│ └──────────────────────────────────────────────┘    │
│                                                     │
│ [📥 정산 파일 다운로드]                              │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 6.2 Session State 사용

| Key | Type | 용도 |
|-----|------|------|
| `_settlement_ref_bytes` | bytes | 업로드된 참조 파일 (세션 내 임시 교체용) |

최소한의 session_state만 사용. 결과는 Streamlit의 자연스러운 리렌더링으로 관리.

## 7. 예외 처리 설계

| 상황 | 감지 방법 | UI 처리 |
|------|-----------|---------|
| 참조 파일 없음 (폴더에도 없고 업로드도 없음) | `_find_reference_file()` returns None | `st.warning("참조 파일을 업로드해 주세요")` + 정산 처리 버튼 비활성화 |
| 참조 파일에 시트 없음 | `pd.read_excel` KeyError | `st.error(f"'{SHEET_NAME}' 시트를 찾을 수 없습니다")` |
| 참조 파일에 필수 칼럼 없음 | 칼럼명 체크 | `st.error("품번코드 또는 매입가 칼럼이 없습니다")` |
| 입력 파일에 필수 칼럼 없음 | 칼럼명 체크 | `st.error("품번코드(필수) 또는 수량 칼럼이 없습니다")` |
| 품번코드 미매칭 | price_map에 없는 키 | `st.warning` + 미매칭 코드 목록 표시, 해당 행은 빈값 처리 |
| 수량이 숫자 아님 | `pd.to_numeric(errors='coerce')` | 해당 행 누계를 NaN 처리 |
| 빈 행 (업체 구분선) | 전체 칼럼 NaN 체크 | 그대로 유지, 정산 계산 스킵 |

## 8. 품번코드 매칭 상세

입력 파일과 참조 파일의 품번코드 타입이 다를 수 있음:
- 입력: 정수(`100001`) 또는 문자열(`"100001"`) 또는 float(`100001.0`)
- 참조: 동일하게 다양

**통일 전략**:
```python
def _normalize_code(val):
    """품번코드를 정수 문자열로 통일"""
    if pd.isna(val):
        return None
    try:
        return str(int(float(val)))
    except (ValueError, TypeError):
        return str(val).strip()
```

price_map의 키와 입력 데이터의 품번코드 모두 `_normalize_code()`로 변환 후 매칭.

## 9. 구현 순서

| 순서 | 작업 | 파일 | 예상 범위 |
|------|------|------|-----------|
| 1 | `settlement_tab.py` 생성 - 상수, 유틸 함수 | settlement_tab.py | ~40줄 |
| 2 | `_find_reference_file()`, `_load_price_map()` 구현 | settlement_tab.py | ~40줄 |
| 3 | `_process_settlement()` 구현 | settlement_tab.py | ~50줄 |
| 4 | `_create_settlement_excel()` 구현 | settlement_tab.py | ~30줄 |
| 5 | `render_settlement_tab()` UI 구현 | settlement_tab.py | ~80줄 |
| 6 | convert.py 수정 (import, 메뉴, 라우팅) | convert.py | 3줄 |
| **합계** | | | **~240줄** |

## 10. 검증 기준

| 항목 | 기대 결과 |
|------|-----------|
| 참조 파일 자동 로드 | `data/정산/참조/` 폴더의 xlsx 파일이 자동으로 인식됨 |
| 참조 파일 업로드 교체 | 업로드한 파일이 기존 파일 대신 사용됨 |
| 매입가 조회 | 입력 파일 `품번코드(필수)` → 참조 파일 `매입가` 정확히 매칭 |
| 칼럼 삽입 위치 | `수량` 바로 뒤에 `농협 매입가`, `누계` 순서로 삽입 |
| 누계 계산 | `누계 = 수량 × 농협 매입가` 정확히 일치 |
| 빈 행 유지 | 업체 구분용 빈 행이 원본 그대로 유지됨 |
| 미매칭 표시 | 매칭 실패한 품번코드가 경고로 표시됨 |
| Excel 다운로드 | 정산 완료된 20열 Excel 파일 다운로드 가능 |
| 예시 파일 비교 | output 예시 파일과 동일한 결과 생성 |
