#!/usr/bin/env python3
"""
Stage 4: 코드북 생성 (v2.0)

Stage 3의 비트 할당을 기반으로 각 필드의 코드북을 생성한다.
계층적 필드는 부모 값별로 별도 코드 테이블을 생성한다.
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import psycopg2

# 경로 설정
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
REFERENCES_DIR = PROJECT_DIR / "references"
OUTPUT_DIR = PROJECT_DIR / "output1"
CODEBOOK_DIR = OUTPUT_DIR / "codebooks"

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

def init_work_tables():
    """테이블 생성"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS codebook (
                entity_type  INTEGER NOT NULL,
                field_name   TEXT NOT NULL,
                parent_value TEXT,
                code         INTEGER NOT NULL,
                value        TEXT NOT NULL,
                label        TEXT,
                frequency    INTEGER DEFAULT 0,
                updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (entity_type, field_name, parent_value, code)
            );

            CREATE INDEX IF NOT EXISTS idx_codebook_lookup
            ON codebook(entity_type, field_name, value);
        """)
    conn.commit()
    conn.close()

def get_entity_types() -> list:
    """처리할 타입 목록"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT type_code, name_ko, qid FROM entity_type_map
            WHERE sample_count > 0 ORDER BY type_code
        """)
        types = [(row[0], row[1], row[2]) for row in cur.fetchall()]
    conn.close()
    return types

def get_bit_allocation(type_code: int) -> list:
    """비트 할당 조회"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT field_name, property_id, bit_width, parent_field
            FROM bit_allocation
            WHERE entity_type = %s
            ORDER BY bit_offset
        """, (type_code,))
        rows = cur.fetchall()
    conn.close()

    return [{
        'field_name': row[0],
        'property_id': row[1],
        'bits': row[2],
        'parent': row[3]
    } for row in rows]

def get_value_counts(qid: str, property_id: str, sample_size: int = 20000) -> Counter:
    """속성값 빈도 조회"""
    conn = get_read_conn()
    with conn.cursor() as cur:
        # 해당 타입의 개체들
        cur.execute("""
            SELECT t2.object_value
            FROM triples t1
            JOIN triples t2 ON t1.subject = t2.subject
            WHERE t1.property = 'P31' AND t1.object_value = %s
              AND t2.property = %s
            LIMIT %s
        """, (qid, property_id, sample_size))
        values = [row[0] for row in cur.fetchall() if row[0]]
    conn.close()
    return Counter(values)

def get_hierarchical_counts(qid: str, parent_prop: str, child_prop: str,
                           sample_size: int = 20000) -> dict:
    """부모-자식 값 쌍 빈도 조회"""
    conn = get_read_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT tp.object_value as parent_val, tc.object_value as child_val
            FROM triples t
            JOIN triples tp ON t.subject = tp.subject AND tp.property = %s
            JOIN triples tc ON t.subject = tc.subject AND tc.property = %s
            WHERE t.property = 'P31' AND t.object_value = %s
            LIMIT %s
        """, (parent_prop, child_prop, qid, sample_size))
        rows = cur.fetchall()
    conn.close()

    result = defaultdict(Counter)
    for parent_val, child_val in rows:
        if parent_val and child_val:
            result[parent_val][child_val] += 1
    return result

def get_label(qid_or_value: str) -> str:
    """Q-ID의 레이블 조회"""
    if not qid_or_value or not qid_or_value.startswith('Q'):
        return qid_or_value or ''

    conn = get_read_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT label FROM entity_labels
            WHERE entity_id = %s AND language = 'en'
            LIMIT 1
        """, (qid_or_value,))
        row = cur.fetchone()
    conn.close()
    return row[0] if row else qid_or_value

def generate_codebook(type_code: int, qid: str, allocation: list) -> list:
    """코드북 생성"""
    codebooks = []

    for field in allocation:
        if field['field_name'] == '_reserved' or not field['property_id']:
            continue

        max_codes = 2 ** field['bits']
        reserved_codes = max(1, int(max_codes * 0.1))  # 10% 예약
        available_codes = max_codes - reserved_codes - 1  # 0은 Unknown

        if field['parent']:
            # 계층적 필드: 부모 값별로 코드북 생성
            # parent는 property_id이므로 property_id로 매칭
            parent_field = next((f for f in allocation if f['property_id'] == field['parent']), None)
            if parent_field and parent_field['property_id']:
                hier_counts = get_hierarchical_counts(
                    qid, parent_field['property_id'], field['property_id']
                )

                for parent_val, child_counts in hier_counts.items():
                    parent_label = get_label(parent_val)
                    entries = []

                    # Unknown 코드
                    entries.append({
                        'code': 0,
                        'value': '_unknown',
                        'label': 'Unknown',
                        'frequency': 0
                    })

                    # 빈도 순 코드 할당
                    for i, (val, freq) in enumerate(child_counts.most_common(available_codes)):
                        entries.append({
                            'code': i + 1,
                            'value': val,
                            'label': get_label(val),
                            'frequency': freq
                        })

                    codebooks.append({
                        'field_name': field['field_name'],
                        'parent_value': parent_val,
                        'parent_label': parent_label,
                        'entries': entries
                    })
        else:
            # 독립 필드
            value_counts = get_value_counts(qid, field['property_id'])
            entries = []

            # Unknown 코드
            entries.append({
                'code': 0,
                'value': '_unknown',
                'label': 'Unknown',
                'frequency': 0
            })

            # 빈도 순 코드 할당
            for i, (val, freq) in enumerate(value_counts.most_common(available_codes)):
                entries.append({
                    'code': i + 1,
                    'value': val,
                    'label': get_label(val),
                    'frequency': freq
                })

            codebooks.append({
                'field_name': field['field_name'],
                'parent_value': '_root',
                'parent_label': None,
                'entries': entries
            })

    return codebooks

def save_codebook(type_code: int, codebooks: list):
    """코드북 DB 저장"""
    conn = get_write_conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM codebook WHERE entity_type = %s", (type_code,))

        for cb in codebooks:
            for entry in cb['entries']:
                cur.execute("""
                    INSERT INTO codebook
                    (entity_type, field_name, parent_value, code, value, label, frequency, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    type_code, cb['field_name'], cb['parent_value'],
                    entry['code'], entry['value'], entry['label'], entry['frequency']
                ))

    conn.commit()
    conn.close()

