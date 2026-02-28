# GEUL Entity SIDX 48비트 전체 활용 마스터 계획

**버전**: v2.0
**작성일**: 2026-02-01
**목표**: Reserved 비트 0, 48비트 전부 활용

---

## 배경

Phase 2 결과에서 11~16비트가 Reserved로 낭비되어 충돌률 6~33%가 발생했습니다.
사용자 지시에 따라 48비트를 전부 활용하도록 재설계합니다.

### 현재 상태

| 타입 | 현재 사용 | Reserved | 충돌률 |
|------|----------|----------|--------|
| Human | 32비트 | **16비트** | 21.25% |
| Star | 32비트 | **16비트** | 18.40% |
| Settlement | 37비트 | **11비트** | 9.68% |
| Organization | 34비트 | **14비트** | 32.64% |
| Film | 35비트 | **13비트** | 9.61% |

---

## 목표

| 타입 | 목표 사용 | Reserved | 목표 충돌률 |
|------|----------|----------|-------------|
| Human | 48비트 | **0비트** | < 5% |
| Star | 48비트 | **0비트** | < 5% |
| Settlement | 48비트 | **0비트** | < 3% |
| Organization | 48비트 | **0비트** | < 10% |
| Film | 48비트 | **0비트** | < 3% |

---

## 타입별 추가 할당 계획

### Human (0x00): +16비트

현재 필드: subclass(5) + occupation(6) + country(8) + era(4) + decade(4) + gender(2) + notability(3) = 32비트

| 새 필드 | 비트 | 속성 | 커버리지 | 근거 |
|---------|------|------|----------|------|
| language | 6 | P1412 | 71.4% | 336개 언어 → 64개 주요 언어 |
| birth_region | 6 | P19 | 91.4% | 국가 내 지역 (국가 종속) |
| activity_field | 4 | P101 | 추가분석 | 전문분야 세분화 |

**새 레이아웃 (48비트)**:
```
[ 0: 4] subclass      (5bit)
[ 5:10] occupation    (6bit) ← P106
[11:18] country       (8bit) ← P27
[19:22] era           (4bit) ← P569
[23:26] decade        (4bit)
[27:28] gender        (2bit) ← P21
[29:31] notability    (3bit)
[32:37] language      (6bit) ← P1412 [NEW]
[38:43] birth_region  (6bit) ← P19 양자화 [NEW]
[44:47] activity      (4bit) ← P101 [NEW]
```

### Star (0x0C): +16비트

현재 필드: constellation(7) + spectral(4) + luminosity(3) + magnitude(4) + ra(4) + dec(4) + flags(6) = 32비트

| 새 필드 | 비트 | 속성 | 커버리지 | 근거 |
|---------|------|------|----------|------|
| radial_vel | 5 | P2216 | 98.3% | 속도 구간 양자화 |
| redshift | 5 | P1090 | 93.5% | z값 구간 양자화 |
| parallax | 4 | P2214 | 26.9% | 거리 추정용 |
| pm_class | 2 | P10751/52 | 58.2% | 고유운동 분류 |

**새 레이아웃 (48비트)**:
```
[ 0: 6] constellation  (7bit) ← P59
[ 7:10] spectral_type  (4bit) ← P215
[11:13] luminosity     (3bit)
[14:17] magnitude      (4bit) ← P1215
[18:21] ra_zone        (4bit) ← P6257
[22:25] dec_zone       (4bit) ← P6258
[26:31] flags          (6bit)
[32:36] radial_vel     (5bit) ← P2216 [NEW]
[37:41] redshift       (5bit) ← P1090 [NEW]
[42:45] parallax       (4bit) ← P2214 [NEW]
[46:47] pm_class       (2bit) ← P10751/52 [NEW]
```

### Settlement (0x1C): +11비트

현재 필드: country(8) + admin_level(4) + admin_code(8) + lat(4) + lon(4) + population(4) + timezone(5) = 37비트

| 새 필드 | 비트 | 속성 | 커버리지 | 근거 |
|---------|------|------|----------|------|
| elevation | 5 | P2044 | 33.7% | 고도 구간 |
| settlement_type | 4 | P31 | 100% | 도시/마을/촌락 세분화 |
| coastal | 2 | 파생 | - | 해안/내륙/도서 |

**새 레이아웃 (48비트)**:
```
[ 0: 7] country        (8bit) ← P17
[ 8:11] admin_level    (4bit)
[12:19] admin_code     (8bit) ← P131
[20:23] lat_zone       (4bit) ← P625
[24:27] lon_zone       (4bit)
[28:31] population     (4bit) ← P1082
[32:36] timezone       (5bit) ← P421
[37:41] elevation      (5bit) ← P2044 [NEW]
[42:45] settlement_type(4bit) ← P31 세분화 [NEW]
[46:47] coastal        (2bit) ← 좌표 파생 [NEW]
```

