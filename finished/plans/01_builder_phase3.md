# Builder Plan: Phase 3 스크립트 수정 및 실행

**역할**: 스크립트 수정, 파이프라인 실행

---

## 목표

새 스키마(v0.2)를 지원하도록 Stage 4-5 스크립트를 수정하고 실행

---

## 작업 목록

### TASK-B1: stage4_codebook.py 수정

**현재 상태**: 기존 필드만 코드북 생성

**수정 필요**:

1. 새 필드 코드북 생성 추가:
   ```python
   NEW_FIELDS = {
       '0x00': ['language', 'birth_region', 'activity_field'],
       '0x0C': ['radial_vel', 'redshift', 'parallax', 'pm_class'],
       '0x1C': ['elevation', 'settlement_type', 'coastal'],
       '0x2C': ['hq_region', 'status', 'ideology', 'sector'],
       '0x33': ['director_fame', 'cast_tier', 'rating', 'format'],
   }
   ```

2. 파생 필드 계산 로직:
   ```python
   def derive_coastal(lat, lon):
       """좌표에서 해안 여부 계산 (50km 기준)"""
       # 간단 버전: 섬나라면 Island, 아니면 Unknown
       return 0  # 일단 Unknown

   def derive_sector(legal_form):
       """법인형태에서 공공/민간 파생"""
       PUBLIC_FORMS = ['government', 'public']
       NONPROFIT_FORMS = ['nonprofit', 'ngo', 'foundation']
       if any(p in legal_form.lower() for p in PUBLIC_FORMS):
           return 1  # Public
       if any(p in legal_form.lower() for p in NONPROFIT_FORMS):
           return 3  # Non-profit
       return 2  # Private
   ```

3. 양자화 규칙 적용:
   ```python
   def apply_quantization(field_name, value):
       """quantization_rules.json 기반 양자화"""
       rules = load_quantization_rules()
       if field_name in rules:
           for r in rules[field_name]['ranges']:
               if r['range'][0] <= value < r['range'][1]:
                   return r['code']
       return 0  # Unknown
   ```

### TASK-B2: stage5_validate.py 수정

**수정 필요**:

1. 새 필드 인코딩 지원
2. 48비트 전체 마스크 테스트 추가
3. 필드별 커버리지 통계

### TASK-B3: 파이프라인 실행

```bash
# DB 연결 확인
PGPASSWORD=test1224 psql -h localhost -U geul_reader -d geuldev -c "SELECT 1"

# Stage 4 실행 (새 코드북)
python scripts/stage4_codebook.py 0x00 0x0C 0x1C 0x2C 0x33

# Stage 5 실행 (검증)
python scripts/stage5_validate.py 0x00 0x0C 0x1C 0x2C 0x33
```

---

## 예상 소요

| 작업 | 예상 |
|------|------|
| TASK-B1 | 스크립트 수정 |
| TASK-B2 | 스크립트 수정 |
| TASK-B3 | 파이프라인 실행 |

---

## 산출물

| 파일 | 내용 |
|------|------|
| output/stage4_v2_report.md | 코드북 생성 보고서 |
| output/stage5_v2_report.md | 검증 보고서 |
| output/codebooks_v2/*.md | 타입별 코드북 (5개) |

---

## 체크리스트

- [ ] TASK-B1: stage4_codebook.py 수정
- [ ] TASK-B2: stage5_validate.py 수정
- [ ] TASK-B3: 파이프라인 실행
- [ ] 결과 보고서 생성
