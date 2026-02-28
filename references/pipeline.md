# Entity SIDX 비트할당 파이프라인 상세 (v2.0)

---

## 파일 구조

```
entity/
├── references/
│   ├── entity_types_64.json      # 64개 EntityType 정의
│   ├── type_schemas.json         # 타입별 48비트 스키마
│   ├── quantization_rules.json   # 양자화 규칙
│   └── pipeline.md               # 본 문서
├── scripts/
│   ├── stage1_run.py             # 속성 추출
│   ├── stage2_dependency.py      # 의존성 탐지
│   ├── stage3_allocate.py        # 비트 할당
│   ├── stage4_codebook.py        # 코드북 생성
│   └── stage5_validate.py        # 검증
├── output1/
│   ├── stage1_report.md
│   ├── stage2_report.md
│   ├── stage3_report.md
│   ├── stage4_report.md
│   ├── stage5_report.md
│   └── codebooks/                # 타입별 코드북
└── cache/
    └── db_schema.md
```

---

## DB 설정

모든 스크립트는 동일한 DB 설정 사용:

```python
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
```

---

## EntityType 64개 목록

**참조 파일:** `references/entity_types_64.json`

| 범위 | 범주 | 개수 |
|------|------|------|
| 0x00-0x07 | 생물/인물 | 8 |
| 0x08-0x0B | 화학/물질 | 4 |
| 0x0C-0x13 | 천체 | 8 |
| 0x14-0x1B | 지형/자연 | 8 |
| 0x1C-0x23 | 장소/행정 | 8 |
| 0x24-0x2B | 건축물 | 8 |
| 0x2C-0x2F | 조직 | 4 |
| 0x30-0x3B | 창작물 | 12 |
| 0x3C-0x3F | 이벤트/예약 | 4 |

**주요 타입 (개체수 100만 이상):**
- 0x00 인간 (12.5M)
- 0x01 생물종 (3.8M)
- 0x0C 항성 (3.6M)
- 0x0D 은하 (2.1M)
- 0x08 화학물질 (1.3M)
- 0x02 유전자 (1.2M)
- 0x09 화합물 (1.1M)
- 0x30 그림 (1.0M)
- 0x03 단백질 (1.0M)

---

## 양자화 규칙

**참조 파일:** `references/quantization_rules.json`

### 좌표 (8비트)
- 위도: 4비트 (8구역: Antarctic ~ Arctic)
- 경도: 4비트 (16구역)

### 시간 (8비트)
- 시대: 4비트 (16개 시대)
- 10년대: 4비트 (시대 내 16구간)

### 인구 (4비트)
- 로그 스케일 12단계

### 저명도 (3비트)
- sitelinks 기준 8단계

### 천체 등급 (4비트)
- 11단계 (Very Bright ~ Very Faint)

---

## Stage 1: 타입별 속성 추출

### 목표
각 EntityType에 속한 개체들이 실제로 어떤 Property를 갖는지 통계 추출.

### 대상
**64개 전체 타입** (`references/entity_types_64.json` 참조)

### 실행
```bash
python scripts/stage1_run.py              # 전체
python scripts/stage1_run.py 0x00         # 특정 타입
python scripts/stage1_run.py 0 12 28      # 여러 타입
```

### 절차

1. `entity_types_64.json` 로드
2. P31(instance of) 기준 EntityType 매핑 테이블 생성
3. 타입별 모든 Property 수집, 다음 통계 계산:
   - **커버리지**: 해당 타입 개체 중 이 속성을 가진 비율 (%)
   - **카디널리티**: 고유값 수
   - **엔트로피**: -Σ p(x) log2 p(x)) — 변별력 지표
4. 커버리지 10% 미만 속성 필터

### 출력
- `geulwork.entity_type_map`: EntityType 매핑
- `geulwork.property_stats`: 타입별 속성 통계
- `output1/stage1_report.md`: 보고서

---

## Stage 2: 계층 의존성 탐지

### 목표
속성 간 종속 관계를 자동 탐지하여 DAG 생성.

### 실행
```bash
python scripts/stage2_dependency.py       # 전체
python scripts/stage2_dependency.py 0x00  # 특정 타입
```

### 방법: 조건부 엔트로피

속성 A, B에 대해:
- H(B|A) = A를 알 때 B의 불확실성
- H(A|B) = B를 알 때 A의 불확실성
- I(A;B) = H(B) - H(B|A) = 상호정보량

**종속 판별 기준:**
- I(A;B) / min(H(A), H(B)) > 0.3 이면 종속으로 판정
- H(B|A) < H(A|B) 이면 A → B (A가 B를 결정)

### 절차

1. Stage 1에서 커버리지 상위 15개 속성 선택 (타입별)
2. 15C2 = 105쌍에 대해 조건부 엔트로피 계산
3. 종속 관계 간선 생성
4. 사이클 제거: 약한 간선(I가 낮은 것)부터 제거
5. DAG 확정

