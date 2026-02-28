# GEUL Entity 64 Type Ontology Validation Plan

**Version:** v1.0
**Date:** 2026-02-01
**Author:** Ontologist
**Status:** Planning

---

## 1. Overview

### 1.1 Objective

64개 EntityType의 48비트 스키마에 대한 체계적 온톨로지 검증을 수행한다. 검증 목표:

1. **MECE 원칙**: 모든 개체가 정확히 하나의 타입에 매핑되는지 확인
2. **경계 사례**: 여러 타입에 속할 수 있는 애매한 사례 식별 및 해결 규칙 수립
3. **상위 분류 정합성**: 위키데이터 P31 체계와의 일치 검증
4. **필드 의미 검증**: 48비트 필드가 해당 타입의 핵심 속성을 포착하는지 확인

### 1.2 Scope

| 검증 범위 | 대상 | 방법 |
|-----------|------|------|
| 타입 정의 | 64개 EntityType | 위키데이터 P31 매핑 분석 |
| 스키마 필드 | 48비트 x 64타입 | Property 커버리지 측정 |
| 경계 사례 | 잠재적 충돌 타입 쌍 | 조건부 분류 규칙 정의 |
| 상위 분류 | 9개 카테고리 | 계층 일관성 검증 |

### 1.3 Risk Matrix

| 타입 | 개체수 | 리스크 레벨 | 핵심 우려사항 |
|------|--------|-------------|---------------|
| 0x31 Document | 45M | **Critical** | 논문/기사/백과 통합으로 충돌 우려 |
| 0x00 Human | 12.5M | High | 소분류 32개로 다양한 직업 커버 |
| 0x01 Taxon | 3.8M | High | 생물 분류 계층 축소 |
| 0x08/0x09 Chemical/Compound | 2.4M | **High** | 경계 불명확 |
| 0x2C-0x2F Organization 계열 | 0.9M | High | 중첩 가능성 |
| 0x07 FictionalCharacter | 98K | Medium | 미디어 믹스 캐릭터 |

---

## 2. MECE Principle Validation

### 2.1 Methodology

**Step 1: P31 Instance-of 분석**
```sql
-- geuldev에서 각 Q-ID가 몇 개의 EntityType에 매핑 가능한지 분석
SELECT
    e.qid,
    COUNT(DISTINCT et.code) as type_count,
    array_agg(et.name_en) as matched_types
FROM wikidata.entities e
JOIN entity_type_mapping m ON e.p31_values @> m.qid_patterns
JOIN entity_types_64 et ON m.entity_type_code = et.code
GROUP BY e.qid
HAVING COUNT(DISTINCT et.code) > 1
ORDER BY type_count DESC
LIMIT 1000;
```

**Step 2: 단일 매핑 비율 측정**
- 목표: 99% 이상의 개체가 정확히 하나의 타입에 매핑
- 다중 매핑 개체 목록 추출 및 분류 규칙 수립

**Step 3: 매핑 불가 개체 식별**
- 어떤 타입에도 매핑되지 않는 개체 추출
- 0x3F Other로 폴백하거나 새 타입 필요성 검토

### 2.2 Validation Queries

```sql
-- 카테고리별 중복 매핑 분석
WITH entity_type_matches AS (
    SELECT
        e.qid,
        jsonb_array_elements_text(e.p31_values) as instance_of
    FROM wikidata.entities e
)
SELECT
    et1.category as cat1,
    et2.category as cat2,
    COUNT(*) as overlap_count
FROM entity_type_matches m
JOIN entity_types_64 et1 ON m.instance_of = et1.qid
JOIN entity_types_64 et2 ON m.instance_of = et2.qid AND et1.code < et2.code
GROUP BY et1.category, et2.category
ORDER BY overlap_count DESC;
```

### 2.3 Expected Outputs

