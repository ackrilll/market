"""
업체별 매핑 설정 모듈 (map.py)

외부 JSON 설정 파일(data/vendor_config.json)에서 업체별 매핑 정보를 로드합니다.
새 업체 추가 시 JSON 파일만 편집하거나, CRUD 함수를 통해 동적으로 관리할 수 있습니다.

유저별 설정 지원:
  - load_user_config(user_id) 호출 시 data/users/{user_id}/vendor_config.json 로드
  - st.session_state["user_config"] / ["user_vendor_map"]에 저장
  - 모든 조회 함수는 유저 config 우선, 없으면 전역 _config 폴백
"""
import json
import os
import logging
import shutil

logger = logging.getLogger(__name__)

# ──────────────────────────────────── 설정 로드 ────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_BASE_DIR, "data", "vendor_config.json")
_FORM_DIR = os.path.join(_BASE_DIR, "data", "target_form")
_USERS_DIR = os.path.join(_BASE_DIR, "data", "users")
_config = None
_vendor_map = {}  # id -> vendor dict 빠른 조회용


def _load_config():
    """JSON 설정 파일을 로드하고 캐싱합니다."""
    global _config, _vendor_map, nh_list
    if _config is not None:
        return

    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _config = json.load(f)
    except FileNotFoundError:
        logger.error(f"설정 파일을 찾을 수 없습니다: {_CONFIG_PATH}")
        _config = {"vendors": [], "default_rename_map": {}, "default_target_columns": []}
    except json.JSONDecodeError as e:
        logger.error(f"설정 파일 JSON 파싱 오류: {e}")
        _config = {"vendors": [], "default_rename_map": {}, "default_target_columns": []}

    # id -> vendor dict 인덱스 구축
    _vendor_map = {v["id"]: v for v in _config.get("vendors", [])}
    # nh_list 동적 갱신
    nh_list = [v["name"] for v in _config.get("vendors", [])]


def _save_config(config=None, config_path=None):
    """설정을 JSON 파일에 원자적으로 저장합니다.

    Args:
        config: 저장할 설정 dict (None이면 전역 _config)
        config_path: 저장 경로 (None이면 전역 _CONFIG_PATH)
    """
    import tempfile
    save_config = config if config is not None else _config
    save_path = config_path if config_path is not None else _CONFIG_PATH
    try:
        config_dir = os.path.dirname(save_path)
        with tempfile.NamedTemporaryFile(
            mode='w', dir=config_dir, delete=False,
            suffix='.tmp', encoding='utf-8'
        ) as tmp:
            json.dump(save_config, tmp, ensure_ascii=False, indent=2)
            tmp_path = tmp.name
        shutil.move(tmp_path, save_path)
    except Exception as e:
        logger.error(f"설정 파일 저장 실패: {e}")
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise


def reload_config():
    """설정 파일을 강제로 다시 로드합니다. (런타임 중 설정 변경 시 사용)"""
    global _config
    _config = None
    _load_config()


def _ensure_config():
    """_config가 None이면 자동으로 로드합니다. (레이스 컨디션 방지)"""
    if _config is None:
        _load_config()


# 모듈 임포트 시 자동 로드
_load_config()


# ──────────────────────────────────── 유저별 설정 ────────────────────────────────────

def _get_user_config_path(user_id):
    """유저별 vendor_config.json 경로를 반환합니다."""
    # Path Traversal 방지: user_id에서 위험한 문자 제거
    safe_id = os.path.basename(user_id)
    return os.path.join(_USERS_DIR, safe_id, "vendor_config.json")


def load_user_config(user_id):
    """유저별 vendor_config.json을 로드하여 session_state에 저장합니다.

    파일이 없으면 빈 업체 목록으로 초기화합니다.
    """
    import streamlit as st
    config_path = _get_user_config_path(user_id)

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"유저 설정 로드 실패 ({user_id}): {e}")
            user_config = _create_empty_user_config()
    else:
        user_config = _create_empty_user_config()
        # 디렉토리 생성 및 파일 저장
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        _save_config(user_config, config_path)

    st.session_state["user_config"] = user_config
    st.session_state["user_vendor_map"] = {v["id"]: v for v in user_config.get("vendors", [])}
    st.session_state["user_config_path"] = config_path


