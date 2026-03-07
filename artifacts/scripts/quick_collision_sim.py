#!/usr/bin/env python3
"""
48비트 전체 활용 충돌률 빠른 시뮬레이션
기존 코드북 + 새 필드 가상 코드북으로 충돌률 추정
"""

import json
import random
from collections import defaultdict
from pathlib import Path

# 새 스키마 로드
SCHEMA_PATH = Path(__file__).parent.parent / "references" / "type_schemas.json"
QUANT_PATH = Path(__file__).parent.parent / "references" / "quantization_rules.json"

def load_schemas():
    with open(SCHEMA_PATH) as f:
        return json.load(f)

def load_quantization():
    with open(QUANT_PATH) as f:
        return json.load(f)

def simulate_field_value(field_name, bits, coverage_pct):
    """필드 값 시뮬레이션 (커버리지 기반)"""
    if random.random() * 100 > coverage_pct:
        return 0  # Unknown

    max_val = (1 << bits) - 1
    # Zipf 분포 시뮬레이션 (상위 코드가 더 자주 사용됨)
    if random.random() < 0.7:  # 70%는 상위 절반
        return random.randint(1, max(1, max_val // 2))
    else:
        return random.randint(1, max_val)

def encode_entity(schema, coverages):
    """개체를 48비트로 인코딩"""
    sidx = 0
    for field in schema['fields']:
        name = field['name']
        bits = field['bits']
        offset = field['offset']

        coverage = coverages.get(name, 50)  # 기본 50%
        value = simulate_field_value(name, bits, coverage)

        sidx |= (value << offset)

    return sidx

def simulate_collision(type_code, schema, sample_size=1000):
    """충돌률 시뮬레이션"""

    # 필드별 커버리지 (Stage 1 보고서 기반)
    coverages = {
        # Human
        'subclass': 100, 'occupation': 97.8, 'country': 94.6,
        'era': 99.3, 'decade': 99.3, 'gender': 100, 'notability': 100,
        'language': 71.4, 'birth_region': 91.4, 'activity_field': 30,

        # Star
        'constellation': 90.4, 'spectral_type': 24.0, 'luminosity': 24.0,
        'magnitude': 98.5, 'ra_zone': 98.4, 'dec_zone': 98.4, 'flags': 50,
        'radial_vel': 52.8, 'redshift': 32.7, 'parallax': 26.9, 'pm_class': 58.2,

        # Settlement
        'admin_level': 80, 'admin_code': 87.2, 'lat_zone': 81.7, 'lon_zone': 81.7,
        'population': 14.1, 'timezone': 35.1, 'elevation': 33.7,
        'settlement_type': 100, 'coastal': 80,

        # Organization
        'org_type': 100, 'legal_form': 75.5, 'industry': 73.3, 'size': 50,
        'hq_region': 65.2, 'status': 19.5, 'ideology': 33.0, 'sector': 80,

        # Film
        'year': 86.3, 'genre': 71.6, 'color': 48.0, 'duration': 46.7,
        'director_fame': 79.7, 'cast_tier': 58.0, 'rating': 50, 'format': 100,
    }

    sidx_counts = defaultdict(int)

    for _ in range(sample_size):
        sidx = encode_entity(schema, coverages)
        sidx_counts[sidx] += 1

    # 충돌 계산
    unique_sidx = len(sidx_counts)
    collisions = sum(1 for c in sidx_counts.values() if c > 1)
    collision_rate = (sample_size - unique_sidx) / sample_size * 100

    return {
        'sample_size': sample_size,
        'unique_sidx': unique_sidx,
        'collisions': collisions,
        'collision_rate': collision_rate
    }

def main():
    schemas = load_schemas()

    print("=" * 60)
    print("48비트 전체 활용 충돌률 시뮬레이션")
    print("=" * 60)
    print()

    results = {}

    type_map = {
        '0x00_Human': ('0x00', '인간', 12500000),
        '0x0C_Star': ('0x0C', '항성', 3600000),
        '0x1C_Settlement': ('0x1C', '정주지', 1100000),
        '0x2C_Organization': ('0x2C', '조직', 531000),
        '0x33_Film': ('0x33', '영화', 336000),
    }

    # 이전 충돌률 (Phase 2 결과)
    prev_collision = {
        '0x00': 21.25,
        '0x0C': 18.40,
        '0x1C': 9.68,
        '0x2C': 32.64,
        '0x33': 9.61,
    }

    for schema_key, (type_code, name, entity_count) in type_map.items():
        if schema_key not in schemas['schemas']:
            continue

        schema = schemas['schemas'][schema_key]

        # 대용량 시뮬레이션
        result = simulate_collision(type_code, schema, sample_size=50000)
        avg_rate = result['collision_rate']
        unique_count = result['unique_sidx']
        prev_rate = prev_collision.get(type_code, 0)
        improvement = prev_rate - avg_rate if prev_rate > 0 else 0

        results[type_code] = {
            'name': name,
            'prev_rate': prev_rate,
            'new_rate': avg_rate,
            'improvement': improvement
        }

        # 비트 합계 검증
        total_bits = sum(f['bits'] for f in schema['fields'])

        print(f"## {name} ({type_code})")
        print(f"   비트 합계: {total_bits}/48")
        print(f"   샘플: 50,000 / 고유 SIDX: {unique_count}")
        print(f"   이전 충돌률: {prev_rate:.2f}%")
        print(f"   예상 충돌률: {avg_rate:.2f}%")
        print(f"   개선율: {improvement:.2f}%p")
        print()

    print("=" * 60)
    print("요약")
    print("=" * 60)
    print()
    print("| 타입 | 이전 | 예상 | 개선 |")
    print("|------|------|------|------|")
    for type_code, r in results.items():
        print(f"| {r['name']} | {r['prev_rate']:.1f}% | {r['new_rate']:.1f}% | -{r['improvement']:.1f}%p |")

    print()
    print("※ 시뮬레이션 기반 추정치 (실제 코드북 적용 시 달라질 수 있음)")

if __name__ == '__main__':
    main()
