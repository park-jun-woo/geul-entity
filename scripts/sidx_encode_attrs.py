#!/usr/bin/env python3
"""
GEUL Entity SIDX Attributes Encoder
48비트 속성 인코딩 (Phase 6)

Usage:
    python scripts/sidx_encode_attrs.py [--type TYPE_CODE] [--limit N]
"""

import json
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import sys
import os

# 상수
BATCH_SIZE = 5000

def load_references(ref_dir):
    """참조 파일 로드"""
    with open(os.path.join(ref_dir, 'type_schemas.json'), 'r') as f:
        schemas = json.load(f)

    with open(os.path.join(ref_dir, 'codebooks_full.json'), 'r') as f:
        codebooks = json.load(f)

    return schemas, codebooks

def build_codebook_maps(codebooks):
    """코드북을 QID → code 매핑으로 변환"""
    maps = {}
    for name, cb in codebooks.get('codebooks', {}).items():
        qid_to_code = {}
        for entry in cb.get('values', []):
            qid = entry.get('qid')
            if qid:
                qid_to_code[qid] = entry['code']
        maps[name] = qid_to_code
    return maps

def get_schema_for_type(schemas, entity_type):
    """EntityType에 해당하는 스키마 반환"""
    hex_key = f"0x{entity_type:02X}"
    for key, schema in schemas.get('schemas', {}).items():
        if key.startswith(hex_key):
            return schema
    return None

def encode_human_attrs(qid, triples, codebook_maps):
    """Human (0x00) 타입 48비트 속성 인코딩"""
    attrs = 0

    # P21 (gender) → offset 27, 2비트
    gender_map = {'Q6581097': 1, 'Q6581072': 2, 'Q1097630': 3}  # male, female, intersex
    for subj, prop, obj in triples:
        if prop == 'P21' and obj in gender_map:
            attrs |= (gender_map[obj] << 27)
            break

    # P27 (country of citizenship) → offset 11, 8비트
    country_map = codebook_maps.get('country', {})
    for subj, prop, obj in triples:
        if prop == 'P27' and obj in country_map:
            attrs |= (country_map[obj] << 11)
            break

    # P106 (occupation) → offset 5, 6비트
    occupation_map = codebook_maps.get('occupation', {})
    for subj, prop, obj in triples:
        if prop == 'P106' and obj in occupation_map:
            attrs |= (occupation_map[obj] << 5)
            break

    # P1412 (languages spoken) → offset 32, 6비트
    language_map = codebook_maps.get('language', {})
    for subj, prop, obj in triples:
        if prop == 'P1412' and obj in language_map:
            attrs |= (language_map[obj] << 32)
            break

    # P569 (date of birth) → era at offset 19, 4비트
    for subj, prop, obj in triples:
        if prop == 'P569' and obj:
            try:
                # +1990-01-01T00:00:00Z 형식
                year = int(obj[1:5]) if obj.startswith('+') else int(obj[0:4])
                era = encode_era(year)
                attrs |= (era << 19)
            except:
                pass
            break

    return attrs

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

def encode_taxon_attrs(qid, triples, codebook_maps):
    """Taxon (0x01) 타입 48비트 속성 인코딩"""
    attrs = 0

    # P105 (taxon rank) → offset 26, 3비트
    rank_map = {
        'Q7432': 1,   # species
        'Q34740': 2,  # genus
        'Q35409': 3,  # family
        'Q36602': 4,  # order
        'Q37517': 5,  # class
        'Q38348': 6,  # phylum
        'Q36732': 7,  # kingdom
    }
    for subj, prop, obj in triples:
        if prop == 'P105' and obj in rank_map:
            attrs |= (rank_map[obj] << 26)
            break

    # P141 (IUCN conservation status) → offset 29, 3비트
    conservation_map = {
        'Q211005': 1,   # LC (Least Concern)
        'Q719675': 2,   # NT (Near Threatened)
        'Q278113': 3,   # VU (Vulnerable)
        'Q11394': 4,    # EN (Endangered)
        'Q219127': 5,   # CR (Critically Endangered)
        'Q239509': 6,   # EW (Extinct in Wild)
        'Q237350': 7,   # EX (Extinct)
    }
    for subj, prop, obj in triples:
        if prop == 'P141' and obj in conservation_map:
            attrs |= (conservation_map[obj] << 29)
            break

    return attrs

def encode_chemical_attrs(qid, triples, codebook_maps):
    """Chemical (0x08) 타입 48비트 속성 인코딩"""
    attrs = 0
    # 화학물질은 추가 속성 인코딩 필요 (현재 기본값)
    return attrs

def encode_star_attrs(qid, triples, codebook_maps):
    """Star (0x0C) 타입 48비트 속성 인코딩"""
    attrs = 0

    # P59 (constellation) → offset 0, 7비트
    constellation_map = codebook_maps.get('constellation', {})
    for subj, prop, obj in triples:
        if prop == 'P59' and obj in constellation_map:
            attrs |= constellation_map[obj]
            break

    return attrs

