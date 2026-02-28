"""
사람 변환 vs 프로그램 변환 결과물 비교 스크립트 (v2)
"""
import pandas as pd
import os
import sys
import io

# stdout을 UTF-8 파일로 리디렉트
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compare_result.txt")
sys.stdout = open(output_path, 'w', encoding='utf-8')

PERSON_DIR = r"c:\Users\skawl\PycharmProjects\365배포\user_test\person_converted\곽서윤 365_주문서_결과물_2026-02-09"
PROGRAM_DIR = r"c:\Users\skawl\PycharmProjects\365배포\user_test\program_converted\결과물"

def read_excel_safe(path, header_row=0):
    """다양한 엔진으로 엑셀 파일 읽기 시도"""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.xls':
        return pd.read_excel(path, engine='xlrd', header=header_row)
    else:
        return pd.read_excel(path, engine='openpyxl', header=header_row)


# 매핑: 사람 파일명 -> 프로그램 파일명
match_table = {
    '강화군농협.xlsx': '0_강화군농협_양식.xlsx',
    '관인농협.xlsx': '2_관인농협_양식.xlsx',
    '담양통합.xlsx': '3_담양_양식.xlsx',
    '당진해나루쌀조공법인.xlsx': '4_당진시농협_양식.xlsx',
    '대명엠씨혈당강하쌀.xlsx': '5_대명엠씨_양식.xlsx',
    '독정RPC택배양식.xlsx': '7_독정_양식.xlsx',
    '무안통합농협.xlsx': '8_무안군농협_양식.xlsx',
    '보성통합택배주문양식.xlsx': '9_보성군농협_양식.xlsx',
    '석곡농협발주양식.xlsx': '10_석곡농협_양식.xlsx',
    '신김포농협.xlsx': '11_신김포농협_양식.xlsx',
    '안중농협.xlsx': '12_안중농협_양식.xlsx',
    '양구군농협.xlsx': '13_양구군농협_양식.xlsx',
    '양구친환경 삶은시래기.xlsx': '14_양구친환경_양식.xlsx',
    '연천군농협미곡종합처리장.xlsx': '17_연천_양식.xlsx',
    '오덕쌀(주)채널스케치.xlsx': '19_오덕쌀_양식.xlsx',
    '오병이어누룽지.xlsx': '20_오병이어_양식.xlsx',
    '율목영농조합법인.xlsx': '21_율목_양식.xlsx',
    '이천농협택배양식(한진).xlsx': '22_이천남부농협_양식.xlsx',
    '철원동송농협(365건강농산).xls': '23_동송농협_양식.xlsx',
    '파주.xlsx': '25_파주_양식.xlsx',
    '팔탄농협 주문서 양식2-9.xls': '26_팔탄농협_양식.xlsx',
    '한국라이스텍 백진주.xlsx': '27_한국라이스텍_양식.xlsx',
}

# 사람에만 있는 파일
person_files = [f for f in os.listdir(PERSON_DIR) if f.endswith(('.xlsx', '.xls'))]
program_files = [f for f in os.listdir(PROGRAM_DIR) if f.endswith(('.xlsx', '.xls'))]

person_only = [f for f in person_files if f not in match_table]
program_only = [f for f in program_files if f not in match_table.values()]

print("=" * 80)
print("1. 파일 구성 비교")
print("=" * 80)
print(f"사람 변환: {len(person_files)}개 파일")
print(f"프로그램 변환: {len(program_files)}개 파일")
print(f"매칭 가능: {len(match_table)}쌍")
print(f"사람에만 존재: {person_only}")
print(f"프로그램에만 존재: {program_only}")

print("\n" + "=" * 80)
print("2. 업체별 행/열 비교")
print("=" * 80)

results = []

for p_file, prog_file in match_table.items():
    p_path = os.path.join(PERSON_DIR, p_file)
    prog_path = os.path.join(PROGRAM_DIR, prog_file)
    
    if not os.path.exists(p_path) or not os.path.exists(prog_path):
        print(f"  ⚠️ 파일 없음: {p_file} or {prog_file}")
        continue
    
    try:
        p_df = read_excel_safe(p_path)
        prog_df = read_excel_safe(prog_path, header_row=1)
        
        vendor = prog_file.split('_')[1] if '_' in prog_file else prog_file
        
        row_match = len(p_df) == len(prog_df)
        status = "OK" if row_match else "DIFF"
        
        result = {
            'vendor': vendor,
            'p_rows': len(p_df),
            'prog_rows': len(prog_df),
            'p_cols': len(p_df.columns),
            'prog_cols': len(prog_df.columns),
            'row_match': row_match,
            'p_columns': list(p_df.columns),
            'prog_columns': list(prog_df.columns),
            'p_df': p_df,
            'prog_df': prog_df,
        }
        results.append(result)
        
        icon = "V" if row_match else "X"
        diff = len(prog_df) - len(p_df)
        diff_str = f" (차이: {'+' if diff > 0 else ''}{diff})" if not row_match else ""
        print(f"  [{icon}] {vendor}: 사람 {len(p_df)}행x{len(p_df.columns)}열 / 프로그램 {len(prog_df)}행x{len(prog_df.columns)}열{diff_str}")
        
    except Exception as e:
        print(f"  [E] {p_file}: {e}")