def _create_empty_user_config():
    """빈 업체 목록을 가진 기본 설정을 반환합니다."""
    _ensure_config()
    return {
        "default_rename_map": dict(_config.get("default_rename_map", {})),
        "default_target_columns": list(_config.get("default_target_columns", [])),
        "vendors": [],
    }


def _get_current_config():
    """현재 활성 설정을 반환합니다 (유저 config 우선, 없으면 전역 폴백)."""
    import streamlit as st
    user_config = st.session_state.get("user_config")
    if user_config is not None:
        return user_config
    _ensure_config()
    return _config


def _get_current_vendor_map():
    """현재 활성 vendor_map을 반환합니다."""
    import streamlit as st
    user_map = st.session_state.get("user_vendor_map")
    if user_map is not None:
        return user_map
    _ensure_config()
    return _vendor_map


def _get_current_config_path():
    """현재 활성 config 파일 경로를 반환합니다."""
    import streamlit as st
    return st.session_state.get("user_config_path", _CONFIG_PATH)


# ──────────────────────────────────── 업체 리스트 ────────────────────────────────────

nh_list = [v["name"] for v in _config.get("vendors", [])]


def get_nh_list():
    """현재 등록된 업체명 리스트를 반환합니다. (동적 갱신 지원)"""
    config = _get_current_config()
    return [v["name"] for v in config.get("vendors", [])]


def get_all_vendors():
    """모든 업체 설정을 리스트로 반환합니다."""
    config = _get_current_config()
    return list(config.get("vendors", []))


def get_vendor_by_id(vendor_id):
    """ID로 업체 설정을 조회합니다."""
    vendor_map = _get_current_vendor_map()
    return vendor_map.get(vendor_id)


def get_vendor_by_name(name):
    """이름으로 업체 설정을 조회합니다."""
    config = _get_current_config()
    for v in config.get("vendors", []):
        if v["name"] == name:
            return v
    return None


# ──────────────────────────────────── 업체 CRUD ────────────────────────────────────

def _next_vendor_id():
    """사용 가능한 다음 업체 ID를 반환합니다."""
    config = _get_current_config()
    vendors = config.get("vendors", [])
    if not vendors:
        return 0
    return max(v["id"] for v in vendors) + 1


def add_vendor_to_config(name, keywords, target_columns=None, rename_map=None,
                         constant_values=None, copy_map=None, split_config=None,
                         form_file=None):
    """새 업체를 설정에 추가합니다.

    Args:
        name: 업체명
        keywords: 분류 키워드 리스트
        target_columns: 대상 칼럼 리스트 (None이면 기본값 사용)
        rename_map: 칼럼명 매핑 dict (None이면 빈 dict)
        constant_values: 고정값 dict (None이면 빈 dict)
        copy_map: 복사 매핑 dict (None이면 빈 dict)
        split_config: 분할 설정 (None이면 없음)
        form_file: 양식 파일명 (None이면 없음)

    Returns:
        새로 생성된 업체의 ID

    Raises:
        ValueError: 이미 존재하는 업체명인 경우
    """
    global nh_list

    # 중복 체크
    if get_vendor_by_name(name) is not None:
        raise ValueError(f"이미 존재하는 업체명입니다: {name}")

    config = _get_current_config()
    new_id = _next_vendor_id()
    vendor_data = {
        "id": new_id,
        "name": name,
        "rename_map": rename_map or {},
        "target_columns": target_columns or list(config.get("default_target_columns", [])),
        "constant_values": constant_values or {},
        "copy_map": copy_map or {},
        "split_config": split_config,
        "keywords": keywords if keywords else [name],
    }
    if form_file:
        vendor_data["form_file"] = form_file

    config["vendors"].append(vendor_data)

    # vendor_map 갱신
    vendor_map = _get_current_vendor_map()
    vendor_map[new_id] = vendor_data

    # session_state 갱신
    import streamlit as st
    if "user_config" in st.session_state:
        st.session_state["user_config"] = config
        st.session_state["user_vendor_map"] = vendor_map

    nh_list = [v["name"] for v in config.get("vendors", [])]
    _save_config(config, _get_current_config_path())

    return new_id


