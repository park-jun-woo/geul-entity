# GEUL Entity SIDX Builder 구현 계획

**작성일:** 2026-02-01
**버전:** v1.0

---

## 1. 현재 스크립트 상태 점검

### 1.1 Stage 1 (stage1_run.py) - 완성도: 95%

**현황:**
- 379줄, 64개 타입 대상 속성 통계 추출 구현 완료
- `entity_types_64.json` 기반 타입 로드
- 커버리지, 카디널리티, 엔트로피 계산 구현
- 보고서 생성 기능 정상 동작

**실행 결과:**
- 63/64개 타입 처리 완료 (stage1_report.md 확인)
- 인간 타입: 50,000 샘플에서 72개 속성 추출

**수정 필요 사항:**
- (경미) `output1/` 디렉토리 → `output/`로 통일 권장
- (경미) 속성 레이블 조회 시 `entity_labels` 테이블 사용 추가 고려

### 1.2 Stage 2 (stage2_dependency.py) - 완성도: 90%

**현황:**
- 407줄, 조건부 엔트로피 기반 종속 관계 탐지
- MI threshold 0.3, 상위 15개 속성 대상
- 사이클 제거 알고리즘 구현
- mermaid 다이어그램 생성

**수정 필요 사항:**
- (권장) 의존성 DAG를 `type_schemas.json`과 교차 검증하는 로직 추가
- (권장) 부모-자식 관계 방향 결정 시 도메인 지식 힌트 반영 옵션

### 1.3 Stage 3 (stage3_allocate.py) - 완성도: 85%

**현황:**
- 522줄, 스키마 기반 + 탐욕적 할당 구현
- `type_schemas.json` 연동
- 충돌률 계산 및 저장

**수정 필요 사항:**
- `[BLOCKER]` **인코딩 로직이 hash() 사용 중** - 코드북 미사용, 결정론적이지 않음
  ```python
  # 현재 (line 297):
  code = hash(str(value)) % (2 ** field['bits'])

  # 개선 필요: Stage 4 코드북 기반 인코딩으로 변경
  ```
- (권장) `quantization_rules.json` 연동하여 좌표/시간/인구 양자화 적용

### 1.4 Stage 4 (stage4_codebook.py) - 완성도: 80%

**현황:**
- 351줄, 기본 구조 구현됨
- 독립 필드 / 계층적 필드 코드북 생성 분리
- 빈도 기반 코드 할당 (0 = Unknown, 이후 빈도순)
- DB 저장 + 마크다운 출력

**수정 필요 사항:**
- ~~`[BLOCKER]`~~ `entity_labels` 테이블 **확인 완료** (line 143)
  - 테이블 존재: `geuldev.entity_labels (entity_id, language, label)`
  - 인덱스: PK(entity_id, language), idx_label, idx_label_lower
  - 현재 코드 정상 동작 예상
- (필수) 양자화 규칙 연동 - 시간/좌표/인구는 `quantization_rules.json` 사용
- (권장) 예약 코드 공간 설정 (10% → configurable)
- (권장) LLM 상식 검증 기능 추가 (옵션)

### 1.5 Stage 5 (stage5_validate.py) - 완성도: 70%

**현황:**
- 395줄, 4가지 테스트 유형 구조화
- 충돌률 테스트, 일관성 테스트, 열화 테스트 구현

**수정 필요 사항:**
- `[BLOCKER]` **5-B 추상 표현 테스트 미구현** (line 239-266은 케이스 정의만)
  ```python
  def generate_abstract_test_cases(types: list) -> list:
      # 테스트 케이스 정의만 있고, 실제 SIMD 마스크 쿼리 미구현
  ```
- (필수) 5-B 테스트 실행 로직 구현
- (권장) 인코딩 일관성 테스트 확대 (현재 상위 5개 타입만)

### 1.6 공통 모듈 추출 필요성

**중복 코드 현황:**
- DB 연결 설정: 5개 스크립트 모두 동일 코드 반복 (총 ~50줄 x 5)
- `get_entity_type_info()`: stage2, stage3에서 유사 함수
- 경로 설정: `SCRIPT_DIR`, `PROJECT_DIR`, `OUTPUT_DIR` 반복

