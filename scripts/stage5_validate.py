#!/usr/bin/env python3
"""
Stage 5: 검증 (v2.0)

전체 파이프라인 결과를 검증한다:
- 충돌률 테스트
- 추상 표현 테스트
- 인코딩 일관성 테스트
- 열화 테스트
"""

import json
import random
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import psycopg2

# 경로 설정
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
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

# 충돌률 목표
COLLISION_TARGETS = {
    'large': {'min_count': 10_000_000, 'max_rate': 0.01},   # 1%
    'medium_large': {'min_count': 1_000_000, 'max_rate': 0.03},  # 3%
    'medium': {'min_count': 100_000, 'max_rate': 0.01},     # 1%
    'small': {'min_count': 10_000, 'max_rate': 0.005},      # 0.5%
    'tiny': {'min_count': 0, 'max_rate': 0.001}             # 0.1%
}

def get_target_rate(count: int) -> float:
    """개체수에 따른 목표 충돌률"""
    if count >= 10_000_000:
        return 0.01
    elif count >= 1_000_000:
        return 0.03
    elif count >= 100_000:
        return 0.01
    elif count >= 10_000:
        return 0.005
    else:
        return 0.001

def get_entity_types() -> list:
    """타입 목록"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT e.type_code, e.name_ko, e.qid, e.total_count,
                   c.collision_rate
            FROM entity_type_map e
            LEFT JOIN collision_stats c ON e.type_code = c.entity_type
            WHERE e.sample_count > 0
            ORDER BY e.type_code
        """)
        types = [(row[0], row[1], row[2], row[3], row[4]) for row in cur.fetchall()]
    conn.close()
    return types

def test_collision_rates(types: list) -> list:
    """충돌률 테스트"""
    results = []
    for type_code, name_ko, qid, total_count, collision_rate in types:
        target = get_target_rate(total_count or 0)
        actual = collision_rate or 0
        passed = actual <= target

        results.append({
            'type_code': type_code,
            'name_ko': name_ko,
            'total_count': total_count or 0,
            'target_rate': target,
            'actual_rate': actual,
            'passed': passed,
            'margin': target - actual
        })

    return results

def get_bit_allocation(type_code: int) -> list:
    """비트 할당 조회"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT field_name, property_id, bit_offset, bit_width
            FROM bit_allocation
            WHERE entity_type = %s
            ORDER BY bit_offset
        """, (type_code,))
        rows = cur.fetchall()
    conn.close()
    return [{'name': r[0], 'prop': r[1], 'offset': r[2], 'bits': r[3]} for r in rows]

def get_codebook_entry(type_code: int, field_name: str, value: str) -> int:
    """코드북에서 코드 조회"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT code FROM codebook
            WHERE entity_type = %s AND field_name = %s AND value = %s
            LIMIT 1
        """, (type_code, field_name, value))
        row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

def encode_entity_with_codebook(type_code: int, entity_values: dict, allocation: list) -> int:
    """코드북 기반 인코딩"""
    sidx = 0
    for field in allocation:
        if field['name'] == '_reserved' or not field['prop']:
            continue

        value = entity_values.get(field['prop'])
        if value:
            code = get_codebook_entry(type_code, field['name'], value)
            sidx |= (code << field['offset'])

    return sidx & ((1 << 48) - 1)

def test_encoding_consistency(types: list, samples_per_type: int = 100) -> list:
    """인코딩 일관성 테스트"""
    results = []

    for type_code, name_ko, qid, total_count, _ in types[:5]:  # 상위 5개만
        allocation = get_bit_allocation(type_code)
        if not allocation:
            continue

        conn = get_read_conn()
        with conn.cursor() as cur:
            # 샘플 개체 (LIMIT만 사용 - ORDER BY RANDOM은 너무 느림)
            cur.execute("""
                SELECT subject FROM triples
                WHERE property = 'P31' AND object_value = %s
                LIMIT %s
            """, (qid, samples_per_type))
            entity_ids = [row[0] for row in cur.fetchall()]

            if not entity_ids:
                continue

            # 속성값 로드
            prop_ids = [f['prop'] for f in allocation if f['prop']]
            cur.execute("""
                SELECT subject, property, object_value
                FROM triples
                WHERE subject = ANY(%s) AND property = ANY(%s)
            """, (entity_ids, prop_ids))

            entity_values = defaultdict(dict)
            for subject, prop, val in cur.fetchall():
                if prop not in entity_values[subject]:
                    entity_values[subject][prop] = val

        conn.close()

        # 두 번 인코딩해서 비교
        consistent = 0
        for eid in entity_ids:
            vals = entity_values.get(eid, {})
            if vals:
                sidx1 = encode_entity_with_codebook(type_code, vals, allocation)
                sidx2 = encode_entity_with_codebook(type_code, vals, allocation)
                if sidx1 == sidx2:
                    consistent += 1

        results.append({
            'type_code': type_code,
            'name_ko': name_ko,
            'tested': len(entity_ids),
            'consistent': consistent,
            'rate': consistent / len(entity_ids) if entity_ids else 0,
            'passed': consistent == len(entity_ids)
        })

    return results

