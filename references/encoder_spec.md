# GEUL Entity SIDX 인코더 명세서

**버전:** v1.0
**작성일:** 2026-02-01
**범위:** Wikidata Entity → 64비트 SIDX 인코딩
**상태:** 설계 완료

---

## 1. 개요

### 1.1 목적

Wikidata 개체(Q-ID)를 64비트 SIDX(Semantic IDentifier eXtended)로 인코딩하는 알고리즘을 정의한다.

### 1.2 전체 파이프라인

```
┌─────────────────┐    ┌──────────────┐    ┌────────────────┐    ┌──────────────────┐    ┌─────────────┐
│ Wikidata Entity │ -> │ P31 분석     │ -> │ EntityType 결정│ -> │ Attributes 추출  │ -> │ SIDX 조립   │
│ (Q-ID)          │    │ (instance of)│    │ (6비트)        │    │ (48비트)         │    │ (64비트)    │
└─────────────────┘    └──────────────┘    └────────────────┘    └──────────────────┘    └─────────────┘
```

### 1.3 SIDX 구조 (64비트)

```
1st WORD (bit 1-16):
┌─────────┬──────┬────────────┐
│ Prefix  │ Mode │ EntityType │
│  7bit   │ 3bit │   6bit     │
└─────────┴──────┴────────────┘

2nd WORD (bit 17-32): Attributes 상위 16비트
3rd WORD (bit 33-48): Attributes 중위 16비트
4th WORD (bit 49-64): Attributes 하위 16비트
```

---

## 2. P31 → EntityType 라우팅

### 2.1 라우팅 우선순위

```
1. 직접 매핑 (64개 기본 타입 QID)
2. 하위 타입 매핑 (type_mapping.json)
3. P279 체인 탐색 (subclass of)
4. 폴백 → Other (0x3F)
```

### 2.2 직접 매핑 (64개 타입)

P31 값이 64개 EntityType QID와 정확히 일치하는 경우.

```python
DIRECT_TYPE_MAP = {
    "Q5": 0x00,           # Human
    "Q16521": 0x01,       # Taxon
    "Q7187": 0x02,        # Gene
    "Q8054": 0x03,        # Protein
    "Q21014462": 0x04,    # CellLine
    "Q101352": 0x05,      # FamilyName
    "Q202444": 0x06,      # GivenName
    "Q15632617": 0x07,    # FictionalCharacter
    "Q113145171": 0x08,   # Chemical
    "Q11173": 0x09,       # Compound
    "Q7946": 0x0A,        # Mineral
    "Q12140": 0x0B,       # Drug
    "Q523": 0x0C,         # Star
    "Q318": 0x0D,         # Galaxy
    "Q3863": 0x0E,        # Asteroid
    "Q83373": 0x0F,       # Quasar
    "Q634": 0x10,         # Planet
    "Q12057": 0x11,       # Nebula
    "Q168845": 0x12,      # StarCluster
    "Q2537": 0x13,        # Moon
    "Q8502": 0x14,        # Mountain
    "Q54050": 0x15,       # Hill
    "Q4022": 0x16,        # River
    "Q23397": 0x17,       # Lake
    "Q47521": 0x18,       # Stream
    "Q23442": 0x19,       # Island
    "Q39594": 0x1A,       # Bay
    "Q35509": 0x1B,       # Cave
    "Q486972": 0x1C,      # Settlement
    "Q532": 0x1D,         # Village
    "Q5084": 0x1E,        # Hamlet
    "Q79007": 0x1F,       # Street
    "Q39614": 0x20,       # Cemetery
    "Q15284": 0x21,       # AdminRegion
    "Q22698": 0x22,       # Park
    "Q473972": 0x23,      # ProtectedArea
    "Q41176": 0x24,       # Building
    "Q16970": 0x25,       # Church
    "Q9842": 0x26,        # School
    "Q3947": 0x27,        # House
    "Q811979": 0x28,      # Structure
    "Q1076486": 0x29,     # SportsVenue
    "Q23413": 0x2A,       # Castle
    "Q12280": 0x2B,       # Bridge
    "Q43229": 0x2C,       # Organization
    "Q4830453": 0x2D,     # Business
    "Q7278": 0x2E,        # PoliticalParty
    "Q847017": 0x2F,      # SportsTeam
    "Q3305213": 0x30,     # Painting
    "Q49848": 0x31,       # Document
    "Q7725634": 0x32,     # LiteraryWork
    "Q11424": 0x33,       # Film
    "Q482994": 0x34,      # Album
    "Q105543609": 0x35,   # MusicalWork
    "Q21191270": 0x36,    # TVEpisode
    "Q7889": 0x37,        # VideoGame
    "Q5398426": 0x38,     # TVSeries
    "Q43305660": 0x39,    # Patent
    "Q7397": 0x3A,        # Software
    "Q35127": 0x3B,       # Website
    "Q27020041": 0x3C,    # SportsSeason
    "Q1656682": 0x3D,     # Event
    "Q40231": 0x3E,       # Election
}
```

