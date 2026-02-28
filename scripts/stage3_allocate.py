#!/usr/bin/env python3
"""
Stage 3: 48비트 속성 비트 할당 최적화 (v2.0)

Stage 1(속성 통계) + Stage 2(DAG) + 양자화 규칙을 기반으로
48비트에 속성을 배치하고 충돌률을 측정한다.
"""

import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import psycopg2

# 경로 설정
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
REFERENCES_DIR = PROJECT_DIR / "references"
OUTPUT_DIR = PROJECT_DIR / "output1"

# 상수
TOTAL_BITS = 48
MIN_BITS = 2
MAX_BITS = 12

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

def load_type_schemas():
    """타입별 스키마 로드"""
    path = REFERENCES_DIR / "type_schemas.json"
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_quantization_rules():
    """양자화 규칙 로드"""
    path = REFERENCES_DIR / "quantization_rules.json"
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def init_work_tables():
    """테이블 생성"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bit_allocation (
                entity_type  INTEGER NOT NULL,
                field_name   TEXT NOT NULL,
                property_id  TEXT,
                bit_offset   INTEGER NOT NULL,
                bit_width    INTEGER NOT NULL,
                parent_field TEXT,
                cardinality  INTEGER,
                coverage     REAL,
                entropy      REAL,
                quant_loss   REAL,
                notes        TEXT,
                updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (entity_type, field_name)
            );

            CREATE TABLE IF NOT EXISTS collision_stats (
                entity_type    INTEGER PRIMARY KEY,
                total_entities INTEGER NOT NULL,
                encoded_count  INTEGER NOT NULL,
                unique_sidx    INTEGER NOT NULL,
                collision_count INTEGER NOT NULL,
                collision_rate REAL NOT NULL,
                updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS encoded_samples (
                entity_type INTEGER NOT NULL,
                entity_id   TEXT NOT NULL,
                sidx_48bit  BIGINT NOT NULL,
                sidx_hex    TEXT NOT NULL,
                field_values JSONB,
                PRIMARY KEY (entity_type, entity_id)
            );

            CREATE INDEX IF NOT EXISTS idx_encoded_samples_sidx
            ON encoded_samples(entity_type, sidx_48bit);
        """)
    conn.commit()
    conn.close()

def get_entity_type_info(type_code: int) -> dict:
    """타입 정보 조회"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT type_name, name_ko, qid, total_count, sample_count
            FROM entity_type_map WHERE type_code = %s
        """, (type_code,))
        row = cur.fetchone()
    conn.close()

    if row:
        return {
            'name_en': row[0], 'name_ko': row[1], 'qid': row[2],
            'total_count': row[3], 'sample_count': row[4]
        }
    return None

def get_property_stats(type_code: int) -> dict:
    """속성 통계 조회"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT property_id, property_label, coverage, cardinality, entropy
            FROM property_stats
            WHERE entity_type = %s AND property_id != 'P31'
            ORDER BY coverage DESC
        """, (type_code,))
        rows = cur.fetchall()
    conn.close()

    return {row[0]: {
        'label': row[1], 'coverage': row[2],
        'cardinality': row[3], 'entropy': row[4]
    } for row in rows}

def get_dependency_dag(type_code: int) -> list:
    """종속 관계 DAG 조회"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT parent_prop, child_prop, mutual_info
            FROM dependency_dag WHERE entity_type = %s
        """, (type_code,))
        rows = cur.fetchall()
    conn.close()

    return [{'parent': r[0], 'child': r[1], 'mi': r[2]} for r in rows]

def get_schema_for_type(type_code: int, schemas: dict) -> dict:
    """타입에 맞는 스키마 반환"""
    schema_key = f"0x{type_code:02X}_"
    for key, schema in schemas.get('schemas', {}).items():
        if key.startswith(schema_key) or key.startswith(f"0x{type_code:02x}_"):
            return schema

    # 기본 스키마
    return schemas.get('default_schema', {})

def calculate_bits_needed(cardinality: int, entropy: float = None, quant_rules: dict = None) -> int:
    """필요 비트수 계산 (OPT-1: 엔트로피 기반 조정)"""
    if cardinality <= 1:
        return 0

    # 기본: 카디널리티 기반
    bits = math.ceil(math.log2(cardinality))

    # 엔트로피가 높으면 비트 추가 (구별력 중요)
    if entropy is not None and entropy > 3.0:
        # 엔트로피 3 이상이면 1비트 추가
        bits += 1
    if entropy is not None and entropy > 5.0:
        # 엔트로피 5 이상이면 추가 1비트
        bits += 1

    return max(MIN_BITS, min(bits, MAX_BITS))