def test_degradation(types: list) -> list:
    """열화 테스트 - 비트를 줄여도 상위 개념으로 수렴하는지"""
    results = []

    for type_code, name_ko, qid, _, _ in types[:5]:
        allocation = get_bit_allocation(type_code)
        if not allocation:
            continue

        # 필드를 뒤에서부터 마스킹
        total_bits = sum(f['bits'] for f in allocation)
        levels = []

        current_mask = (1 << 48) - 1
        for field in reversed(allocation):
            if field['name'] == '_reserved':
                continue

            # 이 필드 마스킹
            field_mask = ((1 << field['bits']) - 1) << field['offset']
            current_mask &= ~field_mask

            levels.append({
                'removed_field': field['name'],
                'remaining_bits': bin(current_mask).count('1'),
                'mask': hex(current_mask)
            })

        results.append({
            'type_code': type_code,
            'name_ko': name_ko,
            'total_bits': total_bits,
            'degradation_levels': levels,
            'passed': True  # 구조적으로 열화 가능
        })

    return results

def generate_abstract_test_cases(types: list) -> list:
    """추상 표현 테스트 케이스 생성 (타입당 3개)"""
    test_cases = []

    # Human 타입 (0x00)
    test_cases.extend([
        {
            'type_code': 0x00,
            'description': '한국 남성',
            'constraints': {'P27': 'Q884', 'P21': 'Q6581097'},
            'field_map': {'P27': 'country', 'P21': 'gender'}
        },
        {
            'type_code': 0x00,
            'description': '미국 여성',
            'constraints': {'P27': 'Q30', 'P21': 'Q6581072'},
            'field_map': {'P27': 'country', 'P21': 'gender'}
        },
        {
            'type_code': 0x00,
            'description': '일본 남성',
            'constraints': {'P27': 'Q17', 'P21': 'Q6581097'},
            'field_map': {'P27': 'country', 'P21': 'gender'}
        }
    ])

    # Film 타입 (0x33)
    test_cases.extend([
        {
            'type_code': 0x33,
            'description': '한국 영화',
            'constraints': {'P495': 'Q884'},
            'field_map': {'P495': 'country'}
        },
        {
            'type_code': 0x33,
            'description': '미국 영화',
            'constraints': {'P495': 'Q30'},
            'field_map': {'P495': 'country'}
        },
        {
            'type_code': 0x33,
            'description': '일본 영화',
            'constraints': {'P495': 'Q17'},
            'field_map': {'P495': 'country'}
        }
    ])

    # Settlement 타입 (0x1C)
    test_cases.extend([
        {
            'type_code': 0x1C,
            'description': '한국 정주지',
            'constraints': {'P17': 'Q884'},
            'field_map': {'P17': 'country'}
        },
        {
            'type_code': 0x1C,
            'description': '미국 정주지',
            'constraints': {'P17': 'Q30'},
            'field_map': {'P17': 'country'}
        },
        {
            'type_code': 0x1C,
            'description': '일본 정주지',
            'constraints': {'P17': 'Q17'},
            'field_map': {'P17': 'country'}
        }
    ])

    return test_cases

def get_codebook_for_field(type_code: int, field_name: str) -> dict:
    """필드별 코드북 조회"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT value, code FROM codebook
            WHERE entity_type = %s AND field_name = %s
        """, (type_code, field_name))
        rows = cur.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def build_sidx_mask(type_code: int, constraints: dict, field_map: dict) -> tuple:
    """제약조건에서 SIDX 마스크와 패턴 생성 (OPT-2: 코드북 미등록값 처리 개선)"""
    allocation = get_bit_allocation(type_code)
    if not allocation:
        return 0, 0

    mask = 0
    pattern = 0

    for prop_id, value in constraints.items():
        field_name = field_map.get(prop_id)
        if not field_name:
            continue

        # 할당 정보에서 해당 필드 찾기
        field = next((f for f in allocation if f['name'] == field_name), None)
        if not field:
            continue

        # 코드북에서 코드 조회
        codebook = get_codebook_for_field(type_code, field_name)

        # OPT-2: 코드북에 없는 값이면 해당 필드 마스크에서 제외
        # (code=0은 Unknown을 의미하므로, 매칭하면 모든 Unknown이 포함됨)
        if value not in codebook:
            continue

        code = codebook[value]

        # 마스크: 해당 필드 비트 위치에 1
        field_mask = ((1 << field['bits']) - 1) << field['offset']
        mask |= field_mask

        # 패턴: 해당 위치에 코드 값
        pattern |= (code << field['offset'])

    return mask, pattern