### 2.3 하위 타입 매핑

P31 값이 직접 매핑에 없지만, 알려진 하위 타입인 경우.

```python
SUBTYPE_MAP = {
    # Document 하위 타입
    "Q13442814": {"type": 0x31, "field": "doc_type", "value": 1},   # scholarly article
    "Q13433827": {"type": 0x31, "field": "doc_type", "value": 2},   # encyclopedia article
    "Q871232": {"type": 0x31, "field": "doc_type", "value": 3},     # editorial
    "Q17633526": {"type": 0x31, "field": "doc_type", "value": 4},   # Wikinews article
    "Q187685": {"type": 0x31, "field": "doc_type", "value": 12},    # doctoral thesis

    # Star 하위 타입 (플래그 설정)
    "Q67206691": {"type": 0x0C, "flag": "IR"},           # infrared source
    "Q1931185": {"type": 0x0C, "flag": "Radio"},         # radio source
    "Q2247863": {"type": 0x0C, "flag": "HighPM"},        # high proper-motion star
    "Q1457376": {"type": 0x0C, "flag": "Binary"},        # eclipsing binary
    "Q2154519": {"type": 0x0C, "flag": "X-ray"},         # X-ray source
    "Q1153690": {"type": 0x0C, "flag": "Variable"},      # long-period variable

    # Village 하위 타입
    "Q13100073": {"type": 0x1D},  # village of China
    "Q56436498": {"type": 0x1D},  # village in India

    # Building 하위 타입
    "Q27686": {"type": 0x24},     # hotel
    "Q61443690": {"type": 0x24}, # branch post office
    "Q2065736": {"type": 0x24},   # cultural property

    # Other 하위 타입
    "Q47150325": {"type": 0x3F, "field": "subtype", "value": 2},   # calendar day
    "Q29654788": {"type": 0x3F, "field": "subtype", "value": 3},   # Unicode character
    "Q49008": {"type": 0x3F, "field": "subtype", "value": 1},      # prime number
}
```

### 2.4 P279 체인 탐색 (subclass of)

직접/하위 매핑 모두 실패 시, P279 체인을 따라 상위 타입 탐색.

```python
def find_type_via_p279(entity_qid: str, wikidata: WikidataClient, max_depth: int = 5) -> int:
    """P279 체인을 따라 EntityType 탐색"""

    visited = set()
    queue = [(entity_qid, 0)]

    while queue:
        qid, depth = queue.pop(0)

        if depth > max_depth:
            continue

        if qid in visited:
            continue
        visited.add(qid)

        # P31 (instance of) 확인
        p31_values = wikidata.get_property(qid, "P31")
        for p31 in p31_values:
            if p31 in DIRECT_TYPE_MAP:
                return DIRECT_TYPE_MAP[p31]
            if p31 in SUBTYPE_MAP:
                return SUBTYPE_MAP[p31]["type"]

        # P279 (subclass of) 따라 탐색
        p279_values = wikidata.get_property(qid, "P279")
        for p279 in p279_values:
            if p279 in DIRECT_TYPE_MAP:
                return DIRECT_TYPE_MAP[p279]
            queue.append((p279, depth + 1))

    return 0x3F  # Other
```

### 2.5 제외 타입 (Wikimedia 내부)

다음 타입은 SIDX 인코딩 대상이 아니다:

| QID | 라벨 | 개체수 |
|-----|------|--------|
| Q4167836 | Wikimedia category | 5.7M |
| Q4167410 | Wikimedia disambiguation page | 1.5M |
| Q11266439 | Wikimedia template | 831K |
| Q13406463 | Wikimedia list article | 378K |
| Q115595777 | taxonomy template | 141K |

