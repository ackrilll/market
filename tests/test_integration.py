"""
통합 테스트 — 업체 추가 → 키워드 설정 → 주문서 변환 파이프라인

Streamlit UI 없이 핵심 변환 로직을 함수 단위로 조합하여,
동적으로 추가된 업체가 분류 → 매핑 → 엑셀 생성까지 정상 동작하는지 검증합니다.
"""
import pytest
import pandas as pd
import io
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from map import (
    add_vendor_to_config,
    remove_vendor_from_config,
    update_vendor_keywords,
    sort_data,
    get_ganghwagun_rename_map,
    get_ganghwagun_target_columns,
    get_constant_values,
    get_copy_map,
    get_vendor_by_id,
)
from convert import create_excel_buffer
import map as map_module


# ──────────────────────── 헬퍼: 변환 파이프라인 핵심 로직 ────────────────────────

def run_conversion_pipeline(idx, sorted_data):
    """convert.py render_convert_tab()의 변환 핵심 로직을 재현합니다.
    
    Streamlit 의존성 없이, 분류된 데이터에 대해 rename → target_columns →
    constant → copy 순으로 적용한 최종 DataFrame을 반환합니다.
    """
    rename_map = get_ganghwagun_rename_map(idx)
    target_columns = get_ganghwagun_target_columns(idx)
    constant_map = get_constant_values(idx)
    copy_map_data = get_copy_map(idx)

    # 중복 컬럼 제거
    df = sorted_data.loc[:, ~sorted_data.columns.duplicated()].copy()

    # rename
    for old_col, new_col in rename_map.items():
        if new_col in df.columns and old_col != new_col:
            df = df.drop(columns=[new_col])
    df = df.rename(columns=rename_map)

    # 누락 컬럼 생성
    for col in target_columns:
        if col not in df.columns:
            df[col] = ""

    df = df.loc[:, ~df.columns.duplicated()].copy()

    # 고정값 적용
    for col, value in constant_map.items():
        if col in df.columns:
            df[col] = value

    # 값 복제
    for origin_col, new_col in copy_map_data.items():
        if origin_col in df.columns and new_col in df.columns:
            df[new_col] = df[origin_col].values

    # 최종 컬럼 순서 적용
    full_df = df[target_columns].copy()

    # 정렬
    if '상품약어' in full_df.columns:
        full_df = full_df.sort_values(by='상품약어', ascending=True, na_position='last').reset_index(drop=True)

    return full_df


# ──────────────────────── 통합 테스트 ────────────────────────

