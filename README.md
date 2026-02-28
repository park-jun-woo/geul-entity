# GEUL Entity Node

**GEUL(General Embedding vector Unified Language) Entity Node의 48비트 속성 스키마를 위키데이터 실데이터 기반으로 자동 설계하는 프로젝트.**

| 항목 | 값 |
|------|-----|
| Author | 박준우 (mail@parkjunwoo.com) |
| License | MIT |
| Status | Standard Proposal (v0.4) |

---

## 1. 개요

**Entity Node**는 GEUL 스트림에서 개체(사람, 장소, 사물, 조직, 개념 등)를 식별하는 **고정 길이 4워드(64비트) 패킷**이다.

| 특성 | 설명 |
|------|------|
| **Non-unique** | 같은 SIDX에 여러 개체 가능 |
| **Multi-SIDX** | 한 개체가 여러 SIDX 가능 (시점/역할별) |
| **비트 = 의미** | 비트 위치 자체가 속성을 나타냄 |
| **추상/구체 연속** | Mode와 Attributes 채움 정도로 구분 |

**예시:**
- 트럼프 (부동산 사업가) → SIDX_A
- 트럼프 (대통령) → SIDX_B (다른 SIDX)
- "Human + Male + Korea" → 추상적 "한국 남자"
- "Human + Male + Korea + 1946 + Business + ..." → 거의 특정 인물

---

## 2. 구조 (4워드 = 64비트)

