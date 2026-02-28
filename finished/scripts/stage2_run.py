#!/usr/bin/env python3
"""
Stage 2: 속성 간 계층 의존성 탐지

조건부 엔트로피를 사용하여 속성 간 종속 관계 DAG 생성
"""

import math
import sys
from collections import defaultdict, Counter
from itertools import combinations
import psycopg2

# 제외할 속성 (외부 ID, 이름 등)
EXCLUDE_PROPERTIES = {
    # 외부 ID
    'P646', 'P214', 'P227', 'P244', 'P213', 'P269', 'P10832', 'P2671',
    'P3368', 'P1006', 'P1015', 'P3083', 'P13228', 'P345', 'P4947',
    'P6127', 'P2704', 'P2603', 'P12096',
    # 이름 (카디널리티 너무 높음)
    'P735', 'P734', 'P1559',
    # 좌표/카탈로그 (연속값)
    'P625', 'P528', 'P6257', 'P6258',
}

def get_read_conn():
    return psycopg2.connect(
        host="localhost", port=5432, dbname="geuldev",
        user="geul_reader", password="test1224"
    )

def get_write_conn():
    return psycopg2.connect(
        host="localhost", port=5432, dbname="geulwork",
        user="geul_writer", password="test1224"
    )

def entropy(counter: Counter) -> float:
    """이산 엔트로피 H(X)"""
    total = sum(counter.values())
    if total == 0:
        return 0.0
    h = 0.0
    for count in counter.values():
        p = count / total
        if p > 0:
            h -= p * math.log2(p)
    return h

def conditional_entropy(joint_counter: Counter, x_counter: Counter) -> float:
    """조건부 엔트로피 H(Y|X) = H(X,Y) - H(X)"""
    h_joint = entropy(joint_counter)
    h_x = entropy(x_counter)
    return h_joint - h_x

def mutual_info(joint_counter: Counter, x_counter: Counter, y_counter: Counter) -> float:
    """상호정보량 I(X;Y) = H(X) + H(Y) - H(X,Y)"""
    h_x = entropy(x_counter)
    h_y = entropy(y_counter)
    h_joint = entropy(joint_counter)
    return h_x + h_y - h_joint

def get_top_properties(entity_type: int, top_n: int = 15):
    """커버리지 상위 속성 조회 (외부 ID 제외)"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT property_id, property_label, coverage, cardinality, entropy
            FROM property_stats
            WHERE entity_type = %s
            ORDER BY coverage DESC
        """, (entity_type,))
        rows = cur.fetchall()
    conn.close()

    # P31 및 제외 속성 필터링
    filtered = []
    for r in rows:
        if r[0] != 'P31' and r[0] not in EXCLUDE_PROPERTIES:
            filtered.append((r[0], r[1], r[2], r[3], r[4]))
            if len(filtered) >= top_n:
                break
    return filtered

def collect_property_pairs(qid: str, properties: list, sample_size: int = 30000):
    """엔티티별 속성값 수집"""
    conn = get_read_conn()

    with conn.cursor() as cur:
        cur.execute("""
            SELECT subject FROM triples
            WHERE property = 'P31' AND object_value = %s
            LIMIT %s
        """, (qid, sample_size))
        entity_ids = [row[0] for row in cur.fetchall()]

    print(f"Collected {len(entity_ids)} sample entities")

    prop_set = set(properties)
    entity_props = defaultdict(dict)

    batch_size = 500
    for i in range(0, len(entity_ids), batch_size):
        batch = entity_ids[i:i+batch_size]
        if i % 5000 == 0:
            print(f"  Progress: {i}/{len(entity_ids)}")

        with conn.cursor() as cur:
            cur.execute("""
                SELECT subject, property, object_value
                FROM triples
                WHERE subject = ANY(%s) AND property = ANY(%s)
            """, (batch, list(prop_set)))

            for subj, prop, val in cur.fetchall():
                if prop not in entity_props[subj]:
                    entity_props[subj][prop] = val

    conn.close()
    return dict(entity_props)

def derive_era_from_birth(entity_props: dict):
    """P569(생년)에서 Era(시대) 파생"""
    for entity_id, props in entity_props.items():
        birth = props.get('P569')
        if birth:
            try:
                # 위키데이터 시간 포맷: +YYYY-MM-DDT00:00:00Z
                if birth.startswith('+') or birth.startswith('-'):
                    year_str = birth[1:].split('-')[0]
                    year = int(year_str)
                else:
                    year = int(birth[:4])

                # 시대 분류
                if year < -3000:
                    era = 'Prehistoric'
                elif year < 500:
                    era = 'Ancient'
                elif year < 1500:
                    era = 'Medieval'
                elif year < 1800:
                    era = 'EarlyModern'
                elif year < 1900:
                    era = 'C19'
                elif year < 2000:
                    era = 'C20'
                else:
                    era = 'C21'

                props['ERA'] = era
            except:
                pass
    return entity_props

