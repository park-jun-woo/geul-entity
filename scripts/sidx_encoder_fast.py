#!/usr/bin/env python3
"""
GEUL Entity SIDX Fast Encoder
최적화된 인코더 - 병렬 처리 및 벌크 인서트

Usage:
    python scripts/sidx_encoder_fast.py [--workers=4] [--batch-size=100000]
"""

import json
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import sys
import os
from multiprocessing import Pool, cpu_count
import time

# 상수
SIDX_PREFIX = 0b0001001  # 7비트 Proposal Entity prefix
DEFAULT_MODE = 0  # 등록 모드

# 전역 캐시 (프로세스별로 로드)
TYPE_MAP = None
CODEBOOKS = None
EXCLUDE_QIDS = None


def load_references():
    """참조 파일 로드"""
    global TYPE_MAP, CODEBOOKS, EXCLUDE_QIDS

    if TYPE_MAP is not None:
        return

    TYPE_MAP = {}
    CODEBOOKS = {}

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref_dir = os.path.join(base_dir, 'references')

    # Primary mapping 로드
    with open(os.path.join(ref_dir, 'primary_mapping.json'), 'r') as f:
        mapping = json.load(f)

    for qid, info in mapping['primary_mappings'].items():
        code = int(info['code'], 16)
        TYPE_MAP[qid] = code

    for qid, info in mapping['subtype_mappings'].items():
        code = int(info['target'], 16)
        TYPE_MAP[qid] = code

    EXCLUDE_QIDS = set(mapping.get('exclude_qids', {}).keys())

    # Codebooks 로드
    codebook_file = os.path.join(ref_dir, 'codebooks_full.json')
    if not os.path.exists(codebook_file):
        codebook_file = os.path.join(ref_dir, 'codebooks.json')

    with open(codebook_file, 'r') as f:
        cb_data = json.load(f)

    for name, cb in cb_data['codebooks'].items():
        CODEBOOKS[name] = {}
        for val in cb['values']:
            if val.get('qid'):
                CODEBOOKS[name][val['qid']] = val['code']


def get_entity_type(p31_value):
    """P31 값에서 EntityType 결정"""
    if not p31_value:
        return 0x3F  # Other

    if p31_value in EXCLUDE_QIDS:
        return None  # 제외

    if p31_value in TYPE_MAP:
        return TYPE_MAP[p31_value]

    return 0x3F  # Other 폴백


def build_sidx(entity_type, attrs=0):
    """64비트 SIDX 조립"""
    word1 = (SIDX_PREFIX << 9) | (DEFAULT_MODE << 6) | entity_type
    word2 = (attrs >> 32) & 0xFFFF
    word3 = (attrs >> 16) & 0xFFFF
    word4 = attrs & 0xFFFF
    sidx = (word1 << 48) | (word2 << 32) | (word3 << 16) | word4
    return sidx


def process_chunk(args):
    """청크 처리 (워커 프로세스)"""
    offset, limit = args
    load_references()

    read_conn = psycopg2.connect('postgresql://geul_reader:test1224@localhost:5432/geuldev')
    read_cur = read_conn.cursor()

    # 엔티티와 P31 값을 한번에 가져오기
    read_cur.execute(f"""
        SELECT e.id, t.object_value
        FROM (
            SELECT id FROM entities ORDER BY id OFFSET {offset} LIMIT {limit}
        ) e
        LEFT JOIN triples t ON t.subject = e.id AND t.property = 'P31'
    """)

    # 엔티티별 P31 값 수집
    entity_p31 = {}
    for qid, p31 in read_cur.fetchall():
        if qid not in entity_p31:
            entity_p31[qid] = []
        if p31:
            entity_p31[qid].append(p31)

    read_conn.close()

    # SIDX 생성
    results = []
    skipped = 0
    for qid, p31_list in entity_p31.items():
        # 첫 번째 P31 값으로 타입 결정
        p31 = p31_list[0] if p31_list else None
        entity_type = get_entity_type(p31)

        if entity_type is None:
            skipped += 1
            continue

        attrs = 0  # 간소화: 추후 Attributes 인코딩 추가
        sidx = build_sidx(entity_type, attrs)
        results.append((qid, sidx, entity_type, DEFAULT_MODE, attrs))

    return results, skipped


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--batch-size', type=int, default=100000)
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    print(f"SIDX Fast Encoder 시작")
    print(f"  Workers: {args.workers}")
    print(f"  Batch size: {args.batch_size:,}")

    start_time = datetime.now()

    # 전체 개체 수
    conn = psycopg2.connect('postgresql://geul_reader:test1224@localhost:5432/geuldev')
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM entities")
    total_count = cur.fetchone()[0]
    conn.close()

    if args.limit > 0:
        total_count = min(args.limit, total_count)

    print(f"  Total entities: {total_count:,}")
    print()

    # 청크 생성
    chunks = []
    for offset in range(0, total_count, args.batch_size):
        limit = min(args.batch_size, total_count - offset)
        chunks.append((offset, limit))

    print(f"총 {len(chunks)}개 청크 처리 시작...")

    # DB 연결
    write_conn = psycopg2.connect('postgresql://geul_writer:test1224@localhost:5432/geulwork')
    write_cur = write_conn.cursor()

    total_processed = 0
    total_skipped = 0

    # 순차 처리 (멀티프로세싱 대신 안정적 처리)
    for i, chunk in enumerate(chunks):
        chunk_start = datetime.now()
        results, skipped = process_chunk(chunk)

        # 결과 저장
        if results:
            execute_values(write_cur, """
                INSERT INTO entity_sidx (qid, sidx, entity_type, mode, attrs)
                VALUES %s
                ON CONFLICT (qid) DO UPDATE SET
                    sidx = EXCLUDED.sidx,
                    entity_type = EXCLUDED.entity_type
            """, results, page_size=10000)
            write_conn.commit()

        total_processed += len(results)
        total_skipped += skipped

        # 진행률
        elapsed = (datetime.now() - start_time).total_seconds()
        pct = (i + 1) / len(chunks) * 100
        rate = total_processed / elapsed if elapsed > 0 else 0
        eta = (total_count - total_processed) / rate / 60 if rate > 0 else 0

        print(f"\r[{pct:5.1f}%] 청크 {i+1}/{len(chunks)} | "
              f"처리: {total_processed:,} | 제외: {total_skipped:,} | "
              f"속도: {rate:.0f}/s | ETA: {eta:.0f}분", end='', flush=True)

    print(f"\n\n완료!")
    print(f"  처리: {total_processed:,}개")
    print(f"  제외: {total_skipped:,}개")
    print(f"  소요시간: {(datetime.now() - start_time).total_seconds():.0f}초")

    # 최종 확인
    write_cur.execute("SELECT COUNT(*) FROM entity_sidx")
    final = write_cur.fetchone()[0]
    print(f"  저장된 SIDX: {final:,}개")

    write_conn.close()


if __name__ == '__main__':
    main()
