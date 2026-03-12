"""
커스텀 Streamlit 칼럼 매핑 컴포넌트 (column_mapper)

드래그 앤 드롭으로 원본 칼럼과 업체 칼럼을 매핑하는 UI를 제공합니다.
"""
import streamlit.components.v1 as components
import os

_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
_component = components.declare_component("column_mapper", path=_COMPONENT_DIR)


def column_mapper(
    vendor_name,
    vendor_id,
    source_columns=None,
    target_columns=None,
    existing_mapping=None,
    source_file_name="",
    target_file_name="",
    key=None,
):
    """
    드래그 앤 드롭 칼럼 매핑 UI를 렌더링합니다.

    Args:
        vendor_name: 업체명
        vendor_id: 업체 ID
        source_columns: 원본 칼럼 리스트
        target_columns: 업체 칼럼 리스트
        existing_mapping: 기존 매핑 {"rename_map": {}, "constant_values": {}, "copy_map": {}}
        source_file_name: 원본 파일명
        target_file_name: 업체 양식 파일명
        key: Streamlit 위젯 키

    Returns:
        dict | None: 사용자 상호작용 결과
    """
    return _component(
        vendor_name=vendor_name,
        vendor_id=vendor_id,
        source_columns=source_columns or [],
        target_columns=target_columns or [],
        existing_mapping=existing_mapping or {},
        source_file_name=source_file_name,
        target_file_name=target_file_name,
        key=key,
        default=None,
    )