def analyze_dependencies(entity_props: dict, properties: list, threshold: float = 0.15):
    """속성 쌍별 종속성 분석"""
    dependencies = []

    for prop_a, prop_b in combinations(properties, 2):
        joint_ab = Counter()
        counter_a = Counter()
        counter_b = Counter()

        for entity_id, props in entity_props.items():
            val_a = props.get(prop_a)
            val_b = props.get(prop_b)

            if val_a is not None:
                counter_a[val_a] += 1
            if val_b is not None:
                counter_b[val_b] += 1
            if val_a is not None and val_b is not None:
                joint_ab[(val_a, val_b)] += 1

        if len(joint_ab) < 10:  # 최소 데이터 필요
            continue

        mi = mutual_info(joint_ab, counter_a, counter_b)
        h_a = entropy(counter_a)
        h_b = entropy(counter_b)

        if min(h_a, h_b) == 0:
            continue

        nmi = mi / min(h_a, h_b)

        if nmi > threshold:
            h_b_given_a = conditional_entropy(joint_ab, counter_a)
            h_a_given_b = conditional_entropy(joint_ab, counter_b)

            if h_b_given_a < h_a_given_b:
                parent, child = prop_a, prop_b
                direction_strength = h_a_given_b - h_b_given_a
            else:
                parent, child = prop_b, prop_a
                direction_strength = h_b_given_a - h_a_given_b

            dependencies.append({
                'parent': parent,
                'child': child,
                'mutual_info': mi,
                'nmi': nmi,
                'direction_strength': direction_strength,
                'h_parent': h_a if parent == prop_a else h_b,
                'h_child': h_b if parent == prop_a else h_a,
            })

    dependencies.sort(key=lambda x: -x['mutual_info'])
    return dependencies

def remove_cycles(dependencies: list):
    """약한 간선부터 제거하여 DAG 생성"""
    edges = sorted(dependencies, key=lambda x: x['mutual_info'])
    parent = {}

    def find(x):
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
            return True
        return False

    dag_edges = []
    for edge in reversed(edges):
        if union(edge['parent'], edge['child']):
            dag_edges.append(edge)

    return dag_edges

def save_dag(entity_type: int, dependencies: list):
    """DAG를 geulwork에 저장"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM dependency_dag WHERE entity_type = %s", (entity_type,))

        for dep in dependencies:
            cur.execute("""
                INSERT INTO dependency_dag (entity_type, parent_prop, child_prop, mutual_info)
                VALUES (%s, %s, %s, %s)
            """, (entity_type, dep['parent'], dep['child'], dep['mutual_info']))

    conn.commit()
    conn.close()

def get_property_label(prop_id: str) -> str:
    """속성 레이블 조회"""
    if prop_id == 'ERA':
        return 'Era (derived)'
    conn = get_read_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT label_en FROM properties_meta WHERE property_id = %s", (prop_id,))
        row = cur.fetchone()
    conn.close()
    return row[0] if row else prop_id

def main():
    type_map = {
        1: ('Human', 'Q5'),
        3: ('Star', 'Q523'),
        10: ('Settlement', 'Q486972'),
        11: ('Organization', 'Q43229'),
        15: ('Film', 'Q11424'),
    }

    if len(sys.argv) > 1:
        target_type = int(sys.argv[1])
        type_map = {k: v for k, v in type_map.items() if k == target_type}

    for type_code, (type_name, qid) in type_map.items():
        print(f"\n{'='*60}")
        print(f"Analyzing dependencies for {type_name} ({qid})")
        print('='*60)

        top_props = get_top_properties(type_code, top_n=10)
        prop_ids = [p[0] for p in top_props]

        # Human의 경우 ERA 추가
        if type_code == 1:
            prop_ids.append('ERA')

        print(f"\nAnalyzing {len(prop_ids)} properties (excluding external IDs):")
        for pid, label, cov, card, ent in top_props:
            print(f"  {pid}: {label[:40]:<40} cov={cov:.1%} card={card}")
        if 'ERA' in prop_ids:
            print(f"  ERA: (derived from P569)")

        print(f"\nCollecting property values...")
        entity_props = collect_property_pairs(qid, [p for p in prop_ids if p != 'ERA'], sample_size=30000)

        # ERA 파생
        if type_code == 1:
            entity_props = derive_era_from_birth(entity_props)

        print(f"\nAnalyzing dependencies...")
        dependencies = analyze_dependencies(entity_props, prop_ids, threshold=0.10)

        if not dependencies:
            print("No significant dependencies found")
            continue

        print(f"\nFound {len(dependencies)} significant relationships:")
        print(f"\n{'Parent':<12} {'Child':<12} {'MI':>6} {'NMI':>6} {'H(P)':>6} {'H(C)':>6}")
        print("-" * 55)
        for dep in dependencies[:20]:
            print(f"{dep['parent']:<12} {dep['child']:<12} {dep['mutual_info']:>5.2f} {dep['nmi']:>5.2f} {dep['h_parent']:>5.2f} {dep['h_child']:>5.2f}")

        dag_edges = remove_cycles(dependencies)

        print(f"\n*** DAG Edges ({len(dag_edges)}) ***")
        for dep in dag_edges:
            parent_label = get_property_label(dep['parent'])[:30]
            child_label = get_property_label(dep['child'])[:30]
            print(f"  {dep['parent']:>8} -> {dep['child']:<8}  ({parent_label} -> {child_label})")

        save_dag(type_code, dag_edges)
        print(f"\nSaved to geulwork.dependency_dag")

if __name__ == "__main__":
    main()
