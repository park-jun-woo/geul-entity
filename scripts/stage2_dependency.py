#!/usr/bin/env python3
"""
Stage 2: 속성 간 계층 의존성 탐지 (v2.0)

Stage 1 결과를 기반으로 조건부 엔트로피를 계산하여
속성 간 종속 관계 DAG를 생성한다.
"""

import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path

import psycopg2

# 경로 설정
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_DIR / "output1"

# DB 설정
DB_CONFIG = {
    "read": {
        "host": "localhost", "port": 5432, "dbname": "geuldev",
        "user": "geul_reader", "password": "test1224"
    },
    "write": {
        "host": "localhost", "port": 5432, "dbname": "geulwork",
        "user": "geul_writer", "password": "test1224"
    }
}

def get_read_conn():
    return psycopg2.connect(**DB_CONFIG["read"])

def get_write_conn():
    return psycopg2.connect(**DB_CONFIG["write"])

def entropy(values: list) -> float:
    """이산 엔트로피 계산"""
    if not values:
        return 0.0
    counter = Counter(values)
    total = len(values)
    h = 0.0
    for count in counter.values():
        p = count / total
        if p > 0:
            h -= p * math.log2(p)
    return h

def conditional_entropy(values_a: list, values_b: list) -> float:
    """H(B|A): A를 알 때 B의 불확실성"""
    if len(values_a) != len(values_b) or not values_a:
        return 0.0

    n = len(values_a)
    groups = defaultdict(list)
    for a, b in zip(values_a, values_b):
        if a is not None and b is not None:
            groups[a].append(b)

    h = 0.0
    valid_count = sum(len(bs) for bs in groups.values())
    if valid_count == 0:
        return 0.0

    for a_val, b_vals in groups.items():
        p_a = len(b_vals) / valid_count
        counter = Counter(b_vals)
        h_b_given_a = 0.0
        for count in counter.values():
            p = count / len(b_vals)
            if p > 0:
                h_b_given_a -= p * math.log2(p)
        h += p_a * h_b_given_a

    return h

def mutual_information(values_a: list, values_b: list) -> float:
    """I(A;B) = H(B) - H(B|A)"""
    h_b = entropy([b for b in values_b if b is not None])
    h_b_given_a = conditional_entropy(values_a, values_b)
    return max(0, h_b - h_b_given_a)

def init_work_tables():
    """테이블 생성"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dependency_dag (
                entity_type INTEGER NOT NULL,
                parent_prop TEXT NOT NULL,
                child_prop TEXT NOT NULL,
                mutual_info REAL NOT NULL,
                h_child_given_parent REAL,
                h_parent_given_child REAL,
                normalized_mi REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (entity_type, parent_prop, child_prop)
            );
        """)
    conn.commit()
    conn.close()

def get_top_properties(entity_type_code: int, top_k: int = 15) -> list:
    """Stage 1 결과에서 상위 속성 가져오기 (외부 ID 제외)"""
    conn = get_write_conn()
    read_conn = get_read_conn()

    # 외부 ID 및 미디어 속성 제외 목록 조회
    with read_conn.cursor() as cur:
        cur.execute("""
            SELECT property_id FROM properties_meta
            WHERE datatype IN ('external-id', 'commonsMedia', 'url')
        """)
        excluded_props = set(row[0] for row in cur.fetchall())
    read_conn.close()

    with conn.cursor() as cur:
        cur.execute("""
            SELECT property_id, property_label, coverage, cardinality, entropy
            FROM property_stats
            WHERE entity_type = %s AND property_id != 'P31'
            ORDER BY coverage DESC, entropy DESC
        """, (entity_type_code,))
        rows = cur.fetchall()
    conn.close()

    # 외부 ID 제외 후 상위 K개 선택
    result = []
    for row in rows:
        if row[0] not in excluded_props:
            result.append({
                'id': row[0],
                'label': row[1],
                'coverage': row[2],
                'cardinality': row[3],
                'entropy': row[4]
            })
            if len(result) >= top_k:
                break

    return result

def get_entity_type_info(entity_type_code: int) -> dict:
    """타입 정보 조회"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT type_name, name_ko, qid, sample_count
            FROM entity_type_map
            WHERE type_code = %s
        """, (entity_type_code,))
        row = cur.fetchone()
    conn.close()

    if row:
        return {
            'name_en': row[0],
            'name_ko': row[1],
            'qid': row[2],
            'sample_count': row[3]
        }
    return None

