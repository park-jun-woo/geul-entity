#!/usr/bin/env python3
"""
64개 EntityType 스키마 검증 스크립트
- 비트 합계 48비트 확인
- 오프셋 연속성 검증
- 충돌률 시뮬레이션
"""

import json
import random
from collections import defaultdict
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent.parent / "references" / "type_schemas.json"

def load_schemas():
    with open(SCHEMA_PATH) as f:
        return json.load(f)

def validate_bits(schema_key, schema):
    """비트 합계 및 오프셋 검증"""
    fields = schema.get('fields', [])
    if not fields:
        return {'valid': True, 'total_bits': 0, 'errors': []}

    errors = []
    total_bits = sum(f['bits'] for f in fields)

    # 48비트 확인
    if total_bits != 48:
        errors.append(f"총 비트 {total_bits} != 48")

    # 오프셋 연속성 확인
    expected_offset = 0
    for f in fields:
        if f['offset'] != expected_offset:
            errors.append(f"필드 {f['name']}: offset {f['offset']} != expected {expected_offset}")
        expected_offset = f['offset'] + f['bits']

    # 마지막 필드가 48비트 경계에 도달하는지
    if expected_offset != 48 and total_bits == 48:
        # 이미 total_bits로 체크됨
        pass

    return {
        'valid': len(errors) == 0,
        'total_bits': total_bits,
        'errors': errors
    }

def simulate_collision(schema, sample_size=10000):
    """충돌률 시뮬레이션"""
    fields = schema.get('fields', [])
    if not fields:
        return {'collision_rate': 0, 'unique_count': 0}

    sidx_set = set()

    for _ in range(sample_size):
        sidx = 0
        for f in fields:
            bits = f['bits']
            max_val = (1 << bits) - 1

            # Zipf 분포 시뮬레이션
            if random.random() < 0.3:
                value = 0  # Unknown
            elif random.random() < 0.7:
                value = random.randint(1, max(1, max_val // 2))
            else:
                value = random.randint(1, max_val)

            sidx |= (value << f['offset'])

        sidx_set.add(sidx)

    unique_count = len(sidx_set)
    collision_rate = (sample_size - unique_count) / sample_size * 100

    return {
        'collision_rate': collision_rate,
        'unique_count': unique_count
    }

def main():
    schemas = load_schemas()

    print("=" * 70)
    print("GEUL Entity 64개 타입 스키마 검증 보고서")
    print("=" * 70)
    print()

    # 통계
    valid_count = 0
    invalid_count = 0
    collision_results = []

    # 중복 키 제거 (0x04_CellLine, 0x04_CellLine_v2 등)
    schema_keys = [k for k in schemas['schemas'].keys() if not k.endswith('_v2')]

    print(f"총 스키마 수: {len(schema_keys)}")
    print()

    # 비트 검증
    print("## 1. 비트 합계 검증")
    print("-" * 70)
    print(f"{'타입':<25} {'비트합':<8} {'상태':<8} {'오류'}")
    print("-" * 70)

    for schema_key in sorted(schema_keys):
        schema = schemas['schemas'][schema_key]
        result = validate_bits(schema_key, schema)

        status = "OK" if result['valid'] else "ERROR"
        if result['valid']:
            valid_count += 1
        else:
            invalid_count += 1

        error_str = "; ".join(result['errors']) if result['errors'] else ""
        print(f"{schema_key:<25} {result['total_bits']:<8} {status:<8} {error_str}")

    print("-" * 70)
    print(f"Valid: {valid_count}, Invalid: {invalid_count}")
    print()

    # 충돌률 시뮬레이션 (상위 10개 타입만)
    print("## 2. 충돌률 시뮬레이션 (샘플 10,000개)")
    print("-" * 70)
    print(f"{'타입':<25} {'개체수':<12} {'고유SIDX':<10} {'충돌률'}")
    print("-" * 70)

    # 개체수 기준 상위 15개
    type_counts = []
    for schema_key in schema_keys:
        schema = schemas['schemas'][schema_key]
        count = schema.get('count', 0)
        type_counts.append((schema_key, count, schema))

    type_counts.sort(key=lambda x: x[1], reverse=True)

    for schema_key, count, schema in type_counts[:15]:
        sim = simulate_collision(schema)
        collision_results.append({
            'type': schema_key,
            'count': count,
            'collision_rate': sim['collision_rate'],
            'unique_count': sim['unique_count']
        })

        print(f"{schema_key:<25} {count:<12,} {sim['unique_count']:<10,} {sim['collision_rate']:.2f}%")

    print("-" * 70)
    print()

    # 요약
    print("## 3. 요약")
    print("-" * 70)
    avg_collision = sum(r['collision_rate'] for r in collision_results) / len(collision_results) if collision_results else 0
    print(f"평균 충돌률: {avg_collision:.2f}%")
    print(f"스키마 유효성: {valid_count}/{len(schema_keys)} ({valid_count/len(schema_keys)*100:.1f}%)")
    print()

    if invalid_count > 0:
        print("[WARNING] 비트 합계가 48이 아닌 스키마가 있습니다. 수정이 필요합니다.")
    else:
        print("[SUCCESS] 모든 스키마가 48비트를 사용합니다.")

    print()
    print("=" * 70)
    print("검증 완료")
    print("=" * 70)

if __name__ == '__main__':
    main()
