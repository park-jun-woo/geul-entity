# Builder Plan: 48비트 전체 활용 구현

**역할**: 스키마/스크립트 수정, 파이프라인 실행

---

## 구현 목표

Reserved 비트를 제거하고 새 필드를 추가하여 48비트 전체 활용

---

## 태스크 목록

### TASK-B1: type_schemas.json 수정

**파일**: `references/type_schemas.json`

**변경 내용**:
1. 모든 타입에서 `reserved` 필드 제거
2. 새 필드 추가 (Architect 승인 후)

**예시 (Human)**:
```json
{
  "0x00_Human": {
    "fields": [
      {"name": "subclass", "bits": 5, "offset": 0},
      {"name": "occupation", "bits": 6, "offset": 5},
      {"name": "country", "bits": 8, "offset": 11},
      {"name": "era", "bits": 4, "offset": 19},
      {"name": "decade", "bits": 4, "offset": 23},
      {"name": "gender", "bits": 2, "offset": 27},
      {"name": "notability", "bits": 3, "offset": 29},
      {"name": "language", "bits": 6, "offset": 32},      // NEW
      {"name": "birth_region", "bits": 6, "offset": 38},  // NEW
      {"name": "activity", "bits": 4, "offset": 44}       // NEW
    ]
  }
}
```

### TASK-B2: quantization_rules.json 업데이트

**파일**: `references/quantization_rules.json`

**추가 규칙**:
```json
{
  "radial_velocity": {
    "type": "numeric_bucket",
    "ranges": [
      {"min": -1000, "max": -100, "code": 0, "label": "very_negative"},
      {"min": -100, "max": -10, "code": 1, "label": "negative"},
      ...
    ]
  },
  "redshift": {
    "type": "log_bucket",
    "base": 10,
    "ranges": [...]
  },
  "elevation": {
    "type": "numeric_bucket",
    "ranges": [
      {"min": -500, "max": 0, "code": 0, "label": "below_sea"},
      {"min": 0, "max": 100, "code": 1, "label": "lowland"},
      ...
    ]
  }
}
```

### TASK-B3: stage3_allocate.py 수정

**변경 내용**:
1. Reserved 필드 생성 로직 제거
2. 새 필드 매핑 추가

```python
# 수정 전
if remaining_bits > 0:
    fields.append({
        'name': 'reserved',
        'bits': remaining_bits,
        ...
    })

# 수정 후
# Reserved 없음 - 48비트 전부 할당
assert sum(f['bits'] for f in fields) == 48, "Must use all 48 bits"
```

### TASK-B4: stage4_codebook.py 확장

**변경 내용**:
1. 새 필드 코드북 생성 로직 추가
2. 파생 필드 계산 로직 구현

```python
def generate_language_codebook():
    """P1412 언어 코드북 (상위 64개)"""
    ...

def generate_birth_region_codebook(country_code):
    """국가별 출생지역 코드북 (64개씩)"""
    ...

def derive_coastal_code(lat, lon):
    """좌표에서 해안 여부 파생"""
    ...
```

### TASK-B5: stage5_validate.py 업데이트

**변경 내용**:
1. 새 필드 포함 충돌률 테스트
2. 새 마스크 패턴 SIMD 테스트

---

## 실행 순서

```bash
# 1. 스키마 수정
vim references/type_schemas.json
vim references/quantization_rules.json

# 2. 스크립트 수정
vim scripts/stage3_allocate.py
vim scripts/stage4_codebook.py
vim scripts/stage5_validate.py

# 3. Stage 3 재실행
python scripts/stage3_allocate.py 0x00 0x0C 0x1C 0x2C 0x33

# 4. Stage 4 재실행 (확장 코드북)
python scripts/stage4_codebook.py 0x00 0x0C 0x1C 0x2C 0x33

# 5. Stage 5 검증
python scripts/stage5_validate.py 0x00 0x0C 0x1C 0x2C 0x33
```

---

## 검증 기준

| 항목 | 목표 | 측정 방법 |
|------|------|----------|
| 비트 합계 | 48비트 정확히 | assert 검사 |
| Human 충돌률 | < 5% | Stage 5-A |
| Star 충돌률 | < 5% | Stage 5-A |
| Settlement 충돌률 | < 3% | Stage 5-A |
| Organization 충돌률 | < 10% | Stage 5-A |
| Film 충돌률 | < 3% | Stage 5-A |
| SIMD 정밀도 | > 80% | Stage 5-B |

---

## 산출물

| 파일 | 내용 |
|------|------|
| references/type_schemas.json | 수정된 스키마 |
| references/quantization_rules.json | 확장된 양자화 규칙 |
| output/stage3_report.md | 새 비트 할당 보고서 |
| output/stage4_report.md | 확장 코드북 보고서 |
| output/stage5_report.md | 검증 보고서 |

---

## 체크리스트

- [ ] TASK-B1: type_schemas.json 수정
- [ ] TASK-B2: quantization_rules.json 업데이트
- [ ] TASK-B3: stage3_allocate.py 수정
- [ ] TASK-B4: stage4_codebook.py 확장
- [ ] TASK-B5: stage5_validate.py 업데이트
- [ ] 파이프라인 실행
- [ ] 검증 통과 확인
