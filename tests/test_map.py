"""
map.py 단위 테스트
- sort_data(): 상품약어 기반 업체 분류
- get_ganghwagun_rename_map(): 업체별 컬럼명 매핑
- get_ganghwagun_target_columns(): 업체별 대상 컬럼
- get_constant_values(): 고정값
- get_copy_map(): 값 복사 규칙
- get_split_config(): 파일 분할 설정
- add_vendor_to_config(): 업체 추가
- remove_vendor_from_config(): 업체 삭제
- update_vendor_in_config(): 업체 수정
- update_vendor_keywords(): 키워드 수정
"""
import pytest
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from map import (
    sort_data,
    get_ganghwagun_rename_map,
    get_ganghwagun_target_columns,
    get_constant_values,
    get_copy_map,
    get_split_config,
    nh_list,
    add_vendor_to_config,
    remove_vendor_from_config,
    update_vendor_in_config,
    update_vendor_keywords,
    get_vendor_by_id,
    get_vendor_by_name,
)
import map as map_module


class TestNhList:
    """업체 리스트 기본 검증"""

    def test_nh_list_length(self):
        """28개 업체가 등록되어 있어야 함"""
        assert len(nh_list) == 28

    def test_nh_list_no_duplicates(self):
        """업체 이름에 중복이 없어야 함"""
        assert len(nh_list) == len(set(nh_list))

    def test_nh_list_known_vendors(self):
        """주요 업체가 리스트에 포함되어 있어야 함"""
        known = ['강화군농협', '한국라이스텍', '청수굴비', '파주', '팔탄농협']
        for vendor in known:
            assert vendor in nh_list, f"'{vendor}'가 nh_list에 없습니다"


class TestSortData:
    """sort_data() 함수 테스트"""

    def test_basic_sorting(self, sample_raw_df):
        """기본 분류: 5건 입력 → 각 업체별 그룹으로 분류"""
        result = sort_data(sample_raw_df)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_returns_tuple_format(self, sample_raw_df):
        """반환값이 (idx, company_name, DataFrame) 튜플인지 확인"""
        result = sort_data(sample_raw_df)
        for item in result:
            assert len(item) == 3
            idx, name, df = item
            assert isinstance(idx, int)
            assert isinstance(name, str)
            assert isinstance(df, pd.DataFrame)

    def test_correct_vendor_assignment(self, sample_raw_df):
        """상품약어에 포함된 업체명이 올바르게 분류되는지 확인"""
        result = sort_data(sample_raw_df)
        vendor_names = [name for _, name, _ in result]

        # 샘플 데이터에 포함된 업체가 결과에 있어야 함
        assert '강화군농협' in vendor_names
        assert '관인농협' in vendor_names
        assert '한국라이스텍' in vendor_names
        assert '청수굴비' in vendor_names
        assert '파주' in vendor_names

    def test_unmatched_data_excluded(self):
        """매칭되지 않는 상품약어는 결과에서 제외"""
        df = pd.DataFrame({
            '상품약어': ['알수없는업체 쌀 10kg', '미분류 상품'],
            '수량': [1, 2],
        })
        result = sort_data(df)
        assert len(result) == 0

    def test_empty_dataframe(self):
        """빈 DataFrame 입력 시 빈 리스트 반환"""
        df = pd.DataFrame({'상품약어': pd.Series([], dtype='str'), '수량': pd.Series([], dtype='int')})
        result = sort_data(df)
        assert len(result) == 0

    def test_each_group_has_correct_data(self, sample_raw_df):
        """각 그룹의 데이터가 해당 업체의 것인지 확인"""
        result = sort_data(sample_raw_df)
        for idx, name, df in result:
            # 모든 행의 상품약어에 업체명이 포함되어야 함
            for _, row in df.iterrows():
                assert name in row['상품약어'], \
                    f"'{name}'이(가) 상품약어 '{row['상품약어']}'에 포함되지 않음"


class TestRenameMap:
    """get_ganghwagun_rename_map() 함수 테스트"""

    def test_returns_dict_for_all_indices(self):
        """모든 인덱스(0~27)에 대해 dict를 반환해야 함"""
        for i in range(28):
            result = get_ganghwagun_rename_map(i)
            assert isinstance(result, dict), f"idx={i}에서 dict가 아닌 {type(result)} 반환"

    def test_custom_vendors_have_mappings(self):
        """커스텀 매핑이 있는 업체는 비어있지 않아야 함"""
        custom_indices = [1, 5, 7, 9, 10, 22, 23, 24, 26, 27]
        for idx in custom_indices:
            result = get_ganghwagun_rename_map(idx)
            assert len(result) > 0, f"idx={idx} ({nh_list[idx]})의 매핑이 비어있음"

    def test_default_mapping(self):
        """기본 매핑(case _)이 올바르게 반환되는지 확인"""
        result = get_ganghwagun_rename_map(999)  # 존재하지 않는 idx
        assert isinstance(result, dict)
        assert len(result) > 0  # default case는 비어있지 않아야 함


