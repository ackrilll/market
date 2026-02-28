"""임시 스크립트: vendor_config.json에 keywords 필드 추가"""
import json

with open('data/vendor_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

count = 0
for v in config['vendors']:
    if 'keywords' not in v:
        v['keywords'] = [v['name']]
        count += 1

with open('data/vendor_config.json', 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print(f"Updated {count} vendors with keywords field")