def remove_vendor_from_config(vendor_id):
    """업체를 설정에서 삭제합니다.

    Args:
        vendor_id: 삭제할 업체 ID

    Raises:
        ValueError: 존재하지 않는 업체 ID인 경우
    """
    global nh_list

    vendor_map = _get_current_vendor_map()
    if vendor_id not in vendor_map:
        raise ValueError(f"존재하지 않는 업체 ID입니다: {vendor_id}")

    config = _get_current_config()
    config["vendors"] = [v for v in config["vendors"] if v["id"] != vendor_id]
    del vendor_map[vendor_id]

    import streamlit as st
    if "user_config" in st.session_state:
        st.session_state["user_config"] = config
        st.session_state["user_vendor_map"] = vendor_map

    nh_list = [v["name"] for v in config.get("vendors", [])]
    _save_config(config, _get_current_config_path())


def update_vendor_in_config(vendor_id, updates):
    """업체 설정을 부분 수정합니다.

    Args:
        vendor_id: 수정할 업체 ID
        updates: 수정할 필드 dict (예: {"rename_map": {...}, "target_columns": [...]})

    Raises:
        ValueError: 존재하지 않는 업체 ID인 경우
    """
    global nh_list

    vendor_map = _get_current_vendor_map()
    vendor = vendor_map.get(vendor_id)
    if vendor is None:
        raise ValueError(f"존재하지 않는 업체 ID입니다: {vendor_id}")

    # id는 수정 불가
    updates.pop("id", None)

    vendor.update(updates)

    config = _get_current_config()
    # vendors 리스트도 갱신
    for i, v in enumerate(config["vendors"]):
        if v["id"] == vendor_id:
            config["vendors"][i] = vendor
            break

    import streamlit as st
    if "user_config" in st.session_state:
        st.session_state["user_config"] = config
        st.session_state["user_vendor_map"] = vendor_map

    nh_list = [v["name"] for v in config.get("vendors", [])]
    _save_config(config, _get_current_config_path())


def update_vendor_keywords(vendor_id, keywords):
    """업체의 키워드를 수정합니다.

    Args:
        vendor_id: 업체 ID
        keywords: 새 키워드 리스트

    Raises:
        ValueError: 존재하지 않는 업체 ID이거나, 빈 키워드 리스트인 경우
    """
    if not keywords:
        raise ValueError("키워드는 최소 1개 이상 필요합니다.")
    update_vendor_in_config(vendor_id, {"keywords": keywords})


# ──────────────────────────────────── 매핑 함수 ────────────────────────────────────

def _get_vendor(idx):
    """인덱스로 업체 설정을 조회합니다."""
    vendor_map = _get_current_vendor_map()
    return vendor_map.get(idx)


def get_ganghwagun_rename_map(idx):
    """사방넷 컬럼명을 대상 양식 컬럼명으로 매핑"""
    vendor = _get_vendor(idx)
    if vendor is not None:
        return dict(vendor.get("rename_map", {}))
    # 등록되지 않은 인덱스 → 기본 매핑
    config = _get_current_config()
    return dict(config.get("default_rename_map", {}))


def get_copy_map(idx):
    """원본 컬럼의 값을 다른 컬럼명으로 복사해야 할 때 정의"""
    vendor = _get_vendor(idx)
    if vendor is not None:
        return dict(vendor.get("copy_map", {}))
    return {}


