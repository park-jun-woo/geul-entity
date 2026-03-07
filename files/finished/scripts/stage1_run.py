#!/usr/bin/env python3
"""
Stage 1: EntityType별 속성 통계 추출 (v2.0)

64개 전체 타입 대상, entity_types_64.json 기반
"""

import json
import math
import sys
import os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import psycopg2

# 경로 설정
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
REFERENCES_DIR = PROJECT_DIR / "references"
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

def load_entity_types():
    """entity_types_64.json에서 타입 목록 로드"""
    json_path = REFERENCES_DIR / "entity_types_64.json"
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    types = []
    for t in data['types']:
        if t['qid']:  # qid가 있는 것만
            code = int(t['code'], 16)
            types.append({
                'code': code,
                'name_en': t['name_en'],
                'name_ko': t['name_ko'],
                'qid': t['qid'],
                'category': t['category'],
                'expected_count': t.get('count', 0)
            })
    return types

def init_work_tables():
    """geulwork에 테이블 생성"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS entity_type_map (
                type_code   INTEGER PRIMARY KEY,
                type_name   TEXT NOT NULL,
                name_ko     TEXT,
                qid         TEXT NOT NULL,
                category    TEXT,
                total_count INTEGER DEFAULT 0,
                sample_count INTEGER DEFAULT 0,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS property_stats (
                entity_type INTEGER NOT NULL,
                property_id TEXT NOT NULL,
                property_label TEXT,
                coverage    REAL NOT NULL,
                cardinality INTEGER NOT NULL,
                entropy     REAL NOT NULL,
                sample_size INTEGER NOT NULL,
                top_values  JSONB,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (entity_type, property_id)
            );

            CREATE INDEX IF NOT EXISTS idx_property_stats_coverage
            ON property_stats(entity_type, coverage DESC);
        """)
    conn.commit()
    conn.close()

def calc_entropy(counter: Counter, total: int) -> float:
    """이산 엔트로피 계산 (bits)"""
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counter.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy

