# Gap Analysis: security-hardening

- **Feature**: 보안 취약점 개선 (security-hardening)
- **분석일**: 2026-03-11
- **Match Rate**: 100% (Gap 수정 후)

---

## 항목별 분석 결과

| # | 항목 | 심각도 | 일치율 | 상태 |
|---|------|--------|:------:|:----:|
| 1 | Path Traversal 방어 | CRITICAL | 100% | PASS |
| 2 | 파일 업로드 보안 강화 | CRITICAL | 100% | PASS |
| 3 | XSS 방어 | HIGH | 100% | PASS (Gap 수정 완료) |
| 4 | 입력값 검증 | HIGH | 100% | PASS |
| 5 | 에러 메시지 정보 노출 방지 | HIGH | 100% | PASS |
| 6 | 원자적 파일 쓰기 | MEDIUM | 100% | PASS |
| 7 | 업로드 Rate Limiting | MEDIUM | N/A | DEFERRED (Streamlit 환경 제약) |
| 8 | 보안 이벤트 로깅 | MEDIUM | 100% | PASS |

---

## 수정된 Gap 상세

### XSS 방어 Gap (항목 3) - 수정 완료

**위치**: `convert.py:455-457`

**문제**: `file_name_str`이 HTML에 이스케이프 없이 삽입되어 악성 파일명을 통한 XSS 가능

**수정 내용**:
- `import html` 추가
- `{file_name_str}` → `{html.escape(file_name_str)}` 적용
- `{formatted_date}` → `{html.escape(formatted_date)}` 적용

---

## 구현 파일별 변경 요약

### vendor_manager.py
- `_validate_vendor_name()`: 특수문자 제거, 길이 제한 100자
- `_validate_file_upload()`: 크기 10MB, 확장자 화이트리스트, Excel 내용 검증
- `_get_form_file_path()`: Path traversal 방어 (`/`, `\`, `..` 차단 + realpath 검증)
- `_save_form_file_from_bytes()`: 업로드 검증 통합, 안전한 파일명 생성
- `_save_form_file()`: `_save_form_file_from_bytes()` 재사용으로 검증 로직 통합

### convert.py
- `st.exception(e)` 제거 → `logger.exception()` + 일반 에러 메시지
- `html.escape()` 적용으로 XSS 방어
- `logging` 모듈 추가

### map.py
- `_save_config()`: tempfile → shutil.move 원자적 저장 패턴

---

## 테스트 결과

| 테스트 | 결과 |
|--------|------|
| `_get_form_file_path("../../.gitignore")` → `None` | PASS |
| `_get_form_file_path("..\\windows\\system32")` → `None` | PASS |
| `.py` 파일 업로드 → 거부 | PASS |
| 10MB 초과 파일 → 거부 | PASS |
| 가짜 Excel 파일 → 거부 | PASS |
| `<script>alert(1)</script>` vendor name → 특수문자 제거 | PASS |
| 빈 문자열 / 100자 초과 vendor name → `None` | PASS |

---

## 향후 고려사항

1. `vendor_manager.py`의 `st.error(f"...: {e}")` 패턴도 일반 메시지로 교체 검토
2. Streamlit Cloud에서 세션 레벨 Rate Limiting 지원 시 재검토
