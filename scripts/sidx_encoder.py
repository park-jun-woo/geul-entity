#!/usr/bin/env python3
"""
GEUL Entity SIDX Encoder
위키데이터 Q-ID → 64비트 SIDX 인코딩

Usage:
    python scripts/sidx_encoder.py [--batch-size=10000] [--offset=0] [--limit=0]
"""

import json
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import sys
import os

# 상수
SIDX_PREFIX = 0b0001001  # 7비트 Proposal Entity prefix
DEFAULT_MODE = 0  # 등록 모드

# 전역 캐시
TYPE_MAP = {}  # QID → (type_code, subtype_info)
CODEBOOKS = {}  # 필드별 코드북
SCHEMAS = {}  # EntityType별 스키마


def load_references():
    """참조 파일 로드"""
    global TYPE_MAP, CODEBOOKS, SCHEMAS

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref_dir = os.path.join(base_dir, 'references')

    # Primary mapping 로드
    with open(os.path.join(ref_dir, 'primary_mapping.json'), 'r') as f:
        mapping = json.load(f)

    # primary_mappings
    for qid, info in mapping['primary_mappings'].items():
        code = int(info['code'], 16)
        TYPE_MAP[qid] = {'code': code, 'name': info['name'], 'subtype': None}

    # subtype_mappings
    for qid, info in mapping['subtype_mappings'].items():
        code = int(info['target'], 16)
        TYPE_MAP[qid] = {
            'code': code,
            'name': info['target_name'],
            'subtype': {
                'field': info.get('subtype_field'),
                'value': info.get('subtype_value'),
                'flag': info.get('flag')
            }
        }

    # exclude list
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

    # Schemas 로드
    with open(os.path.join(ref_dir, 'type_schemas.json'), 'r') as f:
        schema_data = json.load(f)

    for type_key, schema in schema_data['schemas'].items():
        code = int(type_key.split('_')[0], 16)
        SCHEMAS[code] = schema['fields']

    return EXCLUDE_QIDS


def get_entity_type(p31_values, exclude_qids):
    """P31 값에서 EntityType 결정"""
    if not p31_values:
        return 0x3F, None  # Other

    for p31 in p31_values:
        # 제외 대상 확인
        if p31 in exclude_qids:
            return None, None  # 인코딩 제외

        # 직접 매핑 또는 하위 타입 매핑
        if p31 in TYPE_MAP:
            info = TYPE_MAP[p31]
            return info['code'], info.get('subtype')

    # 폴백: Other
    return 0x3F, None


def quantize_year(year_str):
    """연도 양자화 (7비트, 0-127)"""
    if not year_str:
        return 0
    try:
        # "+1985-01-01T00:00:00Z" 형식 파싱
        if year_str.startswith('+'):
            year = int(year_str[1:5])
        elif year_str.startswith('-'):
            year = int(year_str[1:5]) * -1
        else:
            year = int(year_str[:4])

        if year < 1900:
            return 1  # 1900년 이전
        elif year > 2027:
            return 127  # 미래
        else:
            return year - 1900 + 1
    except:
        return 0


def quantize_coord(value, is_lat=True):
    """좌표 양자화 (4비트, 0-15)"""
    if value is None:
        return 0
    try:
        v = float(value)
        if is_lat:  # -90 ~ +90
            zone = int((v + 90) / 12)
        else:  # -180 ~ +180
            zone = int((v + 180) / 24)
        return max(0, min(15, zone))
    except:
        return 0


