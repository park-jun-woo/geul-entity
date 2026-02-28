# 미분류 타입 분석 및 매핑 계획

**분석일**: 2026-02-01
**분석자**: Analyst + Ontologist
**버전**: v1.0

---

## 요약

| 항목 | 개체수 | 비율 |
|------|--------|------|
| 위키데이터 전체 | 117,419,925 | 100% |
| 64개 타입 직접 커버 | 36,295,074 | 30.9% |
| 기존 타입으로 흡수 가능 | 72,010,196 | 61.3% |
| **Wikimedia 내부 (제외)** | 8,565,353 | 7.3% |
| **실 커버리지** | 108,854,572 | 92.7% |

---

## 1. Wikimedia 내부 타입 (제외 대상: 8.6M)

SIDX 인코딩 대상에서 **제외**. 위키 시스템 내부 구조이며 실세계 개체가 아님.

| QID | 개체수 | 레이블 | 제외 사유 |
|-----|--------|--------|-----------|
| Q4167836 | 5,698,822 | Wikimedia category | 분류 페이지 |
| Q4167410 | 1,517,308 | Wikimedia disambiguation page | 동음이의 페이지 |
| Q11266439 | 830,519 | Wikimedia template | 템플릿 |
| Q13406463 | 378,180 | Wikimedia list article | 목록 문서 |
| Q115595777 | 140,524 | taxonomy template | 분류 템플릿 |

---

## 2. 기존 타입으로 흡수 (72.0M)

### 2.1 Document (0x31) 흡수: 47.8M

`doc_type` 필드(5비트, 32개 값)로 하위 유형 구분.

| QID | 개체수 | 레이블 | doc_type 코드 |
|-----|--------|--------|--------------|
| Q13442814 | 45,216,368 | scholarly article | 0x01 |
| Q13433827 | 642,974 | encyclopedia article | 0x02 |
| Q871232 | 513,039 | editorial | 0x03 |
| Q17633526 | 296,002 | Wikinews article | 0x04 |
| Q2782326 | 187,462 | case report | 0x05 |
| Q19389637 | 181,805 | biographical article | 0x06 |
| Q47461344 | 170,007 | written work | 0x07 |
| Q1580166 | 158,057 | dictionary entry | 0x08 |
| Q191067 | 155,529 | article | 0x09 |
| Q5633421 | 99,940 | scientific journal | 0x0A |
| Q87167 | 98,681 | manuscript | 0x0B |
| Q187685 | 94,650 | doctoral thesis | 0x0C |

**합계**: 47,814,514

### 2.2 Star (0x0C) 흡수: 4.8M

천체 관측 소스는 본질적으로 항성 또는 항성계. `spectral_type` 또는 `flags` 필드로 구분.

| QID | 개체수 | 레이블 | 매핑 타입 | 구분 필드 |
|-----|--------|--------|----------|-----------|
| Q67206691 | 2,621,805 | infrared source | Star | flags[IR] |
| Q1931185 | 396,880 | astronomical radio source | Star | flags[Radio] |
| Q2247863 | 306,766 | high proper-motion star | Star | pm_class |
| Q1457376 | 298,485 | eclipsing binary star | Star | flags[Binary] |
| Q2154519 | 157,565 | astrophysical X-ray source | Star | flags[X-ray] |
| Q1153690 | 101,271 | long-period variable star | Star | flags[Variable] |
| Q726242 | 96,968 | RR Lyrae variable | Star | flags[Variable] |

**합계**: 3,979,740

### 2.3 Settlement/Village (0x1C, 0x1D) 흡수: 1.3M

국가별 마을 유형은 Village로 통합.

| QID | 개체수 | 레이블 | 매핑 타입 |
|-----|--------|--------|----------|
| Q13100073 | 592,626 | village of China | Village (0x1D) |
| Q56436498 | 154,095 | village in India | Village (0x1D) |
| Q985488 | 96,640 | residential community | Settlement (0x1C) |
| Q61443690 | 129,183 | branch post office | Building (0x24) |

**합계 (장소)**: 843,361

### 2.4 지형 추가: Valley, Watercourse

현재 64개 타입에 Valley가 없음. **Stream (0x18)**으로 흡수 또는 새 타입 필요.

| QID | 개체수 | 레이블 | 권장 매핑 |
|-----|--------|--------|----------|
| Q355304 | 174,789 | watercourse | Stream (0x18) |
| Q39816 | 134,922 | valley | Hill (0x15) 또는 Other |

### 2.5 Building (0x24) 흡수: 0.4M

| QID | 개체수 | 레이블 | 매핑 타입 |
|-----|--------|--------|----------|
| Q1080794 | 188,771 | public school | School (0x26) |
| Q27686 | 131,503 | hotel | Building (0x24) |
| Q55488 | 113,556 | railway station | Structure (0x28) |

**합계**: 433,830

### 2.6 Painting/창작물 (0x30) 흡수: 2.0M

| QID | 개체수 | 레이블 | 매핑 타입 |
|-----|--------|--------|----------|
| Q2668072 | 504,230 | collection | Other (0x3F) |
| Q2342494 | 371,472 | collectible | Other (0x3F) |
| Q113813711 | 214,456 | coin type | Other (0x3F) |
| Q98276829 | 163,839 | porcelain ware | Painting (0x30) |
| Q11060274 | 144,901 | print | Painting (0x30) |
| Q18593264 | 132,519 | item of collection | Other (0x3F) |
| Q860861 | 125,054 | sculpture | Painting (0x30) |
| Q93184 | 122,863 | drawing | Painting (0x30) |
| Q134556 | 115,325 | single (음반) | Album (0x34) |
| Q5185279 | 106,076 | poem | LiteraryWork (0x32) |