```
1st WORD (16비트)
┌─────────┬──────┬────────────┐
│ Prefix  │ Mode │ EntityType │
│  7bit   │ 3bit │   6bit     │
└─────────┴──────┴────────────┘

2nd WORD (16비트)         3rd WORD (16비트)         4th WORD (16비트)
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│ Attributes 상위  │      │ Attributes 중위  │      │ Attributes 하위  │
│     16비트       │      │     16비트       │      │     16비트       │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

| 필드 | 비트 | 크기 | 설명 |
|------|------|------|------|
| Prefix | 1-7 | 7 | `0001001` (Entity Node 식별) |
| Mode | 8-10 | 3 | 8가지 양화/수 모드 |
| EntityType | 11-16 | 6 | 64개 상위 타입 |
| Attributes | 17-64 | 48 | 타입별 가변 스키마 |

---

## 3. Mode (3비트)

Mode는 개체의 **양화(Quantification)와 수(Number)**를 3비트로 통합 표현한다.

| 코드 | 의미 | 예시 |
|------|------|------|
| 0 | **등록 개체** | 이순신, 삼성전자, BTS |
| 1 | 특정 단수 | "그 사람" |
| 2 | 특정 소수 | "그 몇몇" |
| 3 | 특정 다수 | "그 사람들" |
| 4 | 전칭 | "모든 ~" |
| 5 | 존재 | "어떤 ~" |
| 6 | 불특정 | "아무 ~" |
| 7 | 총칭 | "한국인이란" |

---

## 4. EntityType (6비트 = 64개)

위키데이터 P31(instance of) 빈도 통계 기반, 9개 카테고리로 그룹화.

**생물/인물 (0x00-0x07)**

| 코드 | 타입 | 대표 Q-ID | 개체수 |
|------|------|-----------|--------|
| 0x00 | Human | Q5 | 12.5M |
| 0x01 | Taxon | Q16521 | 3.8M |
| 0x02 | Gene | Q7187 | 1.2M |
| 0x03 | Protein | Q8054 | 1.0M |
| 0x04 | CellLine | Q21014462 | 154K |
| 0x05 | FamilyName | Q101352 | 662K |
| 0x06 | GivenName | Q202444 | 128K |
| 0x07 | FictionalCharacter | Q15632617 | 98K |

**화학/물질 (0x08-0x0B)**

| 코드 | 타입 | 대표 Q-ID | 개체수 |
|------|------|-----------|--------|
| 0x08 | Chemical | Q113145171 | 1.3M |
| 0x09 | Compound | Q11173 | 1.1M |
| 0x0A | Mineral | Q7946 | 62K |
| 0x0B | Drug | Q12140 | 45K |

**천체 (0x0C-0x13)**

| 코드 | 타입 | 대표 Q-ID | 개체수 |
|------|------|-----------|--------|
| 0x0C | Star | Q523 | 3.6M |
| 0x0D | Galaxy | Q318 | 2.1M |
| 0x0E | Asteroid | Q3863 | 249K |
| 0x0F | Quasar | Q83373 | 178K |
| 0x10 | Planet | Q634 | 15K |
| 0x11 | Nebula | Q12057 | 8K |
| 0x12 | StarCluster | Q168845 | 5K |
| 0x13 | Moon | Q2537 | 3K |

**지형/자연 (0x14-0x1B)**

| 코드 | 타입 | 대표 Q-ID | 개체수 |
|------|------|-----------|--------|
| 0x14 | Mountain | Q8502 | 518K |
| 0x15 | Hill | Q54050 | 321K |
| 0x16 | River | Q4022 | 427K |
| 0x17 | Lake | Q23397 | 292K |
| 0x18 | Stream | Q47521 | 194K |
| 0x19 | Island | Q23442 | 153K |
| 0x1A | Bay | Q39594 | 25K |
| 0x1B | Cave | Q35509 | 20K |

**장소/행정 (0x1C-0x23)**

| 코드 | 타입 | 대표 Q-ID | 개체수 |
|------|------|-----------|--------|
| 0x1C | Settlement | Q486972 | 580K |
| 0x1D | Village | Q532 | 245K |
| 0x1E | Hamlet | Q5084 | 148K |
| 0x1F | Street | Q79007 | 711K |
| 0x20 | Cemetery | Q39614 | 298K |
| 0x21 | AdminRegion | Q15284 | 100K |
| 0x22 | Park | Q22698 | 45K |
| 0x23 | ProtectedArea | Q473972 | 35K |

**건축물 (0x24-0x2B)**

| 코드 | 타입 | 대표 Q-ID | 개체수 |
|------|------|-----------|--------|
| 0x24 | Building | Q41176 | 292K |
| 0x25 | Church | Q16970 | 286K |
| 0x26 | School | Q9842 | 242K |
| 0x27 | House | Q3947 | 235K |
| 0x28 | Structure | Q811979 | 216K |
| 0x29 | SportsVenue | Q1076486 | 145K |
| 0x2A | Castle | Q23413 | 42K |
| 0x2B | Bridge | Q12280 | 38K |

**조직 (0x2C-0x2F)**

| 코드 | 타입 | 대표 Q-ID | 개체수 |
|------|------|-----------|--------|
| 0x2C | Organization | Q43229 | 531K |
| 0x2D | Business | Q4830453 | 242K |
| 0x2E | PoliticalParty | Q7278 | 35K |
| 0x2F | SportsTeam | Q847017 | 95K |

**창작물 (0x30-0x3B)**

| 코드 | 타입 | 대표 Q-ID | 개체수 |
|------|------|-----------|--------|
| 0x30 | Painting | Q3305213 | 1.1M |
| 0x31 | Document | Q49848 | 45.0M |
| 0x32 | LiteraryWork | Q7725634 | 395K |
| 0x33 | Film | Q11424 | 336K |
| 0x34 | Album | Q482994 | 303K |
| 0x35 | MusicalWork | Q105543609 | 195K |
| 0x36 | TVEpisode | Q21191270 | 177K |
| 0x37 | VideoGame | Q7889 | 172K |
| 0x38 | TVSeries | Q5398426 | 85K |
| 0x39 | Patent | Q43305660 | 289K |
| 0x3A | Software | Q7397 | 13K |
| 0x3B | Website | Q35127 | 12K |

**이벤트/예약 (0x3C-0x3F)**

| 코드 | 타입 | 대표 Q-ID | 개체수 |
|------|------|-----------|--------|
| 0x3C | SportsSeason | Q27020041 | 183K |
| 0x3D | Event | Q1656682 | 10K |
| 0x3E | Election | Q40231 | 11K |
| 0x3F | Other | - | 예약 |

---

## 5. Attributes (48비트)

- **타입별 가변 스키마** — EntityType마다 다른 의미로 해석
- 고빈도 속성에 더 많은 비트 할당
- 상위 필드 값이 하위 필드 코드북을 결정 (계층적 해석)
- SIMD 필터링에 직접 활용

### Human (0x00) 예시

```
┌──────────┬────────┬────────┬──────┬────────┬────────┬─────────┬────────┬──────────┬──────────┐
│ 소분류   │ 직업   │ 국적   │ 시대 │ 연대   │ 성별   │ 저명도  │ 언어   │ 출생지역 │ 활동분야 │
│  5bit    │  6bit  │  8bit  │ 4bit │  4bit  │  2bit  │  3bit   │  6bit  │   6bit   │   4bit   │
└──────────┴────────┴────────┴──────┴────────┴────────┴─────────┴────────┴──────────┴──────────┘
= 48비트
```

### Star (0x0C) 예시

```
┌──────────┬────────────┬──────────┬──────────┬──────────┬──────────┬────────────┬──────────┬──────────┬──────────┬────────┐
│ 별자리   │ 분광형     │ 광도등급 │ 겉보기등급│ 적경구간 │ 적위구간 │ 특성플래그 │ 시선속도 │ 적색편이 │ 시차     │ 예비   │
│   7bit   │    4bit    │   3bit   │   4bit   │   4bit   │   4bit   │    6bit    │   5bit   │   5bit   │   4bit   │  2bit  │
└──────────┴────────────┴──────────┴──────────┴──────────┴──────────┴────────────┴──────────┴──────────┴──────────┴────────┘
= 48비트
```

64개 타입별 전체 스키마는 `references/type_schemas.json` 참조.

---

## 6. 설계 원칙

1. **타입별 완전 독립** — 각 EntityType마다 48비트 해석이 완전히 다름
2. **계층적 해석** — 상위 필드 값이 하위 필드의 코드 테이블을 결정
3. **우아한 열화** — 비트를 덜 채울수록 추상적 표현
4. **SIMD 최적화** — 비트 마스크로 범위 필터링 가능
5. **기계적 할당** — LLM이 자연어에서 자동으로 SIDX 생성 가능
6. **UID 없음** — 외부 ID는 Triple로 분리, 48비트 전부 의미정렬

---

## 7. 사용 예시

### 등록 개체: 이순신

```python
yi_sun_sin = make_entity(
    mode=0,              # 등록 개체
    entity_type=0x00,    # Human
    attrs=(
        (0x06 << 43) |   # 소분류: Military
        (0x01 << 37) |   # 직업: Admiral
        (0x52 << 29) |   # 국적: Korea
        (0x5 << 25) |    # 시대: Early Modern
        (0x0 << 21) |    # 연대
        (0x01 << 19) |   # 성별: Male
        (0x7 << 16) |    # 저명도: 1000+
        (0x0)            # 언어/출생지역/활동분야
    )
)
```

### 추상: "모든 한국 남자"

```python
all_korean_men = make_entity(
    mode=4,              # 전칭 (모든)
    entity_type=0x00,    # Human
    attrs=(
        (0x00 << 43) |   # 소분류: 일반
        (0x00 << 37) |   # 직업: 일반
        (0x52 << 29) |   # 국적: Korea
        (0x01 << 19) |   # 성별: Male
        (0x0 << 16)      # 저명도: Unknown
    )
)
```

### 대명사: "그 사람"

```python
that_person = make_entity(
    mode=1,              # 특정 단수
    entity_type=0x00,    # Human
    attrs=0              # 속성 미지정
)
```

---

## 8. 5단계 파이프라인

위키데이터 실데이터 기반으로 48비트 코드북을 자동 설계하는 파이프라인.

| Stage | 스크립트 | 설명 |
|-------|----------|------|
| 1 | `scripts/stage1_extract.py` | 위키데이터에서 각 EntityType의 속성 분포 분석 |
| 2 | `scripts/stage2_dependency.py` | 속성 간 조건부 엔트로피로 종속 관계 DAG 생성 |
| 3 | `scripts/stage3_allocate.py` | 48비트에 속성 배치, 충돌 최소화 |
| 4 | `scripts/stage4_codebook.py` | 계층적 코드북 자동 생성 |
| 5 | `scripts/stage5_validate.py` | 전체 개체 인코딩 후 충돌률 측정 |

```bash
# 가상환경 설정
python3 -m venv .venv
source .venv/bin/activate
pip install psycopg2-binary