```python
EXCLUDE_TYPES = {
    "Q4167836", "Q4167410", "Q11266439",
    "Q13406463", "Q115595777"
}
```

### 2.6 타입 결정 알고리즘

```python
def determine_entity_type(entity: WikidataEntity) -> tuple[int, dict]:
    """
    Returns: (entity_type_code, extra_attrs)
    extra_attrs: 하위 타입에서 결정된 추가 속성 (doc_type, flags 등)
    """

    p31_values = entity.get_claims("P31")

    # 1. 제외 타입 검사
    for p31 in p31_values:
        if p31 in EXCLUDE_TYPES:
            raise ExcludedTypeError(f"Wikimedia internal type: {p31}")

    # 2. 직접 매핑
    for p31 in p31_values:
        if p31 in DIRECT_TYPE_MAP:
            return (DIRECT_TYPE_MAP[p31], {})

    # 3. 하위 타입 매핑
    extra_attrs = {}
    for p31 in p31_values:
        if p31 in SUBTYPE_MAP:
            mapping = SUBTYPE_MAP[p31]
            if "field" in mapping:
                extra_attrs[mapping["field"]] = mapping["value"]
            if "flag" in mapping:
                extra_attrs.setdefault("flags", []).append(mapping["flag"])
            return (mapping["type"], extra_attrs)

    # 4. P279 체인 탐색
    for p31 in p31_values:
        found_type = find_type_via_p279(p31, wikidata)
        if found_type != 0x3F:
            return (found_type, {})

    # 5. 폴백
    return (0x3F, {})
```

---

## 3. Attributes 48비트 추출

### 3.1 개요

EntityType이 결정되면, `type_schemas.json`에서 해당 타입의 스키마를 참조하여 48비트 Attributes를 구성한다.

### 3.2 스키마 구조

```json
{
  "0x00_Human": {
    "fields": [
      {"name": "subclass", "bits": 5, "offset": 0},
      {"name": "occupation", "bits": 6, "offset": 5, "property": "P106"},
      {"name": "country", "bits": 8, "offset": 11, "property": "P27"},
      {"name": "era", "bits": 4, "offset": 19, "property": "P569"},
      {"name": "decade", "bits": 4, "offset": 23},
      {"name": "gender", "bits": 2, "offset": 27, "property": "P21"},
      {"name": "notability", "bits": 3, "offset": 29},
      {"name": "language", "bits": 6, "offset": 32, "property": "P1412"},
      {"name": "birth_region", "bits": 6, "offset": 38, "property": "P19"},
      {"name": "activity_field", "bits": 4, "offset": 44, "property": "P101"}
    ]
  }
}
```

### 3.3 속성 추출 로직

```python
def extract_attributes(entity: WikidataEntity, entity_type: int,
                       extra_attrs: dict, schemas: dict) -> int:
    """
    EntityType별 스키마에 따라 48비트 Attributes 생성
    """

    type_key = f"0x{entity_type:02X}_{TYPE_NAMES[entity_type]}"
    schema = schemas["schemas"][type_key]

    attrs = 0

    for field in schema["fields"]:
        field_name = field["name"]
        bits = field["bits"]
        offset = field["offset"]

        # 값 추출
        if field_name in extra_attrs:
            # 하위 타입 매핑에서 이미 결정된 값
            value = extra_attrs[field_name]
        elif "property" in field:
            # Wikidata property에서 추출
            value = extract_property_value(
                entity,
                field["property"],
                field_name,
                bits
            )
        else:
            # 파생 속성 또는 기본값
            value = derive_field_value(entity, field_name, bits)

        # 비트 마스크 적용
        max_val = (1 << bits) - 1
        value = min(value, max_val)

        # Attributes에 삽입
        attrs |= (value << (48 - offset - bits))

    return attrs
```

### 3.4 Property 값 추출

```python
def extract_property_value(entity: WikidataEntity, prop: str,
                           field_name: str, bits: int) -> int:
    """
    Wikidata property에서 값을 추출하여 양자화된 코드로 변환
    """

    raw_value = entity.get_claim_value(prop)

    if raw_value is None:
        return 0  # Unknown

    # 필드별 코드북 조회
    codebook = CODEBOOKS.get(field_name, {})

    if isinstance(raw_value, str):
        # QID 형태 (예: Q-ID)
        if raw_value in codebook:
            return codebook[raw_value]
        return 0

    elif isinstance(raw_value, (int, float)):
        # 수치 값 → 양자화
        return quantize_value(raw_value, field_name, bits)

    elif isinstance(raw_value, dict):
        # 시간 값
        if "time" in raw_value:
            return quantize_time(raw_value["time"], field_name)

    return 0
```