### 2.7 Organization (0x2C) 흡수

| QID | 개체수 | 레이블 | 매핑 타입 |
|-----|--------|--------|----------|
| Q215380 | 95,816 | musical group | Organization (0x2C) |

### 2.8 Taxon (0x01) 흡수

| QID | 개체수 | 레이블 | 매핑 타입 |
|-----|--------|--------|----------|
| Q23038290 | 116,450 | fossil taxon | Taxon (0x01) |
| Q427087 | 98,747 | non-coding RNA | Gene (0x02) |

### 2.9 Chemical (0x08) 흡수

| QID | 개체수 | 레이블 | 매핑 타입 |
|-----|--------|--------|----------|
| Q59199015 | 148,411 | group of stereoisomers | Compound (0x09) |

---

## 3. 새로운 분류 필요 (수학/추상 개념)

현재 64개 타입에 수학 개념 타입이 없음. **Other (0x3F)** 또는 새 카테고리 필요.

| QID | 개체수 | 레이블 | 권장 처리 |
|-----|--------|--------|----------|
| Q47150325 | 201,356 | calendar day of a given year | **Meta** 타입 신설 권장 |
| Q29654788 | 161,479 | Unicode character | **Meta** 타입 신설 권장 |
| Q49008 | 136,820 | prime number | Other (0x3F) |
| Q28920044 | 121,221 | positive integer | Other (0x3F) |
| Q50707 | 95,193 | composite number | Other (0x3F) |

**합계**: 716,069

### 권장안: 0x3F_Other 활용

Other 타입의 48비트 스키마를 다음과 같이 설계:

```
0x3F_Other (기타):
  subtype(8):   수학(01), 시간(02), 문자(03), 제품(04), ...
  generic1(8):  서브타입별 해석
  generic2(8):  서브타입별 해석
  generic3(8):  서브타입별 해석
  generic4(8):  서브타입별 해석
  generic5(8):  서브타입별 해석
```

---

## 4. 기타 미분류 (검토 필요)

| QID | 개체수 | 레이블 | 권장 처리 |
|-----|--------|--------|----------|
| Q3331189 | 729,756 | version, edition or translation | Document (0x31) |
| Q30612 | 391,919 | clinical trial | Event (0x3D) |
| Q4164871 | 128,080 | position | Other (0x3F) |
| Q815382 | 109,676 | meta-analysis | Document (0x31) |
| Q2065736 | 107,479 | cultural property | Building (0x24) 또는 Painting |
| Q7604686 | 100,092 | UK Statutory Instrument | Document (0x31) |
| Q57733494 | 100,495 | badminton event | SportsSeason (0x3C) |

---

## 5. 최종 커버리지 계산

```
위키데이터 전체:           117,419,925  (100.0%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wikimedia 내부 (제외):       8,565,353  (  7.3%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SIDX 대상:               108,854,572  (100.0%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
64개 타입 직접 커버:        36,295,074  ( 33.3%)
기존 타입 흡수:            71,294,127  ( 65.5%)
수학/추상 → Other:            716,069  (  0.7%)
기타 → 매핑:               ~549,302  (  0.5%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
최종 커버리지:            108,854,572  (100.0%)
```

---

## 6. 필요 조치 목록

### 6.1 type_mapping.json 생성 필요

하위 QID → 64개 타입 매핑 테이블:

```json
{
  "Q13442814": {"target": "0x31", "subtype_field": "doc_type", "subtype_value": 1},
  "Q67206691": {"target": "0x0C", "flag_field": "flags", "flag_bit": "IR"},
  "Q13100073": {"target": "0x1D"},
  ...
}
```

### 6.2 type_schemas.json 업데이트

- Document: `doc_type` 코드값 추가 (scholarly article = 0x01 등)
- Star: `flags` 필드에 IR, Radio, X-ray, Binary, Variable 비트 정의
- Other (0x3F): subtype 분류 코드 정의

### 6.3 인코더 로직

```python
def get_entity_type(qid, p31_values):
    # 1. 직접 매핑 확인
    if p31_values & DIRECT_64_TYPES:
        return direct_mapping[p31_value]

    # 2. 하위 타입 매핑 확인
    for p31 in p31_values:
        if p31 in type_mapping:
            return type_mapping[p31]

    # 3. P279 (subclass of) 체인 탐색
    for p31 in p31_values:
        parent = get_parent_class(p31)
        if parent in type_mapping:
            return type_mapping[parent]

    # 4. 폴백: Other
    return 0x3F
```

---

## 7. 결론

| 분류 | 개체수 | 처리 방식 |
|------|--------|-----------|
| 64개 직접 커버 | 36.3M | 기존 스키마 |
| 흡수 (Document 등) | 71.3M | 기존 타입 + subtype 필드 |
| Other 폴백 | 1.2M | 0x3F + subtype 분류 |
| **제외 (Wikimedia)** | 8.6M | SIDX 미생성 |
| **총 SIDX 대상** | 108.9M | 100% 커버 |

**Wikimedia 내부 타입만 제외하고, 나머지 100%는 SIDX 인코딩 가능.**
