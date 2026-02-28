"""
사람 변환 vs 프로그램 변환 결과물 정밀 비교 (v3)
- 헤더 행 자동 감지
- 보류 데이터 병합 고려 (사람 데이터가 프로그램에 포함되어 있는지 확인)
- 양구군농협 제외
"""
import pandas as pd
import os
import sys
import warnings
warnings.filterwarnings('ignore')

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compare_result_v3.txt")
sys.stdout = open(output_path, 'w', encoding='utf-8')

PERSON_DIR = r"c:\Users\skawl\PycharmProjects\365배포\user_test\person_converted\곽서윤 365_주문서_결과물_2026-02-09"
PROGRAM_DIR = r"c:\Users\skawl\PycharmProjects\365배포\user_test\program_converted\결과물"

# 매핑: (사람파일, 프로그램파일, 사람헤더행, 비교기준컬럼)
match_table = [
    ('강화군농협.xlsx',                         '0_강화군농협_양식.xlsx',     1, '수령인'),
    ('관인농협.xlsx',                           '2_관인농협_양식.xlsx',       1, '수령인'),
    ('담양통합.xlsx',                           '3_담양_양식.xlsx',           1, '수령인'),
    ('당진해나루쌀조공법인.xlsx',               '4_당진시농협_양식.xlsx',     1, '수령인'),
    ('대명엠씨혈당강하쌀.xlsx',                 '5_대명엠씨_양식.xlsx',       0, '수령자 성함'),
    ('독정RPC택배양식.xlsx',                    '7_독정_양식.xlsx',           0, '받는분'),
    ('무안통합농협.xlsx',                       '8_무안군농협_양식.xlsx',     1, '수령인'),
    ('보성통합택배주문양식.xlsx',               '9_보성군농협_양식.xlsx',     0, '수령자'),
    ('석곡농협발주양식.xlsx',                   '10_석곡농협_양식.xlsx',      0, '수령자'),
    ('신김포농협.xlsx',                         '11_신김포농협_양식.xlsx',    1, '수령인'),
    ('안중농협.xlsx',                           '12_안중농협_양식.xlsx',      1, '수령인'),
    # 양구군농협 제외 (사용자 요청)
    ('양구친환경 삶은시래기.xlsx',              '14_양구친환경_양식.xlsx',    1, '수령인'),
    ('연천군농협미곡종합처리장.xlsx',           '17_연천_양식.xlsx',          1, '수령인'),
    ('오덕쌀(주)채널스케치.xlsx',               '19_오덕쌀_양식.xlsx',       1, '수령인'),
    ('오병이어누룽지.xlsx',                     '20_오병이어_양식.xlsx',      1, '수령인'),
    ('율목영농조합법인.xlsx',                   '21_율목_양식.xlsx',          1, '수령인'),
    ('이천농협택배양식(한진).xlsx',             '22_이천남부농협_양식.xlsx',  1, '수령인'),
    ('철원동송농협(365건강농산).xls',           '23_동송농협_양식.xlsx',      0, '상품명(365건강농산)'),
    ('파주.xlsx',                               '25_파주_양식.xlsx',          1, '수령인'),
    ('팔탄농협 주문서 양식2-9.xls',            '26_팔탄농협_양식.xlsx',      0, None),
    ('한국라이스텍 백진주.xlsx',                '27_한국라이스텍_양식.xlsx',  0, '수령자'),
]


def read_person(path, header_row):
    ext = os.path.splitext(path)[1].lower()
    engine = 'xlrd' if ext == '.xls' else 'openpyxl'
    df = pd.read_excel(path, engine=engine, header=header_row)
    # NaN 컬럼 제거
    df = df.loc[:, ~df.columns.astype(str).str.startswith('Unnamed')]
    # 완전히 빈 행 제거
    df = df.dropna(how='all').reset_index(drop=True)
    return df


def read_program(path):
    df = pd.read_excel(path, engine='openpyxl', header=1)
    df = df.loc[:, ~df.columns.astype(str).str.startswith('Unnamed')]
    df = df.dropna(how='all').reset_index(drop=True)
    return df


print("=" * 80)
print("365 건강농산 — 사람 변환 vs 프로그램 변환 정밀 비교 (v3)")
print("=" * 80)
print(f"비교 대상: {len(match_table)}개 업체 (양구군농협 제외)")
print()

total = 0
perfect_match = 0
data_match = 0
issues = []