### 출력
- `geulwork.dependency_dag`: 종속 관계
- `output1/stage2_report.md`: DAG 시각화 (mermaid)

---

## Stage 3: 비트 할당 최적화

### 목표
48비트에 속성을 배치하여 충돌 최소화.

### 실행
```bash
python scripts/stage3_allocate.py         # 전체
python scripts/stage3_allocate.py 0x00    # 특정 타입
```

### 스키마 기반 할당
`references/type_schemas.json`에 정의된 타입은 스키마대로 할당.

### 탐욕적 할당 (스키마 없는 타입)
```
budget = 48
for prop in sorted_properties:
    bits = clamp(ceil(log2(cardinality)), 2, 12)
    if budget >= bits:
        assign(prop, bits)
        budget -= bits
```

### 충돌률 목표 (64개 타입)

| 개체수 규모 | 목표 충돌률 | 해당 타입 예시 |
|-------------|------------|---------------|
| 10M 이상 | < 1% | 인간(12.5M) |
| 1M ~ 10M | < 3% | 생물종, 항성, 은하, 화학물질, 유전자 |
| 100K ~ 1M | < 1% | 정주지, 조직, 산, 강, 영화, 앨범 |
| 10K ~ 100K | < 0.5% | 대부분 건축물, 이벤트 |
| 10K 미만 | < 0.1% | 행성, 위성, 성운 |

### 출력
- `geulwork.bit_allocation`: 비트 할당
- `geulwork.collision_stats`: 충돌 통계
- `output1/stage3_report.md`: 보고서

---

## Stage 4: 코드북 생성

### 목표
계층적 코드 테이블 생성. 부모 값에 따라 달라지는 자식 코드북.

### 실행
```bash
python scripts/stage4_codebook.py         # 전체
python scripts/stage4_codebook.py 0x00    # 특정 타입
```

### 코드 할당 원칙

1. 0x00은 항상 "Unknown/Unspecified"
2. 빈도 내림차순 = 낮은 코드 번호
3. 코드 공간의 마지막 10%는 Reserved

### 독립 필드 코드북
```
성별: Unknown=00, Male=01, Female=10, Other=11
```

### 종속 필드 코드북 (부모 값별)
```
Era=Ancient:  Polity: Unknown=000, Egypt=001, Rome=010, ...
Era=Medieval: Polity: Unknown=000, Goryeo=001, Tang=010, ...
Era=Current:  Polity: Unknown=000, Korea=001, USA=010, ...
```

### 출력
- `geulwork.codebook`: 코드 테이블
- `output1/codebooks/`: 타입별 마크다운
- `output1/stage4_report.md`: 보고서

---

## Stage 5: 검증

### 실행
```bash
python scripts/stage5_validate.py         # 전체
python scripts/stage5_validate.py 0x00    # 특정 타입
```

### 5-A: 충돌률 테스트
Stage 3의 충돌률이 목표 이내인지 확인.

### 5-B: 추상 표현 테스트
부분 채움 SIDX로 범위 쿼리:
```
"어떤 한국 남성 정치인"
= Mode=5, Type=Human, 성별=Male, 국적=Korea
→ SIMD 마스크 필터 → 결과 검증
```

### 5-C: 인코딩 일관성 테스트
같은 개체를 다시 인코딩했을 때 같은 SIDX (결정론적).

### 5-D: 열화 테스트
비트를 뒤에서부터 제거하며 상위 개념으로 수렴:
```
이순신(48bit) → 한국 남성 군인 → 한국 남성 → 인간
```

### 출력
- `output1/stage5_report.md`: 전체 검증 결과
- [REVIEW] 태그로 사람 확인 필요 항목 표시

---

## 전체 실행

```bash
cd entity
python scripts/stage1_run.py
python scripts/stage2_dependency.py
python scripts/stage3_allocate.py
python scripts/stage4_codebook.py
python scripts/stage5_validate.py
```

또는 특정 타입만:
```bash
python scripts/stage1_run.py 0x00 0x0C 0x1C 0x2C 0x33
python scripts/stage2_dependency.py 0x00 0x0C 0x1C 0x2C 0x33
python scripts/stage3_allocate.py 0x00 0x0C 0x1C 0x2C 0x33
python scripts/stage4_codebook.py 0x00 0x0C 0x1C 0x2C 0x33
python scripts/stage5_validate.py 0x00 0x0C 0x1C 0x2C 0x33
```

---

## 버전 히스토리

| 버전 | 날짜 | 변경 |
|------|------|------|
| v1.0 | 2026-01-30 | 초안 |
| v2.0 | 2026-02-01 | 64개 타입, 양자화 규칙, 스크립트 v2.0 |