### 3.5 양자화 규칙

수치형 속성은 `quantization_rules.json`에 정의된 구간에 따라 양자화한다.

#### 시대 (era) - 4비트

| 코드 | 범위 | 라벨 |
|------|------|------|
| 0 | - | Unknown |
| 1 | ~BC3000 | Prehistoric |
| 2 | BC3000~500 | Ancient |
| 3 | 500~1000 | Classical |
| 4 | 1000~1500 | Medieval |
| 5 | 1500~1800 | EarlyModern |
| 6 | 1800~1900 | Modern19C |
| 7 | 1900~1950 | Modern20CEarly |
| 8 | 1950~1980 | Contemporary |
| 9 | 1980~2000 | Late20C |
| 10 | 2000~2010 | Early21C |
| 11 | 2010~2020 | 2010s |
| 12 | 2020~ | Current |

#### 저명도 (notability) - 3비트 (sitelinks 기반)

| 코드 | sitelinks | 라벨 |
|------|-----------|------|
| 0 | 0 | Unknown |
| 1 | 1-9 | Minor |
| 2 | 10-49 | Notable |
| 3 | 50-99 | Well-known |
| 4 | 100-199 | Famous |
| 5 | 200-499 | Very Famous |
| 6 | 500-999 | Highly Famous |
| 7 | 1000+ | World Famous |

#### 고도 (elevation) - 5비트

| 코드 | 범위 (m) | 라벨 |
|------|----------|------|
| 0 | - | Unknown |
| 1 | <-100 | Deep Below Sea |
| 2 | -100~0 | Below Sea |
| 3 | 0~50 | Coastal |
| 4 | 50~100 | Low Plain |
| ... | ... | ... |
| 15 | >4000 | Extreme |

### 3.6 플래그 비트 처리

일부 타입은 플래그 비트를 포함한다 (예: Star의 6비트 플래그).

```python
def encode_flags(flag_names: list[str], flag_defs: dict) -> int:
    """
    플래그 이름 목록을 비트 필드로 인코딩

    flag_defs = {"IR": 0, "Radio": 1, "X-ray": 2, "Binary": 3, "Variable": 4, "HighPM": 5}
    """
    flags = 0
    for name in flag_names:
        if name in flag_defs:
            flags |= (1 << flag_defs[name])
    return flags
```

### 3.7 계층적 종속 속성

일부 속성은 상위 속성에 종속된다.

| 종속 속성 | 부모 속성 | 설명 |
|-----------|-----------|------|
| admin (P131) | country (P17) | 행정구역은 국가별 코드북 |
| occupation (P106) | subclass | 직업은 소분류별 코드북 |
| birth_region (P19) | country (P27) | 출생지역은 국적별 코드북 |

```python
def get_codebook_for_field(field_name: str, parent_value: int) -> dict:
    """
    부모 값에 따라 적절한 코드북 반환
    """
    if field_name == "admin":
        return ADMIN_CODEBOOKS.get(parent_value, {})
    elif field_name == "occupation":
        return OCCUPATION_CODEBOOKS.get(parent_value, {})
    elif field_name == "birth_region":
        return REGION_CODEBOOKS.get(parent_value, {})
    return CODEBOOKS.get(field_name, {})
```

---

## 4. SIDX 조립

### 4.1 조립 함수

```python
def encode_sidx(entity: WikidataEntity, mode: int = 0) -> bytes:
    """
    Wikidata Entity를 64비트 SIDX로 인코딩

    Args:
        entity: WikidataEntity 객체
        mode: 0=등록, 1=특정단수, ... 7=총칭

    Returns:
        8바이트 SIDX
    """

    PREFIX = 0b0001001  # 7비트 (Proposal Entity)

    # 1. EntityType 결정
    entity_type, extra_attrs = determine_entity_type(entity)

    # 2. Attributes 추출
    attrs = extract_attributes(entity, entity_type, extra_attrs, SCHEMAS)

    # 3. SIDX 조립
    word1 = (PREFIX << 9) | (mode << 6) | entity_type
    word2 = (attrs >> 32) & 0xFFFF
    word3 = (attrs >> 16) & 0xFFFF
    word4 = attrs & 0xFFFF

    return (
        word1.to_bytes(2, 'big') +
        word2.to_bytes(2, 'big') +
        word3.to_bytes(2, 'big') +
        word4.to_bytes(2, 'big')
    )
```

