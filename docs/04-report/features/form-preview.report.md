# 양식 파일 미리보기 Completion Report

> **Status**: Complete
>
> **Project**: 365 건강농산 주문서 변환 시스템
> **Feature**: 양식 파일 클릭 시 다운로드 → 미리보기 전환
> **Author**: Development Team
> **Completion Date**: 2026-03-12
> **PDCA Cycle**: #2

---

## 1. Summary

### 1.1 Project Overview

| Item | Content |
|------|---------|
| Feature | 양식 파일 미리보기 (다운로드 → 미리보기 전환) |
| Problem | Streamlit Cloud iframe sandbox 제한으로 양식 파일 다운로드 반복 실패 (6회 시도) |
| Solution | 다운로드 제거, 파일명 클릭 시 `st.dataframe`으로 Excel 내용 화면 표시 |
| Start Date | 2026-03-12 |
| Completion Date | 2026-03-12 |
| Duration | 1 day |
| Design Match Rate | 100% |

### 1.2 Results Summary

```
┌──────────────────────────────────────────────────┐
│  Completion Rate: 100%                            │
├──────────────────────────────────────────────────┤
│  ✅ Complete:     3 / 3 requirements             │
│  ⏳ In Progress:   0 / 3 requirements            │
│  ❌ Cancelled:     0 / 3 requirements            │
└──────────────────────────────────────────────────┘
```

---

## 2. Background: 다운로드 실패 히스토리

| 시도 | 커밋 | 방식 | 실패 원인 |
|------|------|------|----------|
| 1 | `704e13b` | base64 blob JS 자동클릭 | iframe sandbox 차단 |
| 2 | `b00e0ea` | Streamlit Cloud 호환 수정 | 동일 sandbox 제한 |
| 3 | `0f3b665` | data URI 방식 | sandbox blob URL 차단 |
| 4 | `a2b0fd1` | 컴포넌트 내부 직접 처리 | sandbox script 제한 |
| 5 | `3c428f4` | window.open 새 창 | sandbox popup 차단 |
| 6 | `803763e` | srcdoc iframe | sandbox 여전히 제한 |

**결론**: Streamlit Cloud의 iframe sandbox는 모든 다운로드 방식을 차단 → 요구사항 변경: **미리보기로 전환**

---

## 3. Completed Items

### 3.1 Functional Requirements (3/3)

| ID | Requirement | Status | File | Notes |
|----|-------------|--------|------|-------|
| FR-01 | 프론트엔드: `download_request` → `preview_request` | ✅ | `index.html:431-441` | 툴팁도 "미리보기"로 변경 |
| FR-02 | 백엔드: 미리보기 요청 처리 + session_state 관리 | ✅ | `vendor_manager.py:188-195` | rerun으로 상태 반영 |
| FR-03 | 백엔드: Excel 내용 표시 + 닫기 기능 | ✅ | `vendor_manager.py:164-181` | st.expander + st.dataframe |

### 3.2 Technical Implementation

#### FR-01: index.html (프론트엔드)

**변경 내용:**
- `download_request` → `preview_request`
- 툴팁: "클릭하여 다운로드" → "클릭하여 미리보기"

#### FR-02: vendor_manager.py (미리보기 요청 처리)

**추가된 코드:**
```python
pv_req = result.get("preview_request")
if pv_req:
    form_file = pv_req.get("form_file", "")
    if form_file:
        st.session_state["_vendor_preview_file"] = form_file
        st.rerun()
    return
```

#### FR-03: vendor_manager.py (미리보기 표시)

**추가된 코드:**
```python
if "_vendor_preview_file" in st.session_state:
    pv_file = st.session_state["_vendor_preview_file"]
    filepath = _get_form_file_path(pv_file)
    if filepath:
        df = pd.read_excel(filepath)
        with st.expander(f"📄 {pv_file}", expanded=True):
            st.dataframe(df, use_container_width=True, height=400)
            if st.button("닫기", key="_close_preview"):
                del st.session_state["_vendor_preview_file"]
                st.rerun()
```

**제거된 코드:**
- srcdoc iframe 다운로드 로직 전체 (31줄)
- `download_request` 처리 블록 (8줄)

### 3.3 보강 사항 (설계 대비 추가)

| 항목 | 구현 |
|------|------|
| 파일 읽기 실패 | `st.error` + session_state 정리 |
| 파일 미존재 | `st.warning` + session_state 정리 |

---

## 4. Quality Metrics

### 4.1 Gap Analysis

| 설계 항목 | 구현 | Match |
|----------|------|-------|
| `download_request` → `preview_request` | ✅ | 100% |
| srcdoc iframe 코드 제거 | ✅ | 100% |
| session_state 기반 미리보기 흐름 | ✅ | 100% |
| `st.expander` + `st.dataframe` | ✅ | 100% |
| "닫기" 버튼 해제 | ✅ | 100% |
| 불필요 import 정리 | ✅ | 100% |

**Overall Match Rate: 100%** (6/6 requirements)

### 4.2 검증 기준

| # | 검증 항목 | 상태 |
|---|----------|------|
| 1 | 파일명 클릭 → Excel 내용 테이블 표시 | ✅ |
| 2 | "닫기" → 미리보기 사라짐 | ✅ |
| 3 | 다른 파일 클릭 → 새 파일로 전환 | ✅ |
| 4 | Streamlit Cloud 호환 (sandbox 무관) | ✅ |

### 4.3 Code Changes Summary

| File | Type | Lines Changed | Purpose |
|------|------|---------------|---------|
| `index.html` | MODIFIED | 3 | preview_request 전환 |
| `vendor_manager.py` | MODIFIED | -39 / +18 | 다운로드→미리보기 교체 |
| **Net** | | **-21** | 코드 감소 (단순화) |

---

## 5. Lessons Learned

### 5.1 What Went Well

- **요구사항 전환 판단**: 6회 실패 후 다운로드→미리보기로 방향 전환이 올바른 결정
- **코드 단순화**: iframe/base64/sandbox 우회 복잡성 제거, 순수 Streamlit 위젯으로 대체
- **Net negative lines**: 코드가 21줄 줄어들면서 기능은 더 안정적

### 5.2 Key Insight

> Streamlit Cloud의 iframe sandbox는 `allow-downloads`, `allow-popups`, `allow-scripts` 모두 제한.
> 파일 다운로드가 필요한 경우 `st.download_button`을 메인 페이지에서 직접 사용하거나,
> 미리보기로 요구사항을 전환하는 것이 현실적.

---

## 6. Flow Diagram

```
User clicks filename
    ↓
JS: value.preview_request = { vendor_id, form_file }
    ↓
Python: result.get("preview_request")
    ↓
session_state["_vendor_preview_file"] = form_file
    ↓
st.rerun()
    ↓
pd.read_excel(filepath)
    ↓
st.expander + st.dataframe (Excel 내용 표시)
    ↓
"닫기" button → del session_state → st.rerun()
```

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-03-12 | 양식 파일 미리보기 완료 보고서 작성 | Development Team |

---

**Conclusion**: Streamlit Cloud iframe sandbox 제한으로 인한 다운로드 실패 문제를 미리보기 방식으로 전환하여 해결. 코드는 21줄 감소하면서 기능은 더 안정적이고 Streamlit Cloud 호환성이 보장됨.
