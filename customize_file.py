import pandas as pd


def get_customize_config(idx):
    """업체별 커스터마이징 종류를 반환"""
    match idx:
        case 27:  # 한국라이스텍
            return ['append_fixed_rows']
        case _:
            return []


def apply_customization(df, idx, customize_type):
    """커스터마이징 타입에 따라 데이터프레임 변환"""
    if customize_type == 'append_fixed_rows':
        if idx == 27:  # 한국라이스텍
            return append_korea_rice_tech_rows(df)
    return df


def append_korea_rice_tech_rows(df):
    """한국라이스텍 고정값 행 추가"""

    # 컬럼 순서: ['주문', '출고', '품목명', '수량', '단가', '금액', '주문자', '추가배송비',
    #           '수령자', '연락처', '주  소', '배송메세지1', '판매경로', '운송장번호',
    #           '주문번호 ', '품목 코드', '거래처코드']

    # 빈 행 추가
    empty_row = pd.DataFrame([{col: '' for col in df.columns}])

    # 안내 문구 행
    notice_row = pd.DataFrame([{
        '품목명': '품목명, 품목코드에 맞추어 노란색으로 표시된 셀에 내용 넣어서 보내주시기 바랍니다.',
        **{col: '' for col in df.columns if col != '품목명'}
    }])

    # 상품 목록 행들
    products = [
        {'품목명': '안동밥상 백진주 백미 10kg', '수량': '5-14-1', '단가': '880904294511', '금액': '1238701787'},
        {'품목명': '안동밥상 백진주 백미 20kg(10kg*2)', '수량': '', '단가': '8809042945111', '금액': '1238701787'},
        {'품목명': '안동밥상 백진주 현미 10kg', '수량': '', '단가': '880904294512', '금액': '1238701787'},
        {'품목명': '안동밥상 백진주 현미 20kg(10kg*2)', '수량': '', '단가': '8809042945121', '금액': '1238701787'},
        {'품목명': '안동밥상 백진주 백미 10kg+현미 10kg', '수량': '', '단가': '8809042945122', '금액': '1238701787'},
        {'품목명': '9분도쌀눈쌀10kg', '수량': '', '단가': '8809042940976', '금액': '1238701787'},
        {'품목명': '백진주쌀 누룽지 700g', '수량': '', '단가': '8809042940266', '금액': '1238701787'},
    ]

    product_rows = []
    for product in products:
        row_data = {col: '' for col in df.columns}
        row_data.update(product)
        product_rows.append(row_data)

    product_df = pd.DataFrame(product_rows)

    # 모든 행 결합
    result_df = pd.concat([df, empty_row, notice_row, product_df], ignore_index=True)

    return result_df