def get_entity_count(qid: str) -> int:
    """해당 타입의 전체 개체수 조회"""
    conn = get_read_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM triples
            WHERE property = 'P31' AND object_value = %s
        """, (qid,))
        count = cur.fetchone()[0]
    conn.close()
    return count

def extract_property_stats(qid: str, sample_size: int = 50000, batch_size: int = 500):
    """특정 타입의 속성 통계 추출"""
    conn = get_read_conn()

    # Step 1: 샘플 개체 ID 추출
    with conn.cursor() as cur:
        cur.execute("""
            SELECT subject FROM triples
            WHERE property = 'P31' AND object_value = %s
            LIMIT %s
        """, (qid, sample_size))
        entity_ids = [row[0] for row in cur.fetchall()]

    total_entities = len(entity_ids)
    if total_entities == 0:
        conn.close()
        return [], 0

    # Step 2: 배치로 속성 수집
    property_entities = defaultdict(set)
    property_values = defaultdict(Counter)

    for i in range(0, total_entities, batch_size):
        batch = entity_ids[i:i+batch_size]

        with conn.cursor() as cur:
            cur.execute("""
                SELECT subject, property, object_value
                FROM triples
                WHERE subject = ANY(%s)
            """, (batch,))

            for subject, prop, obj_val in cur.fetchall():
                property_entities[prop].add(subject)
                if obj_val:
                    property_values[prop][obj_val] += 1

    conn.close()

    # Step 3: 통계 계산
    results = []
    for prop in property_entities:
        entity_count = len(property_entities[prop])
        coverage = entity_count / total_entities
        counter = property_values[prop]
        cardinality = len(counter)
        total_vals = sum(counter.values())
        entropy = calc_entropy(counter, total_vals)

        # 상위 10개 값
        top_values = counter.most_common(10)

        results.append({
            'property_id': prop,
            'coverage': coverage,
            'cardinality': cardinality,
            'entropy': entropy,
            'sample_size': total_entities,
            'top_values': top_values
        })

    # 커버리지 10% 이상만 필터, 정렬
    filtered = [r for r in results if r['coverage'] >= 0.10]
    filtered.sort(key=lambda x: (-x['coverage'], -x['entropy']))

    return filtered, total_entities

def get_property_labels(property_ids: list) -> dict:
    """속성 레이블 조회"""
    if not property_ids:
        return {}
    conn = get_read_conn()
    labels = {}
    with conn.cursor() as cur:
        cur.execute("""
            SELECT property_id, label_en FROM properties_meta
            WHERE property_id = ANY(%s)
        """, (property_ids,))
        for pid, label in cur.fetchall():
            labels[pid] = label
    conn.close()
    return labels

def save_entity_type(type_info: dict, sample_count: int, total_count: int):
    """entity_type_map 저장"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO entity_type_map
            (type_code, type_name, name_ko, qid, category, total_count, sample_count, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (type_code) DO UPDATE SET
                type_name = EXCLUDED.type_name,
                name_ko = EXCLUDED.name_ko,
                qid = EXCLUDED.qid,
                category = EXCLUDED.category,
                total_count = EXCLUDED.total_count,
                sample_count = EXCLUDED.sample_count,
                updated_at = CURRENT_TIMESTAMP
        """, (
            type_info['code'], type_info['name_en'], type_info['name_ko'],
            type_info['qid'], type_info['category'], total_count, sample_count
        ))
    conn.commit()
    conn.close()

def save_property_stats(entity_type_code: int, results: list):
    """property_stats 저장"""
    conn = get_write_conn()
    prop_ids = [r['property_id'] for r in results]
    labels = get_property_labels(prop_ids)

    with conn.cursor() as cur:
        cur.execute("DELETE FROM property_stats WHERE entity_type = %s", (entity_type_code,))

        for r in results:
            cur.execute("""
                INSERT INTO property_stats
                (entity_type, property_id, property_label, coverage, cardinality,
                 entropy, sample_size, top_values, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (
                entity_type_code,
                r['property_id'],
                labels.get(r['property_id'], ''),
                r['coverage'],
                r['cardinality'],
                r['entropy'],
                r['sample_size'],
                json.dumps(r['top_values'])
            ))

    conn.commit()
    conn.close()

def generate_report(all_results: list, output_path: Path):
    """마크다운 보고서 생성"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Stage 1: 타입별 속성 추출 보고서\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # 요약
        f.write("## 요약\n\n")
        f.write(f"64개 EntityType 중 {len(all_results)}개 처리 완료\n\n")

        f.write("| 코드 | 타입 | QID | 전체 개체수 | 샘플 수 | 추출 속성 수 |\n")
        f.write("|------|------|-----|------------|---------|-------------|\n")

        for r in all_results:
            f.write(f"| 0x{r['code']:02X} | {r['name_ko']} | {r['qid']} | ")
            f.write(f"{r['total_count']:,} | {r['sample_count']:,} | {r['property_count']} |\n")

        f.write("\n---\n\n")

        # 타입별 상세
        for r in all_results:
            if r['properties']:
                f.write(f"## {r['name_ko']} (0x{r['code']:02X}) - {r['name_en']}\n\n")
                f.write(f"QID: {r['qid']}, 전체: {r['total_count']:,}, 샘플: {r['sample_count']:,}\n\n")

                f.write("| Property | Label | Coverage | Cardinality | Entropy | 비고 |\n")
                f.write("|----------|-------|----------|-------------|---------|------|\n")

                for p in r['properties'][:20]:
                    label = p.get('label', '')[:30]
                    note = ""
                    if p['cardinality'] > 10000:
                        note = "고카디널리티"
                    elif p['coverage'] >= 0.9 and p['cardinality'] < 20:
                        note = "**핵심**"
                    f.write(f"| {p['property_id']} | {label} | {p['coverage']:.1%} | ")
                    f.write(f"{p['cardinality']:,} | {p['entropy']:.2f} | {note} |\n")

                f.write("\n---\n\n")

        f.write("## 데이터 저장 위치\n\n")
        f.write("- `geulwork.entity_type_map`: EntityType 매핑\n")
        f.write("- `geulwork.property_stats`: 타입별 속성 통계\n")

def main():
    print("=" * 60)
    print("Stage 1: EntityType별 속성 통계 추출 (v2.0)")
    print("=" * 60)

    # 출력 디렉토리 확인
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 테이블 초기화
    print("\n[1] 테이블 초기화...")
    init_work_tables()

    # 타입 목록 로드
    print("[2] entity_types_64.json 로드...")
    entity_types = load_entity_types()
    print(f"    {len(entity_types)}개 타입 로드됨")

    # 명령줄 인자로 특정 타입만 처리
    if len(sys.argv) > 1:
        target_codes = [int(x, 16) if x.startswith('0x') else int(x) for x in sys.argv[1:]]
        entity_types = [t for t in entity_types if t['code'] in target_codes]
        print(f"    필터링 후 {len(entity_types)}개 타입")

    all_results = []

    # 각 타입 처리
    for i, type_info in enumerate(entity_types):
        print(f"\n[{i+1}/{len(entity_types)}] {type_info['name_ko']} ({type_info['qid']})")
        print(f"    코드: 0x{type_info['code']:02X}, 예상: {type_info['expected_count']:,}")

        # 전체 개체수 조회 (빠른 확인용)
        total_count = type_info['expected_count']
        if total_count == 0:
            total_count = get_entity_count(type_info['qid'])

        if total_count == 0:
            print(f"    건너뜀: 개체 없음")
            continue

        # 속성 통계 추출
        sample_size = min(50000, total_count)
        results, sample_count = extract_property_stats(
            type_info['qid'],
            sample_size=sample_size
        )

        print(f"    샘플: {sample_count:,}, 속성: {len(results)}개")

        # 저장
        save_entity_type(type_info, sample_count, total_count)
        if results:
            save_property_stats(type_info['code'], results)

            # 레이블 추가
            labels = get_property_labels([r['property_id'] for r in results])
            for r in results:
                r['label'] = labels.get(r['property_id'], '')

        all_results.append({
            'code': type_info['code'],
            'name_en': type_info['name_en'],
            'name_ko': type_info['name_ko'],
            'qid': type_info['qid'],
            'total_count': total_count,
            'sample_count': sample_count,
            'property_count': len(results),
            'properties': results
        })

    # 보고서 생성
    print("\n[최종] 보고서 생성...")
    report_path = OUTPUT_DIR / "stage1_report.md"
    generate_report(all_results, report_path)
    print(f"    저장: {report_path}")

    print("\n완료!")
    return all_results

if __name__ == "__main__":
    main()