### Organization (0x2C): +14비트

현재 필드: country(8) + org_type(4) + legal_form(6) + industry(8) + era(4) + size(4) = 34비트

| 새 필드 | 비트 | 속성 | 커버리지 | 근거 |
|---------|------|------|----------|------|
| hq_region | 6 | P159 | 65.2% | 본사 지역 (국가 종속) |
| status | 3 | P576 | 19.5% | 활동/해산/합병 |
| ideology | 3 | P1142 | 33% | 정당용 |
| sector | 2 | 파생 | - | 공공/민간/비영리 |

**새 레이아웃 (48비트)**:
```
[ 0: 7] country        (8bit) ← P17
[ 8:11] org_type       (4bit)
[12:17] legal_form     (6bit) ← P1454
[18:25] industry       (8bit) ← P452
[26:29] era            (4bit) ← P571
[30:33] size           (4bit)
[34:39] hq_region      (6bit) ← P159 [NEW]
[40:42] status         (3bit) ← P576 [NEW]
[43:45] ideology       (3bit) ← P1142 [NEW]
[46:47] sector         (2bit) ← 파생 [NEW]
```

### Film (0x33): +13비트

현재 필드: country(8) + year(7) + genre(6) + language(8) + color(2) + duration(4) = 35비트

| 새 필드 | 비트 | 속성 | 커버리지 | 근거 |
|---------|------|------|----------|------|
| director_fame | 4 | P57 | 79.7% | 감독 저명도 코드북 |
| cast_tier | 3 | P161 | 58.0% | 출연진 등급 |
| rating | 3 | 파생 | - | 연령등급 |
| format | 3 | P31 | 100% | 극장/TV/단편/다큐 |

**새 레이아웃 (48비트)**:
```
[ 0: 7] country        (8bit) ← P495
[ 8:14] year           (7bit) ← P577
[15:20] genre          (6bit) ← P136
[21:28] language       (8bit) ← P364
[29:30] color          (2bit) ← P462
[31:34] duration       (4bit) ← P2047
[35:38] director_fame  (4bit) ← P57 [NEW]
[39:41] cast_tier      (3bit) ← P161 [NEW]
[42:44] rating         (3bit) ← 파생 [NEW]
[45:47] format         (3bit) ← P31 세분화 [NEW]
```

---

## 실행 계획

### Phase 3-A: 스키마 업데이트 (Builder)

1. `references/type_schemas.json` 수정
   - Reserved 필드 제거
   - 새 필드 추가

2. `references/quantization_rules.json` 업데이트
   - 새 필드 양자화 규칙 추가

### Phase 3-B: 코드북 확장 (Builder + Ontologist)

1. 새 필드 코드북 생성
   - language: 64개 주요 언어
   - birth_region: 국가별 주요 지역
   - radial_vel: 속도 구간
   - etc.

2. Ontologist 검토
   - 분류 일관성 확인
   - 경계 사례 처리

### Phase 3-C: 파이프라인 재실행 (Builder)

```bash
# Stage 3 재실행 (새 스키마 적용)
python scripts/stage3_allocate.py 0x00 0x0C 0x1C 0x2C 0x33

# Stage 4 재실행 (확장된 코드북)
python scripts/stage4_codebook.py 0x00 0x0C 0x1C 0x2C 0x33

# Stage 5 재실행 (검증)
python scripts/stage5_validate.py 0x00 0x0C 0x1C 0x2C 0x33
```

### Phase 3-D: 검증 (Analyst)

1. 충돌률 측정
2. SIMD 마스크 테스트
3. 열화 테스트

---

## 역할 분담

| 역할 | 담당 작업 |
|------|----------|
| **Architect** | 최종 스키마 승인, 트레이드오프 결정 |
| **Analyst** | 새 필드 후보 데이터 분석, 최적 비트 수 결정 |
| **Builder** | 스크립트 수정, 파이프라인 실행 |
| **Ontologist** | 분류 체계 검증, 코드북 라벨 검토 |

---

## 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 새 필드 커버리지 낮음 | 0 값 과다 | 우아한 열화로 처리 |
| 코드북 오버플로 | 정보 손실 | 비트 재조정 |
| 계층 종속 복잡도 증가 | 인코딩 오류 | 테스트 강화 |

---

## 승인 체크리스트

- [ ] 타입별 새 필드 구성 승인
- [ ] 비트 할당 승인
- [ ] Phase 3 실행 승인

---

*GEUL Entity Team - Full 48-bit Utilization Plan*