| 산출물 | 형식 | 용도 |
|--------|------|------|
| `overlap_matrix.csv` | CSV | 타입 쌍별 중복 개체 수 |
| `unmapped_entities.json` | JSON | 매핑 불가 개체 샘플 |
| `mapping_rules.md` | Markdown | 다중 매핑 시 우선순위 규칙 |

---

## 3. Boundary Case Analysis

### 3.1 Critical Boundary Cases

#### 3.1.1 Document (0x31) - 45M 개체

**문제점:**
- 논문(Q13442814 scholarly article), 기사(Q5707594 news article), 백과사전 항목 등 이질적 개체 통합
- 개체 수 45M으로 전체의 ~50%

**검증 항목:**

| 검증 ID | 질문 | 방법 |
|---------|------|------|
| DOC-1 | 논문/기사/백과가 doc_type 6비트(64개)로 구분 가능한가? | P31 하위 타입 분포 분석 |
| DOC-2 | subject 6비트(64개)가 학문 분야를 커버하는가? | P921 (main subject) 분포 |
| DOC-3 | 충돌률 1% 목표 달성 가능한가? | 48비트 엔트로피 계산 |
| DOC-4 | LiteraryWork(0x32)와 경계가 명확한가? | 소설/에세이 등 분류 기준 |

**세부 분류 규칙 제안:**

```
IF P31 contains Q13442814 (scholarly article) → doc_type = 0x01 (논문)
ELIF P31 contains Q5707594 (news article) → doc_type = 0x02 (기사)
ELIF P31 contains Q17329259 (encyclopedic article) → doc_type = 0x03 (백과)
ELIF P31 contains Q7725634 (literary work) → 타입 0x32 LiteraryWork로 분류
ELSE → doc_type = 0x00 (Unknown)
```

**[REVIEW] Document 분리 검토:**
- 45M이 너무 많으면 ScholarlyArticle(0x??)을 별도 타입으로 분리 고려
- 또는 0x3F Other의 subtype으로 일부 이동

#### 3.1.2 Chemical (0x08) vs Compound (0x09) - 2.4M 개체

**문제점:**
- Chemical(Q113145171): 화학물질 일반
- Compound(Q11173): 화합물 (두 원소 이상 결합)
- 위키데이터에서 P31이 두 가지 모두에 해당하는 경우 다수

**검증 항목:**

| 검증 ID | 질문 | 방법 |
|---------|------|------|
| CHEM-1 | P31이 Chemical/Compound 모두인 개체 수는? | 중복 쿼리 |
| CHEM-2 | 분류 기준이 명확한가? | 화학 전문가 검토 |
| CHEM-3 | 두 타입의 스키마 필드가 적절히 구분되는가? | 필드 비교 |

**분류 규칙 제안:**

```
IF P31 contains Q11173 (chemical compound) → 0x09 Compound 우선
ELIF P31 contains Q113145171 (chemical entity) → 0x08 Chemical
ELIF P31 contains Q81163 (polymer) → 0x09 Compound (polymer 플래그)
ELSE → 0x08 Chemical (기본)
```

**Compound 정의 기준:**
- 두 개 이상의 다른 원소로 구성
- 화학 결합으로 연결
- 일정한 화학식 존재

**Chemical 정의 기준:**
- 순수 원소
- 혼합물
- 불특정 화학물질

#### 3.1.3 FictionalCharacter (0x07) - 98K 개체

**문제점:**
- 미디어 믹스 캐릭터: 만화→애니→영화→게임 등 여러 매체 등장
- 같은 캐릭터가 매체별로 다른 특성 (예: 스파이더맨 MCU vs 코믹스)
- franchise 필드 8비트(256개)로 커버 가능?

**검증 항목:**

