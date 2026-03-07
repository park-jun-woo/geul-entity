import json

with open("geulso/wikidata/wikitrees1.json", "r") as f:
    data = json.load(f)

# 빈도순 정렬
sorted_types = sorted(
    data['type_qids'].items(),
    key=lambda x: -x[1]['count']
)

# 위키미디어 메타 필터링
wiki_keywords = ['wikimedia', 'wikipedia', 'wikinews', 'wikidata', 
                 'template', 'disambiguation', 'category']

def is_wiki_meta(name):
    name_lower = name.lower()
    return any(kw in name_lower for kw in wiki_keywords)

# TOP500 중 메타 제외
filtered = []
for qid, info in sorted_types:
    if not is_wiki_meta(info['name']):
        filtered.append((qid, info['name'], info['count']))
    if len(filtered) >= 500:
        break

# 출력
print(f"필터링 후: {len(filtered)}개\n")
for i, (qid, name, count) in enumerate(filtered[:100], 1):
    print(f"{i:3}. {qid:12} {name:40} : {count:,}")

# 저장
with open("geulso/wikidata/top500_filtered.json", "w") as f:
    json.dump(filtered, f, indent=2, ensure_ascii=False)