**공통 모듈 제안:**
```
scripts/
├── common/
│   ├── __init__.py
│   ├── db.py           # DB 연결, 커서 컨텍스트 매니저
│   ├── paths.py        # 경로 상수
│   └── utils.py        # 엔트로피 계산, 로깅 등
├── stage1_run.py
├── stage2_dependency.py
├── stage3_allocate.py
├── stage4_codebook.py
└── stage5_validate.py
```

**db.py 스케치:**
```python
import psycopg2
from contextlib import contextmanager

DB_CONFIG = {
    "read": {"host": "localhost", "port": 5432, "dbname": "geuldev",
             "user": "geul_reader", "password": "test1224"},
    "write": {"host": "localhost", "port": 5432, "dbname": "geulwork",
              "user": "geul_writer", "password": "test1224"}
}

@contextmanager
def get_read_conn():
    conn = psycopg2.connect(**DB_CONFIG["read"])
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def get_write_conn():
    conn = psycopg2.connect(**DB_CONFIG["write"])
    try:
        yield conn
    finally:
        conn.close()
```

---

## 2. Stage 4 구현 계획 (코드북 생성)

### 2.1 입력

| 소스 | 테이블/파일 | 용도 |
|------|------------|------|
| Stage 2 | `dependency_dag` | 부모-자식 관계 |
| Stage 3 | `bit_allocation` | 필드별 비트폭 |
| 참조 | `quantization_rules.json` | 수치 양자화 규칙 |
| geuldev | `triples` | 실제 값 빈도 조회 |

### 2.2 출력

| 대상 | 형식 | 설명 |
|------|------|------|
| `geulwork.codebook` | DB 테이블 | 런타임 조회용 |
| `output/codebooks/*.md` | 마크다운 | 사람 검토용 |
| `output/stage4_report.md` | 마크다운 | 요약 보고서 |

### 2.3 계층적 코드북 생성 로직

```
[Phase 1] 독립 필드 코드북 생성
  for each field in allocation where parent is NULL:
    if field in quantization_rules:
      → 양자화 규칙 적용 (시간, 좌표, 인구 등)
    else:
      → 빈도 기반 할당 (빈도 내림차순 = 낮은 코드)

[Phase 2] 종속 필드 코드북 생성
  for each edge in dependency_dag (parent → child):
    parent_values = distinct values of parent field
    for each parent_value:
      → child values conditioned on parent_value
      → 빈도 기반 코드 할당 (부모 값별 별도 테이블)

[Phase 3] 코드북 저장
  → DB: codebook 테이블
  → 파일: 타입별 마크다운
```

### 2.4 양자화 규칙 연동 (신규 구현)

```python
def apply_quantization(field_name: str, raw_value: str, rules: dict) -> int:
    """양자화 규칙에 따라 코드 반환"""

    # 시간 (P569 date of birth 등)
    if field_name in ['era', 'decade', 'year']:
        year = parse_year(raw_value)
        return quantize_time(year, rules['time_era'])

    # 좌표 (P625 coordinate)
    if field_name in ['lat_zone', 'lon_zone']:
        coord = parse_coordinate(raw_value)
        return quantize_coordinate(coord, rules['coordinate'])

    # 인구 (P1082)
    if field_name == 'population':
        pop = parse_population(raw_value)
        return quantize_population(pop, rules['population'])

    # 저명도 (sitelinks)
    if field_name == 'notability':
        links = get_sitelinks_count(entity_id)
        return quantize_notability(links, rules['notability'])

    return None  # 양자화 규칙 없음 → 빈도 기반
```

### 2.5 코드북 테이블 스키마 (현재 구현 확인)

```sql
CREATE TABLE codebook (
    entity_type  INTEGER NOT NULL,
    field_name   TEXT NOT NULL,
    parent_value TEXT,          -- '_root' for independent fields
    code         INTEGER NOT NULL,
    value        TEXT NOT NULL,  -- Q-ID or literal
    label        TEXT,           -- human-readable label
    frequency    INTEGER DEFAULT 0,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (entity_type, field_name, parent_value, code)
);
```

---

## 3. Stage 5 구현 계획 (검증)

### 3.1 테스트 구조

```
Stage 5
├── 5-A: 충돌률 테스트 (구현됨)
├── 5-B: 추상 표현 SIMD 테스트 [미구현]
├── 5-C: 인코딩 일관성 테스트 (구현됨, 확장 필요)
└── 5-D: 열화 테스트 (구조만 구현)
```