| 검증 ID | 질문 | 방법 |
|---------|------|------|
| FICT-1 | 미디어 믹스 캐릭터의 "원본" 결정 규칙? | P1080 (from fictional universe) 분석 |
| FICT-2 | franchise 256개가 충분한가? | 위키데이터 P1080 카디널리티 |
| FICT-3 | medium 6비트(64개)가 매체 다양성 커버? | P31 하위 타입 분포 |
| FICT-4 | 실존 인물 기반 가상 캐릭터 처리? | 역사 인물 각색 사례 |

**분류 규칙 제안:**

```
# 캐릭터 분류 우선순위
IF P31 contains Q15632617 (fictional character):
    franchise = first(P1080)  # 최초 등장 프랜차이즈
    medium = first(P1441)     # 최초 등장 매체

# 미디어 믹스 처리
IF 여러 P1080 값:
    - 가장 오래된 출처 선택
    - 또는 가장 저명한(sitelinks 기준) 버전 선택
```

**[REVIEW] 캐릭터 버전 처리:**
- 같은 캐릭터의 다른 버전을 다른 SIDX로 인코딩할지?
- 예: "스파이더맨(코믹스)" vs "스파이더맨(MCU)" → 서로 다른 SIDX

#### 3.1.4 Organization 계열 (0x2C-0x2F) - 0.9M 개체

**문제점:**
- Organization(0x2C): 일반 조직
- Business(0x2D): 기업
- PoliticalParty(0x2E): 정당
- SportsTeam(0x2F): 스포츠팀
- 많은 조직이 여러 성격을 가짐 (예: 축구 구단이 주식회사인 경우)

**검증 항목:**

| 검증 ID | 질문 | 방법 |
|---------|------|------|
| ORG-1 | Business이면서 SportsTeam인 경우? | FC Barcelona, Manchester United |
| ORG-2 | Organization과 하위 타입 간 구분 기준? | P31 계층 분석 |
| ORG-3 | 정당의 산하 단체는 어디에? | 청년 조직, 노동조합 연계 |
| ORG-4 | 국제기구, NGO 분류? | P31 패턴 |

**분류 우선순위 제안:**

```
# 가장 구체적인 타입 우선
1. SportsTeam (0x2F) - P31 contains Q847017
2. PoliticalParty (0x2E) - P31 contains Q7278
3. Business (0x2D) - P31 contains Q4830453 (business)
4. Organization (0x2C) - default fallback

# 예외 규칙
IF 축구 구단이자 주식회사:
    → SportsTeam 우선 (핵심 활동 기준)
```

### 3.2 Medium-Risk Boundary Cases

#### 3.2.1 Mountain (0x14) vs Hill (0x15)

**경계 기준:**
- 위키데이터: Q8502 (mountain) vs Q54050 (hill)
- 일반적 기준: 300m 또는 600m 이상이면 Mountain

**검증:**
- P2044 (elevation) 분포 분석
- 300m 미만인데 Q8502로 분류된 사례
- 600m 이상인데 Q54050으로 분류된 사례

**분류 규칙:**
```
IF P31 = Q8502 (mountain) → 0x14 Mountain
ELIF P31 = Q54050 (hill) → 0x15 Hill
ELIF P2044 (elevation) >= 300m → 0x14 Mountain
ELSE → 0x15 Hill
```

#### 3.2.2 Settlement (0x1C) vs Village (0x1D) vs Hamlet (0x1E)

**경계 기준:**
- Settlement: 일반 정주지
- Village: 마을 (일정 인구/행정 단위)
- Hamlet: 소촌 (행정 단위 미달)

**검증:**
- P31 계층: Q486972 (human settlement) > Q532 (village) > Q5084 (hamlet)
- 인구 기준 적용 가능 여부

**분류 규칙:**
```
IF P31 contains Q5084 (hamlet) → 0x1E Hamlet
ELIF P31 contains Q532 (village) → 0x1D Village
ELIF P31 contains Q486972 (human settlement) → 0x1C Settlement
```

**[NOTE] 스키마 통합:**
- 세 타입이 동일 스키마 사용 (settlement_type 필드로 구분)
- 타입 코드 분리는 쿼리 최적화 목적