### 4.2 비트 레이아웃 상세

```
64비트 SIDX 구조:
┌───────────────────────────────────────────────────────────────────┐
│ Bit 1-7: Prefix (0001001)                                         │
│ Bit 8-10: Mode (000=등록, 001=특정단수, ..., 111=총칭)            │
│ Bit 11-16: EntityType (0x00-0x3F)                                 │
├───────────────────────────────────────────────────────────────────┤
│ Bit 17-64: Attributes (48비트, 타입별 스키마 적용)                │
└───────────────────────────────────────────────────────────────────┘
```

### 4.3 Mode 코드

| 코드 | 이진 | 의미 | 용도 |
|------|------|------|------|
| 0 | 000 | 등록 개체 | Q-ID 연결된 개체 |
| 1 | 001 | 특정 단수 | "그 사람" |
| 2 | 010 | 특정 소수 | "그 몇몇" |
| 3 | 011 | 특정 다수 | "그 사람들" |
| 4 | 100 | 전칭 | "모든 ~" |
| 5 | 101 | 존재 | "어떤 ~" |
| 6 | 110 | 불특정 | "아무 ~" |
| 7 | 111 | 총칭 | "~ 일반" |

---

## 5. 인코딩 예시

### 5.1 Q76 (Barack Obama)

#### 입력 데이터

```
Q76 - Barack Obama
P31: Q5 (Human)
P21: Q6581097 (male)
P27: Q30 (United States)
P569: +1961-08-04 (생년월일)
P106: [Q82955 (politician), Q40348 (lawyer)]
P1412: Q1860 (English)
P19: Q18094 (Honolulu)
sitelinks: 298
```

#### 인코딩 과정

1. **EntityType 결정**: P31=Q5 → Human (0x00)

2. **Attributes 추출** (Human 스키마):
   - subclass: 정치인/법률가 → 5 (Politics)
   - occupation: politician → 1
   - country: Q30 (USA) → 1
   - era: 1961 → 8 (Contemporary, 1950-1980)
   - decade: 1961 → 1 (1960s in era)
   - gender: Q6581097 (male) → 1
   - notability: 298 sitelinks → 5 (Very Famous)
   - language: Q1860 (English) → 1
   - birth_region: Hawaii → 10
   - activity_field: Politics → 5

3. **Attributes 비트 배치**:
   ```
   subclass    (5bit, offset 0):  00101 = 5
   occupation  (6bit, offset 5):  000001 = 1
   country     (8bit, offset 11): 00000001 = 1
   era         (4bit, offset 19): 1000 = 8
   decade      (4bit, offset 23): 0001 = 1
   gender      (2bit, offset 27): 01 = 1
   notability  (3bit, offset 29): 101 = 5
   language    (6bit, offset 32): 000001 = 1
   birth_region(6bit, offset 38): 001010 = 10
   activity    (4bit, offset 44): 0101 = 5
   ```

4. **48비트 Attributes**:
   ```
   00101 000001 00000001 1000 0001 01 101 000001 001010 0101
   = 0x2810884114A5 (예시)
   ```

5. **최종 SIDX**:
   ```
   Prefix (7bit):     0001001
   Mode (3bit):       000 (등록)
   EntityType (6bit): 000000 (Human)

   Word1: 0001001 000 000000 = 0x1200
   Word2-4: Attributes

   SIDX: 0x1200_2810_8841_14A5 (64비트)
   ```

### 5.2 추상 표현: "모든 한국 남성 정치인"

```python
abstract_korean_male_politician = make_entity(
    mode=4,              # 전칭 (모든)
    entity_type=0x00,    # Human
    attrs=(
        (0x05 << 43) |   # subclass: Politics
        (0x01 << 37) |   # occupation: Politician
        (0x52 << 29) |   # country: Korea (가정)
        (0x01 << 19)     # gender: Male
    )
)

# 나머지 비트(era, decade, notability 등)는 0
# → "한국 남성 정치인" 전체를 가리키는 추상 SIDX
```

---