def load_property_values(qid: str, properties: list, sample_size: int = 2000) -> dict:
    """개체들의 속성값 로드"""
    conn = get_read_conn()

    # Step 1: 샘플 개체 ID
    with conn.cursor() as cur:
        cur.execute("""
            SELECT subject FROM triples
            WHERE property = 'P31' AND object_value = %s
            LIMIT %s
        """, (qid, sample_size))
        entity_ids = [row[0] for row in cur.fetchall()]

    if not entity_ids:
        conn.close()
        return {}

    # Step 2: 각 속성의 값 로드
    prop_ids = [p['id'] for p in properties]
    entity_values = {eid: {} for eid in entity_ids}

    with conn.cursor() as cur:
        cur.execute("""
            SELECT subject, property, object_value
            FROM triples
            WHERE subject = ANY(%s) AND property = ANY(%s)
        """, (entity_ids, prop_ids))

        for subject, prop, obj_val in cur.fetchall():
            if subject in entity_values:
                # 첫 번째 값만 사용 (다중값 있을 수 있음)
                if prop not in entity_values[subject]:
                    entity_values[subject][prop] = obj_val

    conn.close()
    return entity_values

def remove_cycles(edges: list) -> list:
    """약한 간선부터 제거하여 DAG 보장"""
    edges_sorted = sorted(edges, key=lambda e: e['mi'], reverse=True)

    dag = []

    def has_path(graph, start, end, seen=None):
        if seen is None:
            seen = set()
        if start == end:
            return True
        seen.add(start)
        for e in graph:
            if e['parent'] == start and e['child'] not in seen:
                if has_path(graph, e['child'], end, seen):
                    return True
        return False

    for edge in edges_sorted:
        if not has_path(dag, edge['child'], edge['parent']):
            dag.append(edge)

    return dag

