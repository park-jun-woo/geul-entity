# Entity SIDX 인코딩 개발 히스토리

Wikidata 108.8M 개체를 64비트 의미정렬 식별자(SIDX)로 인코딩하는 시스템의 설계부터 구현까지의 전체 과정.

---

## 타임라인 요약

| 날짜 | 마일스톤 | 핵심 산출물 |
|------|----------|-------------|
| 2026-01-27 | UID 64비트 식별자 + Entity SIDX 초기 명세 | UID.md, Entity SIDX v0.5 |
| 2026-01-29 | Entity Node 가변 워드 구조 설계 + Lane/Mode 도입 | Entity Node v0.2 |
| 2026-01-30 | **설계 전환: UID 제거 → 순수 의미 인코딩** | Entity Node v0.3 |
| 2026-01-31 | SIDX v0.11 간소화 + 5단계 자동화 파이프라인 착수 | pipeline scripts, SIDX v0.11 |
| 2026-02-01 | 64개 EntityType + 48비트 스키마 설계 완료 (Phase 4) | type_schemas.json, entity_types_64.json |
| 2026-02-01 | 인코더 프로토타입 + 속성 인코딩 실행 (Phase 6) | sidx_full_encoder.py, codebooks_full.json |
| 2026-02-27 | 설계 검토 + 분류 실패 원인 분석 + 검색 아키텍처 설계 | 0227.md 연구일지 |

---

## Phase 1: 기초 설계 — UID와 초기 Entity SIDX (2026-01-27)

### 1.1 UID (Unified Identifier) 64비트 도입

외부 지식 체계(Wikidata, WordNet 등)를 GEUL 내부에서 참조하기 위한 통합 식별자.

**구조:**
- Standard Lane (99%): Q-ID(Wikidata), P-ID(Property), Synset(WordNet), G-ID(GEUL 내부)
- Extension Lane: Schema.org, SNOMED-CT, ICD, Legal, Financial, Custom

### 1.2 Entity SIDX 최초 명세 (v0.5)

- 64비트 구조에 UID를 직접 내장
- Q-ID가 SIDX 비트 안에 포함되는 설계
- **문제:** UID에 비트를 소비하면 의미 인코딩 공간이 부족

---

## Phase 2: 가변 워드 구조와 Lane 분기 (2026-01-29)

### 2.1 Entity Node v0.2 설계

note/2026/0129.md에 기록된 주요 설계 변경:

**가변 워드 구조:**
- 약식 (Lane=0, UIDflag=0): **3워드**
- 정식 (Lane=0, UIDflag=1): **5워드**
- 추상 (Lane=1): **3워드**

**설계 원칙:** TID는 항상 마지막 워드에 배치.

**Lane 재정의:**
- Lane 0 = 구체 개체 (concrete entity)
- Lane 1 = 추상 개체 (abstract entity)

**Prefix 변경:** 6비트 → 7비트 (`0001001`)

---

## Phase 3: 핵심 전환 — UID 제거와 순수 의미 인코딩 (2026-01-30)

### 3.1 Entity Node v0.3 — 가장 중요한 설계 결정

**UID 내장을 완전히 폐기.** Q-ID는 Triple로 분리:

```
Triple(Entity_SIDX, P-external_ID, "Q12345")
```

**이유:** 48비트 전부를 의미 정렬에 사용. SIMD 비트마스크 검색 성능 극대화.

**확정된 구조 (4워드 = 64비트):**

```
Word 1 (16비트): Prefix(7) + Mode(3) + EntityType(6)
Word 2-4 (48비트): 타입별 독립 속성 스키마
```

### 3.2 Mode 시스템 (3비트, 8가지 양화)

| Mode | 의미 | 예시 |
|------|------|------|
| 0 | 등록 (Registered) | 특정 Q-ID 개체 |
| 1 | 특정 단수 | "그 사람" |
| 2 | 특정 소수 | "그 세 명" |
| 3 | 특정 다수 | "그 사람들" |
| 4 | 전칭 (Universal) | "모든 한국인" |
| 5 | 존재 (Existential) | "어떤 한국인" |
| 6 | 불특정 (Indefinite) | "아무 한국인이나" |
| 7 | 총칭 (Generic) | "한국인이란" |

**핵심 통찰:** 등록 개체(Mode 0)와 추상 참조(Mode 4~7)를 하나의 필드로 통합. 별도 Lane이 불필요해짐.

### 3.3 v0.2 → v0.3 비교