class TestVendorPipeline:
    """업체 추가 → 키워드 설정 → 주문서 변환 End-to-End 테스트"""

    @pytest.fixture(autouse=True)
    def setup_pipeline_vendor(self, setup_test_vendors):
        """각 테스트마다 파이프라인용 테스트 업체를 추가합니다."""
        self.mock_save = setup_test_vendors

        # 파이프라인 테스트용 업체 추가
        self.vendor_id = add_vendor_to_config(
            name="파이프라인테스트업체",
            keywords=["파이프라인테스트"],
            target_columns=["수령인", "상품약어", "수량", "수령인주소", "거래처"],
            rename_map={},
            constant_values={"거래처": "365건강농산"},
            copy_map={},
        )

        # 해당 업체 키워드에 매칭되는 샘플 주문 데이터
        self.sample_df = pd.DataFrame({
            '쇼핑몰': ['네이버', '쿠팡', '11번가'],
            '주문번호': ['ORD-INT-001', 'ORD-INT-002', 'ORD-INT-003'],
            '수취인명': ['홍길동', '김철수', '이영희'],
            '상품약어': [
                '파이프라인테스트 쌀 10kg',
                '파이프라인테스트 현미 5kg',
                '테스트업체A 감자 3kg',  # 다른 업체 (테스트업체A)
            ],
            '수량': [1, 2, 3],
            '수취인전화번호': ['010-1111-1111', '010-2222-2222', '010-3333-3333'],
            '수취인휴대폰': ['010-1111-1111', '010-2222-2222', '010-3333-3333'],
            '수취인우편번호': ['12345', '23456', '34567'],
            '수취인주소': ['서울시 강남구', '부산시 해운대구', '대전시 유성구'],
            '배송메세지': ['부재시 문앞', '', '빠른배송'],
            '주문자명': ['홍길동', '김철수', '이영희'],
            '주문자휴대폰': ['010-1111-1111', '010-2222-2222', '010-3333-3333'],
        })

        yield

    # ── 1. 분류 테스트 ──

    def test_added_vendor_appears_in_sort(self):
        """추가한 업체의 키워드로 주문이 올바르게 분류되는지 확인"""
        result = sort_data(self.sample_df)
        vendor_names = [name for _, name, _ in result]

        assert "파이프라인테스트업체" in vendor_names

        # 해당 업체로 분류된 행 수 확인 (2건)
        for vid, name, df in result:
            if name == "파이프라인테스트업체":
                assert len(df) == 2
                assert all("파이프라인테스트" in row for row in df["상품약어"].values)

    def test_updated_keywords_reclassify(self):
        """키워드 변경 후 새 키워드로 분류가 전환되는지 확인"""
        # 기존 키워드로 분류 확인
        result1 = sort_data(self.sample_df)
        names1 = [name for _, name, _ in result1]
        assert "파이프라인테스트업체" in names1

        # 키워드를 변경 (매칭되지 않는 키워드로)
        update_vendor_keywords(self.vendor_id, ["존재하지않는키워드XYZ"])

        # 변경 후 분류되지 않아야 함
        result2 = sort_data(self.sample_df)
        names2 = [name for _, name, _ in result2]
        assert "파이프라인테스트업체" not in names2

    # ── 2. 매핑 테스트 ──

    def test_rename_map_applied(self):
        """추가 업체의 rename_map이 컬럼명에 올바르게 적용되는지 확인"""
        # 커스텀 rename_map을 가진 업체 추가
        custom_id = add_vendor_to_config(
            name="리네임테스트업체",
            keywords=["리네임테스트"],
            target_columns=["받는분", "품명", "수량"],
            rename_map={"수령인": "받는분", "상품약어": "품명"},
        )

        # 데이터 생성
        df = pd.DataFrame({
            '상품약어': ['리네임테스트 쌀 10kg'],
            '수령인': ['테스트수령인'],
            '수량': [1],
        })

        result = run_conversion_pipeline(custom_id, df)
        assert "받는분" in result.columns
        assert "품명" in result.columns
        assert result["받는분"].iloc[0] == "테스트수령인"

    def test_target_columns_order(self):
        """추가 업체의 target_columns 순서대로 출력되는지 확인"""
        result = sort_data(self.sample_df)
        for vid, name, df in result:
            if name == "파이프라인테스트업체":
                pipeline_result = run_conversion_pipeline(vid, df)
                expected_cols = ["수령인", "상품약어", "수량", "수령인주소", "거래처"]
                assert list(pipeline_result.columns) == expected_cols

    def test_constant_values_injected(self):
        """추가 업체의 constant_values가 모든 행에 적용되는지 확인"""
        result = sort_data(self.sample_df)
        for vid, name, df in result:
            if name == "파이프라인테스트업체":
                pipeline_result = run_conversion_pipeline(vid, df)
                # 모든 행의 '거래처' 컬럼이 '365건강농산'이어야 함
                assert all(pipeline_result["거래처"] == "365건강농산")

    def test_copy_map_applied(self):
        """추가 업체의 copy_map이 값을 올바르게 복제하는지 확인"""
        # copy_map 전용 업체 추가 (constant가 없어서 copy 결과 확인 가능)
        copy_id = add_vendor_to_config(
            name="복사테스트업체",
            keywords=["복사테스트"],
            target_columns=["수령인", "상품약어", "수량", "수령인주소", "배송지주소"],
            copy_map={"수령인주소": "배송지주소"},
        )

        df = pd.DataFrame({
            '상품약어': ['복사테스트 쌀 10kg'],
            '수령인': ['테스트수령인'],
            '수량': [1],
            '수령인주소': ['서울시 강남구 테헤란로 123'],
        })

        pipeline_result = run_conversion_pipeline(copy_id, df)
        # 수령인주소 → 배송지주소로 값이 복제되어야 함
        assert pipeline_result["배송지주소"].iloc[0] == "서울시 강남구 테헤란로 123"

    # ── 3. 엑셀 생성 테스트 ──

    def test_excel_buffer_created(self):
        """create_excel_buffer()가 유효한 xlsx 바이너리를 생성하는지 확인"""
        result = sort_data(self.sample_df)
        for vid, name, df in result:
            if name == "파이프라인테스트업체":
                pipeline_result = run_conversion_pipeline(vid, df)
                excel_bytes = create_excel_buffer(pipeline_result, name)

                # 바이너리 데이터가 비어있지 않아야 함
                assert len(excel_bytes) > 0

                # xlsx 매직 바이트 확인 (PK 헤더 = ZIP 형식)
                assert excel_bytes[:2] == b'PK'

                # openpyxl로 다시 읽어서 데이터가 올바른지 확인
                read_df = pd.read_excel(io.BytesIO(excel_bytes), header=1)
                assert len(read_df) == 2  # 2건의 주문

    # ── 4. 전체 흐름 통합 테스트 ──

    def test_full_pipeline_end_to_end(self):
        """업체 추가 → 키워드 → 분류 → 변환 → 엑셀 생성 전체 파이프라인"""
        # 1. 업체 추가 (setup에서 이미 완료)
        vendor = get_vendor_by_id(self.vendor_id)
        assert vendor is not None
        assert vendor["name"] == "파이프라인테스트업체"

        # 2. 키워드로 분류
        sorted_result = sort_data(self.sample_df)
        pipeline_data = None
        for vid, name, df in sorted_result:
            if vid == self.vendor_id:
                pipeline_data = (vid, name, df)
                break
        assert pipeline_data is not None, "추가된 업체로 분류된 데이터가 없습니다"

        vid, name, sorted_df = pipeline_data

        # 3. 변환 파이프라인 실행
        full_df = run_conversion_pipeline(vid, sorted_df)

        # 4. 결과 검증 — 컬럼 순서
        expected = ["수령인", "상품약어", "수량", "수령인주소", "거래처"]
        assert list(full_df.columns) == expected

        # 5. 결과 검증 — 행 수
        assert len(full_df) == 2

        # 6. 결과 검증 — 고정값
        assert all(full_df["거래처"] == "365건강농산")

        # 7. 엑셀 생성
        excel_bytes = create_excel_buffer(full_df, name)
        assert len(excel_bytes) > 0

        # 8. 엑셀 재읽기 검증
        read_back = pd.read_excel(io.BytesIO(excel_bytes), header=1)
        assert len(read_back) == 2
        assert "수령인" in read_back.columns

    # ── 5. 삭제 후 미분류 테스트 ──

    def test_removed_vendor_not_classified(self):
        """삭제된 업체로는 분류가 되지 않는지 확인"""
        # 분류 확인
        result1 = sort_data(self.sample_df)
        names1 = [name for _, name, _ in result1]
        assert "파이프라인테스트업체" in names1

        # 업체 삭제
        remove_vendor_from_config(self.vendor_id)

        # 삭제 후 분류되지 않아야 함
        result2 = sort_data(self.sample_df)
        names2 = [name for _, name, _ in result2]
        assert "파이프라인테스트업체" not in names2
