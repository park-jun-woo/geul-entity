# Analyst Plan: Phase 3 결과 분석

**역할**: 충돌률 분석, 통계 검토

---

## 목표

Stage 5 결과를 분석하여 목표 달성 여부 판단

---

## 분석 항목

### TASK-A1: 충돌률 분석

| 타입 | 목표 | 판정 기준 |
|------|------|----------|
| Human | < 5% | PASS if ≤5%, WARN if 5-10%, FAIL if >10% |
| Star | < 5% | PASS if ≤5%, WARN if 5-10%, FAIL if >10% |
| Settlement | < 3% | PASS if ≤3%, WARN if 3-5%, FAIL if >5% |
| Organization | < 10% | PASS if ≤10%, WARN if 10-15%, FAIL if >15% |
| Film | < 3% | PASS if ≤3%, WARN if 3-5%, FAIL if >5% |

### TASK-A2: 필드별 커버리지 분석

새 필드의 Unknown(code=0) 비율 측정:

| 필드 | 목표 커버리지 | 위험 신호 |
|------|--------------|----------|
| language | > 60% | Unknown > 40% |
| birth_region | > 80% | Unknown > 30% |
| radial_vel | > 50% | Unknown > 60% |
| elevation | > 30% | Unknown > 80% |

### TASK-A3: 비트 효율 분석

각 필드가 충돌 감소에 기여한 정도:

```
효율 = (이전 충돌률 - 현재 충돌률) / 추가 비트 수
```

### TASK-A4: 개선 제안

충돌률 목표 미달 시:
1. Unknown 과다 필드 → 코드북 확장
2. 저효율 필드 → 다른 필드로 교체
3. 전체적 미달 → 비트 재배분

---

## 분석 쿼리

```sql
-- 필드별 Unknown 비율 (Stage 5 결과에서)
SELECT
  field_name,
  COUNT(*) FILTER (WHERE code = 0) * 100.0 / COUNT(*) as unknown_pct
FROM encoding_results
GROUP BY field_name;

-- 충돌 발생 패턴
SELECT
  sidx,
  COUNT(*) as collision_count
FROM encoding_results
GROUP BY sidx
HAVING COUNT(*) > 1
ORDER BY collision_count DESC
LIMIT 20;
```

---

## 산출물

| 파일 | 내용 |
|------|------|
| output/analysis_phase3.md | 분석 보고서 |

---

## 체크리스트

- [ ] TASK-A1: 충돌률 분석
- [ ] TASK-A2: 필드별 커버리지 분석
- [ ] TASK-A3: 비트 효율 분석
- [ ] TASK-A4: 개선 제안 (필요시)
