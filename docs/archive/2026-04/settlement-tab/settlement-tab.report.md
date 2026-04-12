# PDCA Completion Report: settlement-tab (정산 탭)

> **Feature**: settlement-tab
> **완료일**: 2026-04-12
> **Match Rate**: 97%
> **Iteration**: 0회 (첫 구현에서 90% 이상 달성)

---

## 1. 요약

Streamlit 기반 "365 건강농산 주문서 변환 시스템"에 **정산 탭**을 추가하여, 주문 데이터에 농협 매입가와 누계 칼럼을 자동 삽입하는 기능을 구현했다.

## 2. PDCA 진행 이력

| 단계 | 산출물 | 결과 |
|------|--------|------|
| **Plan** | `docs/01-plan/features/settlement-tab.plan.md` | 요구사항 정의, 입출력 데이터 구조, 핵심 로직, UI 설계 |
| **Design** | `docs/02-design/features/settlement-tab.design.md` | 함수 6개 상세 설계, 데이터 흐름도, 예외 처리 7건, 검증 기준 9개 |
| **Do** | `settlement_tab.py` (신규), `convert.py` (수정) | ~230줄 구현, 문법 체크 통과, 예시 데이터 검증 완료 |
| **Check** | `docs/03-analysis/settlement-tab.analysis.md` | Match Rate 97%, 경미한 차이 5건 (기능 영향 없음) |

## 3. 구현 내용

### 3.1 변경 파일

| 파일 | 작업 | 설명 |
|------|------|------|
| `settlement_tab.py` | 신규 | 정산 탭 전체 UI 및 로직 (~230줄) |
| `convert.py` | 수정 | import 1줄, 메뉴 항목 1줄, 라우팅 2줄 추가 |

### 3.2 구현된 함수

| 함수 | 역할 |
|------|------|
| `render_settlement_tab()` | 메인 UI (참조 파일 관리, 입력 업로드, 정산 처리, 결과 표시, 다운로드) |
| `_find_reference_file()` | data/정산/참조/ 폴더에서 참조 파일 자동 탐색 |
| `_load_price_map()` | 365건강농산 시트에서 품번코드→매입가 딕셔너리 생성 |
| `_process_settlement()` | 입력 데이터에 농협 매입가, 누계 칼럼 삽입 + 통계 반환 |
| `_create_settlement_excel()` | 결과 Excel 생성 (한글 너비 보정, AutoFilter, 숫자 서식) |
| `_normalize_code()` | 품번코드 타입 불일치 대응 (float/int/str → 정수 문자열) |

### 3.3 핵심 기능

- **참조 파일 관리**: 폴더 자동 탐색 + 업로드 교체 지원
- **매입가 자동 조회**: 품번코드 기준 매칭 (타입 정규화 포함)
- **칼럼 자동 삽입**: 수량 뒤에 농협 매입가, 누계 순서대로 삽입
- **빈 행 보존**: 업체 구분용 빈 행 원본 유지
- **미매칭 경고**: 참조에 없는 품번코드 목록 표시
- **통계 대시보드**: 전체/매칭/미매칭 건수 + 합계 금액
- **Excel 다운로드**: 스타일 적용된 정산 파일 생성

## 4. 데이터 검증 결과

예시 파일(`data/정산/input/04-10 거래처별 정산_input.xlsx`)로 테스트:

| 항목 | 결과 |
|------|------|
| 칼럼 순서 | 기대 출력과 100% 일치 (20열) |
| 매칭률 | 87/87건 전체 매칭 (미매칭 0건) |
| 농협 매입가 | 84/87 일치 (3건은 참조 파일 가격 변동) |
| 누계 계산 | 수량 x 매입가 정확 일치 |
| 합계 | 4,561,775원 |

## 5. Gap 분석 결과

**종합 Match Rate: 97%** (60항목 중 59항목 일치)

경미한 차이 5건 (모두 기능 영향 없음):
1. Session State 키명 차이 (`_settlement_ref_bytes` → `_settlement_ref_upload`)
2. import 별칭 (`glob` → `glob_mod`)
3. 참조 건수 표시 위치 (expander 내 → 처리 후 info)
4. 출력 파일명 로직 (설계 미기재, 구현에서 추가)
5. 시트 보호 해제 (설계 미기재, 구현에서 추가)

## 6. 추가 라이브러리

없음. 기존 의존성(streamlit, pandas, openpyxl)만 사용.