## 6. 에러 처리

### 6.1 에러 유형

| 에러 | 원인 | 처리 |
|------|------|------|
| ExcludedTypeError | Wikimedia 내부 타입 | 인코딩 스킵 |
| UnknownTypeError | P31 없음 or 매핑 불가 | Other(0x3F) 폴백 |
| MissingPropertyError | 필수 속성 누락 | 기본값 0 |
| QuantizationError | 값 범위 초과 | 최대값 클램프 |

### 6.2 에러 처리 코드

```python
def safe_encode_sidx(entity: WikidataEntity) -> Optional[bytes]:
    """
    에러 처리가 포함된 안전한 인코딩
    """
    try:
        return encode_sidx(entity, mode=0)
    except ExcludedTypeError as e:
        logger.info(f"Skipped Wikimedia type: {entity.qid}")
        return None
    except Exception as e:
        logger.warning(f"Encoding failed for {entity.qid}: {e}")
        # Other 타입으로 폴백 인코딩
        return encode_fallback(entity)
```

---

## 7. 성능 최적화

### 7.1 배치 처리

```python
def batch_encode(entities: list[WikidataEntity],
                 batch_size: int = 1000) -> list[bytes]:
    """
    대량 개체 배치 인코딩
    """
    results = []

    for batch in chunked(entities, batch_size):
        # 타입별 그룹화로 스키마 조회 최소화
        by_type = defaultdict(list)
        for entity in batch:
            try:
                etype, extra = determine_entity_type(entity)
                by_type[etype].append((entity, extra))
            except ExcludedTypeError:
                continue

        # 타입별 일괄 처리
        for etype, group in by_type.items():
            schema = get_schema(etype)
            for entity, extra in group:
                attrs = extract_attributes(entity, etype, extra, schema)
                sidx = assemble_sidx(0, etype, attrs)
                results.append(sidx)

    return results
```

### 7.2 캐싱 전략

```python
# 자주 사용되는 코드북 캐싱
CACHED_CODEBOOKS = {
    "country": load_codebook("country"),
    "occupation": load_codebook("occupation"),
    "language": load_codebook("language"),
}

# P279 체인 탐색 결과 캐싱
P279_CACHE = LRUCache(maxsize=100000)
```

---

## 8. 검증

### 8.1 인코딩 검증

```python
def validate_sidx(sidx: bytes, entity: WikidataEntity) -> bool:
    """
    인코딩 결과 검증
    """
    parsed = parse_sidx(sidx)

    # Prefix 검증
    assert parsed["prefix"] == 0b0001001, "Invalid prefix"

    # EntityType 검증
    expected_type, _ = determine_entity_type(entity)
    assert parsed["entity_type"] == expected_type, "Type mismatch"

    # 비트 범위 검증
    assert 0 <= parsed["mode"] <= 7, "Invalid mode"
    assert 0 <= parsed["entity_type"] <= 63, "Invalid entity type"

    return True
```

### 8.2 디코딩 검증

```python
def decode_and_verify(sidx: bytes) -> dict:
    """
    SIDX 디코딩 및 필드 검증
    """
    word1 = int.from_bytes(sidx[0:2], 'big')
    word2 = int.from_bytes(sidx[2:4], 'big')
    word3 = int.from_bytes(sidx[4:6], 'big')
    word4 = int.from_bytes(sidx[6:8], 'big')

    prefix = (word1 >> 9) & 0x7F
    mode = (word1 >> 6) & 0x7
    entity_type = word1 & 0x3F
    attrs = (word2 << 32) | (word3 << 16) | word4

    # 타입별 스키마로 Attributes 디코딩
    decoded_attrs = decode_attributes(entity_type, attrs)

    return {
        "prefix": prefix,
        "mode": mode,
        "mode_label": MODE_LABELS[mode],
        "entity_type": entity_type,
        "entity_type_label": TYPE_LABELS[entity_type],
        "attributes": decoded_attrs
    }
```

---

## 부록 A: 파일 참조

| 파일 | 내용 |
|------|------|
| `references/entity_types_64.json` | 64개 EntityType 정의 |
| `references/type_schemas.json` | 타입별 48비트 스키마 |
| `references/type_mapping.json` | 하위 타입 매핑 |
| `references/quantization_rules.json` | 양자화 규칙 |

---

## 부록 B: 전체 EntityType 목록