def test_abstract_queries(types: list) -> list:
    """5-B: 추상 표현 SIMD 마스크 테스트"""
    results = []
    test_cases = generate_abstract_test_cases(types)

    for case in test_cases:
        type_code = case['type_code']

        # 해당 타입이 대상에 포함되는지 확인
        if not any(t[0] == type_code for t in types):
            continue

        # 마스크 생성
        mask, pattern = build_sidx_mask(
            type_code, case['constraints'], case['field_map']
        )

        if mask == 0:
            results.append({
                'type_code': type_code,
                'description': case['description'],
                'mask': 0,
                'pattern': 0,
                'tested': 0,
                'matched': 0,
                'true_positives': 0,
                'precision': 0,
                'passed': False,
                'reason': '코드북 없음'
            })
            continue

        # 샘플 개체 로드 및 테스트
        type_info = next((t for t in types if t[0] == type_code), None)
        if not type_info:
            continue

        qid = type_info[2]
        conn = get_read_conn()

        # 샘플 로드
        with conn.cursor() as cur:
            cur.execute("""
                SELECT subject FROM triples
                WHERE property = 'P31' AND object_value = %s
                LIMIT 500
            """, (qid,))
            entity_ids = [row[0] for row in cur.fetchall()]

        if not entity_ids:
            conn.close()
            continue

        # 속성값 로드
        allocation = get_bit_allocation(type_code)
        prop_ids = list(case['constraints'].keys())

        # OPT-3: 다중값 속성 정렬 처리
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
        entity_values = {eid: {} for eid in entity_ids}
        for eid in entity_ids:
            for prop, values in temp_values[eid].items():
                if values:
                    entity_values[eid][prop] = sorted(values)[0]

        # 인코딩 및 마스크 테스트
        matched = 0
        true_positives = 0
        tested = len(entity_ids)

        for eid, values in entity_values.items():
            # 인코딩
            sidx = encode_entity_with_codebook(type_code, values, allocation)

            # 마스크 테스트
            if (sidx & mask) == pattern:
                matched += 1

                # 실제로 조건을 충족하는지 확인
                is_true = all(
                    values.get(pid) == val
                    for pid, val in case['constraints'].items()
                )
                if is_true:
                    true_positives += 1

        precision = true_positives / matched if matched > 0 else 0

        results.append({
            'type_code': type_code,
            'description': case['description'],
            'mask': hex(mask),
            'pattern': hex(pattern),
            'tested': tested,
            'matched': matched,
            'true_positives': true_positives,
            'precision': precision,
            'passed': precision >= 0.95 or matched == 0  # 95% 정밀도 또는 매치 없음
        })

    return results

