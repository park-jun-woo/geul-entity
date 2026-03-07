# Architect Plan: 48비트 전체 활용 설계 결정

**역할**: 최종 스키마 승인, 트레이드오프 결정

---

## 설계 결정 포인트

### DECISION-F1: 필드 우선순위

**질문**: 48비트가 부족할 경우 어떤 필드를 우선할 것인가?

**원칙**:
1. 커버리지 높은 필드 우선
2. 구별력(엔트로피) 높은 필드 우선
3. SIMD 쿼리에 유용한 필드 우선

**타입별 우선순위**:

| 타입 | 1순위 | 2순위 | 3순위 |
|------|-------|-------|-------|
| Human | language | birth_region | activity |
| Star | radial_vel | redshift | parallax |
| Settlement | elevation | settlement_type | coastal |
| Organization | hq_region | status | ideology |
| Film | director_fame | format | cast_tier |

### DECISION-F2: 파생 필드 허용

**질문**: 위키데이터에 없는 파생 필드를 포함할 것인가?

| 파생 필드 | 계산 방법 | 결정 |
|-----------|----------|------|
| coastal | 좌표→해안선 거리 | **허용** (지리적 의미 명확) |
| sector | legal_form→공공/민간 | **허용** (결정론적 매핑) |
| rating | 국가+연도 기반 추정 | **미허용** (불확실성 높음) |

### DECISION-F3: 다중값 처리

**질문**: 다중값 속성(언어, 직업 등)을 어떻게 인코딩할 것인가?

**결정**: 정렬된 첫 번째 값 사용
- 언어: 알파벳 순 첫 번째
- 직업: 빈도 순 첫 번째 (코드북 코드 낮은 것)

### DECISION-F4: 계층 종속 확장

**질문**: 새 필드도 계층 종속을 적용할 것인가?

| 필드 | 부모 필드 | 종속 여부 |
|------|----------|----------|
| birth_region | country | **예** (국가별 64개 코드북) |
| hq_region | country | **예** |
| decade | era | 기존 유지 |
| admin_code | country | 기존 유지 |

### DECISION-F5: Unknown 처리

**질문**: 데이터 없음(Unknown)을 어떻게 처리할 것인가?

**결정**:
- code=0은 항상 Unknown
- Unknown은 열화 시 무시됨
- SIMD 마스크에서 Unknown 필드는 제외

---

## 트레이드오프 분석

### 충돌률 vs 표현력

| 접근법 | 충돌률 | 표현력 | 선택 |
|--------|--------|--------|------|
| 고커버리지만 | 낮음 | 낮음 | |
| 저커버리지 포함 | 높음 | 높음 | |
| **균형** | **중간** | **중간** | **선택** |

**균형 기준**: 커버리지 20% 이상인 필드만 포함

### 비트 정밀도 vs 필드 수

| 접근법 | 정밀도 | 필드 수 | 선택 |
|--------|--------|---------|------|
| 적은 필드, 많은 비트 | 높음 | 적음 | |
| **많은 필드, 적은 비트** | **낮음** | **많음** | **선택** |

**근거**: 다양한 속성으로 개체 구별이 충돌률 감소에 더 효과적

---

## 최종 스키마 승인 체크리스트

### Human (0x00) - 48비트

- [ ] subclass (5) + occupation (6) + country (8) + era (4) + decade (4) + gender (2) + notability (3) = 32비트 ✓
- [ ] language (6) + birth_region (6) + activity (4) = 16비트 ✓
- [ ] 합계 = 48비트 ✓

### Star (0x0C) - 48비트

- [ ] constellation (7) + spectral (4) + luminosity (3) + magnitude (4) + ra (4) + dec (4) + flags (6) = 32비트 ✓
- [ ] radial_vel (5) + redshift (5) + parallax (4) + pm_class (2) = 16비트 ✓
- [ ] 합계 = 48비트 ✓

### Settlement (0x1C) - 48비트

- [ ] country (8) + admin_level (4) + admin_code (8) + lat (4) + lon (4) + population (4) + timezone (5) = 37비트 ✓
- [ ] elevation (5) + settlement_type (4) + coastal (2) = 11비트 ✓
- [ ] 합계 = 48비트 ✓

### Organization (0x2C) - 48비트

- [ ] country (8) + org_type (4) + legal_form (6) + industry (8) + era (4) + size (4) = 34비트 ✓
- [ ] hq_region (6) + status (3) + ideology (3) + sector (2) = 14비트 ✓
- [ ] 합계 = 48비트 ✓

### Film (0x33) - 48비트

- [ ] country (8) + year (7) + genre (6) + language (8) + color (2) + duration (4) = 35비트 ✓
- [ ] director_fame (4) + cast_tier (3) + rating (3) + format (3) = 13비트 ✓
- [ ] 합계 = 48비트 ✓

---

## 실행 승인

### 사용자 확인 필요 항목

1. **새 필드 구성**: 위 스키마 승인
2. **파생 필드**: coastal, sector 허용
3. **충돌률 목표**: 5~10%
4. **Phase 3 실행**: 승인

---

## 롤백 계획

Phase 3 결과가 목표 미달 시:

1. **충돌률 10% 초과**: 필드 비트 재조정
2. **충돌률 20% 초과**: 필드 구성 재검토
3. **충돌률 30% 초과**: 근본적 재설계 (Phase 2 결과로 롤백)

---

*Architect - Full 48-bit Utilization Design*