# 순서대로 실행
python scripts/stage1_extract.py
python scripts/stage2_dependency.py
python scripts/stage3_allocate.py
python scripts/stage4_codebook.py
python scripts/stage5_validate.py
```

---

## 9. 프로젝트 현황

| 항목 | 수치 |
|------|------|
| 위키데이터 전체 개체 | 117,419,925 |
| Wikimedia 내부 (제외) | 8,565,353 (7.3%) |
| SIDX 대상 | 108,854,572 (92.7%) |
| 64개 타입 직접 커버 | 36,295,074 (33.3%) |
| 하위 타입 흡수 | 71,842,429 (66.0%) |
| Other 폴백 | 717,069 (0.7%) |
| **최종 커버리지** | **100%** |
| **충돌률** | **< 0.01%** |

---

## 10. 기술 스택

| 항목 | 기술 |
|------|------|
| 언어 | Python 3.12+ |
| DB | PostgreSQL (ltree 확장 필수) |
| Python 패키지 | psycopg2 |

---

## 관련 프로젝트

| 레포 | 관계 |
|------|------|
| [geul](https://github.com/pjw/geul) | 상위 — 문법 명세 + SIDX 횡단 문서 |
| [geul-verb](https://github.com/pjw/geul-verb) | 형제 — 동사 SIDX 16비트 코드북 |
