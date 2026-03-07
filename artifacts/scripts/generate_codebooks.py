#!/usr/bin/env python3
"""
코드북 생성 스크립트

48비트 Attributes의 주요 필드별 코드북을 생성한다.
- DB 기반: country, occupation, language, genre (property_object_stats 사용)
- 사전 정의: era, constellation
"""

import json
from datetime import datetime
from pathlib import Path
import psycopg2

# 경로 설정
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
REFERENCES_DIR = PROJECT_DIR / "references"
OUTPUT_DIR = PROJECT_DIR / "output"

# DB 설정 (읽기 전용)
DB_CONN = "postgresql://geul_reader:test1224@localhost:5432/geuldev"


def get_conn():
    return psycopg2.connect(DB_CONN)


def get_label(qid: str, conn) -> str:
    """Q-ID의 영어 레이블 조회"""
    if not qid or not qid.startswith('Q'):
        return qid or ''

    with conn.cursor() as cur:
        cur.execute("""
            SELECT label FROM entity_labels
            WHERE entity_id = %s AND language = 'en'
            LIMIT 1
        """, (qid,))
        row = cur.fetchone()
    return row[0] if row else qid


def get_top_values_from_stats(property_ids: list, limit: int, conn) -> list:
    """property_object_stats에서 상위 값 추출 (여러 property 합산)"""
    placeholders = ','.join(['%s'] * len(property_ids))

    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT object_value, SUM(usage_count) as total_cnt
            FROM property_object_stats
            WHERE property_id IN ({placeholders})
              AND object_value LIKE 'Q%%'
            GROUP BY object_value
            ORDER BY total_cnt DESC
            LIMIT %s
        """, property_ids + [limit])
        rows = cur.fetchall()

    result = []
    for qid, cnt in rows:
        label = get_label(qid, conn)
        result.append({
            "qid": qid,
            "label_en": label,
            "count": int(cnt)
        })
    return result


def generate_country_codebook(conn) -> dict:
    """국가 코드북 (8비트, 256개) - P17 country, P27 country of citizenship"""
    print("Generating country codebook...")
    values = get_top_values_from_stats(['P17', 'P27'], 255, conn)

    # code 0 = Unknown
    entries = [{"code": 0, "qid": None, "label_en": "Unknown", "count": 0}]
    for i, v in enumerate(values):
        entries.append({
            "code": i + 1,
            "qid": v["qid"],
            "label_en": v["label_en"],
            "count": v["count"]
        })

    return {
        "bits": 8,
        "max_count": 256,
        "actual_count": len(entries),
        "source": "P17 (country), P27 (country of citizenship)",
        "values": entries
    }


def generate_occupation_codebook(conn) -> dict:
    """직업 코드북 (6비트, 64개) - P106 occupation"""
    print("Generating occupation codebook...")
    values = get_top_values_from_stats(['P106'], 63, conn)

    entries = [{"code": 0, "qid": None, "label_en": "Unknown", "count": 0}]
    for i, v in enumerate(values):
        entries.append({
            "code": i + 1,
            "qid": v["qid"],
            "label_en": v["label_en"],
            "count": v["count"]
        })

    return {
        "bits": 6,
        "max_count": 64,
        "actual_count": len(entries),
        "source": "P106 (occupation)",
        "values": entries
    }


def generate_language_codebook(conn) -> dict:
    """언어 코드북 (6비트, 64개) - P407 language of work, P1412 languages spoken"""
    print("Generating language codebook...")
    values = get_top_values_from_stats(['P407', 'P1412'], 63, conn)

    entries = [{"code": 0, "qid": None, "label_en": "Unknown", "count": 0}]
    for i, v in enumerate(values):
        entries.append({
            "code": i + 1,
            "qid": v["qid"],
            "label_en": v["label_en"],
            "count": v["count"]
        })

    return {
        "bits": 6,
        "max_count": 64,
        "actual_count": len(entries),
        "source": "P407 (language of work), P1412 (languages spoken)",
        "values": entries
    }


def generate_genre_codebook(conn) -> dict:
    """장르 코드북 (6비트, 64개) - P136 genre"""
    print("Generating genre codebook...")
    values = get_top_values_from_stats(['P136'], 63, conn)

    entries = [{"code": 0, "qid": None, "label_en": "Unknown", "count": 0}]
    for i, v in enumerate(values):
        entries.append({
            "code": i + 1,
            "qid": v["qid"],
            "label_en": v["label_en"],
            "count": v["count"]
        })

    return {
        "bits": 6,
        "max_count": 64,
        "actual_count": len(entries),
        "source": "P136 (genre)",
        "values": entries
    }


def generate_era_codebook() -> dict:
    """시대 코드북 (4비트, 16개) - 사전 정의"""
    print("Generating era codebook (predefined)...")

    eras = [
        {"code": 0, "label_en": "Unknown", "label_ko": "알 수 없음", "range": None},
        {"code": 1, "label_en": "Prehistoric", "label_ko": "선사시대", "range": "before 3000 BCE"},
        {"code": 2, "label_en": "Ancient Near East", "label_ko": "고대 근동", "range": "3000-500 BCE"},
        {"code": 3, "label_en": "Classical Antiquity", "label_ko": "고전 고대", "range": "800 BCE - 500 CE"},
        {"code": 4, "label_en": "Late Antiquity", "label_ko": "후기 고대", "range": "200-700 CE"},
        {"code": 5, "label_en": "Early Medieval", "label_ko": "초기 중세", "range": "500-1000 CE"},
        {"code": 6, "label_en": "High Medieval", "label_ko": "성기 중세", "range": "1000-1300 CE"},
        {"code": 7, "label_en": "Late Medieval", "label_ko": "후기 중세", "range": "1300-1500 CE"},
        {"code": 8, "label_en": "Renaissance", "label_ko": "르네상스", "range": "1400-1600 CE"},
        {"code": 9, "label_en": "Early Modern", "label_ko": "근세", "range": "1500-1800 CE"},
        {"code": 10, "label_en": "Industrial Era", "label_ko": "산업화 시대", "range": "1760-1914 CE"},
        {"code": 11, "label_en": "Modern Era", "label_ko": "현대 전기", "range": "1914-1945 CE"},
        {"code": 12, "label_en": "Cold War Era", "label_ko": "냉전 시대", "range": "1945-1991 CE"},
        {"code": 13, "label_en": "Post-Cold War", "label_ko": "탈냉전 시대", "range": "1991-2010 CE"},
        {"code": 14, "label_en": "Contemporary", "label_ko": "동시대", "range": "2010-present"},
        {"code": 15, "label_en": "Future", "label_ko": "미래", "range": "future"}
    ]

    return {
        "bits": 4,
        "max_count": 16,
        "actual_count": len(eras),
        "source": "predefined (historical periodization)",
        "values": eras
    }


def generate_constellation_codebook() -> dict:
    """별자리 코드북 (7비트, 88개) - IAU 공식 88개 별자리"""
    print("Generating constellation codebook (predefined)...")

    # IAU 88 constellations (알파벳 순)
    constellations_data = [
        ("Andromeda", "안드로메다"),
        ("Antlia", "공기펌프자리"),
        ("Apus", "극락조자리"),
        ("Aquarius", "물병자리"),
        ("Aquila", "독수리자리"),
        ("Ara", "제단자리"),
        ("Aries", "양자리"),
        ("Auriga", "마차부자리"),
        ("Bootes", "목동자리"),
        ("Caelum", "조각칼자리"),
        ("Camelopardalis", "기린자리"),
        ("Cancer", "게자리"),
        ("Canes Venatici", "사냥개자리"),
        ("Canis Major", "큰개자리"),
        ("Canis Minor", "작은개자리"),
        ("Capricornus", "염소자리"),
        ("Carina", "용골자리"),
        ("Cassiopeia", "카시오페이아"),
        ("Centaurus", "센타우루스자리"),
        ("Cepheus", "세페우스자리"),
        ("Cetus", "고래자리"),
        ("Chamaeleon", "카멜레온자리"),
        ("Circinus", "컴퍼스자리"),
        ("Columba", "비둘기자리"),
        ("Coma Berenices", "머리털자리"),
        ("Corona Australis", "남쪽왕관자리"),
        ("Corona Borealis", "북쪽왕관자리"),
        ("Corvus", "까마귀자리"),
        ("Crater", "컵자리"),
        ("Crux", "남십자자리"),
        ("Cygnus", "백조자리"),
        ("Delphinus", "돌고래자리"),
        ("Dorado", "황새치자리"),
        ("Draco", "용자리"),
        ("Equuleus", "조랑말자리"),
        ("Eridanus", "에리다누스자리"),
        ("Fornax", "화로자리"),
        ("Gemini", "쌍둥이자리"),
        ("Grus", "두루미자리"),
        ("Hercules", "헤라클레스자리"),
        ("Horologium", "시계자리"),
        ("Hydra", "바다뱀자리"),
        ("Hydrus", "물뱀자리"),
        ("Indus", "인디언자리"),
        ("Lacerta", "도마뱀자리"),
        ("Leo", "사자자리"),
        ("Leo Minor", "작은사자자리"),
        ("Lepus", "토끼자리"),
        ("Libra", "천칭자리"),
        ("Lupus", "이리자리"),
        ("Lynx", "살쾡이자리"),
        ("Lyra", "거문고자리"),
        ("Mensa", "테이블산자리"),
        ("Microscopium", "현미경자리"),
        ("Monoceros", "외뿔소자리"),
        ("Musca", "파리자리"),
        ("Norma", "직각자자리"),
        ("Octans", "팔분의자리"),
        ("Ophiuchus", "뱀주인자리"),
        ("Orion", "오리온자리"),
        ("Pavo", "공작자리"),
        ("Pegasus", "페가수스자리"),
        ("Perseus", "페르세우스자리"),
        ("Phoenix", "불사조자리"),
        ("Pictor", "화가자리"),
        ("Pisces", "물고기자리"),
        ("Piscis Austrinus", "남쪽물고기자리"),
        ("Puppis", "고물자리"),
        ("Pyxis", "나침반자리"),
        ("Reticulum", "그물자리"),
        ("Sagitta", "화살자리"),
        ("Sagittarius", "궁수자리"),
        ("Scorpius", "전갈자리"),
        ("Sculptor", "조각가자리"),
        ("Scutum", "방패자리"),
        ("Serpens", "뱀자리"),
        ("Sextans", "육분의자리"),
        ("Taurus", "황소자리"),
        ("Telescopium", "망원경자리"),
        ("Triangulum", "삼각형자리"),
        ("Triangulum Australe", "남쪽삼각형자리"),
        ("Tucana", "큰부리새자리"),
        ("Ursa Major", "큰곰자리"),
        ("Ursa Minor", "작은곰자리"),
        ("Vela", "돛자리"),
        ("Virgo", "처녀자리"),
        ("Volans", "날치자리"),
        ("Vulpecula", "여우자리")
    ]

    entries = [{"code": 0, "label_en": "Unknown", "label_ko": "알 수 없음"}]
    for i, (en, ko) in enumerate(constellations_data):
        entries.append({
            "code": i + 1,
            "label_en": en,
            "label_ko": ko
        })

    return {
        "bits": 7,
        "max_count": 128,
        "actual_count": len(entries),
        "source": "predefined (IAU 88 constellations)",
        "note": "code 89-127 reserved for future use",
        "values": entries
    }


def main():
    print("=" * 60)
    print("Generating Codebooks for GEUL Entity SIDX")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)

    conn = get_conn()

    codebooks = {
        "version": "v1.0",
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": "GEUL Entity SIDX 48-bit Attributes codebooks",
        "codebooks": {}
    }

    # DB 기반 코드북
    codebooks["codebooks"]["country"] = generate_country_codebook(conn)
    codebooks["codebooks"]["occupation"] = generate_occupation_codebook(conn)
    codebooks["codebooks"]["language"] = generate_language_codebook(conn)
    codebooks["codebooks"]["genre"] = generate_genre_codebook(conn)

    conn.close()

    # 사전 정의 코드북
    codebooks["codebooks"]["era"] = generate_era_codebook()
    codebooks["codebooks"]["constellation"] = generate_constellation_codebook()

    # 저장
    output_path = REFERENCES_DIR / "codebooks.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(codebooks, f, ensure_ascii=False, indent=2)

    print(f"\nSaved: {output_path}")

    # 요약
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    for name, cb in codebooks["codebooks"].items():
        print(f"  {name}: {cb['actual_count']} values ({cb['bits']} bits, max {cb['max_count']})")

    print("\nDone!")


if __name__ == "__main__":
    main()
