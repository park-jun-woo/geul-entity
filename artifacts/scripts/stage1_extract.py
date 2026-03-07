#!/usr/bin/env python3
"""
Stage 1: EntityType별 속성 추출 및 통계 계산

사용법:
    python stage1_extract.py --entity-type Human --qid Q5 --sample 100000

주의: 
    - wikidata DB는 READ ONLY 접속
    - 결과는 geul_work DB에 저장
    - 실행 전 wikidata DB 스키마를 먼저 파악할 것
"""

import argparse
import math
import os
from collections import Counter

import psycopg2
from psycopg2.extras import execute_values

# ─── DB 접속 ───

def get_wikidata_conn():
    """읽기 전용 wikidata 접속"""
    return psycopg2.connect(
        host="localhost", port=5432, dbname="wikidata",
        user="geul_reader", password=os.environ["GEUL_READ_PW"]
    )

def get_work_conn():
    """읽기/쓰기 geul_work 접속"""
    return psycopg2.connect(
        host="localhost", port=5432, dbname="geul_work",
        user="geul_writer", password=os.environ["GEUL_WRITE_PW"]
    )

# ─── 스키마 초기화 ───

def init_work_tables(work_conn):
    """geul_work에 결과 테이블 생성"""
    with work_conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS entity_type_map (
                type_code   INTEGER PRIMARY KEY,
                type_name   TEXT NOT NULL,
                qid         TEXT NOT NULL,
                total_count INTEGER DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS property_stats (
                entity_type INTEGER NOT NULL,
                property_id TEXT NOT NULL,
                property_label TEXT,
                coverage    REAL NOT NULL,
                cardinality INTEGER NOT NULL,
                entropy     REAL NOT NULL,
                sample_size INTEGER NOT NULL,
                PRIMARY KEY (entity_type, property_id)
            );
        """)
    work_conn.commit()

# ─── 엔트로피 계산 ───

def calc_entropy(values: list) -> float:
    """이산 엔트로피 계산 (bits)"""
    counter = Counter(values)
    total = len(values)
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counter.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy

# ─── 메인 로직 ───
#
# 아래는 템플릿이다. wikidata DB의 실제 스키마에 맞게 수정해야 한다.
# 
# 먼저 wikidata DB에 접속하여 테이블/컬럼 구조를 파악할 것:
#   \dt                    -- 테이블 목록
#   \d claims              -- claims 테이블 구조 (예시)
#   \d items               -- items 테이블 구조 (예시)
#
# 일반적인 위키데이터 덤프 스키마 예상:
#   items(id, qid, label, description, ...)
#   claims(item_id, property_id, value, ...)
#   또는
#   statements(subject_id, property_id, object_id, value, ...)
#
# 실제 스키마에 맞게 아래 쿼리를 수정한다.

def extract_properties(wiki_conn, qid: str, sample_size: int):
    """
    특정 타입(qid)의 개체들이 가진 모든 Property와 통계를 추출한다.
    
    TODO: wikidata DB 스키마에 맞게 쿼리 수정
    """
    with wiki_conn.cursor() as cur:
        # Step 1: 해당 타입의 개체 목록 (P31 = instance of)
        # TODO: 실제 테이블/컬럼명으로 수정
        cur.execute("""
            SELECT subject_id 
            FROM statements 
            WHERE property_id = 'P31' AND object_id = %s
            LIMIT %s
        """, (qid, sample_size))
        entity_ids = [row[0] for row in cur.fetchall()]
        
        if not entity_ids:
            print(f"No entities found for {qid}")
            return []
        
        total = len(entity_ids)
        print(f"Found {total} entities for {qid}")
        
        # Step 2: 이 개체들의 모든 Property 수집
        # TODO: 실제 테이블/컬럼명으로 수정
        cur.execute("""
            SELECT property_id, array_agg(value)
            FROM statements
            WHERE subject_id = ANY(%s)
            GROUP BY property_id
        """, (entity_ids,))
        
        results = []
        for prop_id, values in cur.fetchall():
            non_null = [v for v in values if v is not None]
            coverage = len(non_null) / total
            cardinality = len(set(non_null))
            entropy = calc_entropy(non_null)
            
            results.append({
                'property_id': prop_id,
                'coverage': coverage,
                'cardinality': cardinality,
                'entropy': entropy,
                'sample_size': total
            })
        
        return results

def save_results(work_conn, entity_type_code: int, results: list):
    """분석 결과를 geul_work에 저장"""
    with work_conn.cursor() as cur:
        # 기존 데이터 삭제 후 재삽입
        cur.execute(
            "DELETE FROM property_stats WHERE entity_type = %s",
            (entity_type_code,)
        )
        execute_values(cur, """
            INSERT INTO property_stats 
            (entity_type, property_id, coverage, cardinality, entropy, sample_size)
            VALUES %s
        """, [
            (entity_type_code, r['property_id'], r['coverage'],
             r['cardinality'], r['entropy'], r['sample_size'])
            for r in results
        ])
    work_conn.commit()

# ─── CLI ───

def main():
    parser = argparse.ArgumentParser(description="Stage 1: 속성 추출")
    parser.add_argument("--entity-type", required=True, help="타입 이름 (예: Human)")
    parser.add_argument("--type-code", type=int, required=True, help="EntityType 코드 (예: 0)")
    parser.add_argument("--qid", required=True, help="위키데이터 QID (예: Q5)")
    parser.add_argument("--sample", type=int, default=100000, help="샘플 크기")
    args = parser.parse_args()
    
    wiki_conn = get_wikidata_conn()
    work_conn = get_work_conn()
    
    init_work_tables(work_conn)
    
    print(f"Extracting properties for {args.entity_type} ({args.qid})...")
    results = extract_properties(wiki_conn, args.qid, args.sample)
    
    # 커버리지 10% 이상만 필터
    filtered = [r for r in results if r['coverage'] >= 0.10]
    filtered.sort(key=lambda x: (-x['coverage'], -x['entropy']))
    
    print(f"\n{'Property':<15} {'Coverage':>10} {'Cardinality':>12} {'Entropy':>10}")
    print("-" * 50)
    for r in filtered[:20]:
        print(f"{r['property_id']:<15} {r['coverage']:>9.1%} {r['cardinality']:>12} {r['entropy']:>9.2f}")
    
    save_results(work_conn, args.type_code, filtered)
    print(f"\nSaved {len(filtered)} properties to geul_work.property_stats")
    
    wiki_conn.close()
    work_conn.close()

if __name__ == "__main__":
    main()
