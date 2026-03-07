# Analyst Plan: 48비트 전체 활용 분석

**역할**: 새 필드 후보 데이터 분석, 최적 비트 수 결정

---

## 분석 목표

Reserved 비트를 채울 새 필드들의 최적 구성을 데이터 기반으로 결정

---

## 타입별 분석 태스크

### TASK-A1: Human (0x00) 추가 필드 분석

**추가 비트**: 16비트

| 후보 필드 | 속성 | 커버리지 | 카디널리티 | 제안 비트 | 분석 필요 |
|-----------|------|----------|-----------|----------|----------|
| language | P1412 | 71.4% | 336 | 6비트 | 상위 64개 언어 분포 |
| birth_region | P19 | 91.4% | 16,850 | 6비트 | 국가별 지역 클러스터링 |
| activity_field | P101 | ? | ? | 4비트 | 커버리지 확인 필요 |

**분석 쿼리**:
```sql
-- P1412 언어 분포 (상위 64개로 얼마나 커버되는지)
SELECT value, COUNT(*) as cnt
FROM entity_property_values
WHERE entity_type = '0x00' AND property_id = 'P1412'
GROUP BY value ORDER BY cnt DESC LIMIT 100;

-- P101 전문분야 커버리지
SELECT COUNT(DISTINCT entity_id)::float /
       (SELECT COUNT(*) FROM entities WHERE type_code = '0x00') * 100
FROM entity_property_values
WHERE entity_type = '0x00' AND property_id = 'P101';
```

### TASK-A2: Star (0x0C) 추가 필드 분석

**추가 비트**: 16비트

| 후보 필드 | 속성 | 커버리지 | 카디널리티 | 제안 비트 | 분석 필요 |
|-----------|------|----------|-----------|----------|----------|
| radial_vel | P2216 | 98.3% | 36,346 | 5비트 | 속도 분포, 양자화 구간 |
| redshift | P1090 | 93.5% | 75,977 | 5비트 | z값 분포, 양자화 구간 |
| parallax | P2214 | 26.9% | 8,175 | 4비트 | 거리 분포 |
| pm_class | P10751/52 | 58.2% | - | 2비트 | 고유운동 클러스터 |

**양자화 분석**:
```sql
-- radial velocity 분포 (32개 구간 최적화)
SELECT
  WIDTH_BUCKET(value::float, -500, 500, 32) as bucket,
  COUNT(*) as cnt
FROM entity_property_values
WHERE entity_type = '0x0C' AND property_id = 'P2216'
GROUP BY bucket ORDER BY bucket;
```

### TASK-A3: Settlement (0x1C) 추가 필드 분석

**추가 비트**: 11비트

| 후보 필드 | 속성 | 커버리지 | 제안 비트 | 분석 필요 |
|-----------|------|----------|----------|----------|
| elevation | P2044 | 33.7% | 5비트 | 고도 분포, 32구간 |
| settlement_type | P31 | 100% | 4비트 | 하위 타입 분포 |
| coastal | 좌표파생 | - | 2비트 | 해안선 거리 계산 |

### TASK-A4: Organization (0x2C) 추가 필드 분석

**추가 비트**: 14비트

| 후보 필드 | 속성 | 커버리지 | 제안 비트 | 분석 필요 |
|-----------|------|----------|----------|----------|
| hq_region | P159 | 65.2% | 6비트 | 본사 지역 클러스터 |
| status | P576 | 19.5% | 3비트 | 활동/해산 분포 |
| ideology | P1142 | 33% | 3비트 | 정당용, 비정당은 0 |
| sector | 파생 | - | 2비트 | legal_form에서 파생 |

### TASK-A5: Film (0x33) 추가 필드 분석

**추가 비트**: 13비트

| 후보 필드 | 속성 | 커버리지 | 제안 비트 | 분석 필요 |
|-----------|------|----------|----------|----------|
| director_fame | P57 | 79.7% | 4비트 | 감독 작품수/수상 기반 등급 |
| cast_tier | P161 | 58.0% | 3비트 | 출연진 저명도 평균 |
| rating | 파생 | - | 3비트 | 장르/국가 기반 추정 |
| format | P31 | 100% | 3비트 | 극장/TV/단편 구분 |

---

## 분석 우선순위

1. **P1** (즉시): 커버리지 높은 필드 확정 (language, radial_vel, redshift)
2. **P2** (검증 후): 파생 필드 계산 로직 (coastal, sector, rating)
3. **P3** (선택): 저커버리지 필드 포함 여부 (activity_field, ideology)

---

## 산출물

| 파일 | 내용 |
|------|------|
| output/full48_analysis.md | 타입별 새 필드 분석 결과 |
| geulwork.new_field_stats | 새 필드 통계 테이블 |

---

## 체크리스트

- [ ] TASK-A1: Human 추가 필드 분석
- [ ] TASK-A2: Star 추가 필드 분석
- [ ] TASK-A3: Settlement 추가 필드 분석
- [ ] TASK-A4: Organization 추가 필드 분석
- [ ] TASK-A5: Film 추가 필드 분석
- [ ] 비트 최적화 제안서 작성
