"""
주문 변환 매핑 탭 (order_mapping.py)

업체 리스트를 먼저 보여주고, 업체를 클릭하면 해당 업체의 매핑 정보를
조회/등록/수정할 수 있는 UI를 제공합니다.
분류 기준 칼럼 설정은 상단 expander로 분리되어 있습니다.
"""
import streamlit as st
import pandas as pd
import json
import os
from map import (
    get_all_vendors,
    get_vendor_by_name,
    get_vendor_by_id,
    update_vendor_in_config,
    reload_config,
    _FORM_DIR,
    _BASE_DIR,
)


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
                return pd.read_excel(filepath, nrows=5), filepath
            except Exception:
                pass

    # target_form 디렉토리에서 업체명이 포함된 파일 검색
    if os.path.exists(_FORM_DIR):
        for filename in os.listdir(_FORM_DIR):
            if vendor_name in filename and (filename.endswith('.xlsx') or filename.endswith('.xls')):
                filepath = os.path.join(_FORM_DIR, filename)
                try:
                    return pd.read_excel(filepath, nrows=5), filepath
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
            source_df = pd.read_excel(source_file, nrows=5)
            source_columns = list(source_df.columns)
        except Exception as e:
            st.error(f"파일 읽기 실패: {e}")
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
    if "mapping_edit_mode" not in st.session_state:
        st.session_state["mapping_edit_mode"] = False

    selected_vendor_id = st.session_state["selected_mapping_vendor"]

    # ── 업체 목록 (세로 나열) ──
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
            # 같은 업체 다시 클릭하면 접기
            if is_selected:
                st.session_state["selected_mapping_vendor"] = None
                st.session_state["mapping_edit_mode"] = False
            else:
                st.session_state["selected_mapping_vendor"] = vendor["id"]
                st.session_state["mapping_edit_mode"] = False
            st.rerun()

    # ── 상세 패널 ──
    if selected_vendor_id is not None:
        vendor = get_vendor_by_id(selected_vendor_id)
        if vendor is None:
            st.warning("선택된 업체를 찾을 수 없습니다.")
            st.session_state["selected_mapping_vendor"] = None
            return

        st.divider()
        st.markdown(f"### {vendor['name']} 매핑 상세")

        has_mapping, _ = _get_mapping_status(vendor)
        edit_mode = st.session_state.get("mapping_edit_mode", False)

        if has_mapping and not edit_mode:
            _render_mapping_view(vendor)
        else:
            _render_mapping_editor(vendor)


# ────────────────────────────── 매핑 정보 조회 패널 ──────────────────────────────


def _build_unified_mapping_table(vendor):
    """업체의 모든 매핑 정보를 통합 테이블 데이터로 구성합니다."""
    rename_map = vendor.get("rename_map", {})
    constant_values = vendor.get("constant_values", {})
    copy_map = vendor.get("copy_map", {})
    target_columns = vendor.get("target_columns", [])

    # rename_map 역방향: {업체칼럼: 원본칼럼}
    reverse_rename = {v: k for k, v in rename_map.items()}
    # copy_map 역방향: {복사대상칼럼: 원본칼럼}
    reverse_copy = {v: k for k, v in copy_map.items()}

    rows = []
    for col in target_columns:
        col_str = str(col)
        if col_str in reverse_rename:
            src = reverse_rename[col_str]
            if src == col_str:
                mapping_desc = f"← {src} (동일)"
            else:
                mapping_desc = f"← {src}"
        elif col_str in constant_values:
            mapping_desc = f'고정값: "{constant_values[col_str]}"'
        elif col_str in reverse_copy:
            mapping_desc = f"복사: {reverse_copy[col_str]}"
        else:
            mapping_desc = f"← {col_str} (동일)"
        rows.append({"업체 칼럼": col_str, "매핑": mapping_desc})
    return rows


def _render_mapping_view(vendor):
    """매핑 완료 업체의 매핑 정보를 통합 테이블로 조회합니다."""
    st.markdown("#### 칼럼 매핑")

    rows = _build_unified_mapping_table(vendor)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("대상 칼럼이 설정되지 않았습니다.")

    # 버튼: 수정 / 초기화
    st.divider()
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("매핑 수정", key="mapping_edit_btn", type="primary", use_container_width=True):
            st.session_state["mapping_edit_mode"] = True
            st.rerun()
    with btn_col2:
        if st.button("매핑 초기화", key="mapping_reset_btn", use_container_width=True):
            st.session_state["confirm_reset"] = True
            st.rerun()

    # 초기화 확인
    if st.session_state.get("confirm_reset"):
        st.warning(f"**{vendor['name']}**의 매핑을 모두 초기화하시겠습니까?")
        confirm_col1, confirm_col2 = st.columns(2)
        with confirm_col1:
            if st.button("초기화 확인", key="confirm_reset_yes", type="primary", use_container_width=True):
                update_vendor_in_config(vendor["id"], {
                    "rename_map": {},
                    "constant_values": {},
                    "copy_map": {},
                })
                reload_config()
                _remove_vendor_from_mapping_config(vendor["name"])
                st.session_state["confirm_reset"] = False
                st.session_state["mapping_edit_mode"] = False
                st.success(f"'{vendor['name']}' 매핑이 초기화되었습니다.")
                st.rerun()
        with confirm_col2:
            if st.button("취소", key="confirm_reset_no", use_container_width=True):
                st.session_state["confirm_reset"] = False
                st.rerun()


