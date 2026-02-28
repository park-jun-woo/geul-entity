import psycopg2
import json
import os

CONN_STR = "host=localhost user=postgres password=test1224! dbname=geuldev"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "wikitrees1.json")

conn = psycopg2.connect(CONN_STR)
cur = conn.cursor()

# 0. hierarchy 테이블 상태 확인
print("0. hierarchy 테이블 확인...")
cur.execute("SELECT COUNT(*) FROM hierarchy")
print(f"   총 행 수: {cur.fetchone()[0]:,}")

cur.execute("SELECT DISTINCT property FROM hierarchy LIMIT 10")
print(f"   property 값들: {[r[0] for r in cur.fetchall()]}")

cur.execute("SELECT child, parent, property FROM hierarchy LIMIT 5")
print(f"   샘플 데이터:")
for row in cur.fetchall():
    print(f"      {row}")

# 1. P31 목적어로 사용된 Q-ID 목록
print("\n1. P31 목적어 Q-ID 추출 중...")
cur.execute("""
    SELECT object_value, usage_count
    FROM property_object_stats
    WHERE property_id = 'P31' AND object_value LIKE 'Q%'
    ORDER BY usage_count DESC
""")
type_qids = {row[0]: row[1] for row in cur.fetchall()}
print(f"   타입 역할 Q-ID 수: {len(type_qids):,}")

# 2. Q-ID 라벨 가져오기 (영어 우선, 없으면 한국어)
print("\n2. Q-ID 라벨 추출 중...")
qid_list = list(type_qids.keys())

cur.execute("""
    SELECT entity_id, label
    FROM entity_labels
    WHERE entity_id = ANY(%s) AND language = 'en'
""", (qid_list,))
labels_en = {row[0]: row[1] for row in cur.fetchall()}

cur.execute("""
    SELECT entity_id, label
    FROM entity_labels
    WHERE entity_id = ANY(%s) AND language = 'ko'
""", (qid_list,))
labels_ko = {row[0]: row[1] for row in cur.fetchall()}

# 영어 없으면 한국어, 둘 다 없으면 빈 문자열
labels = {qid: labels_en.get(qid, labels_ko.get(qid, "")) for qid in qid_list}
print(f"   라벨 있는 Q-ID: {sum(1 for v in labels.values() if v):,}")

# 3. 타입 간 P279 관계 추출 (triples 테이블에서 직접)
print("\n3. 타입 간 P279 관계 추출 중...")
cur.execute("""
    SELECT subject, object_value
    FROM triples
    WHERE property = 'P279'
      AND subject = ANY(%s)
      AND object_value = ANY(%s)
""", (qid_list, qid_list))
edges = cur.fetchall()
print(f"   P279 엣지 수: {len(edges):,}")

# hierarchy 테이블에서도 시도
if len(edges) == 0:
    print("   triples에서 못찾음, hierarchy 재시도...")
    cur.execute("""
        SELECT child, parent
        FROM hierarchy
        WHERE child = ANY(%s) AND parent = ANY(%s)
    """, (qid_list, qid_list))
    edges = cur.fetchall()
    print(f"   hierarchy 엣지 수: {len(edges):,}")

# 4. 그래프 통계
children = set(e[0] for e in edges)
parents = set(e[1] for e in edges)
roots = parents - children
leaves = children - parents

print(f"\n4. 그래프 통계:")
print(f"   루트 후보: {len(roots):,}")
print(f"   리프 노드: {len(leaves):,}")
print(f"   중간 노드: {len(children & parents):,}")

# 다중 상속 체크
from collections import Counter
child_counts = Counter(e[0] for e in edges)
multi_parent = [(qid, cnt) for qid, cnt in child_counts.items() if cnt > 1]
print(f"   다중 상속 노드: {len(multi_parent):,}")

# 5. 상위 20개 루트
print("\n5. 루트 후보 TOP 20 (인스턴스 수):")
root_with_count = [(qid, type_qids.get(qid, 0), labels.get(qid, "")) for qid in roots]
root_with_count.sort(key=lambda x: -x[1])
for i, (qid, cnt, name) in enumerate(root_with_count[:20], 1):
    print(f"   {i:2}. {qid:12} {name:30} : {cnt:,}")

# 6. 결과 저장
type_qids_with_info = {
    qid: {"name": labels.get(qid, ""), "count": count}
    for qid, count in type_qids.items()
}

result = {
    "type_qids": type_qids_with_info,
    "edges": edges,
    "roots": list(roots),
    "leaves": list(leaves),
    "multi_parent_count": len(multi_parent)
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
print(f"\n결과 저장: {OUTPUT_PATH}")

cur.close()
conn.close()