#### 3.2.3 River (0x16) vs Stream (0x18)

**경계 기준:**
- River: 강 (일정 규모 이상)
- Stream: 시내, 개울

**검증:**
- P2043 (length) 분포
- Strahler stream order 적용 가능 여부

**분류 규칙:**
```
IF P31 contains Q4022 (river) → 0x16 River
ELIF P31 contains Q47521 (stream) → 0x18 Stream
ELIF length >= 50km → 0x16 River
ELSE → 0x18 Stream
```

#### 3.2.4 Building (0x24) vs Structure (0x28)

**경계 기준:**
- Building: 건물 (거주/사용 공간)
- Structure: 구조물 (탑, 댐, 기념비 등)

**검증:**
- P31 계층: Q41176 (building) vs Q811979 (architectural structure)
- use 필드로 구분 가능 여부

### 3.3 Low-Risk Boundary Cases

| 타입 쌍 | 경계 기준 | 분류 규칙 |
|---------|-----------|-----------|
| Gene vs Protein | Q7187 vs Q8054 | P31 직접 매핑 |
| Star vs Galaxy | Q523 vs Q318 | P31 직접 매핑 |
| Film vs TVSeries | Q11424 vs Q5398426 | P31 직접 매핑 |
| Album vs MusicalWork | Q482994 vs Q105543609 | 앨범=컬렉션, 작품=개별곡 |

---

## 4. P31 Hierarchy Alignment

### 4.1 Wikidata P31 Structure

위키데이터 P31(instance of)은 계층적 분류 체계를 형성한다. GEUL 64 타입과의 정합성 검증.

```
Q35120 (entity)
├── Q5 (human) → 0x00 Human
├── Q16521 (taxon) → 0x01 Taxon
├── Q7187 (gene) → 0x02 Gene
├── Q8054 (protein) → 0x03 Protein
├── Q43229 (organization)
│   ├── Q4830453 (business) → 0x2D Business
│   ├── Q7278 (political party) → 0x2E PoliticalParty
│   └── Q847017 (sports team) → 0x2F SportsTeam
├── Q2221906 (geographic location)
│   ├── Q8502 (mountain) → 0x14 Mountain
│   ├── Q4022 (river) → 0x16 River
│   └── Q486972 (settlement) → 0x1C Settlement
...
```

### 4.2 Alignment Validation

**Step 1: 직접 매핑 검증**
```sql
SELECT
    et.code,
    et.name_en,
    et.qid as expected_qid,
    COUNT(e.qid) as entity_count,
    COUNT(CASE WHEN e.p31_values @> jsonb_build_array(et.qid) THEN 1 END) as direct_match,
    ROUND(100.0 * COUNT(CASE WHEN e.p31_values @> jsonb_build_array(et.qid) THEN 1 END) / COUNT(e.qid), 2) as match_rate
FROM entity_types_64 et
LEFT JOIN wikidata.entities e ON e.p31_values @> jsonb_build_array(et.qid)
GROUP BY et.code, et.name_en, et.qid
ORDER BY et.code;
```

**Step 2: 누락된 P31 패턴 탐지**
- 각 EntityType에 매핑되어야 하지만 다른 P31 값을 가진 개체 식별
- 예: Mountain에 매핑되어야 하지만 P31="Q46831" (mountain range)인 경우

**Step 3: P279(subclass of) 체인 검증**
- EntityType의 qid에서 P279를 따라 올라갔을 때 일관된 상위 개념인지 확인

### 4.3 Mapping Table