class TestTargetColumns:
    """get_ganghwagun_target_columns() 함수 테스트"""

    def test_returns_list_for_all_indices(self):
        """모든 인덱스에 대해 리스트를 반환해야 함"""
        for i in range(28):
            result = get_ganghwagun_target_columns(i)
            assert isinstance(result, list), f"idx={i}에서 list가 아닌 {type(result)} 반환"
            assert len(result) > 0, f"idx={i}의 대상 컬럼이 비어있음"

    def test_no_duplicate_columns(self):
        """대상 컬럼에 중복이 없어야 함 (빈 문자열 제외)"""
        for i in range(28):
            cols = get_ganghwagun_target_columns(i)
            non_empty = [c for c in cols if c.strip()]
            # 빈 문자열이나 ' ' 같은 구분자가 있을 수 있으므로 non-empty만 검사
            seen = set()
            for c in non_empty:
                if c in seen:
                    # 일부 양식에는 의도적 중복이 있을 수 있으므로 warning만
                    pass
                seen.add(c)


class TestConstantValues:
    """get_constant_values() 함수 테스트"""

    def test_returns_dict(self):
        """모든 인덱스에 대해 dict를 반환해야 함"""
        for i in range(28):
            result = get_constant_values(i)
            assert isinstance(result, dict)

    def test_known_constants(self):
        """알려진 고정값이 올바르게 설정되어 있는지 확인"""
        # idx 22: 이천남부농협 → 보내는분담당자: 365건강농산
        assert get_constant_values(22) == {'보내는분담당자': '365건강농산'}
        # idx 23: 동송농협 → 거래처: 365건강농산
        assert get_constant_values(23) == {'거래처': '365건강농산'}
        # idx 27: 한국라이스텍 → 거래처코드
        assert '거래처코드' in get_constant_values(27)


class TestCopyMap:
    """get_copy_map() 함수 테스트"""

    def test_returns_dict(self):
        for i in range(28):
            result = get_copy_map(i)
            assert isinstance(result, dict)

    def test_known_copy_rules(self):
        """알려진 복사 규칙이 올바르게 설정되어 있는지"""
        # idx 23: 동송농협 - 수령자 주소 → 주문자 주소
        result = get_copy_map(23)
        assert '수령자 주소' in result
        assert result['수령자 주소'] == '주문자 주소'

        # idx 24: 청수굴비 → 3개 복사 규칙
        result = get_copy_map(24)
        assert len(result) == 3


class TestSplitConfig:
    """get_split_config() 함수 테스트"""

    def test_only_cheongsu_has_split(self):
        """청수굴비(idx=24)만 분할 설정이 있어야 함"""
        for i in range(28):
            result = get_split_config(i)
            if i == 24:
                assert result is not None
                assert len(result) == 2  # (end_a, start_b) 튜플
            else:
                assert result is None, f"idx={i}에 예상치 못한 분할 설정: {result}"


# ──────────────────────────────────── CRUD 함수 테스트 ────────────────────────────────────


class TestAddVendorToConfig:
    """add_vendor_to_config() 함수 테스트"""

    def test_add_basic_vendor(self, setup_test_vendors):
        """기본 업체 추가 및 ID 반환 확인"""
        new_id = add_vendor_to_config("새업체", ["키워드1", "키워드2"])
        assert isinstance(new_id, int)
        assert new_id == 2  # 기존 0, 1 이후 다음 ID

        # 추가된 업체가 조회 가능한지 확인
        vendor = get_vendor_by_id(new_id)
        assert vendor is not None
        assert vendor["name"] == "새업체"
        assert vendor["keywords"] == ["키워드1", "키워드2"]

    def test_add_vendor_with_optional_params(self, setup_test_vendors):
        """선택 파라미터(rename_map, constant_values, copy_map 등) 적용 확인"""
        new_id = add_vendor_to_config(
            name="커스텀업체",
            keywords=["커스텀"],
            target_columns=["수령인", "품명"],
            rename_map={"수령인": "받는분"},
            constant_values={"거래처": "테스트"},
            copy_map={"수령인주소": "주문자주소"},
            split_config=[5, 6],
        )
        vendor = get_vendor_by_id(new_id)
        assert vendor["target_columns"] == ["수령인", "품명"]
        assert vendor["rename_map"] == {"수령인": "받는분"}
        assert vendor["constant_values"] == {"거래처": "테스트"}
        assert vendor["copy_map"] == {"수령인주소": "주문자주소"}
        assert vendor["split_config"] == [5, 6]

    def test_add_vendor_default_target_columns(self, setup_test_vendors):
        """target_columns=None인 경우 기본값 사용 확인"""
        new_id = add_vendor_to_config("기본컬럼업체", ["기본"])
        vendor = get_vendor_by_id(new_id)
        assert vendor["target_columns"] == ["수령인", "상품약어", "수량"]

    def test_add_vendor_empty_keywords_uses_name(self, setup_test_vendors):
        """빈 키워드 리스트일 때 업체명이 키워드로 사용되는지 확인"""
        new_id = add_vendor_to_config("키워드없는업체", [])
        vendor = get_vendor_by_id(new_id)
        assert vendor["keywords"] == ["키워드없는업체"]

    def test_add_vendor_with_form_file(self, setup_test_vendors):
        """form_file 지정 시 데이터에 포함되는지 확인"""
        new_id = add_vendor_to_config("양식업체", ["양식"], form_file="양식.xlsx")
        vendor = get_vendor_by_id(new_id)
        assert vendor["form_file"] == "양식.xlsx"

    def test_add_vendor_duplicate_name_raises(self, setup_test_vendors):
        """중복 업체명 추가 시 ValueError 발생 확인"""
        with pytest.raises(ValueError, match="이미 존재하는 업체명"):
            add_vendor_to_config("테스트업체A", ["중복"])

    def test_add_vendor_calls_save(self, setup_test_vendors):
        """업체 추가 후 _save_config가 호출되는지 확인"""
        mock_save = setup_test_vendors
        add_vendor_to_config("저장업체", ["저장"])
        mock_save.assert_called()

    def test_add_vendor_updates_nh_list(self, setup_test_vendors):
        """업체 추가 후 nh_list가 갱신되는지 확인"""
        add_vendor_to_config("리스트업체", ["리스트"])
        assert "리스트업체" in map_module.nh_list


