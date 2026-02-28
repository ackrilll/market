"""
엑셀 파일의 컬럼 구조를 확인하는 유틸리티 스크립트.
사용법: python read.py <엑셀파일경로>
"""
import pandas as pd
import sys
import os


def inspect_excel(file_path):
    """엑셀 파일의 컬럼 구조를 출력합니다."""
    if not os.path.exists(file_path):
        print(f"[오류] 파일을 찾을 수 없습니다: {file_path}")
        return

    print(f"=== {os.path.basename(file_path)} ===")
    raw_df = pd.read_excel(file_path)

    # 1행 컬럼명
    columns1 = raw_df.columns.tolist()
    print(f"헤더(1행) 컬럼: {columns1}")

    # 2행 컬럼명 (헤더가 2행인 양식 확인용)
    if len(raw_df) > 0:
        columns2 = raw_df.values[0].tolist()
        print(f"데이터(2행) 값:  {columns2}")

    print(f"총 행 수: {len(raw_df)}")
    print(f"총 컬럼 수: {len(columns1)}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python read.py <엑셀파일경로>")
        print("예시:   python read.py data/target_form/강화군농협.xlsx")
        sys.exit(1)

    for path in sys.argv[1:]:
        inspect_excel(path)