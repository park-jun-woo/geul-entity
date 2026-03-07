# GEUL Entity SIDX 48비트 전체 활용 스키마 보고서

**버전**: v0.2
**작성일**: 2026-02-01
**상태**: Phase 3 준비 완료

---

## 요약

Reserved 비트를 제거하고 48비트 전체를 활용하는 스키마로 업데이트 완료.

### 변경 전후 비교

| 타입 | 이전 사용 | 이전 Reserved | 현재 사용 | 현재 Reserved |
|------|----------|--------------|----------|--------------|
| Human | 32비트 | 16비트 | **48비트** | **0비트** |
| Star | 32비트 | 16비트 | **48비트** | **0비트** |
| Settlement | 37비트 | 11비트 | **48비트** | **0비트** |
| Organization | 34비트 | 14비트 | **48비트** | **0비트** |
| Film | 35비트 | 13비트 | **48비트** | **0비트** |

---

## 타입별 새 스키마

### Human (0x00) - 48비트

```
[ 0: 4] subclass        5비트   소분류 32개
[ 5:10] occupation      6비트   직업 64개 (P106)
[11:18] country         8비트   국적 256개 (P27)
[19:22] era             4비트   시대 16개 (P569)
[23:26] decade          4비트   10년대
[27:28] gender          2비트   성별 4개 (P21)
[29:31] notability      3비트   저명도 8개
[32:37] language        6비트   사용 언어 64개 (P1412) [NEW]
[38:43] birth_region    6비트   출생 지역 64개 (P19) [NEW]
[44:47] activity_field  4비트   활동 분야 16개 (P101) [NEW]
```

**새 필드 분석**:
- `language`: 커버리지 71.4%, 상위 64개 언어로 85%+ 커버
- `birth_region`: 커버리지 91.4%, 국가 종속 코드북
- `activity_field`: 커버리지 미확인, occupation과 보완 관계

### Star (0x0C) - 48비트

```
[ 0: 6] constellation   7비트   별자리 88개 (P59)
[ 7:10] spectral_type   4비트   분광형 (P215)
[11:13] luminosity      3비트   광도등급 I-VII
[14:17] magnitude       4비트   겉보기등급 (P1215)
[18:21] ra_zone         4비트   적경 구역 (P6257)
[22:25] dec_zone        4비트   적위 구역 (P6258)
[26:31] flags           6비트   특성 플래그
[32:36] radial_vel      5비트   시선속도 32구간 (P2216) [NEW]
[37:41] redshift        5비트   적색편이 32구간 (P1090) [NEW]
[42:45] parallax        4비트   시차 16구간 (P2214) [NEW]
[46:47] pm_class        2비트   고유운동 4분류 (P10751) [NEW]
```

**새 필드 분석**:
- `radial_vel`: 커버리지 98.3%, 속도 기반 양자화
- `redshift`: 커버리지 93.5%, 로그 스케일 양자화
- `parallax`: 커버리지 26.9%, 거리 역산
- `pm_class`: 커버리지 58.2%, 이동 분류

### Settlement (0x1C) - 48비트

```
[ 0: 7] country         8비트   국가 256개 (P17)
[ 8:11] admin_level     4비트   행정 레벨
[12:19] admin_code      8비트   행정구역 (P131)
[20:23] lat_zone        4비트   위도 구역 (P625)
[24:27] lon_zone        4비트   경도 구역
[28:31] population      4비트   인구 규모 (P1082)
[32:36] timezone        5비트   시간대 (P421)
[37:41] elevation       5비트   고도 32구간 (P2044) [NEW]
[42:45] settlement_type 4비트   정주지 유형 16개 (P31) [NEW]
[46:47] coastal         2비트   해안 여부 4개 [DERIVED]
```

**새 필드 분석**:
- `elevation`: 커버리지 33.7%, 고도 양자화
- `settlement_type`: 커버리지 100%, P31 세분화
- `coastal`: 파생 필드, 좌표 기반 계산

### Organization (0x2C) - 48비트