def encode_attributes(entity_type, properties):
    """48비트 Attributes 인코딩"""
    if entity_type not in SCHEMAS:
        return 0

    attrs = 0
    schema = SCHEMAS[entity_type]

    for field in schema:
        name = field['name']
        bits = field['bits']
        offset = field['offset']
        prop = field.get('property', '')

        value = 0

        # property에서 값 추출
        if prop and prop in properties:
            prop_values = properties[prop]
            if prop_values:
                raw_val = prop_values[0]  # 첫 번째 값 사용

                # 코드북 조회
                if name in CODEBOOKS and raw_val in CODEBOOKS[name]:
                    value = CODEBOOKS[name][raw_val]
                # 양자화 필드
                elif name == 'year' or name == 'decade':
                    value = quantize_year(raw_val)
                elif name == 'lat_zone':
                    value = quantize_coord(raw_val, is_lat=True)
                elif name == 'lon_zone':
                    value = quantize_coord(raw_val, is_lat=False)
                elif name in ('country', 'origin_country'):
                    if raw_val in CODEBOOKS.get('country', {}):
                        value = CODEBOOKS['country'][raw_val]
                elif name == 'occupation':
                    if raw_val in CODEBOOKS.get('occupation', {}):
                        value = CODEBOOKS['occupation'][raw_val]
                elif name == 'language':
                    if raw_val in CODEBOOKS.get('language', {}):
                        value = CODEBOOKS['language'][raw_val]
                elif name == 'genre':
                    if raw_val in CODEBOOKS.get('genre', {}):
                        value = CODEBOOKS['genre'][raw_val]

        # 비트 마스크 적용
        mask = (1 << bits) - 1
        value = value & mask
        attrs |= (value << offset)

    return attrs


def build_sidx(mode, entity_type, attrs):
    """64비트 SIDX 조립"""
    # Word 1: Prefix(7) + Mode(3) + EntityType(6)
    word1 = (SIDX_PREFIX << 9) | (mode << 6) | entity_type

    # Words 2-4: Attributes (48비트)
    word2 = (attrs >> 32) & 0xFFFF
    word3 = (attrs >> 16) & 0xFFFF
    word4 = attrs & 0xFFFF

    # 64비트 정수로 결합
    sidx = (word1 << 48) | (word2 << 32) | (word3 << 16) | word4
    return sidx


def process_batch(entities, props_by_entity, exclude_qids):
    """배치 처리"""
    results = []
    errors = 0

    for qid in entities:
        try:
            # P31 값 가져오기
            props = props_by_entity.get(qid, {})
            p31_values = props.get('P31', [])

            # EntityType 결정
            entity_type, subtype = get_entity_type(p31_values, exclude_qids)

            if entity_type is None:
                continue  # 제외 대상

            # Attributes 인코딩
            attrs = encode_attributes(entity_type, props)

            # subtype 처리
            if subtype and subtype.get('field') and subtype.get('value'):
                # subtype 값을 해당 필드 위치에 설정
                # (이미 type_mapping에서 처리됨)
                pass

            # SIDX 조립
            sidx = build_sidx(DEFAULT_MODE, entity_type, attrs)

            results.append((qid, sidx, entity_type, DEFAULT_MODE, attrs))
        except Exception as e:
            errors += 1

    return results, errors


