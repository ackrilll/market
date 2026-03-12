"""
주문 변환 매핑 탭 (order_mapping.py)

업체 리스트를 먼저 보여주고, 업체를 클릭하면 해당 업체의 매핑 정보를
드래그 앤 드롭 UI로 조회/등록/수정할 수 있습니다.
분류 기준 칼럼 설정은 상단 expander로 분리되어 있습니다.
"""
import streamlit as st
import pandas as pd
import json
import os
import io
import re
import base64
import logging
from map import (
    get_all_vendors,
    get_vendor_by_name,
    get_vendor_by_id,
    update_vendor_in_config,
    reload_config,
    _FORM_DIR,
    _BASE_DIR,
)
from excel_utils import read_excel_with_header_detection
from components.column_mapper import column_mapper

logger = logging.getLogger(__name__)

# 원본 주문서(365 주문내역 통합)의 기본 칼럼 목록
DEFAULT_SOURCE_COLUMNS = [
    "쇼핑몰", "주문번호", "수령인", "상품명", "옵션매핑", "노출옵션",
    "상품약어", "수량", "수령인 전화번호", "수령인 휴대폰", "우편번호",
    "수령인주소", "배송메세지", "구매자", "구매자 휴대폰", ".",
    "사방넷 주문번호(필수)", "송장번호(필수)", "택배사(필수)",
    "사방넷코드(필수)", "택배사코드(필수)", "취소접수일자", "취소완료일자",
]


_MAPPING_CONFIG_PATH = os.path.join(_BASE_DIR, "data", "mapping_config.json")


def _load_mapping_config():
    """매핑 설정 파일을 로드합니다."""
    try:
        with open(_MAPPING_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"source_types": {}}