| 코드 | 타입 | QID | 카테고리 |
|------|------|-----|----------|
| 0x00 | Human | Q5 | 생물/인물 |
| 0x01 | Taxon | Q16521 | 생물/인물 |
| 0x02 | Gene | Q7187 | 생물/인물 |
| 0x03 | Protein | Q8054 | 생물/인물 |
| 0x04 | CellLine | Q21014462 | 생물/인물 |
| 0x05 | FamilyName | Q101352 | 생물/인물 |
| 0x06 | GivenName | Q202444 | 생물/인물 |
| 0x07 | FictionalCharacter | Q15632617 | 생물/인물 |
| 0x08 | Chemical | Q113145171 | 화학/물질 |
| 0x09 | Compound | Q11173 | 화학/물질 |
| 0x0A | Mineral | Q7946 | 화학/물질 |
| 0x0B | Drug | Q12140 | 화학/물질 |
| 0x0C | Star | Q523 | 천체 |
| 0x0D | Galaxy | Q318 | 천체 |
| 0x0E | Asteroid | Q3863 | 천체 |
| 0x0F | Quasar | Q83373 | 천체 |
| 0x10 | Planet | Q634 | 천체 |
| 0x11 | Nebula | Q12057 | 천체 |
| 0x12 | StarCluster | Q168845 | 천체 |
| 0x13 | Moon | Q2537 | 천체 |
| 0x14 | Mountain | Q8502 | 지형/자연 |
| 0x15 | Hill | Q54050 | 지형/자연 |
| 0x16 | River | Q4022 | 지형/자연 |
| 0x17 | Lake | Q23397 | 지형/자연 |
| 0x18 | Stream | Q47521 | 지형/자연 |
| 0x19 | Island | Q23442 | 지형/자연 |
| 0x1A | Bay | Q39594 | 지형/자연 |
| 0x1B | Cave | Q35509 | 지형/자연 |
| 0x1C | Settlement | Q486972 | 장소/행정 |
| 0x1D | Village | Q532 | 장소/행정 |
| 0x1E | Hamlet | Q5084 | 장소/행정 |
| 0x1F | Street | Q79007 | 장소/행정 |
| 0x20 | Cemetery | Q39614 | 장소/행정 |
| 0x21 | AdminRegion | Q15284 | 장소/행정 |
| 0x22 | Park | Q22698 | 장소/행정 |
| 0x23 | ProtectedArea | Q473972 | 장소/행정 |
| 0x24 | Building | Q41176 | 건축물 |
| 0x25 | Church | Q16970 | 건축물 |
| 0x26 | School | Q9842 | 건축물 |
| 0x27 | House | Q3947 | 건축물 |
| 0x28 | Structure | Q811979 | 건축물 |
| 0x29 | SportsVenue | Q1076486 | 건축물 |
| 0x2A | Castle | Q23413 | 건축물 |
| 0x2B | Bridge | Q12280 | 건축물 |
| 0x2C | Organization | Q43229 | 조직 |
| 0x2D | Business | Q4830453 | 조직 |
| 0x2E | PoliticalParty | Q7278 | 조직 |
| 0x2F | SportsTeam | Q847017 | 조직 |
| 0x30 | Painting | Q3305213 | 창작물 |
| 0x31 | Document | Q49848 | 창작물 |
| 0x32 | LiteraryWork | Q7725634 | 창작물 |
| 0x33 | Film | Q11424 | 창작물 |
| 0x34 | Album | Q482994 | 창작물 |
| 0x35 | MusicalWork | Q105543609 | 창작물 |
| 0x36 | TVEpisode | Q21191270 | 창작물 |
| 0x37 | VideoGame | Q7889 | 창작물 |
| 0x38 | TVSeries | Q5398426 | 창작물 |
| 0x39 | Patent | Q43305660 | 창작물 |
| 0x3A | Software | Q7397 | 창작물 |
| 0x3B | Website | Q35127 | 창작물 |
| 0x3C | SportsSeason | Q27020041 | 이벤트 |
| 0x3D | Event | Q1656682 | 이벤트 |
| 0x3E | Election | Q40231 | 이벤트 |
| 0x3F | Other | - | 예약 |

---

## 버전 히스토리

| 버전 | 날짜 | 변경 |
|------|------|------|
| v1.0 | 2026-02-01 | 초기 명세서 작성 |

---

**문서 종료**
