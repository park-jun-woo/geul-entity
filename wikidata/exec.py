import json

with open("geulso/wikidata/wikitrees1.json", "r") as f:
    data = json.load(f)

print(f"roots 개수: {len(data['roots']):,}")
print(f"leaves 개수: {len(data['leaves']):,}")
print(f"edges 개수: {len(data['edges']):,}")

# 루트 중 인스턴스 수 상위 20개
roots_with_count = [
    (qid, data['type_qids'].get(qid, {}).get('count', 0), data['type_qids'].get(qid, {}).get('name', ''))
    for qid in data['roots']
]
roots_with_count.sort(key=lambda x: -x[1])

print("\n루트 TOP 20:")
for i, (qid, cnt, name) in enumerate(roots_with_count[:20], 1):
    print(f"{i:2}. {qid:12} {name:30} : {cnt:,}")