| 항목 | v0.2 | v0.3 |
|------|------|------|
| 의미 비트 | 20비트 | **41비트** |
| UID | 내장 | **Triple 분리** |
| 속성 | 12비트 고정 | **32비트 가변 (후 48비트로 확장)** |
| 구조 | 가변 3/5워드 | **고정 4워드** |

---

## Phase 4: SIDX v0.11 간소화 + 파이프라인 구축 (2026-01-31)

### 4.1 SIDX 비트 설계 헌장

```
bit1 = 1    → 먼 미래 (50%)
bit1-2 = 01 → 미래 (25%)
bit1-3 = 001 → 표준 (12.5%)
bit1-3 = 000 → 자유 (12.5%)
```

현재는 자유 영역 내 `0001` Proposal 접두사 사용.
**설계 원칙:** 1조 년 후에도 사용 가능, 하위 호환 절대 유지.

### 4.2 EntityType 6비트 (64종) 확정

Wikidata `instance_of` (P31) 빈도 분석 기반으로 64개 타입 선정:

| 카테고리 | 범위 | 타입 수 | 개체 수 | 주요 타입 |
|----------|------|---------|---------|-----------|
| 생물/인간 | 0x00-0x07 | 8 | 19.6M | Human(12.5M), Taxon(3.8M), Gene(1.2M) |
| 화학/물질 | 0x08-0x0B | 4 | 2.4M | Chemical(1.3M), Compound(1.1M) |
| 천문 | 0x0C-0x13 | 8 | 6.2M | Star(3.6M), Galaxy(2.1M) |
| 지형/자연 | 0x14-0x1B | 8 | 1.9M | Mountain(518K), River(427K) |
| 행정/위치 | 0x1C-0x23 | 8 | 2.2M | Settlement(580K), Street(711K) |
| 건축물 | 0x24-0x2B | 8 | 1.5M | Building(292K), Church(286K) |
| 조직 | 0x2C-0x2F | 4 | 0.9M | Organization(531K), Business(242K) |
| 창작물 | 0x30-0x3B | 12 | 48.1M | Document(45M), Film(336K) |
| 이벤트/예약 | 0x3C-0x3F | 4 | 0.2M | SportsSeason(183K), Other(예약) |

### 4.3 5단계 자동화 파이프라인

```
Stage 1: Property Extraction    — 타입별 속성 통계 (빈도, 카디널리티, 엔트로피)
Stage 2: Dependency Detection   — 조건부 엔트로피 분석 → DAG 구축
Stage 3: Bit Allocation         — 탐욕 알고리즘 + DAG 순서 비트 배분
Stage 4: Codebook Generation    — 계층적 코드 테이블, 빈도 기반 정렬
Stage 5: Validation             — 충돌률, 추상 표현, SIMD 쿼리 테스트
```

---

## Phase 5: 48비트 속성 스키마 전체 설계 (2026-02-01)

### 5.1 설계 방법론

5가지 원칙:
1. **타입 완전 독립:** 64개 타입이 각자 48비트를 완전히 다르게 해석
2. **계층적 의미:** 상위 필드 값이 하위 필드 코드북을 결정
3. **우아한 열화:** 비트를 덜 채우면 더 추상적 표현
4. **고빈도 최적화:** 자주 쓰는 속성에 더 많은 비트
5. **양자화 규칙:** 연속값 → 이산 구간 매핑

### 5.2 카테고리별 공통 패턴

| 카테고리 | 공통 헤더 | 크기 |
|----------|----------|------|
| 지형 (0x14-0x1B) | country + lat + lon + admin | 22비트 |
| 정주지 (0x1C-0x23) | country + admin_level + admin_code + lat + lon | 28비트 |
| 건물 (0x24-0x2B) | country + admin_code + era | 20비트 |
| 창작물 (0x30-0x38) | country + year + genre | 20~21비트 |

**카테고리 내 비트마스크 범위 검색 시 우아한 열화 작동.**

### 5.3 주요 타입별 스키마 예시

**Human (0x00) — 48비트:**
```
subclass(5b) + occupation(6b) + country(8b) + era(4b) + decade(4b)
+ gender(2b) + notability(3b) + language(6b) + birth_region(6b)
+ activity_field(4b) = 48비트
```

**Taxon (0x01) — 48비트:**
```
kingdom(3b) + phylum(5b) + class(6b) + order(6b) + family(6b)
+ rank(3b) + conservation(3b) + habitat(4b) + body_size(4b)
+ diet(3b) + locomotion(3b) + endemic(2b) = 48비트
```

**Star (0x0C) — 48비트:**
```
constellation(7b) + spectral_type(4b) + luminosity_class(3b)
+ apparent_mag(4b) + ra_zone(4b) + dec_zone(4b) + flags(6b)
+ radial_velocity(5b) + redshift(5b) + parallax(4b) + reserved(2b) = 48비트
```