### 3.2 5-A: 충돌률 테스트 (기존 로직 유지)

```python
def test_collision_rates(types: list) -> list:
    """
    기준:
    - 10M+: < 1%
    - 1M~10M: < 3%
    - 100K~1M: < 1%
    - 10K~100K: < 0.5%
    - <10K: < 0.1%
    """
    # 현재 구현 정상, 변경 불필요
```

### 3.3 5-B: 추상 표현 SIMD 테스트 (신규 구현)

**목표:** "한국 남성 정치인" 같은 추상 표현을 SIDX 마스크로 변환하고, 해당 마스크로 필터링했을 때 정확한 결과가 나오는지 검증.

```python
def test_abstract_queries(types: list) -> list:
    """추상 표현 → SIMD 마스크 → 결과 검증"""
    results = []

    test_cases = [
        {
            'type_code': 0x00,
            'description': '한국 남성 정치인',
            'constraints': {
                'country': 'Q884',    # Korea
                'gender': 'Q6581097'  # male
            }
        },
        {
            'type_code': 0x00,
            'description': '미국 여성 과학자',
            'constraints': {
                'country': 'Q30',     # USA
                'gender': 'Q6581072'  # female
            }
        },
        {
            'type_code': 0x33,
            'description': '2020년대 한국 영화',
            'constraints': {
                'country': 'Q884',
                'year_range': [2020, 2029]
            }
        }
    ]

    for case in test_cases:
        # 1. 제약조건 → SIDX 마스크 생성
        mask, pattern = build_sidx_mask(case['type_code'], case['constraints'])

        # 2. DB에서 실제 개체 샘플 로드
        entities = load_sample_entities(case['type_code'], limit=1000)

        # 3. 각 개체를 인코딩하고 마스크 테스트
        matched = []
        for eid, values in entities.items():
            sidx = encode_with_codebook(case['type_code'], values)
            if (sidx & mask) == pattern:
                matched.append(eid)

        # 4. 결과 검증: 실제로 조건 충족하는지 DB 조회
        true_matches = verify_matches(matched, case['constraints'])

        precision = true_matches / len(matched) if matched else 0
        recall = true_matches / count_true_positives(case) if count_true_positives(case) > 0 else 0

        results.append({
            'description': case['description'],
            'mask': hex(mask),
            'matched': len(matched),
            'true_matches': true_matches,
            'precision': precision,
            'recall': recall,
            'passed': precision >= 0.95  # 95% 이상 정밀도
        })

    return results

def build_sidx_mask(type_code: int, constraints: dict) -> tuple:
    """제약조건에서 SIDX 마스크와 패턴 생성"""
    allocation = get_bit_allocation(type_code)

    mask = 0
    pattern = 0

    for field_name, value in constraints.items():
        field = next((f for f in allocation if f['name'] == field_name), None)
        if not field:
            continue

        # 코드북에서 코드 조회
        code = lookup_code(type_code, field_name, value)

        # 마스크: 해당 필드 비트 위치에 1
        field_mask = ((1 << field['bits']) - 1) << field['offset']
        mask |= field_mask

        # 패턴: 해당 위치에 코드 값
        pattern |= (code << field['offset'])

    return mask, pattern
```

### 3.4 5-C: 인코딩 일관성 테스트 (확장)

**현재:** 상위 5개 타입만 테스트
**개선:** 모든 타입, 다양한 샘플 크기

```python
def test_encoding_consistency_extended(types: list) -> list:
    """확장된 일관성 테스트"""
    results = []

    for type_code, name_ko, qid, _, _ in types:  # 모든 타입
        # 랜덤 샘플 + 엣지 케이스 샘플
        random_samples = get_random_entities(qid, 50)
        edge_samples = get_edge_case_entities(qid, 50)  # 속성 적은/많은 개체

        samples = random_samples + edge_samples

        consistent = 0
        for eid, values in samples:
            sidx1 = encode_with_codebook(type_code, values)
            sidx2 = encode_with_codebook(type_code, values)

            # 추가: 속성 순서 셔플 후 인코딩
            shuffled_values = shuffle_dict(values)
            sidx3 = encode_with_codebook(type_code, shuffled_values)

            if sidx1 == sidx2 == sidx3:
                consistent += 1

        results.append({
            'type_code': type_code,
            'name_ko': name_ko,
            'tested': len(samples),
            'consistent': consistent,
            'passed': consistent == len(samples)
        })

    return results
```