def save_codebook_markdown(type_code: int, name_ko: str, codebooks: list, output_dir: Path):
    """코드북 마크다운 저장"""
    path = output_dir / f"codebook_{type_code:02X}_{name_ko}.md"

    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"# {name_ko} (0x{type_code:02X}) 코드북\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for cb in codebooks:
            if cb['parent_value'] == '_root':
                f.write(f"## {cb['field_name']}\n\n")
            else:
                f.write(f"## {cb['field_name']} (when parent = {cb['parent_label']})\n\n")

            f.write("| Code | Value | Label | Freq |\n")
            f.write("|------|-------|-------|------|\n")

            for entry in cb['entries'][:50]:  # 상위 50개만
                val = entry['value'][:30] if entry['value'] else ''
                label = (entry['label'] or '')[:30]
                f.write(f"| {entry['code']} | {val} | {label} | {entry['frequency']:,} |\n")

            if len(cb['entries']) > 50:
                f.write(f"\n*... and {len(cb['entries']) - 50} more entries*\n")

            f.write("\n---\n\n")

def generate_report(all_results: list, output_path: Path):
    """보고서 생성"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Stage 4: 코드북 생성 보고서\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 요약\n\n")
        f.write("| 타입 | 코드 | 필드 수 | 코드북 수 | 총 엔트리 |\n")
        f.write("|------|------|--------|----------|----------|\n")

        for r in all_results:
            total_entries = sum(len(cb['entries']) for cb in r['codebooks'])
            f.write(f"| {r['name_ko']} | 0x{r['type_code']:02X} | ")
            f.write(f"{len(r['allocation'])} | {len(r['codebooks'])} | {total_entries:,} |\n")

        f.write("\n---\n\n")

        f.write("## 코드북 파일\n\n")
        for r in all_results:
            f.write(f"- `codebooks/codebook_{r['type_code']:02X}_{r['name_ko']}.md`\n")

def main():
    print("=" * 60)
    print("Stage 4: 코드북 생성 (v2.0)")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)
    CODEBOOK_DIR.mkdir(exist_ok=True)
    init_work_tables()

    types = get_entity_types()

    # 필터링
    if len(sys.argv) > 1:
        target_codes = [int(x, 16) if x.startswith('0x') else int(x) for x in sys.argv[1:]]
        types = [(c, n, q) for c, n, q in types if c in target_codes]

    print(f"\n대상: {len(types)}개 타입")

    all_results = []

    for i, (type_code, name_ko, qid) in enumerate(types):
        print(f"\n[{i+1}/{len(types)}] {name_ko} (0x{type_code:02X})")

        allocation = get_bit_allocation(type_code)
        if not allocation:
            print("  할당 없음, 건너뜀")
            continue

        print(f"  코드북 생성 중...")
        codebooks = generate_codebook(type_code, qid, allocation)
        print(f"  코드북: {len(codebooks)}개")

        # 저장
        save_codebook(type_code, codebooks)
        save_codebook_markdown(type_code, name_ko, codebooks, CODEBOOK_DIR)

        all_results.append({
            'type_code': type_code,
            'name_ko': name_ko,
            'allocation': allocation,
            'codebooks': codebooks
        })

    # 보고서
    print("\n보고서 생성...")
    report_path = OUTPUT_DIR / "stage4_report.md"
    generate_report(all_results, report_path)
    print(f"저장: {report_path}")

    print("\n완료!")

if __name__ == "__main__":
    main()