**Document (0x31) — 48비트:**
```
doc_type(6b) + country(8b) + year(7b) + language(6b) + genre(6b)
+ author_count(3b) + citation_count(4b) + review_status(3b)
+ license(3b) + accessibility(2b) = 48비트
```

### 5.4 커버리지 통계

```
Wikidata 전체:     117,419,925
Wikimedia 내부:      8,565,353 (7.3%) — 제외
SIDX 대상:        108,854,572 (92.7%)
직접 매핑:          36,295,074 (33.3%)
하위타입 흡수:      71,842,429 (66.0%)
Other 폴백:           717,069 (0.7%)
최종 커버리지:           100%
충돌률:              < 0.01%
```

---

## Phase 6: 인코더 구현과 실행 (2026-02-01~02)

### 6.1 인코더 아키텍처

**3단계 파이프라인:**

```
P31 → EntityType 라우터
  ├── 직접 매핑 (64개 핵심 타입)
  ├── 하위타입 매핑 (알려진 변형)
  ├── P279 체인 탐색 (최대 5홉)
  └── Other(0x3F) 폴백

속성 추출기
  ├── type_schemas.json에서 스키마 로드
  ├── 각 필드: Wikidata property 값 추출
  ├── 양자화 규칙 적용
  └── 코드북에서 코드 조회

SIDX 조립기
  ├── Word1: PREFIX(7) | MODE(3) | ENTITY_TYPE(6)
  ├── Words 2-4: 48비트 속성
  └── Big Endian 바이트 오더
```

### 6.2 실행 결과

| 타입 | 이름 | 개체 수 | 속성 인코딩 | 비율 | 상태 |
|------|------|---------|-------------|------|------|
| 0x00 | Human | 12,553,670 | 12,182,686 | 97.0% | 완료 |
| 0x01 | Taxon | 3,904,250 | 3,531,305 | 90.5% | 완료 |
| 0x0C | Star | 4,843,949 | 1,729,008 | 35.7% | 완료 |
| 0x31 | Document | 45,000,000 | 24,478 | 3.5% | 부분 |
| 0x3F | Unknown | 19,678,178 | 0 | 0.0% | 미분류 |

**전체:** 108,878,520 SIDX 생성 (100%), 속성 인코딩 17,442,999 (16.0%)

### 6.3 발견된 버그와 수정

**버그 1: P569 (출생년) JSON 파싱**
- 증상: era 값이 전부 0
- 원인: 년도가 `{"time":"+1969-07-15T00:00:00Z",...}` JSON으로 저장
- 수정: `sidx_fix_era.py` 작성 → Human era 인코딩 복구

**버그 2: Star 별자리 매핑 누락**
- 증상: Star 업데이트 0건
- 원인: codebook에 별자리 QID 매핑 없음
- 수정: 87개 별자리 QID를 `codebooks_full.json`에 추가 → 1.7M Star 속성 인코딩

### 6.4 인코딩 예시

**Barack Obama (Q76):**
```
입력: P31=Q5, P21=Q6581097(남성), P27=Q30(미국), P569=1961-08-04,
      P106=[Q82955,Q40348], sitelinks=298

EntityType: Human (0x00)
속성:
  subclass=5 (Politics), occupation=1 (politician)
  country=1 (USA), era=8 (1950-1980), decade=1 (1960s)
  gender=1 (male), notability=5 (Very Famous)
  language=1 (English), birth_region=10 (Hawaii)

SIDX: 0x1200_2810_8841_14A5
```

**추상 표현: "모든 한국 남성 정치인":**
```
Mode: 4 (전칭 = "모든")
EntityType: Human (0x00)
속성: subclass=5, occupation=1, country=82(Korea), gender=1
      (나머지 = 0 → 추상화)

→ SIMD 마스크로 효율적 필터링
```

---

## Phase 7: 설계 검토와 문제 분석 (2026-02-27)

### 7.1 type_schemas.json 전체 검토

| 항목 | 수치 |
|------|------|
| 정의된 타입 | 63/64 (0x3F Other 제외) |
| 총 필드 수 | 738 |
| Wikidata Property 매핑 | 324 (43.9%) |
| 매핑 없음 | **414 (56.1%)** |
| flags 필드 | 41개 타입, 82비트 (용도 미정의) |
| 주관적 필드 | 8개 (fame, notability, popularity 등) |

**구조적 건전성:** 통과 — 63개 타입 전부 48비트 정확, 오프셋 무결.