def _remove_vendor_from_mapping_config(vendor_name):
    """mapping_config.json에서 특정 업체의 매핑을 제거합니다."""
    mapping_config = _load_mapping_config()
    for source_name, source_config in mapping_config.get("source_types", {}).items():
        vendor_mappings = source_config.get("vendor_mappings", {})
        vendor_mappings.pop(vendor_name, None)
    _save_mapping_config(mapping_config)


# ──────────────────────────── 매핑 등록/수정 에디터 ────────────────────────────

_SPECIAL_UNMAPPED = "(미매핑)"
_SPECIAL_CONSTANT = "고정값 입력"
_SPECIAL_COPY = "다른 칼럼 복사"


def _render_mapping_editor(vendor):
    """매핑 등록 또는 수정 UI를 렌더링합니다."""
    vendor_name = vendor["name"]
    vendor_id = vendor["id"]

    has_mapping, _ = _get_mapping_status(vendor)
    if has_mapping:
        st.caption(f"'{vendor_name}' 매핑을 수정합니다.")
    else:
        st.caption(f"'{vendor_name}'에 새 매핑을 등록합니다.")

    # 업체 칼럼 정보
    vendor_columns = vendor.get("target_columns", [])
    vendor_form_df, _ = _load_vendor_form(vendor_name)
    if vendor_form_df is not None:
        vendor_columns = list(vendor_form_df.columns)

    if not vendor_columns:
        st.warning(f"'{vendor_name}' 업체의 양식 칼럼 정보가 없습니다. 업체 관리 탭에서 양식을 설정하세요.")
        return

    # 원본 파일 업로드
    source_file = st.file_uploader(
        "원본 주문서 엑셀 파일 (.xlsx / .xls)",
        type=["xlsx", "xls"],
        help="매핑할 원본 주문서를 업로드하세요.",
        key=f"mapping_source_file_{vendor_id}"
    )

    if source_file is None:
        st.info("원본 주문서 파일을 업로드하면 칼럼 매핑을 편집할 수 있습니다.")
        if has_mapping:
            if st.button("수정 취소", key="cancel_edit_btn", use_container_width=True):
                st.session_state["mapping_edit_mode"] = False
                st.rerun()
        return

    # 원본 파일 읽기
    try:
        source_file.seek(0)
        source_df = pd.read_excel(source_file, nrows=10)
        source_columns = list(source_df.columns)
    except Exception as e:
        st.error(f"파일 읽기 실패: {e}")
        return

    source_name = st.text_input(
        "원본 주문서 이름",
        value=os.path.splitext(source_file.name)[0],
        help="이 주문서 유형의 이름을 입력하세요 (예: 사방넷)",
        key=f"mapping_source_name_{vendor_id}"
    )

    # 양식 비교 뷰
    st.markdown("#### 양식 비교")
    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown(f"**{vendor_name} 양식**")
        if vendor_form_df is not None:
            st.dataframe(vendor_form_df.head(5), use_container_width=True, height=200)
        else:
            st.dataframe(pd.DataFrame(columns=vendor_columns), use_container_width=True, height=200)
        st.caption(f"칼럼 {len(vendor_columns)}개")
    with right_col:
        st.markdown(f"**원본 주문서: {source_name}**")
        st.dataframe(source_df.head(5), use_container_width=True, height=200)
        st.caption(f"칼럼 {len(source_columns)}개")

    st.divider()

    # 인라인 매핑 편집 UI
    _render_inline_mapping_editor(source_name, source_columns, vendor_name, vendor, vendor_columns)


