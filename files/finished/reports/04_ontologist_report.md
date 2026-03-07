# Ontologist 보고서: 분류 체계 검증 결과

**작성일**: 2026-02-01
**작성자**: Ontologist

---

## 1. 분류 체계 검토

### 1.1 EntityType 6비트 할당 (64개 타입)

| 범주 | 코드 범위 | 타입 수 | 검증 상태 |
|------|-----------|---------|-----------|
| 생물 | 0x00-0x07 | 8 | 정상 |
| 물질 | 0x08-0x0F | 8 | 주의 필요 |
| 장소 | 0x10-0x1F | 16 | 정상 |
| 조직 | 0x20-0x2F | 16 | 정상 |
| 창작물 | 0x30-0x3F | 16 | 정상 |

### 1.2 검토된 5개 타입

| 타입 | QID | 위키데이터 정합성 |
|------|-----|------------------|
| Human (0x00) | Q5 | 완전 일치 |
| Star (0x0C) | Q523 | 완전 일치 |
| Settlement (0x1C) | Q486972 | 완전 일치 |
| Organization (0x2C) | Q43229 | 완전 일치 |
| Film (0x33) | Q11424 | 완전 일치 |

## 2. 속성-필드 매핑 검증

### Human (0x00)

| 필드 | 속성 | 의미 정합성 |
|------|------|-------------|
| gender | P21 (sex or gender) | 정합 |
| occupation | P106 (occupation) | 정합 |
| country | P27 (country of citizenship) | 정합 |
| era | P569 (date of birth) | 파생 (연도→시대) |
| decade | - | 미연결 (era에서 파생) |
| subclass | - | 미연결 (P31 하위) |
| notability | - | 미연결 (외부 지표 필요) |

### 경계 사례 발견

1. **P27 vs P19**: 국적(P27)과 출생지(P19)의 차이
   - 권장: 국적 우선, 없으면 출생지 대체

2. **P106 다중값**: 한 사람이 여러 직업 보유
   - 현재: 첫 번째 값 사용
   - 권장: 주요 직업(P108 employer와 연계) 우선

## 3. 계층적 코드북 의미론

### 부모-자식 관계 분석

```
occupation (부모)
├── researcher → country 코드 테이블 A
├── politician → country 코드 테이블 B
└── actor     → country 코드 테이블 C
```

**발견**: 각 직업군별로 국가 분포가 상이함
- researcher: 폴란드, 터키, 스페인 상위
- politician: 프랑스, 미국, 독일 상위

**의미**: 계층적 코드북은 직업-국가 상관관계를 반영

## 4. 누락 타입 분석

### 기존 발견 (plan 단계)

| 타입 | 개체 수 | 권장 처리 |
|------|---------|-----------|
| Valley | 134,000 | 지형 슬롯 예약 |
| Sculpture | 125,000 | Painting 속성 활용 |

### 신규 발견 (Phase 2.5)

| 타입 | 이슈 |
|------|------|
| Film series | Film과 구분 필요 (P31=Q24856) |
| Software | 창작물/도구 경계 모호 |

## 5. 우아한 열화 의미론 검증

### 열화 단계별 의미

```
인간 전체 표현: occupation=researcher, country=Korea, gender=male, decade=1980s
       ↓ 32비트 마스크
       occupation=researcher, country=Korea, gender=male
       ↓ 27비트 마스크
       occupation=researcher, country=Korea
       ↓ 11비트 마스크
       occupation=researcher
       ↓ 0비트 마스크
       "어떤 인간"
```

**결론**: 비트를 줄일수록 상위 개념으로 자연스럽게 수렴 → **설계 원칙 검증 완료**

## 6. 권장 사항

1. **P19/P27 병합 규칙** 문서화
2. **다중값 속성** 우선순위 정의 (주요 직업 판별 휴리스틱)
3. **Film series** 타입 0x34 슬롯 할당 검토
4. **subclass/notability** 필드 데이터 소스 정의

---

*Ontologist - GEUL Entity SIDX Team*