### 7.2 식별된 문제점

**문제 1: 62.2% 분류 실패 (가장 심각)**

Phase 6 실행 결과 67.7M 개체가 Unknown(0x3F) 또는 Misc로 분류됨.

**원인:**
- Country(Q6256), Sovereign State(Q3624078) → 매핑 누락
- G-type Star(Q5864) → Star 매핑 누락
- Common Name Taxon(Q55983715) → Taxon 매핑 누락
- P279 체인 탐색 미구현

**영향:** 미국, 독일, 프랑스 등 국가 → Unknown, 태양(Q525) → Unknown, 개/고양이 → Unknown

**문제 2: Property 매핑률 43.9%**

56.1% 필드를 Wikidata에서 자동으로 채울 수 없음.
- Moon(0%), Compound(13%), Planet(17%) 최악

**문제 3: 과도한 세분화**

Settlement/Village/Hamlet, Mountain/Hill, River/Stream이 거의 동일한 스키마 → 5~8 슬롯 낭비.

**문제 4: 누락된 중요 타입**

Country, City, University, Hospital, Airport, Museum 등이 64개에 포함되지 않음.

**결론:** 구조는 건전하나 데이터 소스와의 정렬이 부족. 리셋이 아닌 정제가 필요.

### 7.3 공통 헤더 전역 고정 불가 확인

- 63개 타입 전체가 공유하는 필드: **0개**
- 가장 많은 `country`도 45/63(71%)만 보유
- country 없는 18타입 (14.9M, 13.6%): Taxon(개는 어느 나라?), Chemical(H₂O에 국적?), Star(별에 국가?)

**결론:** 타입별 독립 스키마가 "비트 자체에 의미를 인코딩" 원칙에 부합하는 올바른 설계.

### 7.4 SIMD 검색 아키텍처 설계

**코드북 leaf Dictionary 방식:**

```
사전 구축: ~35,000 leaf entries (~1MB, L2 캐시 적재)
  ("Human", "country", "Korea") → { mask: 0x..., value: 0x... }
  ("Star", "constellation", "Orion") → { mask: 0x..., value: 0x... }

마스크 조립: O(K), K=1~5 → O(1)
SIMD 스캔: Human 12.5M → ~2ms, Star 3.6M → ~0.6ms
```

**쿼리 파이프라인: LLM + Dictionary 역할 분리**

```
사용자: "1950년대 한국 남성 정치인"
        ↓
[소형 쿼리 LLM] ← 의미 파싱만 (NER + Slot Filling)
        ↓
{ "type": "Human", "conditions": [country=Korea, era=1950s, gender=male, subclass=Politics] }
        ↓
[Dictionary 조립] ← 결정론적 O(K)
        ↓
[SIMD 스캔] ← ~2ms
        ↓
결과 SIDX 목록
```

**LLM 직접 비트 생성을 기각한 이유:** 35,000개 leaf의 offset/bitwidth를 기억 불가, 1비트 오류 → 완전히 다른 결과.

### 7.5 쿼리 LLM 파인튜닝 평가

- 태스크: 닫힌 어휘 선택 (type 64개, field ~11개, value ~50개)
- 학습 데이터: 코드북 35K leaf에서 역방향 자동 생성 → 350K쌍 (GPT-4, 1일)
- 모델 규모: **1~3B + LoRA면 충분** (Text-to-SQL 7B보다 작음)
- 파인튜닝 없이도: 코드북 어휘 550토큰 → Phi-3 Mini / Gemma-2B few-shot 동작

---

## 최종 산출물 목록

### 참조 데이터 (entity/references/)

| 파일 | 크기 | 용도 |
|------|------|------|
| `entity_types_64.json` | 11.7KB | 64개 타입 정의 + QID 매핑 + 빈도 |
| `type_schemas.json` | 83KB | 48비트 속성 스키마 (63타입 × 필드) |
| `codebooks_full.json` | 283KB | QID → 코드 매핑 (전 필드) |
| `type_mapping.json` | 7.7KB | Wikidata 하위타입 → 64타입 매핑 |
| `primary_mapping.json` | 11.7KB | 직접 P31 매핑 |
| `quantization_rules.json` | — | 연속값 → 이산 구간 규칙 |
| `encoder_spec.md` | 25.7KB | 인코더 명세 + 의사코드 |
| `pipeline.md` | — | 5단계 방법론 상세 |
| `SIDX.md` | — | 64비트 비트 설계 헌장 (v0.11) |
| `Entity Node.md` | — | Entity 문법 명세 (v0.4) |

### 스크립트 (entity/scripts/)