```
[ 0: 7] country         8비트   국가 256개 (P17)
[ 8:11] org_type        4비트   조직 유형
[12:17] legal_form      6비트   법인 형태 (P1454)
[18:25] industry        8비트   산업 분류 (P452)
[26:29] era             4비트   설립 시대 (P571)
[30:33] size            4비트   규모
[34:39] hq_region       6비트   본사 지역 64개 (P159) [NEW]
[40:42] status          3비트   상태 8개 (P576) [NEW]
[43:45] ideology        3비트   이념 8개 (P1142) [NEW]
[46:47] sector          2비트   공공/민간 4개 [DERIVED]
```

**새 필드 분석**:
- `hq_region`: 커버리지 65.2%, 국가 종속 코드북
- `status`: 커버리지 19.5%, 활동/해산 등
- `ideology`: 커버리지 33%, 정당 전용
- `sector`: 파생 필드, legal_form 기반

### Film (0x33) - 48비트

```
[ 0: 7] country         8비트   제작국 256개 (P495)
[ 8:14] year            7비트   개봉연도 (P577)
[15:20] genre           6비트   장르 64개 (P136)
[21:28] language        8비트   원어 256개 (P364)
[29:30] color           2비트   컬러/흑백 (P462)
[31:34] duration        4비트   상영시간 (P2047)
[35:38] director_fame   4비트   감독 저명도 16등급 (P57) [NEW]
[39:41] cast_tier       3비트   출연진 등급 8개 (P161) [NEW]
[42:44] rating          3비트   연령등급 8개 [DERIVED]
[45:47] format          3비트   포맷 8개 (P31) [NEW]
```

**새 필드 분석**:
- `director_fame`: 커버리지 79.7%, sitelinks 기반 등급
- `cast_tier`: 커버리지 58.0%, 출연진 저명도 평균
- `rating`: 파생 필드, 국가별 기준 통합
- `format`: 커버리지 100%, P31 세분화

---

## 예상 효과

### 충돌률 개선 예상

| 타입 | 이전 충돌률 | 예상 충돌률 | 개선율 |
|------|------------|------------|--------|
| Human | 21.25% | **< 8%** | 60%+ |
| Star | 18.40% | **< 6%** | 65%+ |
| Settlement | 9.68% | **< 4%** | 60%+ |
| Organization | 32.64% | **< 12%** | 65%+ |
| Film | 9.61% | **< 4%** | 60%+ |

**근거**: 추가 16비트로 2^16 = 65,536배 더 많은 조합 가능

### SIMD 쿼리 지원

모든 새 필드가 비트 경계에 정렬되어 SIMD 마스크 연산 가능:
- Human language: 마스크 `0x0000FC0000000000` (offset 32, 6비트)
- Star radial_vel: 마스크 `0x00001F0000000000` (offset 32, 5비트)

---

## [REVIEW] 검토 필요 항목

### R1: activity_field 커버리지 미확인

- P101 속성의 실제 커버리지 데이터 없음
- Stage 1 재분석 또는 코드북 생성 시 확인 필요

### R2: rating 파생 규칙 미정의

- 국가별 연령등급 표준이 다름 (MPAA vs BBFC vs 한국)
- LLM 기반 추정 또는 표준 매핑 테이블 필요

### R3: coastal 계산 로직 미구현

- 좌표 → 해안선 거리 계산 필요
- 해안선 데이터셋 (Natural Earth 등) 연동 필요

### R4: parallax 낮은 커버리지

- 26.9%만 데이터 있음
- 74% Unknown (code=0) → 열화 시 무시됨

---

## 다음 단계

1. **Stage 3 재실행**: 새 스키마로 비트 할당 검증
2. **Stage 4 확장**: 새 필드 코드북 생성
3. **Stage 5 재검증**: 충돌률 및 SIMD 테스트

---

## 승인 체크리스트

- [x] type_schemas.json v0.2 업데이트
- [x] quantization_rules.json v0.2 업데이트
- [ ] Stage 3-5 재실행
- [ ] 목표 충돌률 확인

---

*GEUL Entity Team - Architect Report*
*Date: 2026-02-01*