| EntityType | Primary QID | Alternative QIDs | Notes |
|------------|-------------|------------------|-------|
| 0x00 Human | Q5 | Q15632617 (fictional) 제외 | |
| 0x01 Taxon | Q16521 | Q310890 (monotypic), Q55983715 | |
| 0x08 Chemical | Q113145171 | Q79529 (chemical substance) | |
| 0x09 Compound | Q11173 | Q81163 (polymer) | |
| 0x2C Organization | Q43229 | Q783794 (company), Q6881511 | 하위타입 제외 |
| 0x31 Document | Q49848 | Q13442814, Q5707594, Q17329259 | 통합 타입 |

### 4.4 Expected Outputs

| 산출물 | 형식 | 용도 |
|--------|------|------|
| `p31_alignment_report.md` | Markdown | 정합성 검증 결과 |
| `qid_mapping_table.json` | JSON | 타입별 QID 매핑 |
| `unmapped_p31_patterns.csv` | CSV | 매핑 규칙에 없는 P31 패턴 |

---

## 5. Schema Field Validation

### 5.1 Field Coverage Analysis

각 EntityType의 48비트 필드가 해당 타입의 핵심 속성을 포착하는지 검증.

**검증 방법:**
```sql
-- 타입별 Property 사용 빈도 vs 스키마 필드 커버리지
SELECT
    et.code,
    et.name_en,
    p.property_id,
    p.property_label,
    p.usage_count,
    p.coverage_rate,
    CASE WHEN s.property IS NOT NULL THEN 'Covered' ELSE 'Not in Schema' END as schema_status
FROM entity_types_64 et
JOIN property_usage p ON p.entity_type = et.code
LEFT JOIN type_schemas_properties s ON s.type_code = et.code AND s.property = p.property_id
WHERE p.coverage_rate > 10  -- 10% 이상 사용되는 속성
ORDER BY et.code, p.coverage_rate DESC;
```

### 5.2 Type-Specific Validation

#### 5.2.1 Human (0x00) Schema Validation

| 필드 | 비트 | Property | 커버리지 목표 | 검증 질문 |
|------|------|----------|--------------|-----------|
| subclass | 5 | - | - | 32개 소분류가 주요 인물 유형 커버? |
| occupation | 6 | P106 | 80%+ | 64개 직업이 충분? |
| country | 8 | P27 | 95%+ | 256개 국가가 역사 국가 포함? |
| era | 4 | P569 | 90%+ | 16개 시대 구분이 적절? |
| gender | 2 | P21 | 98%+ | 4개로 충분 (Unknown, M, F, Other) |
| notability | 3 | sitelinks | 100% | 8단계 구분이 의미있는 변별력? |
| language | 6 | P1412 | 50%+ | 64개 언어가 충분? |
| birth_region | 6 | P19 | 70%+ | 국가 종속 64개 지역이 충분? |
| activity_field | 4 | P101 | 40%+ | 16개 분야가 적절? |

#### 5.2.2 Document (0x31) Schema Validation - Critical

| 필드 | 비트 | Property | 검증 질문 |
|------|------|----------|-----------|
| language | 8 | P407 | 학술 논문 언어 분포가 256개로 커버? |
| year | 7 | P577 | 1900-2027로 대부분 커버? 고문서 처리? |
| doc_type | 6 | P31 | 논문/기사/백과 등 64개로 충분? |
| subject | 6 | P921 | 학문 분야 64개가 적절? OECD FOS 참조 |
| publisher | 6 | P123 | 출판사 유형 64개? |
| length_class | 5 | P1104 | 페이지 수 32단계? |
| citations | 4 | - | 인용수 16단계? |
| access | 3 | P6954 | Open/Closed 등 8개? |
| format | 3 | - | PDF/HTML 등 8개? |

**[REVIEW] Document 충돌률 시뮬레이션:**
```python
# 48비트 엔트로피 계산
# 목표: H > 45.5 bits (충돌률 1% for 45M entities)
# 필요 조건: 2^48 / 45M ≈ 6200 slots per entity
```

#### 5.2.3 Organization (0x2C) Schema Validation

