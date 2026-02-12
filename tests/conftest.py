"""
365 건강농산 주문서 변환기 — 테스트 설정 (conftest.py)
공통 fixture 정의
"""
import pytest
import pandas as pd
import os
import sys
import copy
from unittest.mock import patch

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import map as map_module


@pytest.fixture
def mock_save_config():
    """_save_config를 mock하여 실제 파일 저장을 방지합니다."""
    with patch.object(map_module, '_save_config') as mock_save:
        yield mock_save


@pytest.fixture
def setup_test_vendors(mock_save_config):
    """CRUD 테스트용 초기 상태를 설정하고, 테스트 후 원래 상태로 복원합니다."""
    # 원래 상태를 백업
    original_config = copy.deepcopy(map_module._config)
    original_vendor_map = copy.deepcopy(map_module._vendor_map)
    original_nh_list = list(map_module.nh_list)

    # 테스트용 최소 설정으로 교체
    test_config = {
        "default_rename_map": {"수취인명": "수령인", "상품약어": "상품약어"},
        "default_target_columns": ["수령인", "상품약어", "수량"],
        "vendors": [
            {
                "id": 0,
                "name": "테스트업체A",
                "rename_map": {},
                "target_columns": ["수령인", "상품약어", "수량"],
                "constant_values": {},
                "copy_map": {},
                "split_config": None,
                "keywords": ["테스트A"]
            },
            {
                "id": 1,
                "name": "테스트업체B",
                "rename_map": {"수령인": "받는분"},
                "target_columns": ["받는분", "상품약어", "수량"],
                "constant_values": {"거래처": "365건강농산"},
                "copy_map": {},
                "split_config": None,
                "keywords": ["테스트B"]
            }
        ]
    }
    map_module._config = test_config
    map_module._vendor_map = {v["id"]: v for v in test_config["vendors"]}
    map_module.nh_list = [v["name"] for v in test_config["vendors"]]

    yield mock_save_config  # mock_save_config 객체를 전달하여 호출 여부 검증 가능

    # 복원
    map_module._config = original_config
    map_module._vendor_map = original_vendor_map
    map_module.nh_list = original_nh_list


@pytest.fixture
def sample_raw_df():
    """사방넷 통합 주문내역을 모방하는 샘플 DataFrame"""
    return pd.DataFrame({
        '쇼핑몰': ['네이버', '네이버', '쿠팡', '쿠팡', '11번가'],
        '주문번호': ['ORD001', 'ORD002', 'ORD003', 'ORD004', 'ORD005'],
        '수령인': ['홍길동', '김철수', '이영희', '박민수', '최지은'],
        '상품약어': [
            '강화군농협 쌀 10kg',
            '관인농협 현미 5kg',
            '한국라이스텍 백진주 10kg',
            '청수굴비 영광굴비 세트',
            '파주 임진강쌀 20kg'
        ],
        '수량': [1, 2, 1, 3, 1],
        '수령인 전화번호': ['010-1111-1111', '010-2222-2222', '010-3333-3333', '010-4444-4444', '010-5555-5555'],
        '수령인 휴대폰': ['010-1111-1111', '010-2222-2222', '010-3333-3333', '010-4444-4444', '010-5555-5555'],
        '우편번호': ['12345', '23456', '34567', '45678', '56789'],
        '수령인주소': [
            '인천 강화군 강화읍 123',
            '경기 연천군 관인면 456',
            '경북 안동시 풍산읍 789',
            '전남 영광군 법성면 012',
            '경기 파주시 문산읍 345'
        ],
        '배송메세지': ['부재시 문앞', '경비실', '', '깨지지 않게', '빠른배송'],
        '구매자': ['홍길동', '김철수', '이영희', '박민수', '최지은'],
        '구매자 휴대폰': ['010-1111-1111', '010-2222-2222', '010-3333-3333', '010-4444-4444', '010-5555-5555'],
    })


@pytest.fixture
def sample_sorted_df():
    """sort_data()를 통과한 후의 단일 업체 데이터"""
    return pd.DataFrame({
        '수령인': ['홍길동'],
        '상품약어': ['강화군농협 쌀 10kg'],
        '수량': [1],
        '수령인 전화번호': ['010-1111-1111'],
        '수령인 휴대폰': ['010-1111-1111'],
        '우편번호': ['12345'],
        '수령인주소': ['인천 강화군 강화읍 123'],
        '배송메세지': ['부재시 문앞'],
        '구매자': ['홍길동'],
        '구매자 휴대폰': ['010-1111-1111'],
        'nh_id': [0],
    })