def allocate_from_schema(type_code: int, schema: dict, prop_stats: dict, dag: list) -> list:
    """스키마 기반 비트 할당"""
    allocation = []
    parent_map = {e['child']: e['parent'] for e in dag}

    for field in schema.get('fields', []):
        prop_id = None
        stats = None

        # 속성 매핑 찾기
        props_map = schema.get('properties', {})
        for pid, fname in props_map.items():
            if fname == field['name'] or fname.startswith(field['name']):
                prop_id = pid
                stats = prop_stats.get(pid)
                break

        allocation.append({
            'field_name': field['name'],
            'property_id': prop_id,
            'bits': field['bits'],
            'offset': field['offset'],
            'parent': field.get('parent') or (parent_map.get(prop_id) if prop_id else None),
            'cardinality': stats['cardinality'] if stats else 0,
            'coverage': stats['coverage'] if stats else 0,
            'entropy': stats['entropy'] if stats else 0,
            'quant_loss': 0,
            'notes': field.get('description', '')
        })

    return allocation

def allocate_greedy(type_code: int, prop_stats: dict, dag: list) -> list:
    """탐욕적 비트 할당 (스키마 없는 타입용)"""
    parent_map = {e['child']: e['parent'] for e in dag}
    parents = set(parent_map.values())
    children = set(parent_map.keys())

    # 독립 속성 먼저, 그 다음 종속 속성
    independent = []
    dependent = []

    for pid, stats in prop_stats.items():
        if pid in children:
            dependent.append((pid, stats))
        else:
            independent.append((pid, stats))

    # OPT-1: 개선된 우선순위 함수
    # coverage × entropy / sqrt(cardinality) 가중치 적용
    # - 커버리지 높음: 많은 개체에 적용 가능
    # - 엔트로피 높음: 구별력 좋음 (값이 다양하게 분포)
    # - 카디널리티 낮음: 적은 비트로 표현 가능
    def priority(item):
        pid, s = item
        coverage = s['coverage']
        entropy = max(s['entropy'], 0.1)  # 0 방지
        cardinality = max(s['cardinality'], 2)

        # 구별력 점수: 높은 엔트로피 + 높은 커버리지 + 낮은 카디널리티
        discrimination = coverage * entropy / math.sqrt(cardinality)
        return (-discrimination, -entropy, -coverage)

    independent.sort(key=priority)
    dependent.sort(key=priority)

    sorted_props = independent + dependent

    budget = TOTAL_BITS
    allocation = []
    offset = 0

    for pid, stats in sorted_props:
        if budget <= 0:
            break

        # 비트수 결정 (OPT-1: 엔트로피 반영)
        bits = calculate_bits_needed(stats['cardinality'], stats['entropy'])
        bits = min(bits, budget)

        if bits < MIN_BITS:
            continue

        quant_loss = max(0, math.log2(max(stats['cardinality'], 1)) - bits)

        allocation.append({
            'field_name': pid,
            'property_id': pid,
            'bits': bits,
            'offset': offset,
            'parent': parent_map.get(pid),
            'cardinality': stats['cardinality'],
            'coverage': stats['coverage'],
            'entropy': stats['entropy'],
            'quant_loss': quant_loss,
            'notes': stats.get('label', '')
        })

        offset += bits
        budget -= bits

    # 잔여 비트
    if budget > 0:
        allocation.append({
            'field_name': '_reserved',
            'property_id': None,
            'bits': budget,
            'offset': offset,
            'parent': None,
            'cardinality': 0,
            'coverage': 0,
            'entropy': 0,
            'quant_loss': 0,
            'notes': '예약'
        })

    return allocation

# 코드북 캐시 (타입별, 필드별)
_codebook_cache = {}