| 필드 | 비트 | Property | 검증 질문 |
|------|------|----------|-----------|
| country | 8 | P17 | 다국적 기업 본사 국가 결정 기준? |
| org_type | 4 | - | 16개 조직 유형이 충분? |
| legal_form | 6 | P1454 | 국가별 법인 형태 64개? |
| industry | 8 | P452 | ISIC 기준 256개 산업? |
| era | 4 | P571 | 설립 시대 16개? |
| size | 4 | - | 직원 수/매출 기준 16단계? |
| hq_region | 6 | P159 | 국가 종속 64개 지역? |
| status | 3 | P576 | 활동/폐업/합병 등 8개? |
| ideology | 3 | P1142 | 정당용 8개 이념? |
| sector | 2 | - | 공공/민간/비영리/혼합 4개? |

### 5.3 Field Semantic Validation

**Step 1: 필드 값 분포 분석**
- 각 필드의 실제 값 분포가 비트 할당과 일치하는지 확인
- 예: country 8비트(256개) 할당인데 실제 150개 국가만 사용되면 OK
- 반대로 300개 국가가 필요하면 문제

**Step 2: 종속 필드 검증**
- country → admin_code 종속 관계에서 각 국가별 실제 행정구역 수 확인
- 예: 미국 50개 주, 중국 34개 성급 행정구 → 8비트(256개)로 충분

**Step 3: 양자화 정확도 검증**
- 연속값(고도, 인구, 좌표)의 양자화가 의미 있는 구분을 만드는지
- 예: 인구 4비트(16단계) → 로그 스케일 적용 시 100 ~ 10억 커버 가능

### 5.4 Expected Outputs

| 산출물 | 형식 | 용도 |
|--------|------|------|
| `field_coverage_report.md` | Markdown | 필드별 Property 커버리지 |
| `field_distribution.csv` | CSV | 필드 값 분포 통계 |
| `schema_gaps.json` | JSON | 스키마에 없지만 중요한 Property 목록 |

---

## 6. Validation Execution Plan

### 6.1 Phase 1: Data Preparation (2 days)

| Task | Description | Output |
|------|-------------|--------|
| 1.1 | P31 매핑 테이블 생성 | `geulwork.entity_type_map` |
| 1.2 | Property 사용 통계 수집 | `geulwork.property_usage_stats` |
| 1.3 | 타입별 샘플 추출 (10K/type) | `geulwork.type_samples` |

### 6.2 Phase 2: MECE Validation (3 days)

| Task | Description | Output |
|------|-------------|--------|
| 2.1 | 다중 매핑 개체 식별 | `overlap_matrix.csv` |
| 2.2 | 매핑 불가 개체 분석 | `unmapped_entities.json` |
| 2.3 | 분류 우선순위 규칙 정의 | `mapping_rules.md` |

### 6.3 Phase 3: Boundary Case Analysis (5 days)

| Task | Description | Priority |
|------|-------------|----------|
| 3.1 | Document 45M 분석 | Critical |
| 3.2 | Chemical/Compound 경계 | High |
| 3.3 | Organization 계열 분류 | High |
| 3.4 | FictionalCharacter 미디어믹스 | Medium |
| 3.5 | Geography 타입 경계 | Medium |

### 6.4 Phase 4: P31 Alignment (2 days)

| Task | Description | Output |
|------|-------------|--------|
| 4.1 | QID 직접 매핑 검증 | `p31_alignment_report.md` |
| 4.2 | 누락 패턴 탐지 | `unmapped_p31_patterns.csv` |
| 4.3 | 매핑 테이블 완성 | `qid_mapping_table.json` |

### 6.5 Phase 5: Schema Field Validation (3 days)

| Task | Description | Priority |
|------|-------------|----------|
| 5.1 | Human 스키마 검증 | High |
| 5.2 | Document 스키마 검증 | Critical |
| 5.3 | Organization 스키마 검증 | High |
| 5.4 | 기타 타입 스키마 검증 | Medium |

