#!/usr/bin/env python3
"""
GEUL Entity SIDX Era Fix
Human 타입의 Era 필드만 수정 (P569 JSON 파싱 버그 수정)

Usage:
    python scripts/sidx_fix_era.py
"""

import json
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import sys

BATCH_SIZE = 5000

def encode_era(year):
    """연도를 4비트 era 코드로 변환"""
    if year < 0:
        return 0  # 고대
    elif year < 500:
        return 1  # 고대
    elif year < 1000:
        return 2  # 중세 초기
    elif year < 1500:
        return 3  # 중세
    elif year < 1700:
        return 4  # 근세
    elif year < 1800:
        return 5  # 18세기
    elif year < 1850:
        return 6  # 19세기 전반
    elif year < 1900:
        return 7  # 19세기 후반
    elif year < 1950:
        return 8  # 20세기 전반
    elif year < 1970:
        return 9  # 1950-1970
    elif year < 1990:
        return 10  # 1970-1990
    elif year < 2000:
        return 11  # 1990s
    elif year < 2010:
        return 12  # 2000s
    elif year < 2020:
        return 13  # 2010s
    else:
        return 14  # 2020s+

def parse_birth_year(obj_value):
    """P569 값에서 연도 추출 (JSON 또는 문자열)"""
    if not obj_value:
        return None

    try:
        # JSON 형식인 경우
        if obj_value.startswith('{'):
            data = json.loads(obj_value)
            time_str = data.get('time', '')
            # +1990-01-01T00:00:00Z 형식
            if time_str.startswith('+'):
                return int(time_str[1:5])
            elif time_str.startswith('-'):
                return -int(time_str[1:5])
            else:
                return int(time_str[0:4])
        # 단순 문자열인 경우
        elif obj_value.startswith('+'):
            return int(obj_value[1:5])
        elif obj_value.startswith('-'):
            return -int(obj_value[1:5])
        else:
            return int(obj_value[0:4])
    except:
        return None

def main():
    print("=" * 60)
    print("GEUL Entity SIDX Era 수정 (Human)")
    print("=" * 60)

    # DB 연결
    print("\n[1/4] DB 연결...")
    read_conn = psycopg2.connect('postgresql://geul_reader:test1224@localhost:5432/geuldev')
    write_conn = psycopg2.connect('postgresql://geul_writer:test1224@localhost:5432/geulwork')
    read_cur = read_conn.cursor()
    write_cur = write_conn.cursor()

    # Human 타입 개체 조회
    print("\n[2/4] Human 타입 개체 조회...")
    write_cur.execute("SELECT qid FROM entity_sidx WHERE entity_type = 0")
    targets = [r[0] for r in write_cur.fetchall()]
    total_count = len(targets)
    print(f"  - 대상 개체: {total_count:,}개")

    # Era 인코딩
    print(f"\n[3/4] Era 인코딩 시작 (배치 크기: {BATCH_SIZE:,})...")
    start_time = datetime.now()

    processed = 0
    updated = 0
    offset = 0
    ERA_MASK = 0xF << 19  # 비트 19-22 (4비트)

    while offset < total_count:
        batch = targets[offset:offset + BATCH_SIZE]

        # P569 트리플 조회
        read_cur.execute("""
            SELECT subject, object_value
            FROM triples
            WHERE subject IN %s AND property = 'P569'
        """, (tuple(batch),))

        p569_map = {}
        for subj, obj in read_cur.fetchall():
            if subj not in p569_map:
                year = parse_birth_year(obj)
                if year is not None:
                    p569_map[subj] = year

        # Era 업데이트
        results = []
        for qid in batch:
            if qid in p569_map:
                year = p569_map[qid]
                era = encode_era(year)
                era_bits = era << 19
                results.append((era_bits, qid))

        # 벌크 업데이트 (Era 비트만 갱신)
        if results:
            execute_values(write_cur, """
                UPDATE entity_sidx AS e SET
                    attrs = (e.attrs & ~%s::bigint) | d.era_bits,
                    sidx = (e.sidx & ~%s::bigint) | d.era_bits
                FROM (VALUES %%s) AS d(era_bits, qid)
                WHERE e.qid = d.qid
            """ % (ERA_MASK, ERA_MASK), results, template="(%s::bigint, %s)")
            write_conn.commit()
            updated += len(results)

        processed += len(batch)
        offset += BATCH_SIZE

        # 진행률
        pct = processed / total_count * 100
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = processed / elapsed if elapsed > 0 else 0
        eta = (total_count - processed) / rate / 60 if rate > 0 else 0
        print(f"\r  [{pct:5.1f}%] {processed:,}/{total_count:,} | "
              f"업데이트: {updated:,} | 속도: {rate:.0f}/s | ETA: {eta:.1f}분", end='', flush=True)

    # 완료
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n\n[4/4] 완료!")
    print("=" * 60)
    print(f"  처리: {processed:,}개")
    print(f"  업데이트: {updated:,}개 ({updated/processed*100:.1f}%)")
    print(f"  소요시간: {elapsed/60:.1f}분")

    # 샘플 확인
    write_cur.execute("""
        SELECT qid, sidx, attrs FROM entity_sidx
        WHERE entity_type = 0 AND (attrs >> 19) & 0xF > 0
        LIMIT 5
    """)
    print(f"\n  샘플 (Era > 0):")
    for qid, sidx, attrs in write_cur.fetchall():
        era = (attrs >> 19) & 0xF
        print(f"    {qid}: sidx=0x{sidx:016X} era={era}")

    read_conn.close()
    write_conn.close()
    print("\n완료!")

if __name__ == '__main__':
    main()