def get_codebook(type_code: int, field_name: str) -> dict:
    """코드북 조회 (캐시 사용)"""
    cache_key = (type_code, field_name)
    if cache_key in _codebook_cache:
        return _codebook_cache[cache_key]

    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT value, code FROM codebook
            WHERE entity_type = %s AND field_name = %s
        """, (type_code, field_name))
        rows = cur.fetchall()
    conn.close()

    codebook = {row[0]: row[1] for row in rows}
    _codebook_cache[cache_key] = codebook
    return codebook

def encode_entity(entity_values: dict, allocation: list, type_code: int = None) -> int:
    """개체를 48비트로 인코딩 (코드북 기반, 결정론적)"""
    sidx = 0

    for field in allocation:
        if field['field_name'] == '_reserved':
            continue

        prop_id = field['property_id']
        if not prop_id or prop_id not in entity_values:
            continue

        value = entity_values[prop_id]
        if value is None:
            continue

        # 코드북에서 코드 조회, 없으면 0 (Unknown)
        if type_code is not None:
            codebook = get_codebook(type_code, field['field_name'])
            code = codebook.get(value, 0)  # Unknown = 0
        else:
            # 코드북 없을 시 해시 기반 (임시, Stage 4 이전용)
            code = abs(hash(str(value))) % (2 ** field['bits'])

        sidx |= (code << field['offset'])

    return sidx & ((1 << TOTAL_BITS) - 1)

def calculate_collision_rate(type_code: int, qid: str, allocation: list, sample_size: int = 10000) -> dict:
    """충돌률 계산"""
    conn = get_read_conn()

    # 샘플 개체 로드
    with conn.cursor() as cur:
        cur.execute("""
            SELECT subject FROM triples
            WHERE property = 'P31' AND object_value = %s
            LIMIT %s
        """, (qid, sample_size))
        entity_ids = [row[0] for row in cur.fetchall()]

    if not entity_ids:
        conn.close()
        return {'total': 0, 'encoded': 0, 'unique': 0, 'collisions': 0, 'rate': 0}

    # 속성값 로드
    prop_ids = [f['property_id'] for f in allocation if f['property_id']]
    entity_values = {eid: {} for eid in entity_ids}

    # OPT-3: 다중값 속성 정렬 처리
    # 먼저 모든 값을 수집
    from collections import defaultdict as dd
    temp_values = {eid: dd(list) for eid in entity_ids}

    with conn.cursor() as cur:
        cur.execute("""
            SELECT subject, property, object_value
            FROM triples
            WHERE subject = ANY(%s) AND property = ANY(%s)
            ORDER BY subject, property, object_value
        """, (entity_ids, prop_ids))

        for subject, prop, obj_val in cur.fetchall():
            if subject in temp_values:
                temp_values[subject][prop].append(obj_val)

    conn.close()

    # 정렬된 첫 번째 값만 사용 (결정론성 보장)
    for eid in entity_ids:
        for prop, values in temp_values[eid].items():
            if values:
                entity_values[eid][prop] = sorted(values)[0]

    # 인코딩
    sidx_counts = defaultdict(int)
    encoded_count = 0

    for eid, values in entity_values.items():
        if values:
            sidx = encode_entity(values, allocation)
            sidx_counts[sidx] += 1
            encoded_count += 1

    unique_count = len(sidx_counts)
    collision_count = sum(1 for c in sidx_counts.values() if c > 1)
    collision_rate = collision_count / unique_count if unique_count > 0 else 0

    return {
        'total': len(entity_ids),
        'encoded': encoded_count,
        'unique': unique_count,
        'collisions': collision_count,
        'rate': collision_rate
    }

def save_allocation(type_code: int, allocation: list, collision_stats: dict):
    """결과 저장"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        # 할당 저장
        cur.execute("DELETE FROM bit_allocation WHERE entity_type = %s", (type_code,))
        for a in allocation:
            cur.execute("""
                INSERT INTO bit_allocation
                (entity_type, field_name, property_id, bit_offset, bit_width,
                 parent_field, cardinality, coverage, entropy, quant_loss, notes, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (
                type_code, a['field_name'], a['property_id'], a['offset'], a['bits'],
                a['parent'], a['cardinality'], a['coverage'], a['entropy'],
                a['quant_loss'], a['notes']
            ))

        # 충돌 통계 저장
        cur.execute("""
            INSERT INTO collision_stats
            (entity_type, total_entities, encoded_count, unique_sidx, collision_count, collision_rate, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (entity_type) DO UPDATE SET
                total_entities = EXCLUDED.total_entities,
                encoded_count = EXCLUDED.encoded_count,
                unique_sidx = EXCLUDED.unique_sidx,
                collision_count = EXCLUDED.collision_count,
                collision_rate = EXCLUDED.collision_rate,
                updated_at = CURRENT_TIMESTAMP
        """, (
            type_code, collision_stats['total'], collision_stats['encoded'],
            collision_stats['unique'], collision_stats['collisions'], collision_stats['rate']
        ))

    conn.commit()
    conn.close()

def generate_report(all_results: list, output_path: Path):
    """보고서 생성"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Stage 3: 48비트 할당 최적화 보고서\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 요약\n\n")
        f.write("| 타입 | 코드 | 필드 수 | 사용 비트 | 충돌률 |\n")
        f.write("|------|------|--------|----------|--------|\n")

        for r in all_results:
            if not r:
                continue
            total_bits = sum(a['bits'] for a in r['allocation'])
            f.write(f"| {r['name_ko']} | 0x{r['type_code']:02X} | {len(r['allocation'])} | ")
            f.write(f"{total_bits}/48 | {r['collision']['rate']:.2%} |\n")

        f.write("\n---\n\n")

        for r in all_results:
            if not r:
                continue

            f.write(f"## {r['name_ko']} (0x{r['type_code']:02X})\n\n")

            f.write("### 비트 레이아웃\n\n")
            f.write("```\n")
            for a in r['allocation']:
                end = a['offset'] + a['bits'] - 1
                f.write(f"[{a['offset']:2d}:{end:2d}] {a['field_name']:<15} ({a['bits']}bit)")
                if a['property_id']:
                    f.write(f" ← {a['property_id']}")
                f.write("\n")
            f.write("```\n\n")

            f.write("### 상세\n\n")
            f.write("| 필드 | 속성 | 비트 | 카디널리티 | 커버리지 | 손실 |\n")
            f.write("|------|------|------|-----------|----------|------|\n")
            for a in r['allocation']:
                f.write(f"| {a['field_name']} | {a['property_id'] or '-'} | {a['bits']} | ")
                f.write(f"{a['cardinality']:,} | {a['coverage']:.1%} | {a['quant_loss']:.2f} |\n")

            f.write(f"\n### 충돌 통계\n\n")
            c = r['collision']
            f.write(f"- 샘플: {c['total']:,}\n")
            f.write(f"- 인코딩: {c['encoded']:,}\n")
            f.write(f"- 고유 SIDX: {c['unique']:,}\n")
            f.write(f"- 충돌 SIDX: {c['collisions']:,}\n")
            f.write(f"- **충돌률: {c['rate']:.2%}**\n")

            f.write("\n---\n\n")

def main():
    print("=" * 60)
    print("Stage 3: 48비트 속성 비트 할당 최적화 (v2.0)")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)
    init_work_tables()

    # 설정 로드
    schemas = load_type_schemas()
    quant_rules = load_quantization_rules()

    # 타입 목록
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT type_code, name_ko, qid FROM entity_type_map
            WHERE sample_count > 0 ORDER BY type_code
        """)
        types = [(row[0], row[1], row[2]) for row in cur.fetchall()]
    conn.close()

    # 필터링
    if len(sys.argv) > 1:
        target_codes = [int(x, 16) if x.startswith('0x') else int(x) for x in sys.argv[1:]]
        types = [(c, n, q) for c, n, q in types if c in target_codes]

    print(f"\n대상: {len(types)}개 타입")

    all_results = []

    for i, (type_code, name_ko, qid) in enumerate(types):
        print(f"\n[{i+1}/{len(types)}] {name_ko} (0x{type_code:02X})")

        prop_stats = get_property_stats(type_code)
        dag = get_dependency_dag(type_code)
        schema = get_schema_for_type(type_code, schemas)

        # 할당
        if schema and schema.get('fields'):
            print(f"  스키마 기반 할당")
            allocation = allocate_from_schema(type_code, schema, prop_stats, dag)
        else:
            print(f"  탐욕적 할당 (스키마 없음)")
            allocation = allocate_greedy(type_code, prop_stats, dag)

        total_bits = sum(a['bits'] for a in allocation)
        print(f"  필드: {len(allocation)}개, 비트: {total_bits}/48")

        # 충돌률 계산
        print(f"  충돌률 계산 중...")
        collision = calculate_collision_rate(type_code, qid, allocation, sample_size=10000)
        print(f"  충돌률: {collision['rate']:.2%}")

        # 저장
        save_allocation(type_code, allocation, collision)

        all_results.append({
            'type_code': type_code,
            'name_ko': name_ko,
            'allocation': allocation,
            'collision': collision
        })

    # 보고서
    print("\n보고서 생성...")
    report_path = OUTPUT_DIR / "stage3_report.md"
    generate_report(all_results, report_path)
    print(f"저장: {report_path}")

    print("\n완료!")

if __name__ == "__main__":
    main()