### 6.6 Phase 6: Report & Resolution (2 days)

| Task | Description | Output |
|------|-------------|--------|
| 6.1 | 종합 검증 보고서 | `04_ontology_validation_report.md` |
| 6.2 | 스키마 수정 제안 | `schema_amendments.json` |
| 6.3 | 분류 규칙 문서화 | `classification_rules.md` |

### 6.7 Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1 | Day 1-2 | DB access |
| Phase 2 | Day 3-5 | Phase 1 |
| Phase 3 | Day 6-10 | Phase 2 |
| Phase 4 | Day 11-12 | Phase 1 |
| Phase 5 | Day 13-15 | Phase 3, 4 |
| Phase 6 | Day 16-17 | Phase 2-5 |
| **Total** | **17 days** | |

---

## 7. Critical Issues & Resolutions

### 7.1 Issue Tracking Template

```markdown
## [ISSUE-XXX] Title

**Severity:** Critical / High / Medium / Low
**Status:** Open / In Progress / Resolved
**Affected Types:** 0xNN, 0xNN

### Description
[문제 설명]

### Impact
[영향 범위]

### Proposed Resolution
[해결 방안]

### Decision
[결정 사항]

### Action Items
- [ ] Task 1
- [ ] Task 2
```

### 7.2 Pre-identified Issues

#### [ISSUE-001] Document 타입 과대 규모

**Severity:** Critical
**Status:** Open
**Affected Types:** 0x31 Document

**Description:**
Document 타입에 45M 개체가 할당되어 전체의 ~50%를 차지. 48비트로 충돌률 1% 달성 가능성 검증 필요.

**Impact:**
- 충돌률 목표 미달 시 SIDX 유니크성 손상
- LLM 인코딩 시 모호성 증가

**Proposed Resolution:**
1. Document 내 doc_type 필드로 세분화 강화
2. 필요시 ScholarlyArticle을 별도 타입으로 분리
3. 또는 충돌 허용하고 Triple로 구분

**Decision:** [검증 후 결정]

#### [ISSUE-002] Chemical/Compound 경계 모호

**Severity:** High
**Status:** Open
**Affected Types:** 0x08 Chemical, 0x09 Compound

**Description:**
두 타입의 정의가 위키데이터에서 중첩됨. P31이 두 타입 모두에 해당하는 개체 다수.

**Proposed Resolution:**
1. Compound 우선 규칙 적용 (화합물 정의에 맞으면 Compound)
2. Chemical은 순수 원소, 혼합물, 불특정 물질로 제한
3. 스키마 필드 차별화 강화

#### [ISSUE-003] FictionalCharacter 미디어 믹스

**Severity:** Medium
**Status:** Open
**Affected Types:** 0x07 FictionalCharacter

**Description:**
같은 캐릭터가 여러 매체에 등장할 때 어떤 버전을 기준으로 인코딩할지 불명확.

**Proposed Resolution:**
1. 최초 등장 매체/프랜차이즈 기준
2. 또는 가장 저명한 버전 기준
3. 필요시 캐릭터 버전별로 다른 SIDX 허용

#### [ISSUE-004] Organization 계열 중첩

**Severity:** High
**Status:** Open
**Affected Types:** 0x2C-0x2F

**Description:**
축구 구단이 주식회사이면서 스포츠팀인 경우 등 다중 분류 필요.

**Proposed Resolution:**
1. "핵심 활동" 기준으로 가장 구체적인 타입 선택
2. 우선순위: SportsTeam > PoliticalParty > Business > Organization
3. org_type 필드로 부차적 성격 표현

---

## 8. Acceptance Criteria

### 8.1 MECE Validation

| Metric | Target | Measurement |
|--------|--------|-------------|
| 단일 매핑 비율 | >= 99% | 정확히 하나의 타입에 매핑되는 개체 비율 |
| 매핑 불가 비율 | <= 0.1% | 어떤 타입에도 매핑 안 되는 개체 비율 |
| 분류 규칙 커버리지 | 100% | 모든 다중 매핑 케이스에 규칙 존재 |

