"""
커스텀 Streamlit 테이블 컴포넌트 (vendor_table)

셀 내 드래그앤드롭 파일 업로드를 지원하는 업체 관리 테이블입니다.
"""
import streamlit.components.v1 as components
import os
import base64

_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
_component = components.declare_component("vendor_table", path=_COMPONENT_DIR)

# map.py의 _FORM_DIR 경로
_FORM_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "target_form")


def vendor_table(vendors, key=None):
    """
    커스텀 업체 관리 테이블을 렌더링합니다.

    Args:
        vendors: 업체 데이터 리스트 (각 항목: id, name, keywords, form_file)
        key: Streamlit 위젯 키

    Returns:
        dict | None: 사용자 상호작용 결과
    """
    vendor_data = []
    for v in vendors:
        keywords = ", ".join(v.get("keywords", [v["name"]]))
        form_file = v.get("form_file", "")

        # 양식 파일이 있으면 base64로 읽어서 전달 (다운로드용)
        form_file_data = None
        if form_file:
            filepath = os.path.join(_FORM_DIR, form_file)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "rb") as f:
                        form_file_data = base64.b64encode(f.read()).decode("utf-8")
                except Exception:
                    pass

        vendor_data.append({
            "id": v["id"],
            "name": v["name"],
            "keywords": keywords,
            "form_file": form_file,
            "form_file_data": form_file_data,
        })

    component_value = _component(
        vendors=vendor_data,
        key=key,
        default=None,
    )

    return component_value

