"""
주문 변환 매핑 탭 (order_mapping.py)

임의 형식의 주문서를 업로드하면, 등록된 업체 양식과 나란히 표시하여
사용자가 칼럼 매핑과 분류 기준 칼럼을 직접 설정할 수 있는 UI를 제공합니다.
"""
import streamlit as st
import pandas as pd
import json
import os
from map import (
    get_all_vendors,
    get_vendor_by_name,
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


def render_mapping_tab():
    """주문 변환 매핑 탭 UI를 렌더링합니다."""
    st.subheader("매핑 관리")
    st.caption("원본 주문서의 칼럼을 업체 양식 칼럼에 매핑하고, 분류 기준 칼럼을 설정합니다.")

    vendors = get_all_vendors()
    if not vendors:
        st.info("등록된 업체가 없습니다. 먼저 업체 관리 탭에서 업체를 추가하세요.")
        return

    # ── 1. 원본 주문서 업로드 ──
    st.markdown("###  원본 주문서 업로드")
    source_file = st.file_uploader(
        "원본 주문서 엑셀 파일 (.xlsx)",
        type=["xlsx", "xls"],
        help="사방넷 등 임의 형식의 주문서를 업로드하세요.",
        key="mapping_source_file"
    )

    if source_file is None:
        st.info(" 원본 주문서 파일을 업로드하세요.")
        _show_existing_mappings()
        return

    # 원본 파일 읽기
    try:
        source_file.seek(0)
        source_df = pd.read_excel(source_file, nrows=10)
        source_columns = list(source_df.columns)
    except Exception as e:
        st.error(f"파일 읽기 실패: {e}")
        return

    # 원본 주문서 이름 설정
    source_name = st.text_input(
        "원본 주문서 이름",
        value=os.path.splitext(source_file.name)[0],
        help="이 주문서 유형의 이름을 입력하세요 (예: 사방넷)",
        key="source_name_input"
    )

    # ── 2. 대상 업체 선택 ──
    st.markdown("###  매핑 대상 업체 선택")
    vendor_names = [v["name"] for v in vendors]
    selected_vendor = st.selectbox(
        "업체 선택",
        options=vendor_names,
        key="mapping_vendor_select"
    )

    if not selected_vendor:
        return

    # 업체 양식 로드
    vendor = get_vendor_by_name(selected_vendor)
    vendor_form_df, vendor_form_path = _load_vendor_form(selected_vendor)
    vendor_columns = vendor.get("target_columns", []) if vendor else []

    # 양식 파일에 칼럼이 있으면 그 칼럼 사용
    if vendor_form_df is not None:
        vendor_columns = list(vendor_form_df.columns)

    if not vendor_columns:
        st.warning(f"'{selected_vendor}' 업체의 양식 칼럼 정보가 없습니다. 업체 관리 탭에서 양식을 설정하세요.")
        return

    # ── 3. 모드 선택 ──
    st.markdown("###  설정 모드")
    mode = st.radio(
        "모드 선택",
        options=[" 분류 기준 칼럼 선택", " 칼럼 매핑"],
        horizontal=True,
        key="mapping_mode"
    )

    # ── 4. 모드별 UI ──
    if " 분류 기준 칼럼 선택" in mode:
        _render_classification_mode(source_name, source_columns)
    else:
        # 칼럼 매핑 모드 — 좌우 양식 비교 뷰 표시
        st.markdown("###  양식 비교")
        left_col, right_col = st.columns(2)

        with left_col:
            st.markdown(f"** 원본 주문서: {source_name}**")
            st.dataframe(source_df.head(5), use_container_width=True, height=200)
            st.caption(f"칼럼 {len(source_columns)}개: {', '.join(source_columns[:10])}{'...' if len(source_columns) > 10 else ''}")

        with right_col:
            st.markdown(f"** {selected_vendor} 양식**")
            if vendor_form_df is not None:
                st.dataframe(vendor_form_df.head(5), use_container_width=True, height=200)
            else:
                col_df = pd.DataFrame(columns=vendor_columns)
                st.dataframe(col_df, use_container_width=True, height=200)
            st.caption(f"칼럼 {len(vendor_columns)}개: {', '.join(str(c) for c in vendor_columns[:10])}{'...' if len(vendor_columns) > 10 else ''}")

        st.divider()
        _render_mapping_mode(source_name, source_columns, selected_vendor, vendor, vendor_columns)


def _render_classification_mode(source_name, source_columns):
    """분류 기준 칼럼 선택 모드 UI — 원본 파일 칼럼만 표시, 클릭으로 선택"""
    st.markdown("###  분류 기준 칼럼 선택")
    st.caption("원본 주문서의 칼럼 중 업체 분류에 사용할 칼럼을 **클릭**하세요. "
               "이 칼럼의 값에 업체 키워드가 포함되어 있으면 해당 업체로 분류됩니다.")

    # 현재 설정 로드
    mapping_config = _load_mapping_config()
    source_config = mapping_config.get("source_types", {}).get(source_name, {})
    current_classification_col = source_config.get("classification_column", "")

    # 세션 상태에 선택된 칼럼 저장
    session_key = f"selected_class_col_{source_name}"
    if session_key not in st.session_state:
        st.session_state[session_key] = current_classification_col

    selected_col = st.session_state[session_key]

    # ── 칼럼 버튼 그리드 (원본파일 칼럼만 표시, 데이터 없음) ──
    st.markdown("** 원본 주문서 칼럼** — 칼럼을 클릭하여 분류 기준을 선택하세요")

    # 5열 그리드로 칼럼 버튼 배치
    cols_per_row = 5
    for row_start in range(0, len(source_columns), cols_per_row):
        row_cols = st.columns(cols_per_row)
        for i, col in enumerate(source_columns[row_start:row_start + cols_per_row]):
            with row_cols[i]:
                is_selected = (col == selected_col)
                btn_type = "primary" if is_selected else "secondary"
                label = f" {col}" if is_selected else col
                if st.button(
                    label,
                    key=f"class_col_{source_name}_{row_start + i}",
                    type=btn_type,
                    use_container_width=True,
                ):
                    st.session_state[session_key] = col
                    st.rerun()

    # ── 선택 결과 표시 + 저장 ──
    if selected_col:
        st.success(f" '{selected_col}' 칼럼이 분류 기준으로 선택되었습니다.")
        st.caption(f"예: '{selected_col}' 칼럼 값에 '강화'가 포함되면 → 강화군농협으로 분류")

        if st.button(" 분류 기준 저장", key="save_classification", type="primary", use_container_width=True):
            if source_name not in mapping_config.get("source_types", {}):
                mapping_config.setdefault("source_types", {})[source_name] = {}
            mapping_config["source_types"][source_name]["classification_column"] = selected_col
            _save_mapping_config(mapping_config)
            st.success(f" '{source_name}'의 분류 기준 칼럼이 '{selected_col}'로 저장되었습니다.")
    else:
        st.info(" 위에서 칼럼을 클릭하여 분류 기준을 선택하세요.")


def _render_mapping_mode(source_name, source_columns, vendor_name, vendor, vendor_columns):
    """칼럼 매핑 모드 UI"""
    st.markdown("###  칼럼 매핑")
    st.caption("원본 주문서의 칼럼을 업체 양식의 칼럼에 매핑하세요. "
               "왼쪽(원본)에서 칼럼을 선택하고, 오른쪽(업체)에서 대응 칼럼을 선택합니다. "
               "**' 해당 없음'**을 선택하면 직접 고정값을 입력할 수 있습니다.")

    # 현재 매핑 로드
    mapping_config = _load_mapping_config()
    source_config = mapping_config.get("source_types", {}).get(source_name, {})
    vendor_mappings = source_config.get("vendor_mappings", {})
    current_map = vendor_mappings.get(vendor_name, {}).get("column_map", {})
    current_constants = vendor_mappings.get(vendor_name, {}).get("constant_values", {})

    # 세션 상태에 매핑 & 고정값 저장
    session_key = f"mapping_{source_name}_{vendor_name}"
    const_session_key = f"constants_{source_name}_{vendor_name}"
    if session_key not in st.session_state:
        st.session_state[session_key] = dict(current_map)
    if const_session_key not in st.session_state:
        st.session_state[const_session_key] = dict(current_constants)

    current_mapping = st.session_state[session_key]
    current_constant_values = st.session_state[const_session_key]

    _NA_OPTION = " 해당 없음"

    # 새 매핑 추가 UI
    st.markdown("####  매핑 추가")
    map_col1, map_col2, map_col3 = st.columns([2, 2, 1])

    with map_col1:
        src_col = st.selectbox(
            "원본 칼럼",
            options=["(선택)"] + source_columns + [_NA_OPTION],
            key="map_src_col"
        )
    with map_col2:
        dst_col = st.selectbox(
            "업체 칼럼",
            options=["(선택)"] + [str(c) for c in vendor_columns],
            key="map_dst_col"
        )
    with map_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        add_mapping = st.button(" 추가", key="add_mapping_btn")

    # "해당 없음" 선택 시 고정값 입력 필드 표시
    custom_value = ""
    if src_col == _NA_OPTION:
        custom_value = st.text_input(
            " 고정값 입력",
            placeholder="이 업체 칼럼에 항상 들어갈 값을 입력하세요",
            help="예: CJ대한통운, 2025-01-01 등",
            key="map_custom_value"
        )

    if add_mapping:
        if dst_col == "(선택)":
            st.warning(" 업체 칼럼을 선택하세요.")
        elif src_col == "(선택)":
            st.warning(" 원본 칼럼을 선택하거나 '해당 없음'을 선택하세요.")
        elif src_col == _NA_OPTION:
            # 고정값 매핑
            if not custom_value.strip():
                st.warning(" 고정값을 입력하세요.")
            else:
                current_constant_values[dst_col] = custom_value.strip()
                st.session_state[const_session_key] = current_constant_values
                st.rerun()
        else:
            # 일반 칼럼 매핑
            current_mapping[src_col] = dst_col
            st.session_state[session_key] = current_mapping
            st.rerun()

    # 현재 매핑 & 고정값 테이블
    has_any = bool(current_mapping) or bool(current_constant_values)
    if has_any:
        st.markdown("####  현재 매핑 관계")
        mapping_rows = []
        for src, dst in current_mapping.items():
            mapping_rows.append({"원본 칼럼": src, "→": "→", "업체 칼럼": dst, "유형": "칼럼 매핑"})
        for dst, val in current_constant_values.items():
            mapping_rows.append({"원본 칼럼": f" \"{val}\"", "→": "→", "업체 칼럼": dst, "유형": "고정값"})

        st.dataframe(
            pd.DataFrame(mapping_rows),
            use_container_width=True,
            hide_index=True,
        )

        # 개별 매핑 삭제
        st.markdown("####  매핑 삭제")
        delete_options = [f"{src} → {dst}" for src, dst in current_mapping.items()]
        delete_options += [f" \"{val}\" → {dst} (고정값)" for dst, val in current_constant_values.items()]
        to_delete = st.multiselect(
            "삭제할 매핑 선택",
            options=delete_options,
            key="delete_mapping_select"
        )

        if to_delete and st.button(" 선택 매핑 삭제", key="delete_mapping_btn"):
            for item in to_delete:
                if "(고정값)" in item:
                    # 고정값 삭제: ' "val" → dst (고정값)' 형식에서 dst 추출
                    dst = item.split(" → ")[1].replace(" (고정값)", "")
                    current_constant_values.pop(dst, None)
                else:
                    src = item.split(" → ")[0]
                    current_mapping.pop(src, None)
            st.session_state[session_key] = current_mapping
            st.session_state[const_session_key] = current_constant_values
            st.rerun()

        st.divider()

        # 매핑 저장
        save_col1, save_col2 = st.columns([1, 1])
        with save_col1:
            if st.button(" 매핑 저장", key="save_mapping", type="primary", use_container_width=True):
                # mapping_config.json에 저장
                mapping_config.setdefault("source_types", {})
                if source_name not in mapping_config["source_types"]:
                    mapping_config["source_types"][source_name] = {}
                mapping_config["source_types"][source_name].setdefault("vendor_mappings", {})
                mapping_config["source_types"][source_name]["vendor_mappings"][vendor_name] = {
                    "column_map": dict(current_mapping),
                    "constant_values": dict(current_constant_values),
                }
                _save_mapping_config(mapping_config)

                # vendor_config.json의 rename_map + constant_values도 갱신
                if vendor:
                    try:
                        update_vendor_in_config(vendor["id"], {
                            "rename_map": dict(current_mapping),
                            "constant_values": dict(current_constant_values),
                        })
                        reload_config()
                    except Exception:
                        pass  # 갱신 실패해도 mapping_config는 저장됨

                total = len(current_mapping) + len(current_constant_values)
                st.success(f" '{source_name}' → '{vendor_name}' 매핑이 저장되었습니다! "
                           f"(칼럼 매핑 {len(current_mapping)}개, 고정값 {len(current_constant_values)}개)")

        with save_col2:
            if st.button(" 초기화", key="reset_mapping", use_container_width=True):
                st.session_state[session_key] = {}
                st.session_state[const_session_key] = {}
                st.rerun()
    else:
        st.info("매핑이 없습니다. 위에서 원본 칼럼과 업체 칼럼을 선택하여 매핑을 추가하세요.")


def _show_existing_mappings():
    """기존 저장된 매핑 정보를 표시합니다."""
    mapping_config = _load_mapping_config()
    source_types = mapping_config.get("source_types", {})

    if not source_types:
        return

    st.divider()
    st.markdown("###  저장된 매핑 설정")

    for source_name, source_config in source_types.items():
        with st.expander(f" {source_name}", expanded=False):
            # 분류 기준
            classification_col = source_config.get("classification_column", "")
            if classification_col:
                st.markdown(f"**분류 기준 칼럼:** `{classification_col}`")

            # 업체별 매핑
            vendor_mappings = source_config.get("vendor_mappings", {})
            if vendor_mappings:
                for vendor_name, mapping_info in vendor_mappings.items():
                    col_map = mapping_info.get("column_map", {})
                    if col_map:
                        st.markdown(f"**{vendor_name}** ({len(col_map)}개 매핑)")
                        map_data = [{"원본": src, "→": "→", "업체": dst} for src, dst in col_map.items()]
                        st.dataframe(pd.DataFrame(map_data), use_container_width=True, hide_index=True, height=150)
