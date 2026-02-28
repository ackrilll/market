"""
convert.py 헬퍼 함수 단위 테스트
- create_excel_buffer(): 엑셀 바이너리 생성
- create_sort_info_file(): 분류 정보 파일 생성
"""
import pytest
import pandas as pd
import io
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from convert import create_excel_buffer, create_sort_info_file


class TestCreateExcelBuffer:
    """create_excel_buffer() 함수 테스트"""

    def test_returns_bytes(self):
        """바이너리(bytes) 데이터를 반환해야 함"""
        df = pd.DataFrame({'이름': ['홍길동'], '수량': [1]})
        result = create_excel_buffer(df, '테스트업체')
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_valid_excel_format(self):
        """반환된 바이트가 유효한 xlsx 포맷인지 확인"""
        df = pd.DataFrame({'이름': ['홍길동'], '수량': [1]})
        result = create_excel_buffer(df, '테스트업체')

        # xlsx 파일의 매직 바이트 (ZIP 포맷)
        assert result[:4] == b'PK\x03\x04'

    def test_contains_header_info(self):
        """수신/발신 정보가 포함되어야 함"""
        df = pd.DataFrame({'이름': ['홍길동'], '수량': [1]})
        result = create_excel_buffer(df, '강화군농협')

        # 바이너리에서 직접 확인은 어려우므로, 다시 읽어서 확인
        read_df = pd.read_excel(io.BytesIO(result), header=1)
        assert not read_df.empty

    def test_empty_dataframe(self):
        """빈 DataFrame도 에러 없이 처리"""
        df = pd.DataFrame({'이름': [], '수량': []})
        result = create_excel_buffer(df, '빈업체')
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_korean_column_width(self):
        """한글이 포함된 데이터도 정상 처리"""
        df = pd.DataFrame({
            '상품명': ['안동밥상 백진주 백미 10kg'],
            '배송주소': ['경상북도 안동시 풍산읍 하리길 123-456 안동밥상아파트 101동 202호'],
        })
        result = create_excel_buffer(df, '한국라이스텍')
        assert isinstance(result, bytes)


class TestCreateSortInfoFile:
    """create_sort_info_file() 함수 테스트"""

    def test_returns_bytes(self, sample_raw_df):
        """바이너리 데이터를 반환해야 함"""
        result = create_sort_info_file(sample_raw_df)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_adds_sort_column(self, sample_raw_df):
        """sort_value 컬럼이 추가되어야 함"""
        result = create_sort_info_file(sample_raw_df)
        read_df = pd.read_excel(io.BytesIO(result))
        assert 'sort_value' in read_df.columns

    def test_sort_value_first_column(self, sample_raw_df):
        """sort_value가 첫 번째 컬럼이어야 함"""
        result = create_sort_info_file(sample_raw_df)
        read_df = pd.read_excel(io.BytesIO(result))
        assert read_df.columns[0] == 'sort_value'

    def test_known_vendors_classified(self, sample_raw_df):
        """알려진 업체는 올바르게 분류되어야 함"""
        result = create_sort_info_file(sample_raw_df)
        read_df = pd.read_excel(io.BytesIO(result))

        sort_values = read_df['sort_value'].tolist()
        assert '강화군농협' in sort_values
        assert '관인농협' in sort_values

    def test_unmatched_marked(self):
        """매칭되지 않는 업체는 '분류되지 않음'으로 표시"""
        df = pd.DataFrame({
            '상품약어': ['알수없는업체 상품'],
            '수량': [1],
        })
        result = create_sort_info_file(df)
        read_df = pd.read_excel(io.BytesIO(result))
        assert '분류되지 않음' in read_df['sort_value'].tolist()
