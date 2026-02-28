# GEUL Entity SIDX Analyst Plan

**작성일**: 2026-02-01
**역할**: Analyst
**버전**: v1.0

---

## 1. 현재 상태 요약

### 1.1 Stage 1 완료 현황

| 상태 | 타입 코드 | 타입명 | 개체수 | 추출 속성 |
|------|----------|--------|--------|----------|
| 완료 | 0x00 | 인간 | 12.5M | 72개 |
| 완료 | 0x01 | 생물종 | 3.8M | 30개 |
| 완료 | 0x02 | 유전자 | 1.2M | 23개 |
| 완료 | 0x03 | 단백질 | 1.0M | 12개 |
| 완료 | 0x04 | 세포주 | 153K | 9개 |
| 완료 | 0x05 | 가문명 | 661K | 14개 |
| 완료 | 0x06 | 이름 | 128K | 11개 |
| ... | ... | ... | ... | ... |
| 완료 | **전체 63개** | - | - | 평균 17.8개 |

**geulwork.entity_type_map**: 63개 타입 등록됨
**geulwork.property_stats**: 총 1,106개 속성-타입 조합 저장됨

### 1.2 Stage 2 현재 상태

| 분석 완료 | 타입명 | DAG 간선 수 |
|----------|--------|------------|
| 완료 | 인간 (0x00) | 99 |
| 완료 | 생물종 (0x01) | 104 |
| 완료 | 유전자 (0x02) | 82 |
| 완료 | 단백질 (0x03) | 51 |
| 완료 | 세포주 (0x04) | 26 |
| 완료 | 가문명 (0x05) | 68 |
| 완료 | 이름 (0x06) | 42 |
| **미완료** | 나머지 56개 | - |

---

## 2. Stage 1 보완 필요 사항

### 2.1 분석 완료 상태

Stage 1은 **63개 타입 전체 완료**. entity_type_map과 property_stats 테이블에 결과 저장됨.

### 2.2 [REVIEW] 데이터 품질 확인 필요 타입

샘플 수가 예상보다 현저히 적은 타입들:

| 타입 코드 | 타입명 | 예상 개체수 | 실제 샘플 | 비율 |
|----------|--------|------------|----------|------|
| 0x09 | 화합물 | 1,061,080 | 53 | 0.005% |
| 0x0A | 광물 | 62,000 | 0 | 0% |
| 0x10 | 행성 | 15,000 | 12 | 0.08% |
| 0x11 | 성운 | 8,000 | 0 | 0% |
| 0x13 | 위성 | 3,000 | 57 | 1.9% |

**원인 분석 필요:**
1. QID 매핑 오류 가능성 (P31 값이 다른 Q-ID 사용)
2. 하위 타입으로 분산되어 있을 가능성
3. 데이터 누락

**확인 SQL:**
```sql
-- 화합물 관련 P31 값 분포 확인
SELECT t.object_value, COUNT(*) as cnt
FROM triples t
WHERE t.property = 'P31'
  AND t.object_value IN (
    SELECT subject FROM triples
    WHERE property = 'P279' AND object_value = 'Q11173'
  )
GROUP BY t.object_value
ORDER BY cnt DESC
LIMIT 20;
```

### 2.3 우선순위 재정의

**1순위: 개체수 100만 이상 (9개)**
- 0x00 인간 (12.5M) - 완료
- 0x31 문서 (45M) - 완료 (샘플 50K)
- 0x01 생물종 (3.8M) - 완료
- 0x0C 항성 (3.6M) - Stage 2 필요
- 0x0D 은하 (2.1M) - Stage 2 필요
- 0x08 화학물질 (1.3M) - Stage 2 필요
- 0x02 유전자 (1.2M) - 완료
- 0x09 화합물 (1.1M) - [REVIEW] 데이터 확인 필요
- 0x30 그림 (1.0M) - Stage 2 필요
- 0x03 단백질 (1.0M) - 완료

---

## 3. Stage 2 분석 계획

### 3.1 조건부 엔트로피 계산 방법론

현재 구현된 방법:
```
H(B|A) = Σ p(a) * H(B|A=a)
I(A;B) = H(B) - H(B|A)
NMI = I(A;B) / min(H(A), H(B))
```

**종속 판별 기준:**
- NMI > 0.3 이면 종속 관계로 판정
- H(B|A) < H(A|B) 이면 A → B (A가 B를 결정)

### 3.2 [REVIEW] MI 임계값 0.3 검토

**현재 Human(0x00) 결과 분석:**

