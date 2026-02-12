"""
업체별 매핑 설정 모듈 (map.py)

외부 JSON 설정 파일(data/vendor_config.json)에서 업체별 매핑 정보를 로드합니다.
새 업체 추가 시 JSON 파일만 편집하거나, CRUD 함수를 통해 동적으로 관리할 수 있습니다.
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


def _save_config():
    """현재 설정을 JSON 파일에 저장합니다."""
    try:
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(_config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"설정 파일 저장 실패: {e}")
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


# ──────────────────────────────────── 업체 리스트 ────────────────────────────────────

nh_list = [v["name"] for v in _config.get("vendors", [])]


def get_nh_list():
    """현재 등록된 업체명 리스트를 반환합니다. (동적 갱신 지원)"""
    _ensure_config()
    return [v["name"] for v in _config.get("vendors", [])]


def get_all_vendors():
    """모든 업체 설정을 리스트로 반환합니다."""
    _ensure_config()
    return list(_config.get("vendors", []))


def get_vendor_by_id(vendor_id):
    """ID로 업체 설정을 조회합니다."""
    return _vendor_map.get(vendor_id)


def get_vendor_by_name(name):
    """이름으로 업체 설정을 조회합니다."""
    _ensure_config()
    for v in _config.get("vendors", []):
        if v["name"] == name:
            return v
    return None


# ──────────────────────────────────── 업체 CRUD ────────────────────────────────────

def _next_vendor_id():
    """사용 가능한 다음 업체 ID를 반환합니다."""
    _ensure_config()
    vendors = _config.get("vendors", [])
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
    
    new_id = _next_vendor_id()
    vendor_data = {
        "id": new_id,
        "name": name,
        "rename_map": rename_map or {},
        "target_columns": target_columns or list(_config.get("default_target_columns", [])),
        "constant_values": constant_values or {},
        "copy_map": copy_map or {},
        "split_config": split_config,
        "keywords": keywords if keywords else [name],
    }
    if form_file:
        vendor_data["form_file"] = form_file
    
    _config["vendors"].append(vendor_data)
    _vendor_map[new_id] = vendor_data
    nh_list = [v["name"] for v in _config.get("vendors", [])]
    _save_config()
    
    return new_id


def remove_vendor_from_config(vendor_id):
    """업체를 설정에서 삭제합니다.
    
    Args:
        vendor_id: 삭제할 업체 ID
        
    Raises:
        ValueError: 존재하지 않는 업체 ID인 경우
    """
    global nh_list
    
    if vendor_id not in _vendor_map:
        raise ValueError(f"존재하지 않는 업체 ID입니다: {vendor_id}")
    
    _config["vendors"] = [v for v in _config["vendors"] if v["id"] != vendor_id]
    del _vendor_map[vendor_id]
    nh_list = [v["name"] for v in _config.get("vendors", [])]
    _save_config()


def update_vendor_in_config(vendor_id, updates):
    """업체 설정을 부분 수정합니다.
    
    Args:
        vendor_id: 수정할 업체 ID
        updates: 수정할 필드 dict (예: {"rename_map": {...}, "target_columns": [...]})
        
    Raises:
        ValueError: 존재하지 않는 업체 ID인 경우
    """
    global nh_list
    
    vendor = _vendor_map.get(vendor_id)
    if vendor is None:
        raise ValueError(f"존재하지 않는 업체 ID입니다: {vendor_id}")
    
    # id는 수정 불가
    updates.pop("id", None)
    
    vendor.update(updates)
    
    # vendors 리스트도 갱신
    for i, v in enumerate(_config["vendors"]):
        if v["id"] == vendor_id:
            _config["vendors"][i] = vendor
            break
    
    nh_list = [v["name"] for v in _config.get("vendors", [])]
    _save_config()


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
    _ensure_config()
    return _vendor_map.get(idx)


def get_ganghwagun_rename_map(idx):
    """사방넷 컬럼명을 대상 양식 컬럼명으로 매핑"""
    vendor = _get_vendor(idx)
    if vendor is not None:
        return dict(vendor.get("rename_map", {}))
    # 등록되지 않은 인덱스 → 기본 매핑
    _ensure_config()
    return dict(_config.get("default_rename_map", {}))


def get_copy_map(idx):
    """원본 컬럼의 값을 다른 컬럼명으로 복사해야 할 때 정의"""
    vendor = _get_vendor(idx)
    if vendor is not None:
        return dict(vendor.get("copy_map", {}))
    return {}


def get_date_map(idx, formatted_date):
    """날짜 관련 고정값 매핑 (필요시)"""
    # 현재는 idx 24(청수굴비)만 날짜 매핑이 필요
    vendor = _get_vendor(idx)
    if vendor and vendor.get("split_config"):
        return {"날짜": formatted_date}
    return {}


def get_ganghwagun_target_columns(idx):
    """최종 엑셀에 들어갈 컬럼 순서 정의"""
    vendor = _get_vendor(idx)
    if vendor is not None:
        return list(vendor.get("target_columns", []))
    _ensure_config()
    return list(_config.get("default_target_columns", []))


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

def sort_data(df):
    """상품약어를 기준으로 업체별 ID를 부여하고 리스트로 반환"""
    current_nh_list = get_nh_list()
    
    # 1. 초기화
    df['nh_id'] = -1

    # 2. 키워드 기반 업체 매핑
    vendors = get_all_vendors()
    for vendor in vendors:
        vid = vendor["id"]
        keywords = vendor.get("keywords", [vendor["name"]])
        for keyword in keywords:
            df.loc[df['상품약어'].str.contains(keyword, na=False, regex=False), 'nh_id'] = vid

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