### 3.5 5-D: 열화 테스트 (구현 보완)

```python
def test_degradation_semantic(types: list) -> list:
    """열화 시 의미 수렴 검증"""
    results = []

    for type_code, name_ko, qid, _, _ in types[:10]:
        allocation = get_bit_allocation(type_code)

        # 구체적 개체 선택 (유명인)
        entity = get_famous_entity(qid)
        full_sidx = encode_with_codebook(type_code, entity['values'])

        degradation_chain = [decode_sidx(type_code, full_sidx)]

        # 뒤에서부터 필드 마스킹
        current_sidx = full_sidx
        for field in reversed(allocation):
            if field['name'] == '_reserved':
                continue

            # 필드 마스킹
            field_mask = ((1 << field['bits']) - 1) << field['offset']
            current_sidx &= ~field_mask

            decoded = decode_sidx(type_code, current_sidx)
            degradation_chain.append(decoded)

        # 검증: 열화 체인이 의미적으로 일반화되는지
        # 예: "이순신" → "한국 남성 군인" → "한국 남성" → "인간"
        is_generalizing = verify_generalization(degradation_chain)

        results.append({
            'type_code': type_code,
            'entity': entity['label'],
            'chain': degradation_chain,
            'passed': is_generalizing
        })

    return results
```

---

## 4. 실행 순서 및 의존성

### 4.1 데이터 흐름

```
                 entity_types_64.json
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│ Stage 1: stage1_run.py                                     │
│   geuldev.triples → geulwork.entity_type_map               │
│                   → geulwork.property_stats                │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│ Stage 2: stage2_dependency.py                              │
│   geulwork.property_stats → geulwork.dependency_dag        │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│ Stage 3: stage3_allocate.py                                │
│   geulwork.dependency_dag   → geulwork.bit_allocation      │
│   type_schemas.json         → geulwork.collision_stats     │
│   quantization_rules.json                                  │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│ Stage 4: stage4_codebook.py                                │
│   geulwork.bit_allocation → geulwork.codebook              │
│   geulwork.dependency_dag → output/codebooks/*.md          │
│   quantization_rules.json                                  │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│ Stage 5: stage5_validate.py                                │
│   geulwork.* → output/stage5_report.md                     │
│   [REVIEW] 태그 항목 → 사람 검토                             │
└────────────────────────────────────────────────────────────┘
```

### 4.2 의존성 매트릭스

| Stage | 입력 의존 | 출력 | 선행 조건 |
|-------|----------|------|-----------|
| 1 | entity_types_64.json, geuldev.triples | entity_type_map, property_stats | 없음 |
| 2 | property_stats | dependency_dag | Stage 1 완료 |
| 3 | dependency_dag, type_schemas.json | bit_allocation, collision_stats | Stage 2 완료 |
| 4 | bit_allocation, dependency_dag | codebook | Stage 3 완료 |
| 5 | 모든 테이블 | stage5_report.md | Stage 4 완료 |

### 4.3 재실행 시 캐시 활용 방안

**현재:** 각 Stage는 해당 테이블을 DELETE 후 재생성

**개선안:**

```python
def should_rerun(stage: int, type_code: int) -> bool:
    """스테이지 재실행 필요 여부 판단"""
    conn = get_write_conn()

    # 이전 스테이지 결과 타임스탬프
    prev_ts = get_last_updated(stage - 1, type_code)

    # 현재 스테이지 결과 타임스탬프
    curr_ts = get_last_updated(stage, type_code)

    # 참조 파일 수정 시간
    ref_ts = get_reference_mtime(stage)

    return (prev_ts > curr_ts) or (ref_ts > curr_ts)

# 실행 시:
for type_code in types:
    if should_rerun(4, type_code):
        process_stage4(type_code)
    else:
        print(f"Skipping 0x{type_code:02X} (cached)")
```

**스테이지별 캐시 키:**

| Stage | 캐시 키 | 무효화 조건 |
|-------|--------|-------------|
| 1 | (type_code, qid) | entity_types_64.json 변경 |
| 2 | (type_code,) | property_stats 변경 |
| 3 | (type_code,) | dependency_dag 변경, type_schemas.json 변경 |
| 4 | (type_code,) | bit_allocation 변경, quantization_rules.json 변경 |
| 5 | (type_code,) | 항상 재실행 (검증) |

