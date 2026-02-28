import json

with open("data/vendor_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

print("=" * 60)
print("업체별 분류 키워드 목록")
print("=" * 60)
print()
print("분류 방식: df['상품약어'].str.contains(키워드, regex=False)")
print(f"총 업체 수: {len(config['vendors'])}개")
print()
print(f"{'idx':<5} {'업체명':<20} {'매칭 키워드':<20}")
print("-" * 50)

for v in config["vendors"]:
    # 현재 키워드 = 업체명 그 자체
    print(f"{v['id']:<5} {v['name']:<20} {v['name']:<20}")

print()
print("=" * 60)
print("주의: 키워드 포함 관계로 인한 오매칭 가능성")
print("=" * 60)

names = [v["name"] for v in config["vendors"]]
for i, n1 in enumerate(names):
    for j, n2 in enumerate(names):
        if i != j and n1 in n2:
            print(f"  [!] '{n1}' (idx {i}) 이(가) '{n2}' (idx {j})에 포함됨")
