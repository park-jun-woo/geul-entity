# Entity SIDX: 현재 상태와 다음 단계

*2026년 2월 27일 대화 정리*

---

## 현재 상태

구조는 건전하다. 데이터 정렬이 안 됐다.

### 작동하는 것

- 64비트 SIDX 설계 확정 (Prefix 7b + Mode 3b + EntityType 6b + 속성 48b)
- 64개 EntityType × 48비트 속성 스키마 완성
- 인코더 구현 완료, 108.8M SIDX 생성
- 코드북(codebooks_full.json) 283KB
- Human 타입 속성 인코딩 97.0% 성공

### 작동하지 않는 것

- 62.2% 분류 실패 (67.7M 개체가 Unknown)
- 원인: 매핑 누락 (Country, Sovereign State 등이 테이블에 없음)
- P279 체인 탐색 미구현
- 동사 코드북과의 결합 테스트 없음
- 검색 파이프라인 없음

---

## 단계 1: 분류율 62% → 90%+ (1~2주)

### 1-1. primary_mapping.json 매핑 보강

누락된 핵심 QID 추가. 수작업이지만 하루면 된다.

- Q6256 (Country) → Settlement 또는 신규 타입
- Q3624078 (Sovereign State) → Settlement 또는 신규 타입
- Q5864 (G-type Star) → Star (0x0C)
- Q55983715 (Common Name Taxon) → Taxon (0x01)

이것만으로 수백만 개가 Unknown에서 빠져나온다.

### 1-2. P279 체인 탐색 구현

최대 5홉. "Solar-type Star" → P279 → "Star" 자동 매핑.

이게 되면 수동 매핑에서 자동 매핑으로 전환된다. 위키데이터에 새 하위타입이 추가되어도 P279를 타고 올라가서 64개 중 하나에 도달한다.

### 1-3. 64개 타입 재배치

과도한 세분화 통합: Settlement/Village/Hamlet → 하나로.
빈 슬롯에 누락 타입 추가: Country, City, University, Hospital, Airport 등.

---

## 단계 2: 동사 + 엔티티 결합 테스트 (1주)

verb_bits.json (13,767 동사) + Entity SIDX (108.8M 엔티티).

각각은 완성됐지만 결합 테스트가 없다. 간단한 문장 10개로 엔드투엔드 인코딩/디코딩 테스트.

```
"Barack Obama가 연설했다"
  → Entity: Q76 SIDX (Human, USA, 1960s, politician)
  → Verb: speak.v.01 (16비트 코드)
  → 한정사: 과거, 사실, 높은확신
  → 디코딩: 원문 복원
```

이게 돌아가면 "GEUL이 작동한다"의 최소 증명.

---

## 단계 3: SIMD 검색 PoC — RAG 대비 벤치마크 (2~3주)

### 목표

SIDX 비트마스크 검색이 RAG보다 낫고, 퍼블릭 도메인에서 작동한다는 것을 증명한다.

### 쿼리 파이프라인

PoC에서는 쿼리 LLM 없이 하드코딩으로 진행한다.

```
하드코딩 쿼리 (사람이 직접 조건 입력)
  → 코드북에서 mask + value 조립 (결정적, O(K))
    → SIMD 전수 스캔 (밀리초 단위)
      → 결과 SIDX 목록
```

LLM이 자연어를 코드북 키워드로 바꿔주는 부분은 PoC 범위 밖. 나중 문제.

### 비교 대상: RAG

같은 쿼리를 RAG 파이프라인에도 던진다.

```
자연어 쿼리
  → 임베딩 생성
    → 벡터 검색 (코사인 유사도)
      → 리랭킹
        → 결과
```

### 비교 축 세 가지

**속도.** 마스크 조립 + SIMD 스캔 vs 임베딩 생성 + 벡터 검색 + 리랭킹. 둘 다 시간 측정.