def _render_inline_mapping_editor(source_name, source_columns, vendor_name, vendor, vendor_columns):
    """업체 칼럼마다 selectbox로 매핑을 편집하는 인라인 UI"""
    existing_rename = vendor.get("rename_map", {})
    existing_constants = vendor.get("constant_values", {})
    existing_copy = vendor.get("copy_map", {})

    # 역방향 매핑 구성
    reverse_rename = {v: k for k, v in existing_rename.items()}
    reverse_copy = {v: k for k, v in existing_copy.items()}

    # selectbox 옵션
    src_options = [_SPECIAL_UNMAPPED] + [str(c) for c in source_columns] + [_SPECIAL_CONSTANT, _SPECIAL_COPY]

    st.markdown("#### 칼럼 매핑 수정")
    st.caption("각 업체 칼럼에 대응할 원본 칼럼을 선택하세요.")

    # 각 업체 칼럼에 대해 selectbox 렌더링
    for i, target_col in enumerate(vendor_columns):
        tc = str(target_col)

        # 현재 매핑 값 결정 (pre-select)
        if tc in reverse_rename:
            current_value = reverse_rename[tc]
        elif tc in existing_constants:
            current_value = _SPECIAL_CONSTANT
        elif tc in reverse_copy:
            current_value = _SPECIAL_COPY
        else:
            # 원본에 동일 이름 칼럼이 있으면 자동 매칭
            if tc in source_columns:
                current_value = tc
            else:
                current_value = _SPECIAL_UNMAPPED

        # selectbox index 계산
        if current_value in src_options:
            default_idx = src_options.index(current_value)
        else:
            default_idx = 0

        col_left, col_right = st.columns([1, 1])
        with col_left:
            st.text_input("업체 칼럼", value=tc, disabled=True, key=f"target_label_{vendor_name}_{i}",
                          label_visibility="collapsed" if i > 0 else "visible")
        with col_right:
            selected = st.selectbox(
                "원본 칼럼" if i == 0 else f"원본 칼럼 {i}",
                options=src_options,
                index=default_idx,
                key=f"mapping_select_{vendor_name}_{i}",
                label_visibility="collapsed" if i > 0 else "visible",
            )

        # 고정값 입력 필드
        if selected == _SPECIAL_CONSTANT:
            existing_val = existing_constants.get(tc, "")
            st.text_input(
                f"'{tc}' 고정값",
                value=existing_val,
                placeholder="항상 들어갈 값을 입력하세요",
                key=f"const_input_{vendor_name}_{i}",
            )

        # 복사 원본 선택
        if selected == _SPECIAL_COPY:
            copy_src = reverse_copy.get(tc, "")
            copy_options = [str(c) for c in vendor_columns if str(c) != tc]
            copy_default = copy_options.index(copy_src) if copy_src in copy_options else 0
            st.selectbox(
                f"'{tc}'에 복사할 칼럼",
                options=copy_options,
                index=copy_default,
                key=f"copy_input_{vendor_name}_{i}",
            )

    st.divider()

    # 저장 / 취소 버튼
    save_col1, save_col2 = st.columns(2)
    with save_col1:
        if st.button("매핑 저장", key=f"save_mapping_{vendor_name}", type="primary", use_container_width=True):
            # selectbox 값들을 파싱하여 3개 dict 생성
            new_rename_map = {}
            new_constant_values = {}
            new_copy_map = {}

            for i, target_col in enumerate(vendor_columns):
                tc = str(target_col)
                selected = st.session_state.get(f"mapping_select_{vendor_name}_{i}", _SPECIAL_UNMAPPED)

                if selected == _SPECIAL_UNMAPPED:
                    continue
                elif selected == _SPECIAL_CONSTANT:
                    val = st.session_state.get(f"const_input_{vendor_name}_{i}", "")
                    if val.strip():
                        new_constant_values[tc] = val.strip()
                elif selected == _SPECIAL_COPY:
                    copy_src = st.session_state.get(f"copy_input_{vendor_name}_{i}", "")
                    if copy_src:
                        new_copy_map[copy_src] = tc
                else:
                    # 원본 칼럼 매핑
                    new_rename_map[selected] = tc

            # mapping_config.json에 저장
            mapping_config = _load_mapping_config()
            mapping_config.setdefault("source_types", {})
            if source_name not in mapping_config["source_types"]:
                mapping_config["source_types"][source_name] = {}
            mapping_config["source_types"][source_name].setdefault("vendor_mappings", {})
            mapping_config["source_types"][source_name]["vendor_mappings"][vendor_name] = {
                "column_map": dict(new_rename_map),
                "constant_values": dict(new_constant_values),
            }
            _save_mapping_config(mapping_config)

            # vendor_config.json 갱신
            try:
                update_vendor_in_config(vendor["id"], {
                    "rename_map": dict(new_rename_map),
                    "constant_values": dict(new_constant_values),
                    "copy_map": dict(new_copy_map),
                })
                reload_config()
            except Exception:
                pass

            total = len(new_rename_map) + len(new_constant_values) + len(new_copy_map)
            st.success(f"'{vendor_name}' 매핑이 저장되었습니다! ({total}개)")
            st.session_state["mapping_edit_mode"] = False
            st.rerun()

    with save_col2:
        if st.button("취소", key=f"cancel_mapping_{vendor_name}", use_container_width=True):
            st.session_state["mapping_edit_mode"] = False
            st.rerun()