| 스크립트 | 역할 |
|----------|------|
| `sidx_full_encoder.py` | 전체 인코더 (P31 라우팅 + 속성 인코딩) |
| `sidx_encode_attrs.py` | 속성 인코딩 전용 |
| `sidx_fix_era.py` | P569 JSON 파싱 버그 수정 |

### 출력 (entity/output/)

| 파일 | 용도 |
|------|------|
| `phase4_final_report.md` | 64타입 스키마 완성 보고서 |
| `phase6_encoding_report.md` | 인코더 실행 결과 보고서 |

---

## 핵심 설계 결정 기록

### 1. UID 내장 → Triple 분리 (가장 중요한 전환)

v0.5에서 Q-ID를 SIDX 비트 안에 넣으려 했으나, v0.3에서 완전히 폐기.

**이유:** "왜 비트를 ID에 낭비하나? Triple로 따로 저장하면 48비트 전부 의미에 쓸 수 있다."
**효과:** 의미 비트 20비트 → 41비트 → 48비트로 확대.

### 2. 고정 64타입 vs 계층적 타이핑

6비트 고정 타입 선택. 계층적 타이핑은 기각.

**이유:** 6비트 타입 필드가 SIMD 필터링에 최적. 세부 분류는 48비트 속성 내에서 처리.
**트레이드오프:** 일부 granularity 손실, 고엔트로피 속성 필드로 보상.

### 3. 타입별 완전 독립 스키마

63개 타입이 48비트를 각자 완전히 다르게 해석.

**이유:** 공통 헤더 강제는 "비트 자체에 의미를 인코딩" 원칙에 위배. Taxon에 country 필드는 무의미.
**효과:** 정보 밀도 최대화. Human은 직업, Star는 광도, Document는 장르에 비트 집중.

### 4. 양자화 vs 정확값

연속 속성(년도, 등급, 거리 등)을 이산 구간으로 양자화.

**이유:** SIMD 범위 필터링 활성화, 압축 효율.
**트레이드오프:** 정밀도 손실, 의미 레이어에서는 수용 가능.

### 5. 계층적 코드북 (부모→자식 결정)

상위 필드 값이 하위 필드 코드북을 결정.

**예시:** 국가 → 국가별 행정구역 코드, 시대 → 시대별 정체 테이블.
**효과:** N×M 코드북 폭발 → N으로 압축 (계층적 압축).

### 6. LLM + Dictionary 분리 검색

LLM이 비트를 직접 생성하지 않고, 의미 파싱만 담당.

**이유:** 35,000개 leaf의 offset/bitwidth를 LLM이 기억할 수 없음. 1비트 오류 = 완전히 다른 결과.
**해법:** LLM은 닫힌 어휘 선택, Dictionary가 결정론적 마스크 조립.

---

## 버전 이력

| 버전 | 날짜 | 주요 변경 |
|------|------|----------|
| v0.5 | 01-27 | 초기 구조, UID 내장 |
| v0.2 | 01-29 | 가변 워드 (3/5워드), Lane 분기 |
| v0.3 | 01-30 | **UID 제거, 순수 의미 인코딩, Mode 3비트** |
| v0.4 | 02-01 | SIDX v0.11 정렬, 4워드 64비트 확정, 48비트 속성 |
| Phase 4 | 02-01 | 64타입 × 48비트 스키마 완성, 커버리지 92.7% |
| Phase 6 | 02-02 | 인코더 구현, 108.8M SIDX 생성, 버그 수정 |
| 검토 | 02-27 | 62.2% 분류 실패 원인 분석, 검색 아키텍처 설계 |

---

## 잔여 과제

### 긴급 (분류 실패 62.2% 해소)
- [ ] Q6256(Country), Q3624078(Sovereign State) → primary_mapping.json 추가
- [ ] Q5864(G-type Star) → Star 매핑 추가
- [ ] Q55983715(Common Name Taxon) → Taxon 매핑 추가
- [ ] P279 체인 탐색 구현 (최대 5홉)

### 중기 (스키마 정제)
- [ ] 과도한 세분화 타입 통합 (Settlement/Village/Hamlet 등)
- [ ] 누락 타입 추가 (Country, City, University 등)
- [ ] Property 매핑률 43.9% → 70%+ 개선
- [ ] 주관적 필드 8개 처리 방안

### 장기 (시스템 통합)
- [ ] 코드북 자동 생성 (16개 미완료 타입)
- [ ] 디코더 구현 (64비트 SIDX → 자연어)
- [ ] WMS 통합 + SIMD 성능 테스트
- [ ] GEUL 스트림 포맷 통합 테스트