# 3. 컬럼 구조 비교
print("\n" + "=" * 80)
print("3. 컬럼 구조 상세 비교 (모든 업체)")
print("=" * 80)

for r in results:
    p_cols = set(str(c).strip() for c in r['p_columns'] if str(c).strip() and str(c) != 'nan')
    prog_cols = set(str(c).strip() for c in r['prog_columns'] if str(c).strip() and str(c) != 'nan')
    
    common = p_cols & prog_cols
    only_person = p_cols - prog_cols
    only_program = prog_cols - p_cols
    
    print(f"\n--- {r['vendor']} ---")
    print(f"  공통 컬럼 ({len(common)}개): {sorted(common)[:10]}{'...' if len(common) > 10 else ''}")
    if only_person:
        print(f"  사람에만 ({len(only_person)}개): {sorted(only_person)}")
    if only_program:
        print(f"  프로그램에만 ({len(only_program)}개): {sorted(only_program)}")

# 4. 값 비교 (공통 컬럼의 데이터 일치율)
print("\n" + "=" * 80)
print("4. 데이터 값 비교 (공통 컬럼)")
print("=" * 80)

for r in results:
    p_df = r['p_df']
    prog_df = r['prog_df']
    
    p_cols_clean = {str(c).strip(): c for c in p_df.columns}
    prog_cols_clean = {str(c).strip(): c for c in prog_df.columns}
    
    common_clean = set(p_cols_clean.keys()) & set(prog_cols_clean.keys())
    common_clean = {c for c in common_clean if c and c != 'nan'}
    
    if not common_clean or min(len(p_df), len(prog_df)) == 0:
        continue
    
    print(f"\n--- {r['vendor']} (공통 {len(common_clean)}개 컬럼, {min(len(p_df), len(prog_df))}행 비교) ---")
    
    min_rows = min(len(p_df), len(prog_df))
    mismatches = []
    
    for col_name in sorted(common_clean):
        p_col = p_cols_clean[col_name]
        prog_col = prog_cols_clean[col_name]
        
        match_count = 0
        total = min_rows
        sample_diffs = []
        
        for i in range(min_rows):
            p_val = str(p_df[p_col].iloc[i]).strip() if pd.notna(p_df[p_col].iloc[i]) else ""
            prog_val = str(prog_df[prog_col].iloc[i]).strip() if pd.notna(prog_df[prog_col].iloc[i]) else ""
            
            if p_val == prog_val:
                match_count += 1
            else:
                if len(sample_diffs) < 2:
                    sample_diffs.append((i+1, p_val[:30], prog_val[:30]))
        
        pct = match_count / total * 100 if total > 0 else 0
        if pct < 100:
            mismatches.append((col_name, pct, match_count, total, sample_diffs))
    
    if mismatches:
        for col_name, pct, match, total, diffs in mismatches:
            print(f"  [!] {col_name}: {pct:.0f}% 일치 ({match}/{total})")
            for row_num, p_val, prog_val in diffs:
                print(f"      행{row_num}: 사람='{p_val}' vs 프로그램='{prog_val}'")
    else:
        print(f"  [V] 모든 공통 컬럼 데이터 100% 일치!")

# 5. 최종 요약
print("\n" + "=" * 80)
print("5. 최종 요약")
print("=" * 80)
total = len(results)
row_ok = sum(1 for r in results if r['row_match'])
print(f"\n비교 완료: {total}개 업체")
print(f"행 수 일치: {row_ok}개")
print(f"행 수 불일치: {total - row_ok}개")

for r in results:
    if not r['row_match']:
        diff = r['prog_rows'] - r['p_rows']
        print(f"  - {r['vendor']}: 사람 {r['p_rows']}행 vs 프로그램 {r['prog_rows']}행 ({'+' if diff > 0 else ''}{diff})")
