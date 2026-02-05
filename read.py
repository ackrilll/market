import pandas as pd
import os
import xlrd

# root_path = r"C:\Users\skawl\OneDrive\문서\365건강농산\목표양식"
# for basename in os.listdir(root_path):
#     file_path = os.path.join(root_path, basename)
#     raw_df = pd.read_excel(file_path)
#     columns = raw_df.columns.tolist()
#     if "우편번호" in columns:
#         print("우편번호 칼럼 있음")
#         pass
#     else:
#         print("우편번호 칼럼 없어서 다음 행 확인")
#         columns = raw_df.values[0].tolist()
#     print(f"-----------------------------{basename}-------------------------")
#     print(columns)

# file_path = r"C:\Users\skawl\OneDrive\문서\365건강농산\목표양식\한국라이스텍 백진주.xlsx"
# raw_df = pd.read_excel(file_path)
columns1 = raw_df.columns.tolist()
print(columns1)
columns2 = raw_df.values[0].tolist()
print(columns2)

# root_path = r"C:\Users\skawl\OneDrive\문서\365건강농산\목표양식"
# list = os.listdir(root_path)
# new_list =[]
# for name in list:
#     name = name.replace('.xlsx','')
#     if "농협" in name:
#         new_list.insert(0,name)
#     else:
#         new_list.append(name)
# print(new_list)