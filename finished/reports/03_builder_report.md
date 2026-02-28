# Builder 보고서: 구현 및 파이프라인 실행 결과

**작성일**: 2026-02-01
**작성자**: Builder

---

## 1. 스크립트 현황

| 스크립트 | 버전 | 상태 | 수정 사항 |
|----------|------|------|-----------|
| stage1_run.py | v1.0 | 정상 | - |
| stage2_dependency.py | v2.0 | 수정됨 | 외부 ID 필터링 추가 |
| stage3_allocate.py | v2.1 | 수정됨 | 엔트로피 기반 우선순위 |
| stage4_codebook.py | v2.1 | 수정됨 | 샘플 5K→20K, parent_field 버그 수정 |
| stage5_validate.py | v2.1 | 수정됨 | 마스크 로직, 다중값 정렬 |

## 2. Phase 2.5 최적화 구현

### OPT-1: 비트 할당 개선

```python
# 변경 전
universality = coverage / log2(cardinality)

# 변경 후 (stage3_allocate.py:219-227)
discrimination = coverage * entropy / sqrt(cardinality)
```

### OPT-2: SIMD 마스크 로직

```python
# 변경: 코드북에 없는 값은 마스크에서 제외
if value not in codebook:
    continue  # mask에 해당 필드 미포함
```

### OPT-3: 다중값 속성 정렬

```python
# 변경: 정렬된 첫 번째 값 사용으로 결정론성 보장
values = sorted(temp_values[eid][prop])
entity_values[eid][prop] = values[0]
```

### OPT-4: 코드북 커버리지 확대

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| sample_size | 5,000 | 20,000 |
| 총 코드북 | 18,204 | 43,439 |
| 총 엔트리 | 49,971 | 142,506 |

## 3. 해결된 버그

| ID | 문제 | 해결 |
|----|------|------|
| B-001 | hash() 비결정론성 | 코드북 기반 인코딩 |
| B-002 | Stage 5-B 미구현 | 추상 표현 테스트 구현 |
| B-004 | 외부 ID 오염 | datatype 필터링 |
| BUG-1 | parent_field 매칭 오류 | property_id로 매칭 |
| BUG-2 | ORDER BY RANDOM 느림 | LIMIT만 사용 |
| BUG-3 | 딕셔너리 키 불일치 | 'name'/'prop' 통일 |

## 4. 실행 결과

### 파이프라인 실행 시간

| Stage | 실행 시간 | 비고 |
|-------|-----------|------|
| Stage 2 | ~2분 | 5개 타입, 298 DAG 엣지 |
| Stage 3 | ~3분 | 충돌률 계산 포함 |
| Stage 4 | ~40분 | 20K 샘플, 레이블 조회 병목 |
| Stage 5 | ~5분 | 4가지 테스트 |

### DB 테이블 생성

| 테이블 | 행 수 |
|--------|-------|
| entity_type_map | 63 |
| property_stats | 1,847 |
| dependency_dag | 298 |
| bit_allocation | 38 |
| codebook | 43,439 |
| collision_stats | 5 |

## 5. 남은 작업

| 우선순위 | 작업 | 예상 공수 |
|----------|------|-----------|
| P1 | quantization_rules.json 연동 | 4h |
| P2 | 공통 모듈 추출 (scripts/common/) | 8h |
| P2 | 타임스탬프 기반 캐시 | 4h |
| P3 | Stage 4 병렬화 (레이블 조회) | 8h |

---

*Builder - GEUL Entity SIDX Team*