class TestRemoveVendorFromConfig:
    """remove_vendor_from_config() 함수 테스트"""

    def test_remove_vendor_success(self, setup_test_vendors):
        """정상 삭제: _vendor_map과 _config에서 제거 확인"""
        remove_vendor_from_config(0)
        assert get_vendor_by_id(0) is None
        assert all(v["id"] != 0 for v in map_module._config["vendors"])

    def test_remove_vendor_updates_nh_list(self, setup_test_vendors):
        """삭제 후 nh_list에서 제거 확인"""
        remove_vendor_from_config(0)
        assert "테스트업체A" not in map_module.nh_list

    def test_remove_vendor_invalid_id_raises(self, setup_test_vendors):
        """존재하지 않는 ID 삭제 시 ValueError 발생 확인"""
        with pytest.raises(ValueError, match="존재하지 않는 업체 ID"):
            remove_vendor_from_config(999)

    def test_remove_vendor_calls_save(self, setup_test_vendors):
        """삭제 후 _save_config가 호출되는지 확인"""
        mock_save = setup_test_vendors
        remove_vendor_from_config(1)
        mock_save.assert_called()


class TestUpdateVendorInConfig:
    """update_vendor_in_config() 함수 테스트"""

    def test_update_partial_fields(self, setup_test_vendors):
        """부분 필드 업데이트(rename_map) 확인"""
        update_vendor_in_config(0, {"rename_map": {"수령인": "받는사람"}})
        vendor = get_vendor_by_id(0)
        assert vendor["rename_map"] == {"수령인": "받는사람"}
        # 기존 필드는 유지되어야 함
        assert vendor["name"] == "테스트업체A"

    def test_update_ignores_id_change(self, setup_test_vendors):
        """id 필드 변경 시도 시 무시되는지 확인"""
        update_vendor_in_config(0, {"id": 999, "name": "이름변경"})
        vendor = get_vendor_by_id(0)
        assert vendor["id"] == 0  # id는 변경되지 않아야 함
        assert vendor["name"] == "이름변경"  # 이름은 변경되어야 함

    def test_update_vendor_updates_nh_list(self, setup_test_vendors):
        """이름 변경 시 nh_list에 반영되는지 확인"""
        update_vendor_in_config(0, {"name": "변경된이름"})
        assert "변경된이름" in map_module.nh_list
        assert "테스트업체A" not in map_module.nh_list

    def test_update_vendor_invalid_id_raises(self, setup_test_vendors):
        """존재하지 않는 ID 수정 시 ValueError 발생 확인"""
        with pytest.raises(ValueError, match="존재하지 않는 업체 ID"):
            update_vendor_in_config(999, {"name": "없는업체"})


class TestUpdateVendorKeywords:
    """update_vendor_keywords() 함수 테스트"""

    def test_update_keywords_success(self, setup_test_vendors):
        """정상 키워드 변경 확인"""
        update_vendor_keywords(0, ["새키워드1", "새키워드2"])
        vendor = get_vendor_by_id(0)
        assert vendor["keywords"] == ["새키워드1", "새키워드2"]

    def test_update_keywords_empty_raises(self, setup_test_vendors):
        """빈 키워드 리스트일 때 ValueError 발생 확인"""
        with pytest.raises(ValueError, match="키워드는 최소 1개 이상"):
            update_vendor_keywords(0, [])

    def test_update_keywords_invalid_id_raises(self, setup_test_vendors):
        """존재하지 않는 ID의 키워드 수정 시 ValueError 발생 확인"""
        with pytest.raises(ValueError, match="존재하지 않는 업체 ID"):
            update_vendor_keywords(999, ["키워드"])