def analyze_dependencies(entity_type_code: int, top_k: int = 10, mi_threshold: float = 0.3):
    """속성 간 종속 관계 분석"""
    type_info = get_entity_type_info(entity_type_code)
    if not type_info:
        print(f"  타입 정보 없음: {entity_type_code}")
        return None

    properties = get_top_properties(entity_type_code, top_k)
    if len(properties) < 2:
        print(f"  속성 부족: {len(properties)}개")
        return None

    print(f"  분석 대상 속성: {[p['id'] for p in properties]}")

    # 속성값 로드
    print(f"  속성값 로드 중...")
    entity_values = load_property_values(
        type_info['qid'],
        properties,
        sample_size=min(2000, type_info['sample_count'] or 2000)
    )

    if not entity_values:
        print(f"  개체 없음")
        return None

    entity_ids = list(entity_values.keys())
    prop_entropy = {p['id']: p['entropy'] for p in properties}

    # 모든 속성 쌍에 대해 MI 계산
    print(f"  {len(properties)}C2 = {len(properties)*(len(properties)-1)//2} 쌍 분석 중...")
    edges = []

    for prop_a, prop_b in combinations(properties, 2):
        pid_a, pid_b = prop_a['id'], prop_b['id']

        values_a = [entity_values[eid].get(pid_a) for eid in entity_ids]
        values_b = [entity_values[eid].get(pid_b) for eid in entity_ids]

        # 둘 다 있는 경우만
        valid_pairs = [(a, b) for a, b in zip(values_a, values_b)
                       if a is not None and b is not None]

        if len(valid_pairs) < 100:
            continue

        vals_a = [p[0] for p in valid_pairs]
        vals_b = [p[1] for p in valid_pairs]

        mi = mutual_information(vals_a, vals_b)
        h_b_given_a = conditional_entropy(vals_a, vals_b)
        h_a_given_b = conditional_entropy(vals_b, vals_a)

        min_h = min(prop_entropy.get(pid_a, 1), prop_entropy.get(pid_b, 1))
        if min_h > 0:
            normalized_mi = mi / min_h
        else:
            normalized_mi = 0

        if normalized_mi > mi_threshold:
            if h_b_given_a < h_a_given_b:
                edges.append({
                    'parent': pid_a, 'child': pid_b, 'mi': mi,
                    'h_child_given_parent': h_b_given_a,
                    'h_parent_given_child': h_a_given_b,
                    'normalized_mi': normalized_mi
                })
            else:
                edges.append({
                    'parent': pid_b, 'child': pid_a, 'mi': mi,
                    'h_child_given_parent': h_a_given_b,
                    'h_parent_given_child': h_b_given_a,
                    'normalized_mi': normalized_mi
                })

    dag = remove_cycles(edges)

    # 결과 저장
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM dependency_dag WHERE entity_type = %s",
            (entity_type_code,)
        )
        for e in dag:
            cur.execute("""
                INSERT INTO dependency_dag
                (entity_type, parent_prop, child_prop, mutual_info,
                 h_child_given_parent, h_parent_given_child, normalized_mi, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (
                entity_type_code, e['parent'], e['child'], e['mi'],
                e['h_child_given_parent'], e['h_parent_given_child'],
                e['normalized_mi']
            ))
    conn.commit()
    conn.close()

    return {
        'type_code': entity_type_code,
        'type_info': type_info,
        'properties': properties,
        'edges': dag
    }

def generate_report(all_results: list, output_path: Path):
    """보고서 생성"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Stage 2: 계층 의존성 탐지 보고서\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 요약\n\n")
        total_edges = sum(len(r['edges']) for r in all_results if r)
        f.write(f"분석 타입: {len([r for r in all_results if r])}개\n")
        f.write(f"총 종속 관계: {total_edges}개\n\n")

        f.write("---\n\n")

        for r in all_results:
            if not r:
                continue

            info = r['type_info']
            f.write(f"## {info['name_ko']} (0x{r['type_code']:02X})\n\n")

            if r['edges']:
                f.write("### 종속 관계 DAG\n\n")
                f.write("```mermaid\ngraph TD\n")
                for e in r['edges']:
                    f.write(f"    {e['parent']} --> {e['child']}\n")
                f.write("```\n\n")

                f.write("| Parent | Child | MI | NMI | H(C|P) |\n")
                f.write("|--------|-------|----|----|--------|\n")
                for e in r['edges']:
                    f.write(f"| {e['parent']} | {e['child']} | ")
                    f.write(f"{e['mi']:.3f} | {e['normalized_mi']:.3f} | ")
                    f.write(f"{e['h_child_given_parent']:.3f} |\n")
            else:
                f.write("종속 관계 없음 (모든 속성 독립)\n")

            f.write("\n---\n\n")

        f.write("## 해석\n\n")
        f.write("- **MI (Mutual Information)**: 상호정보량, 두 속성이 공유하는 정보량\n")
        f.write("- **NMI (Normalized MI)**: MI / min(H(A), H(B)), 종속 강도\n")
        f.write("- **H(C|P)**: 부모를 알 때 자식의 불확실성\n")
        f.write("- **Parent → Child**: 부모 속성이 자식 속성을 결정함\n")

def main():
    print("=" * 60)
    print("Stage 2: 속성 간 계층 의존성 탐지 (v2.0)")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)
    init_work_tables()

    # 분석할 타입 목록
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT type_code, name_ko FROM entity_type_map
            WHERE sample_count > 0
            ORDER BY type_code
        """)
        types = [(row[0], row[1]) for row in cur.fetchall()]
    conn.close()

    # 명령줄 인자로 필터링
    if len(sys.argv) > 1:
        target_codes = [int(x, 16) if x.startswith('0x') else int(x) for x in sys.argv[1:]]
        types = [(c, n) for c, n in types if c in target_codes]

    print(f"\n분석 대상: {len(types)}개 타입")

    all_results = []
    for i, (type_code, name_ko) in enumerate(types):
        print(f"\n[{i+1}/{len(types)}] {name_ko} (0x{type_code:02X})")
        result = analyze_dependencies(type_code, top_k=15, mi_threshold=0.3)
        all_results.append(result)

        if result:
            print(f"  종속 관계: {len(result['edges'])}개")

    # 보고서 생성
    print("\n보고서 생성...")
    report_path = OUTPUT_DIR / "stage2_report.md"
    generate_report(all_results, report_path)
    print(f"저장: {report_path}")

    print("\n완료!")

if __name__ == "__main__":
    main()
