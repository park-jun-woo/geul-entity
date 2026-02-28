# Phase 3: 48비트 검증 및 튜닝 마스터 계획

**버전**: v1.0
**작성일**: 2026-02-01
**목표**: 새 스키마(v0.2)로 Stage 3-5 재실행 및 충돌률 검증

---

## 배경

Phase 2.5에서 48비트 전체 활용 스키마를 설계하고 시뮬레이션으로 검증했습니다.

### 완료된 작업

- [x] type_schemas.json v0.2 (Reserved 제거, 새 필드 추가)
- [x] quantization_rules.json v0.2 (새 양자화 규칙)
- [x] 시뮬레이션 검증 (충돌률 0.0~0.1%)

### 미완료 작업

- [ ] Stage 3-5 파이프라인 재실행
- [ ] 실제 충돌률 측정
- [ ] SIMD 마스크 테스트

---

## 목표 지표

| 타입 | 이전 충돌률 | 목표 충돌률 | 시뮬레이션 예상 |
|------|------------|------------|----------------|
| Human | 21.25% | < 5% | 0.0% |
| Star | 18.40% | < 5% | 0.1% |
| Settlement | 9.68% | < 3% | 0.0% |
| Organization | 32.64% | < 10% | 0.0% |
| Film | 9.61% | < 3% | 0.0% |

---

## 실행 계획

### Phase 3-A: 스크립트 수정 (Builder)

Stage 4 스크립트를 새 필드 지원하도록 수정:

1. `stage4_codebook.py` 수정
   - 새 필드 코드북 생성 로직 추가
   - P1412 (language), P2216 (radial_vel) 등
   - 파생 필드 계산 (coastal, sector, rating)

2. `stage5_validate.py` 수정
   - 새 필드 포함 인코딩
   - 48비트 전체 마스크 테스트

### Phase 3-B: 파이프라인 실행 (Builder)

```bash
# 1. Stage 4: 확장 코드북 생성
python scripts/stage4_codebook.py 0x00 0x0C 0x1C 0x2C 0x33

# 2. Stage 5: 검증
python scripts/stage5_validate.py 0x00 0x0C 0x1C 0x2C 0x33
```

### Phase 3-C: 결과 검토 (Architect + Analyst)

1. 충돌률 목표 달성 여부
2. 코드북 커버리지 분석
3. Unknown 비율 분석

### Phase 3-D: 튜닝 (필요시)

충돌률 목표 미달 시:
- 코드북 확장
- 비트 재배분
- 필드 교체

---

## 역할 분담

| 역할 | 담당 작업 |
|------|----------|
| **Builder** | 스크립트 수정, 파이프라인 실행 |
| **Analyst** | 결과 분석, 통계 검토 |
| **Ontologist** | 새 코드북 라벨 검증 |
| **Architect** | 최종 승인, 튜닝 결정 |
| **DBA** | 성능 분석 (필요시) |

---

## 산출물

| 파일 | 내용 |
|------|------|
| output/stage4_v2_report.md | 확장 코드북 보고서 |
| output/stage5_v2_report.md | 검증 보고서 |
| output/codebooks_v2/*.md | 새 코드북 (5개 타입) |

---

## 리스크

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| DB 연결 실패 | 중 | 높음 | 로컬 캐시 활용 |
| 코드북 오버플로 | 낮음 | 중 | 비트 재조정 |
| 충돌률 목표 미달 | 낮음 | 중 | Phase 3-D 튜닝 |

---

## 승인 체크리스트

- [ ] Phase 3-A: 스크립트 수정 완료
- [ ] Phase 3-B: 파이프라인 실행 완료
- [ ] Phase 3-C: 결과 검토 완료
- [ ] 충돌률 목표 달성 확인

---

*GEUL Entity Team - Phase 3 Master Plan*