상위 종속 관계 (NMI > 0.9):
| Parent | Child | NMI | 해석 |
|--------|-------|-----|------|
| P227 (GND ID) | P214 (VIAF ID) | 0.999 | 외부 ID 간 상관 |
| P214 (VIAF ID) | P10832 (WorldCat ID) | 0.999 | 외부 ID 간 상관 |
| P213 (ISNI) | P214 (VIAF ID) | 0.998 | 외부 ID 간 상관 |

**문제점 발견:**
- 현재 DAG는 **외부 식별자(ID) 간 상관**을 많이 포착함
- 이는 SIDX 설계에 **무의미한 종속 관계**
- SIDX에서 외부 ID는 Triple로 분리되므로 제외 필요

**제안: 외부 ID 속성 필터링**
```sql
-- 외부 ID 속성 목록 (datatype = 'external-id')
SELECT property_id, label_en
FROM properties_meta
WHERE datatype = 'external-id';
```

**조정안:**
1. `datatype = 'external-id'` 속성 제외
2. P18(image) 등 미디어 속성 제외
3. MI 임계값은 0.3 유지 (충분히 보수적)

### 3.3 샘플 크기 결정 기준

**현재**: 50,000개 고정

**분석:**
- Human 12.5M에서 50K는 0.4% - 통계적으로 충분
- Star 3.6M에서 50K는 1.4% - 충분
- Planet 15K에서 12개는 0.08% - **불충분**

**제안 기준:**
| 전체 개체수 | 샘플 크기 | 비율 |
|------------|----------|------|
| 1M 이상 | 50,000 | 0.1-5% |
| 100K-1M | 30,000 | 3-30% |
| 10K-100K | min(전체, 10,000) | 10-100% |
| 10K 미만 | 전체 | 100% |

### 3.4 Stage 2 실행 우선순위

**1차 (즉시):** 개체수 100만 이상 + 데이터 충분
```bash
python scripts/stage2_dependency.py 0x0C 0x0D 0x08 0x30
```

**2차:** 중요 타입 (장소, 조직, 창작물)
```bash
python scripts/stage2_dependency.py 0x1C 0x2C 0x33 0x34
```

**3차:** 나머지 전체
```bash
python scripts/stage2_dependency.py
```

---

## 4. Stage 3 지원 분석

### 4.1 충돌률 시뮬레이션 방법

**목표:** 48비트에 속성을 할당했을 때, 서로 다른 개체가 동일 SIDX를 갖는 비율

**시뮬레이션 절차:**
```python
def estimate_collision(entity_type, bit_allocation, sample_size=50000):
    # 1. 샘플 개체 로드
    entities = load_sample(entity_type, sample_size)

    # 2. 각 개체를 48비트로 인코딩
    sidx_list = []
    for e in entities:
        sidx = encode_48bit(e, bit_allocation)
        sidx_list.append(sidx)

    # 3. 중복 계산
    unique = len(set(sidx_list))
    collision_rate = 1 - (unique / len(sidx_list))

    return collision_rate
```

**확인 SQL (사전 분석용):**
```sql
-- 주요 속성 조합의 고유값 수 확인 (Human)
SELECT
    COUNT(DISTINCT CONCAT(
        COALESCE((SELECT object_value FROM triples WHERE subject = e.id AND property = 'P21' LIMIT 1), 'X'),
        COALESCE((SELECT object_value FROM triples WHERE subject = e.id AND property = 'P27' LIMIT 1), 'X'),
        COALESCE((SELECT object_value FROM triples WHERE subject = e.id AND property = 'P106' LIMIT 1), 'X')
    )) as unique_combos,
    COUNT(*) as total
FROM (
    SELECT DISTINCT subject as id FROM triples
    WHERE property = 'P31' AND object_value = 'Q5' LIMIT 50000
) e;
```

### 4.2 비트 할당 최적화 입력 데이터

Stage 3에 필요한 입력:

1. **property_stats 테이블** (완료)
   - 속성별 커버리지, 카디널리티, 엔트로피

2. **dependency_dag 테이블** (진행중)
   - 속성 간 종속 관계 DAG

3. **양자화 규칙** (quantization_rules.json - 완료)
   - 연속값 → 이산값 변환 규칙

4. **코드 공간 추정** (신규 필요)
   - 각 속성의 실제 사용 값 분포

**신규 테이블 제안: `property_value_dist`**
```sql
CREATE TABLE property_value_dist (
    entity_type INTEGER NOT NULL,
    property_id TEXT NOT NULL,
    value_code TEXT NOT NULL,      -- 양자화된 값
    frequency INTEGER NOT NULL,
    cumulative_freq REAL,          -- 누적 비율
    PRIMARY KEY (entity_type, property_id, value_code)
);
```