**정확도.** RAG은 의미적으로 유사한 것이 올라온다. "한국 정치인"을 검색하면 "한국 외교관", "북한 정치인"도 올라온다. SIDX는 조건에 정확히 맞는 것만 나온다. country=Korea AND occupation=politician. 거짓 양성(false positive) 비율 비교.

**재현성.** SIDX는 같은 쿼리 100번 돌려도 같은 결과. 결정적. RAG은 임베딩 모델이나 인덱스 상태에 따라 달라질 수 있다. 결정적 vs 비결정적.

### 벤치마크 시나리오 (5개)

| # | 쿼리 | 타입 | SIDX 조건 |
|---|------|------|-----------|
| Q1 | 1950년대 한국 남성 정치인 | Human | country=Korea, era=1950s, gender=male, occupation=politician |
| Q2 | 오리온자리 G형 항성 | Star | constellation=Orion, spectral_type=G |
| Q3 | 2000년 이후 영어권 공포 영화 | Film | year≥2000, language=English, genre=horror |
| Q4 | 포유류 중 멸종위기 초식동물 | Taxon | class=Mammalia, conservation=endangered, diet=herbivore |
| Q5 | 19세기 유럽 건축물 | Building | era=19c, country∈Europe |

5개 시나리오로 타입이 전부 다르다. 각각에서 속도/정확도/재현성 측정.

### 데이터: 위키데이터 (퍼블릭 도메인)

사유 데이터가 아니라 누구나 접근 가능한 위키데이터 108.8M 엔티티에서 실행한다. 재현 가능. 논문 리뷰어가 직접 돌려볼 수 있다.

---

## 차후 과제: 쿼리 LLM (PoC 범위 밖)

PoC 이후, 자연어 → 코드북 키워드 변환을 자동화할 때 필요.

### 태스크 특성

자유 생성이 아니라 닫힌 어휘 선택.

```
type:   64개 중 택 1
field:  타입당 ~11개 중 택 N
value:  필드당 ~50개 중 택 1
```

코드북 전체 leaf 수: 추정 35,000~100,000개. 정확한 수는 codebooks_full.json에서 카운트 필요.

### 학습 데이터 전략

합성보다 실제 데이터 우선.

```
80%  실제 쿼리 (허깅페이스 공개 데이터셋 + Claude 세션 로그)
15%  코드북 역방향 보완 (희귀 타입 커버)
5%   엣지 케이스 (오타, 약어, 혼합 언어)
```

공개 데이터셋 후보: ShareGPT, OpenAssistant, WildChat 등에서 엔티티 검색 의도 쿼리 필터링.

### 모델 규모

1~3B + LoRA면 충분. Text-to-SQL(7B)보다 단순한 태스크.
파인튜닝 없이도 코드북 어휘 550토큰이면 Phi-3 Mini / Gemma-2B few-shot 동작 가능.

### LLM + Dictionary 분리 원칙

LLM이 비트를 직접 생성하지 않는다. 코드북 leaf의 offset/bitwidth를 LLM이 기억할 수 없다. 1비트 오류 = 완전히 다른 결과.

LLM은 닫힌 어휘 선택만 담당. Dictionary가 결정론적으로 마스크를 조립.

---

## 전체 로드맵에서의 위치

```
단계 1: 매핑 보강 + P279 체인       → 분류율 90%+          ← 지금 여기
단계 2: 동사 + 엔티티 결합          → 엔드투엔드 인코딩 증명
단계 3: 하드코딩 쿼리 + SIMD PoC   → RAG 대비 벤치마크
─────────────────────────────────────────────────────
  ↑ Phase 1 완료선 (목표.md 0→15%)
─────────────────────────────────────────────────────
단계 4: 쿼리 LLM 파인튜닝          → 자연어 → 코드북 자동화
단계 5: 파이프라인 통합             → 검증 → 필터 → 정합성 → 탐색
```

단계 3까지가 PoC. "작동한다"를 증명하는 것.
단계 4부터가 시스템. "쓸 수 있다"를 만드는 것.