def _save_mapping_config(config):
    """매핑 설정 파일을 저장합니다."""
    with open(_MAPPING_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _load_vendor_form(vendor_name):
    """업체의 양식 파일을 로드하여 DataFrame으로 반환합니다."""
    for ext in ['.xlsx', '.xls']:
        filepath = os.path.join(_FORM_DIR, f"{vendor_name}{ext}")
        if os.path.exists(filepath):
            try:
                return read_excel_with_header_detection(filepath, nrows=5), filepath
            except Exception:
                pass

    # target_form 디렉토리에서 업체명이 포함된 파일 검색
    if os.path.exists(_FORM_DIR):
        for filename in os.listdir(_FORM_DIR):
            if vendor_name in filename and (filename.endswith('.xlsx') or filename.endswith('.xls')):
                filepath = os.path.join(_FORM_DIR, filename)
                try:
                    return read_excel_with_header_detection(filepath, nrows=5), filepath
                except Exception:
                    pass
    return None, None


def _get_mapping_status(vendor):
    """업체의 매핑 상태를 판단합니다.

    rename_map, constant_values, copy_map, target_columns 중 하나라도 있으면 매핑 완료.
    """
    rename_map = vendor.get("rename_map", {})
    constant_values = vendor.get("constant_values", {})
    copy_map = vendor.get("copy_map", {})
    target_columns = vendor.get("target_columns", [])

    has_mapping = bool(rename_map) or bool(constant_values) or bool(copy_map) or bool(target_columns)
    mapping_count = len(rename_map) + len(constant_values) + len(copy_map)
    if not mapping_count and target_columns:
        mapping_count = len(target_columns)
    return has_mapping, mapping_count


# ──────────────────────────────────── 메인 렌더링 ────────────────────────────────────


def render_mapping_tab():
    """주문 변환 매핑 탭 UI를 렌더링합니다."""
    st.subheader("매핑 관리")
    st.caption("업체를 선택하여 칼럼 매핑을 조회하거나 등록/수정합니다.")

    vendors = get_all_vendors()
    if not vendors:
        st.info("등록된 업체가 없습니다. 먼저 업체 관리 탭에서 업체를 추가하세요.")
        return

    # ── 1. 분류 기준 칼럼 설정 (expander) ──
    _render_classification_section()

    st.divider()

    # ── 2. 업체 목록 + 상세 패널 ──
    _render_vendor_list_and_detail(vendors)


# ──────────────────────────────── 분류 기준 칼럼 설정 ────────────────────────────────


def _render_classification_section():
    """분류 기준 칼럼 설정 UI (expander)"""
    mapping_config = _load_mapping_config()

    # 현재 설정된 분류 기준 표시
    current_col = ""
    source_types = mapping_config.get("source_types", {})
    for source_name, source_config in source_types.items():
        col = source_config.get("classification_column", "")
        if col:
            current_col = col
            break

    expander_label = f"분류 기준 칼럼 설정 — 현재: {current_col}" if current_col else "분류 기준 칼럼 설정"
    with st.expander(expander_label, expanded=False):
        st.caption("원본 주문서의 칼럼 중 업체 분류에 사용할 칼럼을 선택합니다. "
                   "이 칼럼의 값에 업체 키워드가 포함되어 있으면 해당 업체로 분류됩니다.")

        source_file = st.file_uploader(
            "원본 주문서 엑셀 파일 (.xlsx / .xls)",
            type=["xlsx", "xls"],
            help="분류 기준 칼럼을 설정하기 위해 원본 주문서를 업로드하세요.",
            key="classification_source_file"
        )

        if source_file is None:
            if current_col:
                st.info(f"현재 분류 기준 칼럼: **{current_col}**")
            else:
                st.info("원본 주문서를 업로드하면 칼럼을 선택할 수 있습니다.")
            return

        # 원본 파일 읽기
        try:
            source_file.seek(0)
            file_bytes = source_file.read()
            source_df = read_excel_with_header_detection(file_bytes, nrows=5)
            source_columns = list(source_df.columns)
        except Exception as e:
            st.error("파일 읽기에 실패했습니다. 올바른 Excel 파일인지 확인하세요.")
            return

        source_name = st.text_input(
            "원본 주문서 이름",
            value=os.path.splitext(source_file.name)[0],
            help="이 주문서 유형의 이름을 입력하세요 (예: 사방넷)",
            key="class_source_name_input"
        )

        # 세션 상태에 선택된 칼럼 저장
        session_key = f"selected_class_col_{source_name}"
        source_config = source_types.get(source_name, {})
        saved_col = source_config.get("classification_column", "")
        if session_key not in st.session_state:
            st.session_state[session_key] = saved_col

        selected_col = st.session_state[session_key]

        # 칼럼 버튼 그리드 (5열)
        st.markdown("**칼럼을 클릭하여 분류 기준을 선택하세요**")
        cols_per_row = 5
        for row_start in range(0, len(source_columns), cols_per_row):
            row_cols = st.columns(cols_per_row)
            for i, col in enumerate(source_columns[row_start:row_start + cols_per_row]):
                with row_cols[i]:
                    is_selected = (col == selected_col)
                    btn_type = "primary" if is_selected else "secondary"
                    label = f"✔ {col}" if is_selected else col
                    if st.button(
                        label,
                        key=f"class_col_{source_name}_{row_start + i}",
                        type=btn_type,
                        use_container_width=True,
                    ):
                        st.session_state[session_key] = col
                        st.rerun()

        # 선택 결과 + 저장
        if selected_col:
            st.success(f"'{selected_col}' 칼럼이 분류 기준으로 선택되었습니다.")
            if st.button("분류 기준 저장", key="save_classification", type="primary", use_container_width=True):
                mapping_config.setdefault("source_types", {})
                if source_name not in mapping_config["source_types"]:
                    mapping_config["source_types"][source_name] = {}
                mapping_config["source_types"][source_name]["classification_column"] = selected_col
                _save_mapping_config(mapping_config)
                st.success(f"'{source_name}'의 분류 기준 칼럼이 '{selected_col}'로 저장되었습니다.")
        else:
            st.info("위에서 칼럼을 클릭하여 분류 기준을 선택하세요.")


# ──────────────────────────── 업체 목록 + 상세 패널 ────────────────────────────


def _render_vendor_list_and_detail(vendors):
    """업체 목록과 상세 패널을 렌더링합니다."""
    st.markdown("### 업체별 매핑 현황")

    # 세션 상태 초기화
    if "selected_mapping_vendor" not in st.session_state:
        st.session_state["selected_mapping_vendor"] = None
    selected_vendor_id = st.session_state["selected_mapping_vendor"]

    # ── 업체 목록 + 선택된 업체 아래에 상세 패널 인라인 표시 ──
    for vendor in vendors:
        has_mapping, mapping_count = _get_mapping_status(vendor)
        is_selected = (vendor["id"] == selected_vendor_id)

        if has_mapping:
            status_icon = "🟢"
            status_text = f"매핑 완료 - {mapping_count}개"
        else:
            status_icon = "🔴"
            status_text = "미매핑"

        btn_label = f"{status_icon} {vendor['name']} ({status_text})"
        btn_type = "primary" if is_selected else "secondary"

        if st.button(
            btn_label,
            key=f"vendor_mapping_btn_{vendor['id']}",
            type=btn_type,
            use_container_width=True,
        ):
            if is_selected:
                st.session_state["selected_mapping_vendor"] = None
            else:
                st.session_state["selected_mapping_vendor"] = vendor["id"]
            st.rerun()

        # ── 선택된 업체 바로 아래에 상세 패널 표시 ──
        if is_selected:
            with st.container(border=True):
                st.markdown(f"#### {vendor['name']} 매핑 상세")
                _render_mapping_component(vendor)


# ────────────────────────────── D&D 매핑 컴포넌트 통합 ──────────────────────────────


def _save_uploaded_file(file_data, vendor_name, side):
    """base64 파일 데이터를 저장하고 칼럼을 추출합니다.

    Args:
        file_data: {"name": str, "data": base64_str}
        vendor_name: 업체명
        side: "source" 또는 "target"

    Returns:
        (columns, filename) 또는 ([], None)
    """
    if not file_data or not file_data.get("data"):
        return [], None

    try:
        raw = base64.b64decode(file_data["data"])
        original_name = file_data["name"]

        # 파일 크기 검증
        if len(raw) > 10 * 1024 * 1024:
            st.error("파일 크기가 10MB를 초과합니다.")
            return [], None

        # Excel 검증 + 칼럼 추출
        df = read_excel_with_header_detection(raw, nrows=5)
        columns = [str(c) for c in df.columns]

        if side == "target":
            # 업체 양식 파일 저장
            os.makedirs(_FORM_DIR, exist_ok=True)
            ext = os.path.splitext(original_name)[1].lower()
            safe_name = re.sub(r'[^\w\s\-()]', '', vendor_name).strip()
            if not safe_name:
                st.error("유효하지 않은 업체명입니다.")
                return columns, None
            filename = f"{safe_name}{ext}"
            filepath = os.path.join(_FORM_DIR, filename)

            if not os.path.realpath(filepath).startswith(os.path.realpath(_FORM_DIR)):
                st.error("잘못된 파일 경로입니다.")
                return columns, None

            with open(filepath, "wb") as f:
                f.write(raw)

            # GitHub 동기화
            try:
                from github_sync import commit_file
                rel_path = os.path.relpath(filepath, _BASE_DIR).replace("\\", "/")
                commit_file(rel_path, raw, f"auto: upload form {filename}")
            except Exception as e:
                logger.warning(f"GitHub 동기화 실패 (양식 파일 저장은 완료): {e}")

            return columns, filename

        return columns, original_name

    except Exception as e:
        logger.error(f"파일 처리 실패: {e}")
        st.error(f"파일 처리 실패: {e}")
        return [], None


def _render_mapping_component(vendor):
    """드래그 앤 드롭 매핑 컴포넌트를 렌더링합니다."""
    vendor_name = vendor["name"]
    vendor_id = vendor["id"]

    rename_map = vendor.get("rename_map", {})
    constant_values = vendor.get("constant_values", {})
    copy_map = vendor.get("copy_map", {})
    target_columns = vendor.get("target_columns", [])

    # 업체 칼럼 목록 (양식 파일에서 가져오기)
    vendor_columns = [str(c) for c in target_columns]
    vendor_form_df, _ = _load_vendor_form(vendor_name)
    if vendor_form_df is not None:
        vendor_columns = [str(c) for c in vendor_form_df.columns]

    # 원본 칼럼: 세션에 저장된 것 또는 기본 원본 칼럼 사용
    source_col_key = f"_mapper_source_cols_{vendor_id}"
    if source_col_key not in st.session_state:
        st.session_state[source_col_key] = list(DEFAULT_SOURCE_COLUMNS)
    source_columns = st.session_state[source_col_key]

    # 기존 매핑 정보
    existing_mapping = {
        "rename_map": rename_map,
        "constant_values": constant_values,
        "copy_map": copy_map,
    }

    # 파일명
    target_file_name = vendor.get("form_file", "")

    # 컴포넌트 렌더링
    result = column_mapper(
        vendor_name=vendor_name,
        vendor_id=vendor_id,
        source_columns=source_columns,
        target_columns=vendor_columns,
        existing_mapping=existing_mapping,
        source_file_name="",
        target_file_name=target_file_name,
        key=f"column_mapper_{vendor_id}",
    )

    # ── 컴포넌트 반환값 처리 ──
    if result is None:
        return

    action = result.get("action")

    # 원본 파일 업로드
    if action == "upload_source":
        file_data = result.get("source_file")
        if file_data:
            columns, _ = _save_uploaded_file(file_data, vendor_name, "source")
            if columns:
                st.session_state[source_col_key] = columns
                st.rerun()

    # 업체 양식 파일 업로드
    elif action == "upload_target":
        file_data = result.get("target_file")
        if file_data:
            columns, filename = _save_uploaded_file(file_data, vendor_name, "target")
            if columns and filename:
                updates = {"form_file": filename, "target_columns": columns}
                update_vendor_in_config(vendor_id, updates)
                reload_config()
                st.rerun()

    # 매핑 저장
    elif action == "save":
        mapping = result.get("mapping", {})
        new_rename_map = mapping.get("rename_map", {})
        new_constant_values = mapping.get("constant_values", {})
        new_copy_map = mapping.get("copy_map", {})

        # 파일 업로드가 함께 온 경우 처리
        source_file = result.get("source_file")
        target_file = result.get("target_file")

        if target_file:
            columns, filename = _save_uploaded_file(target_file, vendor_name, "target")
            if columns and filename:
                update_vendor_in_config(vendor_id, {
                    "form_file": filename,
                    "target_columns": columns,
                })

        if source_file:
            columns, _ = _save_uploaded_file(source_file, vendor_name, "source")
            if columns:
                st.session_state[source_col_key] = columns

        # vendor_config.json 갱신
        try:
            update_vendor_in_config(vendor_id, {
                "rename_map": dict(new_rename_map),
                "constant_values": dict(new_constant_values),
                "copy_map": dict(new_copy_map),
            })
            reload_config()
        except Exception as e:
            logger.error(f"매핑 저장 실패: {e}")

        total = len(new_rename_map) + len(new_constant_values) + len(new_copy_map)
        st.success(f"'{vendor_name}' 매핑이 저장되었습니다! ({total}개)")
        st.rerun()

    # 매핑 초기화
    elif action == "reset":
        update_vendor_in_config(vendor_id, {
            "rename_map": {},
            "constant_values": {},
            "copy_map": {},
        })
        reload_config()
        _remove_vendor_from_mapping_config(vendor_name)
        st.success(f"'{vendor_name}' 매핑이 초기화되었습니다.")
        st.rerun()


def _remove_vendor_from_mapping_config(vendor_name):
    """mapping_config.json에서 특정 업체의 매핑을 제거합니다."""
    mapping_config = _load_mapping_config()
    for source_name, source_config in mapping_config.get("source_types", {}).items():
        vendor_mappings = source_config.get("vendor_mappings", {})
        vendor_mappings.pop(vendor_name, None)
    _save_mapping_config(mapping_config)
