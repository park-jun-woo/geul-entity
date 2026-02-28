# Ontologist Plan: 48비트 전체 활용 분류 검증

**역할**: 새 필드 분류 체계 검증, 코드북 라벨 검토

---

## 검증 목표

새로 추가되는 필드들이 MECE 원칙을 준수하고 기존 온톨로지와 정합성을 유지하는지 확인

---

## 타입별 검증 태스크

### TASK-O1: Human (0x00) 새 필드 검증

#### language (6비트 = 64개)

**검증 항목**:
- [ ] 64개 언어 선정이 ISO 639-1/2와 정합한가?
- [ ] 다중언어 사용자 처리 방침 (첫 번째 값? 모국어?)
- [ ] "Unknown" 코드 할당 (code=0)

**경계 사례**:
- 방언 vs 언어 (광동어/북경어, 세르비아어/크로아티아어)
- 수화 포함 여부
- 고대어/사어 처리

#### birth_region (6비트 = 64개/국가)

**검증 항목**:
- [ ] 국가별 지역 분류 일관성
- [ ] 행정구역 vs 지리구역 선택
- [ ] 역사적 국경 변화 처리 (소련 출생자 등)

**경계 사례**:
- 분쟁지역 (크림반도, 팔레스타인)
- 도시국가 (싱가포르, 바티칸)
- 해외영토 (괌, 푸에르토리코)

#### activity_field (4비트 = 16개)

**검증 항목**:
- [ ] P101 (field of work)과 P106 (occupation) 구분
- [ ] 16개 분야가 MECE한가?
- [ ] occupation과 중복 없는가?

**제안 분류**:
```
0: Unknown
1: Arts
2: Science
3: Technology
4: Business
5: Politics
6: Sports
7: Religion
8: Military
9: Law
10: Medicine
11: Education
12: Media
13: Social
14: Other
15: Reserved
```

### TASK-O2: Star (0x0C) 새 필드 검증

#### radial_vel (5비트 = 32구간)

**검증 항목**:
- [ ] 천문학 표준 단위 (km/s) 사용
- [ ] 양자화 구간이 천문학적으로 의미있는가?
- [ ] 청색/적색 편이와 redshift 필드 중복 없는가?

#### redshift (5비트 = 32구간)

**검증 항목**:
- [ ] z값 표준 정의 사용
- [ ] 코스몰로지컬 vs 도플러 redshift 구분
- [ ] 음수 redshift (blueshift) 처리

#### parallax (4비트 = 16구간)

**검증 항목**:
- [ ] 거리 추정과의 관계 명확
- [ ] 측정 정밀도에 따른 구간 설정

### TASK-O3: Settlement (0x1C) 새 필드 검증

#### elevation (5비트 = 32구간)

**검증 항목**:
- [ ] 해수면 기준 일관성
- [ ] 음수 고도 (사해, 네덜란드) 처리

**제안 구간**:
```
0: Unknown
1: Below sea (-500~0m)
2-5: Lowland (0~100, 100~200, 200~300, 300~500m)
6-10: Highland (500~750, 750~1000, 1000~1500, 1500~2000, 2000~2500m)
11-15: Mountain (2500~3000, 3000~3500, 3500~4000, 4000~4500, 4500+m)
16-31: Reserved for finer granularity
```

#### settlement_type (4비트 = 16개)

**검증 항목**:
- [ ] P31 하위 타입과 정합
- [ ] 문화권별 차이 (도시/마을 기준)

**제안 분류**:
```
0: Unknown
1: Capital
2: Megacity (10M+)
3: Major City (1M+)
4: City (100K+)
5: Town (10K+)
6: Village (1K+)
7: Hamlet (<1K)
8: District (행정구)
9: Borough
10: Township
11: Commune
12-15: Reserved
```

#### coastal (2비트 = 4개)

**검증 항목**:
- [ ] 해안선 정의 (강 하구 포함?)
- [ ] 섬 전체를 coastal로 볼 것인가?

**제안 분류**:
```
0: Unknown
1: Inland (>50km from coast)
2: Coastal (<50km)
3: Island
```

### TASK-O4: Organization (0x2C) 새 필드 검증

#### hq_region (6비트 = 64개/국가)

- Settlement의 birth_region과 유사하게 처리

#### status (3비트 = 8개)

**제안 분류**:
```
0: Unknown
1: Active
2: Inactive
3: Dissolved
4: Merged
5: Acquired
6: Bankrupt
7: Historical
```

#### ideology (3비트 = 8개)

**검증 항목**:
- [ ] 정당 전용 (비정당은 0)
- [ ] 정치학적 분류 기준

**제안 분류**:
```
0: N/A (비정당)
1: Far-left
2: Left
3: Center-left
4: Center
5: Center-right
6: Right
7: Far-right
```

#### sector (2비트 = 4개)

```
0: Unknown
1: Public (정부/공기업)
2: Private
3: Non-profit
```

### TASK-O5: Film (0x33) 새 필드 검증

#### director_fame (4비트 = 16등급)

**검증 항목**:
- [ ] 저명도 산정 기준 (작품수? 수상? 흥행?)
- [ ] 신인 감독 처리

#### cast_tier (3비트 = 8등급)

**검증 항목**:
- [ ] 출연진 저명도 집계 방법
- [ ] 주연/조연 가중치

#### rating (3비트 = 8개)

**제안 분류**:
```
0: Unknown
1: G (전체관람가)
2: PG
3: PG-13 / 12
4: R / 15
5: NC-17 / 18
6: X / Adult
7: Unrated
```

#### format (3비트 = 8개)

**제안 분류**:
```
0: Unknown
1: Feature Film (극영화)
2: Short Film (단편)
3: Documentary
4: Animation
5: TV Movie
6: Direct-to-video
7: Web Film
```

---

## 공통 원칙

1. **code=0은 항상 Unknown/N/A**
2. **상위 코드가 더 일반적** (열화 시 의미 유지)
3. **외부 표준 우선** (ISO, 학문 분류 등)
4. **문화 중립** (특정 국가 기준 피함)

---

## 산출물

| 파일 | 내용 |
|------|------|
| output/ontology_review.md | 분류 체계 검토 결과 |
| output/codebook_labels.json | 검증된 라벨 목록 |

---

## 체크리스트

- [ ] TASK-O1: Human 새 필드 검증
- [ ] TASK-O2: Star 새 필드 검증
- [ ] TASK-O3: Settlement 새 필드 검증
- [ ] TASK-O4: Organization 새 필드 검증
- [ ] TASK-O5: Film 새 필드 검증
- [ ] 경계 사례 문서화
- [ ] Architect 승인 요청
