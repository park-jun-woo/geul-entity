#!/usr/bin/env python3
"""
GEUL Entity SIDX Full Encoder
1.17억 개체 전체 인코딩

Usage:
    python scripts/sidx_encode_all.py [--resume]
"""

import json
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import sys
import os

# 상수
SIDX_PREFIX = 0b0001001
DEFAULT_MODE = 0
BATCH_SIZE = 10000

def main():
    resume_mode = '--resume' in sys.argv

    print("=" * 60)
    print("GEUL Entity SIDX 전체 인코딩")
    if resume_mode:
        print("(재개 모드)")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref_dir = os.path.join(base_dir, 'references')

    # 1. 참조 파일 로드
    print("\n[1/4] 참조 파일 로드...")

    with open(os.path.join(ref_dir, 'primary_mapping.json'), 'r') as f:
        mapping = json.load(f)

    TYPE_MAP = {}
    for qid, info in mapping['primary_mappings'].items():
        TYPE_MAP[qid] = int(info['code'], 16)
    for qid, info in mapping['subtype_mappings'].items():
        TYPE_MAP[qid] = int(info['target'], 16)

    EXCLUDE_QIDS = set(mapping.get('exclude_qids', {}).keys())

    print(f"  - TYPE_MAP: {len(TYPE_MAP)}개")
    print(f"  - EXCLUDE: {len(EXCLUDE_QIDS)}개")

    # 2. DB 연결
    print("\n[2/4] DB 연결...")
    read_conn = psycopg2.connect('postgresql://geul_reader:test1224@localhost:5432/geuldev')
    write_conn = psycopg2.connect('postgresql://geul_writer:test1224@localhost:5432/geulwork')
    read_cur = read_conn.cursor()
    write_cur = write_conn.cursor()

    # 전체 개체 수
    read_cur.execute("SELECT COUNT(*) FROM entities")
    total_count = read_cur.fetchone()[0]
    print(f"  - 전체 개체: {total_count:,}개")

    # 재개 모드: 기존 데이터 확인
    if resume_mode:
        write_cur.execute("SELECT COUNT(*) FROM entity_sidx")
        existing_count = write_cur.fetchone()[0]
        print(f"  - 기존 인코딩: {existing_count:,}개 (유지)")
    else:
        # 테이블 초기화
        write_cur.execute("TRUNCATE TABLE entity_sidx")
        write_conn.commit()
        print("  - entity_sidx 테이블 초기화")

    # 3. 배치 처리
    print(f"\n[3/4] 인코딩 시작 (배치 크기: {BATCH_SIZE:,})...")
    start_time = datetime.now()

    processed = 0
    encoded = 0
    skipped = 0
    errors = 0
    offset = 0

    while True:
        # 엔티티 배치 가져오기
        read_cur.execute(f"""
            SELECT id FROM entities
            ORDER BY id
            OFFSET {offset} LIMIT {BATCH_SIZE}
        """)
        entities = [r[0] for r in read_cur.fetchall()]

        if not entities:
            break

        # P31 값 조회
        read_cur.execute("""
            SELECT subject, object_value
            FROM triples
            WHERE subject IN %s AND property = 'P31'
        """, (tuple(entities),))

        p31_map = {}
        for subj, obj in read_cur.fetchall():
            if subj not in p31_map:
                p31_map[subj] = []
            p31_map[subj].append(obj)

        # SIDX 생성
        results = []
        for qid in entities:
            try:
                p31_list = p31_map.get(qid, [])

                # EntityType 결정
                entity_type = 0x3F  # 기본 Other
                for p31 in p31_list:
                    if p31 in EXCLUDE_QIDS:
                        entity_type = None
                        break
                    if p31 in TYPE_MAP:
                        entity_type = TYPE_MAP[p31]
                        break

                if entity_type is None:
                    skipped += 1
                    continue

                # SIDX 조립
                attrs = 0  # Attributes는 추후 확장
                word1 = (SIDX_PREFIX << 9) | (DEFAULT_MODE << 6) | entity_type
                sidx = (word1 << 48) | attrs

                results.append((qid, sidx, entity_type, DEFAULT_MODE, attrs))
                encoded += 1
            except Exception as e:
                errors += 1

        # 벌크 인서트 (중복 무시)
        if results:
            execute_values(write_cur, """
                INSERT INTO entity_sidx (qid, sidx, entity_type, mode, attrs)
                VALUES %s
                ON CONFLICT (qid) DO NOTHING
            """, results, page_size=5000)
            write_conn.commit()

        processed += len(entities)
        offset += len(entities)

        # 진행률 (1% 단위로 출력)
        pct = processed / total_count * 100
        if processed % (BATCH_SIZE * 10) == 0 or processed >= total_count:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total_count - processed) / rate / 60 if rate > 0 else 0
            print(f"\r  [{pct:5.1f}%] {processed:,}/{total_count:,} | "
                  f"인코딩: {encoded:,} | 제외: {skipped:,} | "
                  f"속도: {rate:.0f}/s | ETA: {eta:.0f}분", end='', flush=True)

    # 4. 완료
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n\n[4/4] 완료!")
    print("=" * 60)
    print(f"  처리: {processed:,}개")
    print(f"  인코딩: {encoded:,}개")
    print(f"  제외(Wikimedia): {skipped:,}개")
    print(f"  에러: {errors:,}개")
    print(f"  소요시간: {elapsed/60:.1f}분 ({elapsed:.0f}초)")
    print(f"  평균속도: {processed/elapsed:.0f}개/초")

    # 결과 확인
    write_cur.execute("SELECT COUNT(*) FROM entity_sidx")
    final_count = write_cur.fetchone()[0]
    print(f"\n  entity_sidx 테이블: {final_count:,}개")

    # 타입별 통계
    write_cur.execute("""
        SELECT entity_type, COUNT(*) as cnt
        FROM entity_sidx
        GROUP BY entity_type
        ORDER BY cnt DESC
        LIMIT 10
    """)
    print("\n  상위 10개 타입:")
    for row in write_cur.fetchall():
        print(f"    0x{row[0]:02X}: {row[1]:,}개")

    read_conn.close()
    write_conn.close()
    print("\n완료!")


if __name__ == '__main__':
    main()
