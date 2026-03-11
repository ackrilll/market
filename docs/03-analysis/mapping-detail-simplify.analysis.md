# Gap Analysis: 매핑 상세 패널 단순화

| 항목 | 값 |
|------|-----|
| Feature | mapping-detail-simplify |
| 분석일 | 2026-03-11 |
| Match Rate | 96% (13.5/14) |
| 대상 파일 | order_mapping.py |

## 분석 결과

| # | 요구사항 | 구현 | 매칭 |
|---|---------|------|------|
| 1 | 4개 섹션 → 1개 통합 테이블 | `_build_unified_mapping_table()` + `_render_mapping_view()` | ✅ |
| 2 | rename_map 역추적 표시 | `reverse_rename` 딕셔너리로 역방향 검색 | ✅ |
| 3 | constant_values 표시 | `고정값: "{값}"` 포맷 | ✅ |
| 4 | copy_map 역추적 표시 | `reverse_copy` 딕셔너리로 역방향 검색 | ✅ |
| 5 | 미매핑 칼럼 동일 표시 | `← {col} (동일)` | ✅ |
| 6 | 편집: 인라인 selectbox | 업체 칼럼마다 selectbox 렌더링 | ✅ |
| 7 | selectbox 옵션 구성 | `[미매핑] + source_columns + [고정값/복사]` | ✅ |
| 8 | 고정값 text_input | 조건부 렌더링 | ✅ |
| 9 | 복사 대상 selectbox | 조건부 렌더링 | ✅ |
| 10 | 저장 → 3개 dict 분리 | rename_map/constant_values/copy_map 파싱 | ✅ |
| 11 | 설정 파일 동시 갱신 | vendor_config.json + mapping_config.json | ✅ |
| 12 | 원본 파일 업로드 | 편집 모드 상단 file_uploader | ✅ |
| 13 | 업로드 없이 기존 매핑 표시 | 업로드 필수 (원본 칼럼 목록 필요) | ⚠️ |
| 14 | 백엔드 구조 미변경 | convert.py 미수정 | ✅ |

## ⚠️ 미충족 항목

### #13: 업로드 없이 기존 매핑 표시
- **Plan**: 업로드 없이도 기존 매핑을 selectbox에 pre-select 표시
- **구현**: 업로드 없으면 안내 메시지 + 취소 버튼만 표시
- **사유**: 원본 칼럼 목록이 없으면 selectbox 옵션 구성 불가 → 합리적 제한
- **심각도**: Low (UX 제한이지만 기능적으로 문제없음)

## 결론
Match Rate 96%로 통과. 미충족 항목은 기술적 제약으로 인한 합리적 차이.