---

## 5. 필요한 SQL 쿼리 목록

### 5.1 Stage 1 보완 쿼리

```sql
-- Q1: 데이터 부족 타입의 실제 P31 분포 확인
SELECT t.object_value, l.label, COUNT(*) as cnt
FROM triples t
LEFT JOIN entity_labels l ON t.object_value = l.entity_id AND l.language = 'en'
WHERE t.property = 'P31'
  AND t.subject IN (
    SELECT subject FROM triples WHERE property = 'P31' AND object_value = 'Q11173'
  )
GROUP BY t.object_value, l.label
ORDER BY cnt DESC
LIMIT 30;

-- Q2: 특정 QID의 하위 타입 목록
SELECT t.subject, l.label, COUNT(*) as instance_count
FROM triples t
JOIN entity_labels l ON t.subject = l.entity_id AND l.language = 'en'
WHERE t.property = 'P279' AND t.object_value = 'Q11173'  -- subclass of Compound
GROUP BY t.subject, l.label
ORDER BY instance_count DESC
LIMIT 20;
```

### 5.2 Stage 2 쿼리

```sql
-- Q3: 외부 ID 속성 목록 (제외 대상)
SELECT property_id, label_en, usage_count
FROM properties_meta
WHERE datatype = 'external-id'
ORDER BY usage_count DESC;

-- Q4: 의미있는 속성만 필터링
SELECT ps.property_id, pm.label_en, ps.coverage, ps.cardinality, ps.entropy
FROM property_stats ps
JOIN properties_meta pm ON ps.property_id = pm.property_id
WHERE ps.entity_type = 0  -- Human
  AND pm.datatype NOT IN ('external-id', 'commonsMedia')
  AND ps.coverage > 0.1
ORDER BY ps.coverage DESC, ps.entropy DESC
LIMIT 15;

-- Q5: 현재 DAG에서 외부 ID 제거 후 결과
SELECT d.parent_prop, d.child_prop, d.mutual_info, d.normalized_mi
FROM dependency_dag d
JOIN properties_meta pm1 ON d.parent_prop = pm1.property_id
JOIN properties_meta pm2 ON d.child_prop = pm2.property_id
WHERE d.entity_type = 0
  AND pm1.datatype NOT IN ('external-id', 'commonsMedia')
  AND pm2.datatype NOT IN ('external-id', 'commonsMedia')
ORDER BY d.mutual_info DESC
LIMIT 20;
```

### 5.3 Stage 3 준비 쿼리

```sql
-- Q6: 속성값 분포 (코드북 생성용)
SELECT t.object_value, l.label, COUNT(*) as cnt,
       ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER() * 100, 2) as pct
FROM triples t
LEFT JOIN entity_labels l ON t.object_value = l.entity_id AND l.language = 'en'
WHERE t.property = 'P21'  -- sex or gender
  AND t.subject IN (
    SELECT subject FROM triples WHERE property = 'P31' AND object_value = 'Q5' LIMIT 50000
  )
GROUP BY t.object_value, l.label
ORDER BY cnt DESC
LIMIT 20;

-- Q7: 복합 키 고유값 수 (충돌률 추정용)
WITH sample AS (
    SELECT DISTINCT subject FROM triples
    WHERE property = 'P31' AND object_value = 'Q5' LIMIT 50000
),
attrs AS (
    SELECT
        s.subject,
        MAX(CASE WHEN t.property = 'P21' THEN t.object_value END) as gender,
        MAX(CASE WHEN t.property = 'P27' THEN t.object_value END) as country,
        MAX(CASE WHEN t.property = 'P106' THEN t.object_value END) as occupation
    FROM sample s
    LEFT JOIN triples t ON s.subject = t.subject AND t.property IN ('P21', 'P27', 'P106')
    GROUP BY s.subject
)
SELECT
    COUNT(*) as total,
    COUNT(DISTINCT CONCAT(gender, '|', country, '|', occupation)) as unique_combos,
    ROUND(1 - COUNT(DISTINCT CONCAT(gender, '|', country, '|', occupation))::numeric / COUNT(*), 4) as collision_rate
FROM attrs;
```

### 5.4 데이터 품질 확인 쿼리