for p_file, prog_file, p_header, key_col in match_table:
    p_path = os.path.join(PERSON_DIR, p_file)
    prog_path = os.path.join(PROGRAM_DIR, prog_file)
    
    vendor = prog_file.split('_')[1] if '_' in prog_file else prog_file.replace('.xlsx', '')
    total += 1
    
    if not os.path.exists(p_path):
        print(f"  ⚠️ {vendor}: 사람 파일 없음 → {p_file}")
        issues.append((vendor, "사람 파일 없음"))
        continue
    if not os.path.exists(prog_path):
        print(f"  ⚠️ {vendor}: 프로그램 파일 없음 → {prog_file}")
        issues.append((vendor, "프로그램 파일 없음"))
        continue
    
    try:
        p_df = read_person(p_path, p_header)
        prog_df = read_program(prog_path)
        
        print(f"\n{'─'*60}")
        print(f"📋 {vendor}")
        print(f"   사람: {len(p_df)}행 x {len(p_df.columns)}열")
        print(f"   프로그램: {len(prog_df)}행 x {len(prog_df.columns)}열")
        
        # 행 수 비교
        if len(p_df) == len(prog_df):
            print(f"   ✅ 행 수 일치")
        elif len(prog_df) > len(p_df):
            extra = len(prog_df) - len(p_df)
            print(f"   ℹ️ 프로그램이 {extra}행 더 많음 (보류 데이터 병합 가능)")
        else:
            diff = len(p_df) - len(prog_df)
            print(f"   ⚠️ 사람이 {diff}행 더 많음")
        
        # 사람 데이터의 핵심 값(수령인)이 프로그램에 포함되어 있는지 확인
        if key_col and key_col in p_df.columns:
            person_names = set(str(v).strip() for v in p_df[key_col].dropna().tolist() if str(v).strip())
            
            # 프로그램에서 매칭되는 컬럼 찾기
            prog_key_col = None
            for col in prog_df.columns:
                if key_col == str(col).strip():
                    prog_key_col = col
                    break
                # 비슷한 이름 매칭
                if key_col in str(col) or str(col) in key_col:
                    prog_key_col = col
                    break
            
            if prog_key_col:
                prog_names = set(str(v).strip() for v in prog_df[prog_key_col].dropna().tolist() if str(v).strip())
                
                found = person_names & prog_names
                missing = person_names - prog_names
                
                if missing:
                    print(f"   ⚠️ 사람 '{key_col}' 중 프로그램에 없는 값: {missing}")
                    issues.append((vendor, f"사람 데이터 누락: {missing}"))
                else:
                    print(f"   ✅ 사람의 모든 '{key_col}' 값이 프로그램에 포함됨 ({len(found)}명)")
                    data_match += 1
            else:
                print(f"   ℹ️ 프로그램에서 '{key_col}' 컬럼을 찾지 못함")
                # 전체 컬럼 출력
                print(f"   프로그램 컬럼: {list(prog_df.columns)}")
        else:
            if key_col:
                print(f"   ℹ️ 사람 파일에 '{key_col}' 컬럼 없음")
                print(f"   사람 컬럼: {list(p_df.columns)}")
            else:
                print(f"   ℹ️ 키 컬럼 미지정 (수동 확인 필요)")
        
        # 공통 컬럼 데이터 비교 (동일 행 수만큼)
        p_cols = set(str(c).strip() for c in p_df.columns)
        prog_cols = set(str(c).strip() for c in prog_df.columns)
        common = p_cols & prog_cols
        common = {c for c in common if c and c != 'nan'}
        
        if common and min(len(p_df), len(prog_df)) > 0:
            min_rows = min(len(p_df), len(prog_df))
            all_match = True
            mismatch_details = []
            
            for col_name in sorted(common):
                # 사람과 프로그램 각각에서 컬럼 찾기
                p_col = [c for c in p_df.columns if str(c).strip() == col_name][0]
                prog_col = [c for c in prog_df.columns if str(c).strip() == col_name][0]
                
                match_count = 0
                for i in range(min_rows):
                    p_val = str(p_df[p_col].iloc[i]).strip() if pd.notna(p_df[p_col].iloc[i]) else ""
                    prog_val = str(prog_df[prog_col].iloc[i]).strip() if pd.notna(prog_df[prog_col].iloc[i]) else ""
                    if p_val == prog_val:
                        match_count += 1
                
                pct = match_count / min_rows * 100
                if pct < 100:
                    all_match = False
                    mismatch_details.append(f"     {col_name}: {pct:.0f}% ({match_count}/{min_rows})")
            
            if all_match:
                print(f"   ✅ 공통 {len(common)}개 컬럼 데이터 100% 일치")
                perfect_match += 1
            else:
                print(f"   📊 공통 {len(common)}개 컬럼 비교:")
                for d in mismatch_details:
                    print(d)
    
    except Exception as e:
        print(f"  ❌ {vendor}: 오류 → {e}")
        issues.append((vendor, str(e)))

print(f"\n{'='*80}")
print("📊 최종 요약")
print(f"{'='*80}")
print(f"비교 업체: {total}개 (양구군농협 제외)")
print(f"사람 데이터 포함 확인: {data_match}/{total} ✅")
print(f"공통 컬럼 100% 일치: {perfect_match}/{total}")
print()

if issues:
    print(f"⚠️ 문제 발견 ({len(issues)}건):")
    for vendor, desc in issues:
        print(f"  - {vendor}: {desc}")
else:
    print("🎉 모든 업체 정상!")

sys.stdout.close()
sys.stdout = sys.__stdout__
print("완료! 결과 → user_test/compare_result_v3.txt")