### 8.2 Boundary Cases

| Metric | Target | Measurement |
|--------|--------|-------------|
| Critical 이슈 해결 | 100% | Document, Chemical/Compound |
| High 이슈 해결 | >= 80% | Organization 계열 등 |
| 분류 규칙 문서화 | 100% | 모든 경계 케이스에 명시적 규칙 |

### 8.3 P31 Alignment

| Metric | Target | Measurement |
|--------|--------|-------------|
| 직접 매핑 정확도 | >= 95% | 기대 QID와 실제 P31 일치율 |
| 누락 패턴 | <= 5% | 매핑 규칙에 없는 P31 비율 |
| 계층 일관성 | 100% | P279 체인 무모순성 |

### 8.4 Schema Fields

| Metric | Target | Measurement |
|--------|--------|-------------|
| 핵심 Property 커버리지 | >= 80% | 10% 이상 사용 속성의 스키마 포함 비율 |
| 필드 값 오버플로 | 0% | 할당 비트 초과하는 값 없음 |
| 충돌률 (Document) | <= 1% | 동일 SIDX에 다른 개체 매핑 비율 |

---

## 9. Deliverables

### 9.1 Reports

| 문서 | 내용 | 경로 |
|------|------|------|
| 종합 검증 보고서 | 전체 검증 결과 요약 | `output/04_ontology_validation_report.md` |
| MECE 분석 보고서 | 다중/무매핑 분석 | `output/mece_analysis.md` |
| 경계 사례 분석 | 각 타입 쌍 분석 | `output/boundary_cases.md` |
| P31 정합성 보고서 | 위키데이터 매핑 검증 | `output/p31_alignment.md` |
| 스키마 검증 보고서 | 필드별 커버리지 | `output/schema_validation.md` |

### 9.2 Data Files

| 파일 | 내용 | 경로 |
|------|------|------|
| 타입 중첩 매트릭스 | 타입 쌍별 중복 개체 수 | `output/overlap_matrix.csv` |
| QID 매핑 테이블 | 타입-QID 매핑 | `output/qid_mapping_table.json` |
| 분류 규칙 | 경계 사례 처리 규칙 | `output/classification_rules.json` |
| 스키마 수정 제안 | 검증 후 수정 사항 | `output/schema_amendments.json` |

### 9.3 Database Tables (geulwork)

| 테이블 | 내용 |
|--------|------|
| `ontology_overlap` | 타입 쌍별 중복 개체 |
| `ontology_unmapped` | 매핑 불가 개체 |
| `ontology_p31_mapping` | P31-타입 매핑 규칙 |
| `ontology_field_stats` | 필드별 값 분포 통계 |

---

## 10. Review Checklist

### [REVIEW] Critical Items

- [ ] Document 45M 충돌률 1% 달성 가능성 검증
- [ ] Chemical vs Compound 분류 기준 확정
- [ ] Organization 계열 우선순위 규칙 확정
- [ ] FictionalCharacter 미디어 믹스 처리 방침

### [REVIEW] High Priority Items

- [ ] Human subclass 32개 목록 확정
- [ ] Taxon 생물 분류 계층 축소 방식
- [ ] Gene/Protein 스키마 생물학 전문가 검토
- [ ] Document doc_type 64개 목록

### [REVIEW] Medium Priority Items

- [ ] Mountain vs Hill 고도 기준 (300m vs 600m)
- [ ] Settlement/Village/Hamlet 인구 기준
- [ ] franchise 코드북 256개 선정
- [ ] sport 종목 코드북 64개

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-02-01 | Initial plan |

---

*GEUL Entity Team - Ontology Validation Plan*
*Author: Ontologist*
*Date: 2026-02-01*