def get_date_map(idx, formatted_date):
    """날짜 관련 고정값 매핑 (필요시)"""
    vendor = _get_vendor(idx)
    if vendor and vendor.get("split_config"):
        return {"날짜": formatted_date}
    return {}


def get_ganghwagun_target_columns(idx):
    """최종 엑셀에 들어갈 컬럼 순서 정의"""
    vendor = _get_vendor(idx)
    if vendor is not None:
        return list(vendor.get("target_columns", []))
    config = _get_current_config()
    return list(config.get("default_target_columns", []))


def get_constant_values(idx):
    """업체별로 고정적으로 들어가야 하는 값 정의"""
    vendor = _get_vendor(idx)
    if vendor is not None:
        return dict(vendor.get("constant_values", {}))
    return {}


def get_split_config(idx):
    """파일 분할 설정 반환 (분할이 필요한 업체만 tuple 반환)"""
    vendor = _get_vendor(idx)
    if vendor is not None:
        sc = vendor.get("split_config")
        if sc and isinstance(sc, list) and len(sc) == 2:
            return tuple(sc)
    return None


# ──────────────────────────────────── 분류 함수 ────────────────────────────────────

_MAPPING_CONFIG_PATH = os.path.join(_BASE_DIR, "data", "mapping_config.json")
_DEFAULT_CLASSIFICATION_COLUMN = "상품약어"


def _get_classification_column():
    """mapping_config.json에서 분류 기준 칼럼을 조회합니다.

    여러 source_type 중 classification_column이 설정된 첫 번째 값을 반환합니다.
    설정이 없으면 기본값 '상품약어'를 반환합니다.
    """
    try:
        with open(_MAPPING_CONFIG_PATH, "r", encoding="utf-8") as f:
            mapping_config = json.load(f)

        source_types = mapping_config.get("source_types", {})
        for source_name, source_config in source_types.items():
            col = source_config.get("classification_column", "")
            if col:
                return col
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    return _DEFAULT_CLASSIFICATION_COLUMN


def sort_data(df):
    """분류 기준 칼럼의 키워드를 기반으로 업체별 ID를 부여하고 리스트로 반환.

    분류 기준 칼럼은 mapping_config.json의 classification_column 설정을 따르며,
    설정이 없으면 기본값 '상품약어'를 사용합니다.
    """
    current_nh_list = get_nh_list()

    # 0. 분류 기준 칼럼 결정
    classification_col = _get_classification_column()

    # 분류 기준 칼럼이 DataFrame에 존재하는지 확인
    if classification_col not in df.columns:
        logger.warning(
            f"분류 기준 칼럼 '{classification_col}'이(가) 데이터에 없습니다. "
            f"기본값 '{_DEFAULT_CLASSIFICATION_COLUMN}'로 대체합니다."
        )
        classification_col = _DEFAULT_CLASSIFICATION_COLUMN
        if classification_col not in df.columns:
            logger.error(f"기본 분류 칼럼 '{classification_col}'도 데이터에 없습니다. 분류를 수행할 수 없습니다.")
            return []

    # 1. 초기화
    df['nh_id'] = -1

    # 2. 키워드 기반 업체 매핑 (동적 칼럼 사용)
    vendors = get_all_vendors()
    for vendor in vendors:
        vid = vendor["id"]
        keywords = vendor.get("keywords", [vendor["name"]])
        for keyword in keywords:
            df.loc[df[classification_col].str.contains(keyword, na=False, regex=False), 'nh_id'] = vid

    # 3. 데이터가 존재하는 ID만 추출하여 리스트 생성
    sorted_df_list = []
    valid_ids = df[df['nh_id'] != -1]['nh_id'].unique()
    valid_ids.sort()

    for i in valid_ids:
        vendor = get_vendor_by_id(int(i))
        if vendor:
            subset = df[df['nh_id'] == i].copy()
            sorted_df_list.append((int(i), vendor["name"], subset))

    return sorted_df_list