def main():
    """메인 실행"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch-size', type=int, default=10000)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    print(f"SIDX Encoder 시작: batch_size={args.batch_size}, offset={args.offset}")

    # 참조 파일 로드
    print("참조 파일 로드 중...")
    exclude_qids = load_references()
    print(f"  - TYPE_MAP: {len(TYPE_MAP)}개")
    print(f"  - CODEBOOKS: {len(CODEBOOKS)}개")
    print(f"  - SCHEMAS: {len(SCHEMAS)}개")
    print(f"  - EXCLUDE: {len(exclude_qids)}개")

    # DB 연결
    read_conn = psycopg2.connect('postgresql://geul_reader:test1224@localhost:5432/geuldev')
    write_conn = psycopg2.connect('postgresql://geul_writer:test1224@localhost:5432/geulwork')

    read_cur = read_conn.cursor()
    write_cur = write_conn.cursor()

    # 전체 개체 수 확인
    read_cur.execute("SELECT COUNT(*) FROM entities")
    total_count = read_cur.fetchone()[0]
    print(f"전체 개체 수: {total_count:,}")

    if args.limit > 0:
        total_to_process = min(args.limit, total_count - args.offset)
    else:
        total_to_process = total_count - args.offset

    print(f"처리 대상: {total_to_process:,}개\n")

    # 배치 처리
    processed = 0
    total_errors = 0
    batch_id = 0
    current_offset = args.offset

    # 핵심 property 목록 (Attributes 인코딩에 필요한 것들)
    key_properties = [
        'P31',   # instance of (EntityType 결정)
        'P27',   # country of citizenship
        'P17',   # country
        'P495',  # country of origin
        'P106',  # occupation
        'P569',  # date of birth
        'P571',  # inception
        'P577',  # publication date
        'P136',  # genre
        'P407',  # language
        'P1412', # languages spoken
        'P625',  # coordinate location
        'P131',  # admin territorial entity
        'P21',   # sex or gender
        'P703',  # found in taxon
        'P171',  # parent taxon
        'P105',  # taxon rank
        'P141',  # conservation status
        'P215',  # spectral class
    ]
    prop_list = "'" + "','".join(key_properties) + "'"

    while processed < total_to_process:
        batch_start = datetime.now()
        batch_size = min(args.batch_size, total_to_process - processed)

        # 엔티티 ID 가져오기
        read_cur.execute(f"""
            SELECT id FROM entities
            ORDER BY id
            OFFSET {current_offset} LIMIT {batch_size}
        """)
        entities = [row[0] for row in read_cur.fetchall()]

        if not entities:
            break

        # 해당 엔티티들의 트리플 가져오기
        entity_list = "'" + "','".join(entities) + "'"
        read_cur.execute(f"""
            SELECT subject, property, object_value
            FROM triples
            WHERE subject IN ({entity_list})
            AND property IN ({prop_list})
        """)

        # 엔티티별 properties 구성
        props_by_entity = {}
        for row in read_cur.fetchall():
            subj, prop, obj = row
            if subj not in props_by_entity:
                props_by_entity[subj] = {}
            if prop not in props_by_entity[subj]:
                props_by_entity[subj][prop] = []
            props_by_entity[subj][prop].append(obj)

        # 배치 처리
        results, errors = process_batch(entities, props_by_entity, exclude_qids)
        total_errors += errors

        # 결과 저장
        if results:
            execute_values(write_cur, """
                INSERT INTO entity_sidx (qid, sidx, entity_type, mode, attrs)
                VALUES %s
                ON CONFLICT (qid) DO UPDATE SET
                    sidx = EXCLUDED.sidx,
                    entity_type = EXCLUDED.entity_type,
                    mode = EXCLUDED.mode,
                    attrs = EXCLUDED.attrs,
                    created_at = NOW()
            """, results)
            write_conn.commit()

        # 진행상황 기록
        batch_end = datetime.now()
        write_cur.execute("""
            INSERT INTO encoding_progress
            (batch_id, start_offset, end_offset, processed, errors, started_at, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (batch_id, current_offset, current_offset + len(entities),
              len(results), errors, batch_start, batch_end))
        write_conn.commit()

        processed += len(entities)
        current_offset += len(entities)
        batch_id += 1

        # 진행률 출력
        pct = processed / total_to_process * 100
        elapsed = (batch_end - batch_start).total_seconds()
        rate = len(entities) / elapsed if elapsed > 0 else 0
        eta_sec = (total_to_process - processed) / rate if rate > 0 else 0
        eta_min = eta_sec / 60

        print(f"\r[{pct:5.1f}%] {processed:,}/{total_to_process:,} | "
              f"배치: {len(results):,}개 ({elapsed:.1f}s, {rate:.0f}/s) | "
              f"에러: {total_errors:,} | ETA: {eta_min:.0f}분", end='', flush=True)

    print(f"\n\n완료!")
    print(f"  - 처리: {processed:,}개")
    print(f"  - 에러: {total_errors:,}개")

    # 최종 통계
    write_cur.execute("SELECT COUNT(*) FROM entity_sidx")
    final_count = write_cur.fetchone()[0]
    print(f"  - 저장된 SIDX: {final_count:,}개")

    read_conn.close()
    write_conn.close()


if __name__ == '__main__':
    main()