```sql
-- Q8: 속성 누락률 확인
SELECT
    ps.property_id,
    pm.label_en,
    ps.coverage,
    ROUND((1 - ps.coverage) * 100, 1) as missing_pct
FROM property_stats ps
JOIN properties_meta pm ON ps.property_id = pm.property_id
WHERE ps.entity_type = 0
  AND pm.datatype NOT IN ('external-id')
ORDER BY ps.coverage DESC;

-- Q9: 이상값 탐지 (카디널리티 vs 커버리지)
SELECT
    ps.property_id,
    pm.label_en,
    ps.coverage,
    ps.cardinality,
    CASE
        WHEN ps.cardinality > 10000 AND ps.coverage > 0.5 THEN 'HIGH_CARD_HIGH_COV'
        WHEN ps.cardinality < 10 AND ps.coverage > 0.9 THEN 'LOW_CARD_HIGH_COV'
        ELSE 'NORMAL'
    END as flag
FROM property_stats ps
JOIN properties_meta pm ON ps.property_id = pm.property_id
WHERE ps.entity_type = 0;
```

---

## 6. 데이터 품질 이슈

### 6.1 발견된 문제점

#### 6.1.1 외부 ID 오염
- **문제**: dependency_dag에 외부 ID 간 상관이 대량 포함
- **영향**: 실제 의미적 종속 관계 파악 어려움
- **해결**: Stage 2 재실행 시 datatype='external-id' 제외

#### 6.1.2 QID 매핑 불일치
- **문제**: 일부 타입 (화합물, 광물, 성운)의 샘플 수 극히 적음
- **원인 추정**:
  - P31 값이 하위 타입 Q-ID로 설정됨
  - entity_types_64.json의 QID가 실제 사용과 불일치
- **해결**: Q-ID 재검증 및 하위 타입 통합 쿼리 필요

#### 6.1.3 다중값 속성 처리
- **문제**: 현재 첫 번째 값만 사용 (occupation 등 다중값 가능)
- **영향**: 정보 손실 및 엔트로피 과소 추정
- **해결**:
  - 주된 값(preferred rank) 선택
  - 또는 다중값 조합을 새 값으로 처리

### 6.2 예상 문제점

#### 6.2.1 시간 데이터 파싱
- P569(date of birth), P577(publication date) 등
- ISO 8601 형식, 부분 날짜(연도만), 불확실 날짜 등 혼재
- 양자화 시 파싱 로직 필요

#### 6.2.2 좌표 데이터 형식
- P625(coordinates) 값 형식 확인 필요
- WKT, JSON, 또는 별도 qualifier로 저장되었을 수 있음

#### 6.2.3 언어별 레이블 누락
- 일부 개체는 영어 레이블 없음
- 코드북 생성 시 fallback 전략 필요

### 6.3 [REVIEW] 결정 필요 사항

1. **QID 재매핑 여부**
   - 옵션 A: 하위 타입까지 포함하는 재귀 쿼리
   - 옵션 B: entity_types_64.json QID 수정
   - 권장: 옵션 A (데이터 기반 적응)

2. **다중값 처리 정책**
   - 옵션 A: 첫 번째 값만 (현재)
   - 옵션 B: preferred rank 값
   - 옵션 C: 가장 빈번한 값
   - 권장: 옵션 B

3. **외부 ID 제외 범위**
   - 옵션 A: datatype='external-id' 전체 제외
   - 옵션 B: 일부 유지 (P18 image 등은 유의미)
   - 권장: 옵션 A + P18 등 미디어도 제외

---

## 7. 실행 계획

### 7.1 즉시 실행 (Day 1)

1. **Q-ID 검증 쿼리 실행**
   - 화합물, 광물, 성운 등 데이터 부족 타입 원인 파악

2. **Stage 2 스크립트 수정**
   - 외부 ID 속성 필터링 추가
   - 샘플 크기 동적 조정

3. **Human (0x00) DAG 재분석**
   - 외부 ID 제외 후 결과 확인

### 7.2 단기 (Day 2-3)

1. **Stage 2 전체 타입 실행**
   ```bash
   python scripts/stage2_dependency.py
   ```

2. **property_value_dist 테이블 생성**
   - 코드북 생성 준비

### 7.3 중기 (Day 4-5)

1. **Stage 3 충돌률 시뮬레이션**
2. **type_schemas.json 검증**
   - 기정의 스키마 vs 데이터 기반 최적 할당 비교

---

## 8. 참고 자료

- `references/entity_types_64.json`: 64개 EntityType 정의
- `references/type_schemas.json`: 5개 타입 스키마 초안
- `references/quantization_rules.json`: 양자화 규칙
- `references/pipeline.md`: 전체 파이프라인 상세
- `cache/db_schema.md`: DB 스키마 캐시
- `output/stage1_report.md`: Stage 1 보고서

---

*Analyst: Claude Opus 4.5*
*Generated: 2026-02-01*
