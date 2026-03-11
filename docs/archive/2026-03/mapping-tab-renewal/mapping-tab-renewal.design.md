# Design Document: 매핑 관리 탭 리뉴얼

> Feature: mapping-tab-renewal
> Created: 2026-03-11
> Phase: Design (retroactive - post-implementation)
> Status: Implemented

---

## 1. Overview

매핑 관리 탭(`order_mapping.py`)의 UX를 리뉴얼한다. 기존의 "원본 업로드 → 업체 선택 → 모드 전환" 순서 대신, **업체 리스트를 먼저 보여주고 클릭하면 상세 패널이 표시**되는 방식으로 변경한다.

### 변경 동기
- 업체 관리 탭과 일관된 UX 제공
- 업체별 매핑 상태를 한눈에 파악 가능
- 매핑 등록/조회/수정 워크플로우 개선

---

## 2. Architecture

### 2.1 UI 구조

```
매핑 관리 탭
├── 분류 기준 칼럼 설정 (st.expander)
│   ├── 원본 파일 업로드
│   ├── 칼럼 버튼 그리드 (5열)
│   └── [저장] 버튼
│
├── 업체 목록 (세로 나열, st.button)
│   ├── 🟢 업체A (매핑 완료 - N개)
│   ├── 🔴 업체B (미매핑)
│   └── ...
│
└── 상세 패널 (업체 클릭 시)
    ├── [매핑 완료] 조회 모드
    │   ├── rename_map 테이블
    │   ├── constant_values 테이블
    │   ├── copy_map 테이블
    │   ├── target_columns 표시
    │   └── [수정] / [초기화] 버튼
    │
    └── [미매핑 or 수정 모드] 편집 모드
        ├── 원본 파일 업로드
        ├── 양식 비교 뷰 (좌우 2컬럼)
        ├── 매핑 추가 UI (selectbox + 고정값)
        ├── 현재 매핑 테이블 + 삭제
        └── [저장] / [취소] 버튼
```

### 2.2 함수 구조

| 함수 | 역할 |
|------|------|
| `render_mapping_tab()` | 메인 진입점: expander + 업체목록 + 상세패널 |
| `_render_classification_section()` | 분류 기준 칼럼 설정 (expander 내부) |
| `_render_vendor_list_and_detail(vendors)` | 업체 목록 렌더링 + 선택 시 상세 패널 |
| `_render_mapping_view(vendor)` | 매핑 조회 모드 (읽기 전용) |
| `_render_mapping_editor(vendor)` | 매핑 등록/수정 모드 (편집) |
| `_render_mapping_edit_ui(...)` | 칼럼 매핑 편집 UI (등록/수정 공통) |
| `_get_mapping_status(vendor)` | 업체 매핑 상태 판단 (🟢/🔴) |
| `_remove_vendor_from_mapping_config(name)` | 초기화 시 mapping_config 정리 |

### 2.3 유틸리티 함수 (기존 재활용)

| 함수 | 변경 |
|------|------|
| `_load_mapping_config()` | 변경 없음 |
| `_save_mapping_config()` | 변경 없음 |
| `_load_vendor_form()` | 변경 없음 |

---

## 3. Data Flow

### 3.1 session_state 키

| 키 | 타입 | 용도 |
|----|------|------|
| `selected_mapping_vendor` | `int \| None` | 현재 선택된 업체 ID |
| `mapping_edit_mode` | `bool` | 수정 모드 여부 |
| `confirm_reset` | `bool` | 초기화 확인 다이얼로그 |
| `mapping_{vendor_name}` | `dict` | 편집 중인 rename_map |
| `constants_{vendor_name}` | `dict` | 편집 중인 constant_values |

### 3.2 매핑 상태 판단

```python
def _get_mapping_status(vendor):
    rename_map = vendor.get("rename_map", {})
    constant_values = vendor.get("constant_values", {})
    has_mapping = bool(rename_map) or bool(constant_values)
    mapping_count = len(rename_map) + len(constant_values)
    return has_mapping, mapping_count
```

### 3.3 저장 흐름

```
매핑 저장 클릭
├── mapping_config.json 갱신 (source_types → vendor_mappings)
├── vendor_config.json 갱신 (rename_map + constant_values)
├── reload_config() 호출
├── session_state 임시 키 정리
└── edit_mode → False (조회 모드로 전환)
```

### 3.4 초기화 흐름

```
초기화 클릭 → 확인 다이얼로그
├── vendor_config.json: rename_map={}, constant_values={}
├── mapping_config.json: 해당 업체 매핑 제거
├── reload_config()
└── 상태 🟢 → 🔴 변경
```

---

## 4. Dependencies

### 4.1 수정 파일

| 파일 | 변경 유형 |
|------|----------|
| `order_mapping.py` | 전면 재작성 |

### 4.2 의존 모듈 (변경 없음)

| 모듈 | 사용하는 함수 |
|------|-------------|
| `map.py` | `get_all_vendors`, `get_vendor_by_id`, `get_vendor_by_name`, `update_vendor_in_config`, `reload_config` |

### 4.3 데이터 파일 (구조 변경 없음)

| 파일 | 용도 |
|------|------|
| `data/mapping_config.json` | 분류기준 + 업체별 칼럼 매핑 |
| `data/vendor_config.json` | 업체 설정 (rename_map, constant_values 등) |

---

## 5. Before/After Comparison

### Before
```
1. 원본 주문서 업로드 (필수 선행)
2. 업체 선택 (selectbox)
3. 모드 선택 (radio: 분류기준 / 칼럼매핑)
4. 모드별 UI 렌더링
```

### After
```
1. 분류 기준 칼럼 설정 (접기/펼치기 expander)
2. 업체 목록 세로 나열 (매핑 상태 표시)
3. 업체 클릭 → 상세 패널
   a. 매핑 완료: 조회 → [수정] / [초기화]
   b. 미매핑: 등록 UI (파일 업로드 → 매핑 편집 → 저장)
```

---

## 6. Verification Checklist

- [ ] 업체 목록이 매핑 상태(🟢/🔴)와 함께 표시되는지
- [ ] 매핑 완료 업체 클릭 시 rename_map, constant_values, copy_map, target_columns 표시
- [ ] 미매핑 업체 클릭 시 매핑 등록 UI 표시
- [ ] 매핑 등록: 파일 업로드 → 칼럼 매핑 → 저장 → 🟢 전환
- [ ] 매핑 수정: [수정] → 편집 → 저장 → 반영
- [ ] 매핑 초기화: [초기화] → 확인 → 🔴 전환
- [ ] 분류 기준 expander 정상 작동
- [ ] 주문서 변환 탭 정상 동작 (매핑 변경 후)
- [ ] 구문 검사 통과