---

## 5. 에러 처리 및 로깅

### 5.1 예외 상황 처리 패턴

```python
import logging
from contextlib import contextmanager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('output/pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PipelineError(Exception):
    """파이프라인 실행 중 복구 불가능한 오류"""
    pass

class SkippableError(Exception):
    """건너뛸 수 있는 오류 (해당 타입만 스킵)"""
    pass

@contextmanager
def process_type(type_code: int, name_ko: str):
    """타입 처리 컨텍스트"""
    logger.info(f"Processing 0x{type_code:02X} {name_ko}")
    try:
        yield
        logger.info(f"Completed 0x{type_code:02X}")
    except SkippableError as e:
        logger.warning(f"Skipped 0x{type_code:02X}: {e}")
    except Exception as e:
        logger.error(f"Failed 0x{type_code:02X}: {e}")
        raise PipelineError(f"Stage failed at 0x{type_code:02X}") from e
```

### 5.2 DB 에러 처리

```python
from psycopg2 import OperationalError, DatabaseError

def safe_execute(cur, query, params=None, retries=3):
    """재시도 가능한 쿼리 실행"""
    for attempt in range(retries):
        try:
            cur.execute(query, params)
            return cur
        except OperationalError as e:
            if attempt < retries - 1:
                logger.warning(f"DB connection lost, retrying ({attempt + 1}/{retries})")
                time.sleep(1)
            else:
                raise
```

### 5.3 진행 상황 로깅

```python
from tqdm import tqdm

def main():
    types = get_entity_types()

    with tqdm(types, desc="Stage 4") as pbar:
        for type_code, name_ko, qid in pbar:
            pbar.set_postfix(type=name_ko)

            with process_type(type_code, name_ko):
                # 처리 로직
                codebooks = generate_codebook(type_code, qid, allocation)

                # 중간 로깅
                logger.debug(f"  Generated {len(codebooks)} codebooks")

    # 최종 요약
    logger.info(f"Stage 4 completed: {len(types)} types processed")
```

### 5.4 로그 파일 구조

```
output/
├── pipeline.log          # 전체 실행 로그
├── stage1_run.log        # Stage 1 상세 로그
├── stage2_dependency.log
├── stage3_allocate.log
├── stage4_codebook.log
└── stage5_validate.log
```

---

## 6. 블로커 요약 및 우선순위

| 우선순위 | 항목 | 영향 범위 | 해결 방안 |
|----------|------|-----------|-----------|
| **P0** | Stage 3 hash() 사용 | 전체 인코딩 결정론성 | 코드북 기반 인코딩으로 대체 |
| **P0** | Stage 5-B 미구현 | 추상 표현 검증 불가 | 신규 구현 |
| ~~P1~~ | ~~entity_labels 테이블 확인~~ | ~~Stage 4 레이블 조회~~ | **해결됨** - 테이블 존재 확인 |
| **P1** | 양자화 규칙 미연동 | 수치 필드 인코딩 | quantization_rules.json 연동 |
| **P2** | 공통 모듈 추출 | 유지보수성 | 리팩토링 |
| **P2** | 캐시 활용 | 재실행 효율 | 타임스탬프 비교 로직 |

---

## 7. 다음 단계 액션 아이템

1. **즉시 (P0)**
   - [ ] geuldev.entity_labels 테이블 존재 여부 확인
   - [ ] Stage 3의 encode_entity() 함수를 코드북 기반으로 수정
   - [ ] Stage 5-B test_abstract_queries() 구현

2. **단기 (P1)**
   - [ ] quantization_rules.json 연동 함수 구현
   - [ ] Stage 4에 양자화 로직 통합

3. **중기 (P2)**
   - [ ] scripts/common/ 모듈 추출
   - [ ] 캐시 무효화 로직 구현
   - [ ] 로깅 표준화

---

## 부록: DB 스키마 확인 쿼리

```sql
-- entity_labels 테이블 존재 확인
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'entity_labels';

-- 레이블 테이블 스키마 확인
\d entity_labels

-- 샘플 데이터 확인
SELECT * FROM entity_labels WHERE entity_id = 'Q5' LIMIT 5;
```