def encode_attrs_for_type(entity_type, qid, triples, codebook_maps):
    """EntityType별 속성 인코딩 라우팅"""
    if entity_type == 0x00:  # Human
        return encode_human_attrs(qid, triples, codebook_maps)
    elif entity_type == 0x01:  # Taxon
        return encode_taxon_attrs(qid, triples, codebook_maps)
    elif entity_type == 0x08:  # Chemical
        return encode_chemical_attrs(qid, triples, codebook_maps)
    elif entity_type == 0x0C:  # Star
        return encode_star_attrs(qid, triples, codebook_maps)
    else:
        return 0  # 기본값

def main():
    # 인자 파싱
    target_type = None
    limit = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--type' and i + 1 < len(args):
            target_type = int(args[i + 1], 16) if args[i + 1].startswith('0x') else int(args[i + 1])
            i += 2
        elif args[i] == '--limit' and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        else:
            i += 1

    print("=" * 60)
    print("GEUL Entity SIDX 속성 인코딩")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref_dir = os.path.join(base_dir, 'references')

    # 1. 참조 파일 로드
    print("\n[1/4] 참조 파일 로드...")
    schemas, codebooks = load_references(ref_dir)
    codebook_maps = build_codebook_maps(codebooks)
    print(f"  - 스키마: {len(schemas.get('schemas', {}))}개")
    print(f"  - 코드북: {len(codebook_maps)}개")

    # 2. DB 연결
    print("\n[2/4] DB 연결...")
    read_conn = psycopg2.connect('postgresql://geul_reader:test1224@localhost:5432/geuldev')
    write_conn = psycopg2.connect('postgresql://geul_writer:test1224@localhost:5432/geulwork')
    read_cur = read_conn.cursor()
    write_cur = write_conn.cursor()

    # 대상 개체 조회
    if target_type is not None:
        write_cur.execute(
            "SELECT qid, entity_type FROM entity_sidx WHERE entity_type = %s AND attrs = 0",
            (target_type,)
        )
        type_name = f"0x{target_type:02X}"
    else:
        write_cur.execute(
            "SELECT qid, entity_type FROM entity_sidx WHERE attrs = 0 AND entity_type IN (0, 1, 8, 12)"
        )
        type_name = "Human/Taxon/Chemical/Star"

    targets = write_cur.fetchall()

    if limit:
        targets = targets[:limit]

    total_count = len(targets)
    print(f"  - 대상 타입: {type_name}")
    print(f"  - 대상 개체: {total_count:,}개")

    if total_count == 0:
        print("\n처리할 개체가 없습니다.")
        return

    # 3. 속성 인코딩
    print(f"\n[3/4] 속성 인코딩 시작 (배치 크기: {BATCH_SIZE:,})...")
    start_time = datetime.now()

    processed = 0
    updated = 0
    offset = 0

    while offset < total_count:
        batch = targets[offset:offset + BATCH_SIZE]
        qids = [t[0] for t in batch]
        type_map = {t[0]: t[1] for t in batch}

        # 트리플 조회 (P21, P27, P106, P569, P1412, P105, P141, P59)
        read_cur.execute("""
            SELECT subject, property, object_value
            FROM triples
            WHERE subject IN %s
              AND property IN ('P21', 'P27', 'P106', 'P569', 'P1412', 'P105', 'P141', 'P59')
        """, (tuple(qids),))

        triples_map = {}
        for subj, prop, obj in read_cur.fetchall():
            if subj not in triples_map:
                triples_map[subj] = []
            triples_map[subj].append((subj, prop, obj))

        # 속성 인코딩
        results = []
        for qid in qids:
            entity_type = type_map[qid]
            triples = triples_map.get(qid, [])
            attrs = encode_attrs_for_type(entity_type, qid, triples, codebook_maps)

            if attrs > 0:
                results.append((attrs, qid))
                updated += 1

        # 벌크 업데이트
        if results:
            execute_values(write_cur, """
                UPDATE entity_sidx AS e SET
                    attrs = d.attrs,
                    sidx = (e.sidx & x'FFFF000000000000'::bigint) | d.attrs
                FROM (VALUES %s) AS d(attrs, qid)
                WHERE e.qid = d.qid
            """, results, template="(%s::bigint, %s)")
            write_conn.commit()

        processed += len(batch)
        offset += BATCH_SIZE

        # 진행률
        pct = processed / total_count * 100
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = processed / elapsed if elapsed > 0 else 0
        eta = (total_count - processed) / rate / 60 if rate > 0 else 0
        print(f"\r  [{pct:5.1f}%] {processed:,}/{total_count:,} | "
              f"업데이트: {updated:,} | 속도: {rate:.0f}/s | ETA: {eta:.1f}분", end='', flush=True)

    # 4. 완료
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n\n[4/4] 완료!")
    print("=" * 60)
    print(f"  처리: {processed:,}개")
    print(f"  업데이트: {updated:,}개 ({updated/processed*100:.1f}%)")
    print(f"  소요시간: {elapsed/60:.1f}분")

    # 샘플 확인
    if updated > 0 and target_type is not None:
        write_cur.execute("""
            SELECT qid, sidx, attrs FROM entity_sidx
            WHERE entity_type = %s AND attrs > 0
            LIMIT 5
        """, (target_type,))
        print(f"\n  샘플 (0x{target_type:02X}):")
        for qid, sidx, attrs in write_cur.fetchall():
            print(f"    {qid}: sidx=0x{sidx:016X} attrs=0x{attrs:012X}")

    read_conn.close()
    write_conn.close()
    print("\n완료!")

if __name__ == '__main__':
    main()