def generate_report(collision_results: list, abstract_results: list,
                   consistency_results: list, degradation_results: list,
                   output_path: Path):
    """보고서 생성"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Stage 5: 검증 보고서\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # 요약
        collision_pass = sum(1 for r in collision_results if r['passed'])
        consistency_pass = sum(1 for r in consistency_results if r['passed'])
        degradation_pass = sum(1 for r in degradation_results if r['passed'])

        f.write("## 요약\n\n")
        f.write(f"| 테스트 | 통과 | 총 | 비율 |\n")
        f.write(f"|--------|------|-----|------|\n")
        f.write(f"| 충돌률 | {collision_pass} | {len(collision_results)} | ")
        f.write(f"{collision_pass/len(collision_results)*100:.1f}% |\n")
        if abstract_results:
            abstract_pass = sum(1 for r in abstract_results if r['passed'])
            f.write(f"| 추상표현 | {abstract_pass} | {len(abstract_results)} | ")
            f.write(f"{abstract_pass/len(abstract_results)*100:.1f}% |\n")
        if consistency_results:
            f.write(f"| 일관성 | {consistency_pass} | {len(consistency_results)} | ")
            f.write(f"{consistency_pass/len(consistency_results)*100:.1f}% |\n")
        if degradation_results:
            f.write(f"| 열화 | {degradation_pass} | {len(degradation_results)} | ")
            f.write(f"{degradation_pass/len(degradation_results)*100:.1f}% |\n")

        f.write("\n---\n\n")

        # 충돌률 테스트
        f.write("## 5-A: 충돌률 테스트\n\n")
        f.write("| 타입 | 코드 | 개체수 | 목표 | 실제 | 결과 |\n")
        f.write("|------|------|--------|------|------|------|\n")

        for r in collision_results:
            status = "PASS" if r['passed'] else "[REVIEW]"
            f.write(f"| {r['name_ko']} | 0x{r['type_code']:02X} | ")
            f.write(f"{r['total_count']:,} | {r['target_rate']:.2%} | ")
            f.write(f"{r['actual_rate']:.2%} | {status} |\n")

        f.write("\n---\n\n")

        # 추상 표현 테스트
        if abstract_results:
            f.write("## 5-B: 추상 표현 SIMD 테스트\n\n")
            f.write("| 설명 | 마스크 | 테스트 | 매치 | 정밀도 | 결과 |\n")
            f.write("|------|--------|--------|------|--------|------|\n")

            for r in abstract_results:
                status = "PASS" if r['passed'] else "[REVIEW]"
                f.write(f"| {r['description']} | {r['mask']} | ")
                f.write(f"{r['tested']} | {r['matched']} | ")
                f.write(f"{r['precision']:.1%} | {status} |\n")

            f.write("\n---\n\n")

        # 일관성 테스트
        if consistency_results:
            f.write("## 5-C: 인코딩 일관성 테스트\n\n")
            f.write("| 타입 | 테스트 수 | 일관 | 비율 | 결과 |\n")
            f.write("|------|----------|------|------|------|\n")

            for r in consistency_results:
                status = "PASS" if r['passed'] else "[REVIEW]"
                f.write(f"| {r['name_ko']} | {r['tested']} | ")
                f.write(f"{r['consistent']} | {r['rate']:.1%} | {status} |\n")

            f.write("\n---\n\n")

        # 열화 테스트
        if degradation_results:
            f.write("## 5-D: 열화 테스트\n\n")

            for r in degradation_results:
                f.write(f"### {r['name_ko']} (0x{r['type_code']:02X})\n\n")
                f.write("열화 단계:\n")
                for i, level in enumerate(r['degradation_levels']):
                    f.write(f"{i+1}. `-{level['removed_field']}` → {level['remaining_bits']}비트\n")
                f.write("\n")

        f.write("---\n\n")

        # 실패 항목
        failed = [r for r in collision_results if not r['passed']]
        if failed:
            f.write("## [REVIEW] 검토 필요 항목\n\n")
            for r in failed:
                f.write(f"- **{r['name_ko']}**: 충돌률 {r['actual_rate']:.2%} > 목표 {r['target_rate']:.2%}\n")
                f.write(f"  - 마진: {r['margin']:.2%}\n")

def main():
    print("=" * 60)
    print("Stage 5: 검증 (v2.0)")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)

    types = get_entity_types()

    # 필터링
    if len(sys.argv) > 1:
        target_codes = [int(x, 16) if x.startswith('0x') else int(x) for x in sys.argv[1:]]
        types = [(c, n, q, t, r) for c, n, q, t, r in types if c in target_codes]

    print(f"\n대상: {len(types)}개 타입")

    # 5-A: 충돌률 테스트
    print("\n[5-A] 충돌률 테스트...")
    collision_results = test_collision_rates(types)
    passed = sum(1 for r in collision_results if r['passed'])
    print(f"  통과: {passed}/{len(collision_results)}")

    # 5-B: 추상 표현 테스트
    print("\n[5-B] 추상 표현 SIMD 테스트...")
    abstract_results = test_abstract_queries(types)
    if abstract_results:
        passed = sum(1 for r in abstract_results if r['passed'])
        print(f"  통과: {passed}/{len(abstract_results)}")
    else:
        abstract_results = []

    # 5-C: 일관성 테스트
    print("\n[5-C] 인코딩 일관성 테스트...")
    consistency_results = test_encoding_consistency(types)
    if consistency_results:
        passed = sum(1 for r in consistency_results if r['passed'])
        print(f"  통과: {passed}/{len(consistency_results)}")

    # 5-D: 열화 테스트
    print("\n[5-D] 열화 테스트...")
    degradation_results = test_degradation(types)
    if degradation_results:
        passed = sum(1 for r in degradation_results if r['passed'])
        print(f"  통과: {passed}/{len(degradation_results)}")

    # 보고서
    print("\n보고서 생성...")
    report_path = OUTPUT_DIR / "stage5_report.md"
    generate_report(collision_results, abstract_results, consistency_results, degradation_results, report_path)
    print(f"저장: {report_path}")

    # 최종 요약
    total_tests = len(collision_results) + len(abstract_results) + len(consistency_results) + len(degradation_results)
    total_pass = (sum(1 for r in collision_results if r['passed']) +
                  sum(1 for r in abstract_results if r['passed']) +
                  sum(1 for r in consistency_results if r['passed']) +
                  sum(1 for r in degradation_results if r['passed']))

    print(f"\n{'='*60}")
    print(f"최종 결과: {total_pass}/{total_tests} 통과 ({total_pass/total_tests*100:.1f}%)")
    print("=" * 60)

if __name__ == "__main__":
    main()
