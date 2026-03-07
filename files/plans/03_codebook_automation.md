# 59개 타입 코드북 생성 자동화 전략

**Version:** v1.0
**Created:** 2026-02-01
**Status:** Planning

---

## 1. 개요

### 1.1 목표
64개 EntityType 중 예약(0x3F) 및 데이터 미존재 타입을 제외한 59개 타입에 대해:
- 코드북 JSON을 자동 생성
- 카테고리별 공통 양자화 규칙 재사용
- LLM 검증을 통한 품질 보장
- 배치 처리로 전체 타입 일괄 생성

### 1.2 현재 상태

```
구현 완료:
- scripts/stage1_extract.py: 속성 분석 (템플릿)
- scripts/stage2_dependency.py: 종속성 분석
- scripts/stage3_allocate.py: 비트 할당
- scripts/stage4_codebook.py: 코드북 생성 (단일 타입)
- scripts/stage5_validate.py: 검증

미구현:
- 배치 오케스트레이터
- 카테고리별 공통 규칙 적용 로직
- LLM 검증 자동화
- 코드북 JSON 표준 포맷
```

---

## 2. 타입 카테고리화

### 2.1 9개 카테고리

| 범위 | 카테고리 | 개수 | 공통 속성 |
|------|----------|------|-----------|
| 0x00-0x07 | 생물/인물 | 8 | era, language, notability |
| 0x08-0x0B | 화학/물질 | 4 | classification, formula_type |
| 0x0C-0x13 | 천체 | 8 | constellation, magnitude, coordinate |
| 0x14-0x1B | 지형/자연 | 8 | coordinate, elevation, country |
| 0x1C-0x23 | 장소/행정 | 8 | country, coordinate, population |
| 0x24-0x2B | 건축물 | 8 | country, era, coordinate |
| 0x2C-0x2F | 조직 | 4 | country, era, industry, status |
| 0x30-0x3B | 창작물 | 12 | country, era, genre, language |
| 0x3C-0x3F | 이벤트/예약 | 4 | country, era, date |

### 2.2 카테고리별 공통 양자화 규칙

**references/quantization_rules.json**에서 재사용할 규칙:

```json
{
  "shared_rules": {
    "생물/인물": ["time_era", "time_decade", "notability", "language"],
    "화학/물질": [],
    "천체": ["magnitude", "radial_velocity", "redshift", "parallax", "pm_class"],
    "지형/자연": ["coordinate", "elevation", "population"],
    "장소/행정": ["coordinate", "population", "elevation", "settlement_type", "coastal"],
    "건축물": ["coordinate", "time_era"],
    "조직": ["time_era", "org_status", "ideology", "sector"],
    "창작물": ["time_era", "duration", "film_rating", "film_format", "director_fame", "cast_tier"],
    "이벤트": ["time_era"]
  }
}
```

---

## 3. 배치 처리 아키텍처

### 3.1 오케스트레이터 설계

```
scripts/
├── run_all_stages.py           # 전체 파이프라인 오케스트레이터
├── batch_codebook.py           # 코드북 배치 생성 (신규)
└── codebook_validator.py       # LLM 검증 (신규)
```

### 3.2 run_all_stages.py 구조

```python
#!/usr/bin/env python3
"""
전체 파이프라인 오케스트레이터

실행 모드:
  --full        : 전체 타입 순차 처리
  --parallel N  : N개 워커로 병렬 처리
  --category X  : 특정 카테고리만
  --resume      : 실패 지점부터 재시작
"""

import argparse
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

TYPES_FILE = "references/entity_types_64.json"
CHECKPOINT_FILE = "cache/pipeline_checkpoint.json"

def load_types(category=None):
    """타입 목록 로드 (카테고리 필터링)"""
    with open(TYPES_FILE) as f:
        data = json.load(f)

    types = [t for t in data['types'] if t['qid'] is not None]

    if category:
        types = [t for t in types if t['category'] == category]

    return types

def run_stage(stage: int, type_code: str):
    """단일 스테이지 실행"""
    scripts = {
        1: "stage1_extract.py",
        2: "stage2_dependency.py",
        3: "stage3_allocate.py",
        4: "stage4_codebook.py",
        5: "stage5_validate.py"
    }

    result = subprocess.run(
        ["python", f"scripts/{scripts[stage]}", type_code],
        capture_output=True, text=True
    )

    return {
        'type_code': type_code,
        'stage': stage,
        'success': result.returncode == 0,
        'stdout': result.stdout,
        'stderr': result.stderr
    }

def save_checkpoint(completed: list, failed: list):
    """체크포인트 저장"""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({'completed': completed, 'failed': failed}, f)

def load_checkpoint():
    """체크포인트 로드"""
    if Path(CHECKPOINT_FILE).exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {'completed': [], 'failed': []}

def process_type_full(type_info: dict) -> dict:
    """단일 타입 전체 스테이지 처리"""
    type_code = type_info['code']
    results = []

    for stage in [1, 2, 3, 4, 5]:
        result = run_stage(stage, type_code)
        results.append(result)

        if not result['success']:
            return {
                'type_code': type_code,
                'success': False,
                'failed_stage': stage,
                'results': results
            }

    return {
        'type_code': type_code,
        'success': True,
        'results': results
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--parallel', type=int, default=1)
    parser.add_argument('--category', type=str)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--stage', type=int, help='특정 스테이지만 실행')
    args = parser.parse_args()

    types = load_types(args.category)

    if args.resume:
        checkpoint = load_checkpoint()
        types = [t for t in types if t['code'] not in checkpoint['completed']]

    print(f"처리 대상: {len(types)}개 타입")

    completed = []
    failed = []

    if args.parallel > 1:
        with ProcessPoolExecutor(max_workers=args.parallel) as executor:
            futures = {executor.submit(process_type_full, t): t for t in types}
            for future in as_completed(futures):
                result = future.result()
                if result['success']:
                    completed.append(result['type_code'])
                else:
                    failed.append(result)
                save_checkpoint(completed, failed)
    else:
        for t in types:
            result = process_type_full(t)
            if result['success']:
                completed.append(result['type_code'])
            else:
                failed.append(result)
            save_checkpoint(completed, failed)

    print(f"\n완료: {len(completed)}, 실패: {len(failed)}")

    if failed:
        print("\n실패 목록:")
        for f in failed:
            print(f"  - {f['type_code']} (stage {f['failed_stage']})")

if __name__ == "__main__":
    main()
```

### 3.3 병렬 처리 전략

**권장 병렬도:**
- Stage 1 (속성 추출): 4-8 워커 (DB I/O bound)
- Stage 2 (종속성): 2-4 워커 (CPU bound)
- Stage 3 (비트 할당): 8-16 워커 (lightweight)
- Stage 4 (코드북): 4-8 워커 (DB I/O bound)
- Stage 5 (검증): 2-4 워커 (mixed)

**의존성 처리:**
```
Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5
(타입 간에는 독립, 스테이지 간에는 순차)
```

---

## 4. 코드북 JSON 표준 포맷

### 4.1 단일 타입 코드북 구조

```json
{
  "version": "1.0",
  "generated": "2026-02-01T12:00:00Z",
  "entity_type": {
    "code": "0x00",
    "name_ko": "인간",
    "name_en": "Human",
    "qid": "Q5"
  },
  "schema": {
    "total_bits": 48,
    "fields": [
      {
        "name": "subclass",
        "bits": 5,
        "offset": 0,
        "parent": null,
        "quantization_rule": null
      },
      {
        "name": "occupation",
        "bits": 6,
        "offset": 5,
        "parent": "subclass",
        "quantization_rule": null
      },
      {
        "name": "era",
        "bits": 4,
        "offset": 19,
        "parent": null,
        "quantization_rule": "time_era"
      }
    ]
  },
  "codebooks": {
    "subclass": {
      "parent_value": null,
      "codes": [
        {"code": 0, "value": "_unknown", "label": "Unknown", "frequency": 0},
        {"code": 1, "value": "Q82955", "label": "Politician", "frequency": 523421},
        {"code": 2, "value": "Q937857", "label": "Football player", "frequency": 312567}
      ]
    },
    "occupation": {
      "conditional": true,
      "by_parent": {
        "Q82955": {
          "parent_label": "Politician",
          "codes": [
            {"code": 0, "value": "_unknown", "label": "Unknown", "frequency": 0},
            {"code": 1, "value": "Q30461", "label": "President", "frequency": 2345}
          ]
        },
        "Q937857": {
          "parent_label": "Football player",
          "codes": [
            {"code": 0, "value": "_unknown", "label": "Unknown", "frequency": 0},
            {"code": 1, "value": "Q18141", "label": "Goalkeeper", "frequency": 8234}
          ]
        }
      }
    },
    "era": {
      "parent_value": null,
      "quantized": true,
      "rule": "time_era",
      "codes": [
        {"code": 0, "label": "Unknown"},
        {"code": 1, "label": "Prehistoric", "range": [null, -3000]},
        {"code": 2, "label": "Ancient", "range": [-3000, 500]}
      ]
    }
  },
  "statistics": {
    "total_entities_sampled": 500000,
    "coverage_by_field": {
      "subclass": 0.95,
      "occupation": 0.78,
      "era": 0.92
    },
    "collision_rate": 0.008
  }
}
```

### 4.2 통합 코드북 인덱스

```json
{
  "version": "1.0",
  "generated": "2026-02-01T12:00:00Z",
  "types": [
    {
      "code": "0x00",
      "name": "Human",
      "file": "codebook_00_Human.json",
      "fields": 10,
      "total_codes": 1245
    },
    {
      "code": "0x01",
      "name": "Taxon",
      "file": "codebook_01_Taxon.json",
      "fields": 8,
      "total_codes": 892
    }
  ],
  "shared_quantization": {
    "time_era": "quantization/time_era.json",
    "coordinate": "quantization/coordinate.json",
    "magnitude": "quantization/magnitude.json"
  }
}
```

### 4.3 디렉토리 구조

```
output/
├── codebooks/
│   ├── index.json                     # 통합 인덱스
│   ├── codebook_00_Human.json
│   ├── codebook_01_Taxon.json
│   ├── ...
│   └── codebook_3E_Election.json
├── quantization/
│   ├── time_era.json
│   ├── coordinate.json
│   ├── magnitude.json
│   └── ...
└── reports/
    ├── stage4_report.md
    └── validation_summary.md
```

---

## 5. LLM 검증 자동화

### 5.1 검증 프롬프트 템플릿

```python
# templates/codebook_verify_prompt.txt

"""
아래는 "{entity_type}" 타입의 "{field_name}" 필드 코드북입니다.

## 코드북
{codebook_table}

## 검증 질문

1. **완전성**: 일반적으로 기대되는 값 중 누락된 것이 있습니까?
   - 예: 성별 필드에 Male, Female만 있고 Non-binary가 없는 경우

2. **일관성**: 같은 레벨의 값들이 상호 배타적입니까?
   - 예: "과학자"와 "물리학자"가 동시에 있으면 계층 오류

3. **상식 정합성**: 코드 할당 순서(빈도)가 상식과 일치합니까?
   - 예: "정치인"이 1번인데 실제로는 "운동선수"가 더 많은 경우

4. **레이블 명확성**: 모든 레이블이 명확하게 해석됩니까?
   - 예: "Q12345" 같은 미해석 QID가 남아있는 경우

## 응답 형식

```json
{{
  "passed": true/false,
  "issues": [
    {{
      "type": "completeness|consistency|common_sense|clarity",
      "severity": "error|warning|info",
      "description": "문제 설명",
      "suggestion": "수정 제안"
    }}
  ],
  "confidence": 0.0-1.0
}}
```
"""
```

### 5.2 검증 자동화 스크립트

```python
#!/usr/bin/env python3
"""
scripts/codebook_validator.py

LLM을 사용한 코드북 검증 자동화
"""

import json
import os
from pathlib import Path

import anthropic

TEMPLATE_FILE = "templates/codebook_verify_prompt.txt"
OUTPUT_DIR = Path("output/codebooks")

def load_template():
    with open(TEMPLATE_FILE) as f:
        return f.read()

def format_codebook_table(codes: list) -> str:
    """코드북을 마크다운 테이블로 포맷"""
    lines = ["| Code | Value | Label | Freq |"]
    lines.append("|------|-------|-------|------|")
    for entry in codes[:30]:  # 상위 30개만
        lines.append(f"| {entry['code']} | {entry['value'][:20]} | {entry['label'][:25]} | {entry.get('frequency', 0):,} |")
    if len(codes) > 30:
        lines.append(f"| ... | ({len(codes) - 30} more) | | |")
    return "\n".join(lines)

def validate_codebook(entity_type: str, field_name: str, codes: list) -> dict:
    """단일 코드북 LLM 검증"""
    template = load_template()
    codebook_table = format_codebook_table(codes)

    prompt = template.format(
        entity_type=entity_type,
        field_name=field_name,
        codebook_table=codebook_table
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    # JSON 파싱
    try:
        result = json.loads(response.content[0].text)
    except json.JSONDecodeError:
        result = {
            "passed": False,
            "issues": [{"type": "parse_error", "description": "LLM 응답 파싱 실패"}],
            "confidence": 0
        }

    return result

def validate_type_codebooks(type_code: str) -> list:
    """타입 전체 코드북 검증"""
    codebook_file = OUTPUT_DIR / f"codebook_{type_code}.json"

    if not codebook_file.exists():
        return [{"error": f"코드북 파일 없음: {codebook_file}"}]

    with open(codebook_file) as f:
        data = json.load(f)

    entity_type = data['entity_type']['name_ko']
    results = []

    for field_name, field_data in data['codebooks'].items():
        if field_data.get('quantized'):
            # 양자화 규칙은 이미 검증됨
            results.append({
                "field": field_name,
                "skipped": True,
                "reason": "quantized rule"
            })
            continue

        if field_data.get('conditional'):
            # 조건부 코드북은 각 부모값별로 검증
            for parent_val, parent_data in field_data['by_parent'].items():
                result = validate_codebook(
                    entity_type,
                    f"{field_name} (when {parent_val})",
                    parent_data['codes']
                )
                result['field'] = field_name
                result['parent_value'] = parent_val
                results.append(result)
        else:
            result = validate_codebook(
                entity_type,
                field_name,
                field_data['codes']
            )
            result['field'] = field_name
            results.append(result)

    return results

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', help='특정 타입만 검증')
    parser.add_argument('--all', action='store_true', help='전체 검증')
    parser.add_argument('--output', default='output/validation_results.json')
    args = parser.parse_args()

    results = {}

    if args.type:
        results[args.type] = validate_type_codebooks(args.type)
    elif args.all:
        for codebook_file in OUTPUT_DIR.glob("codebook_*.json"):
            type_code = codebook_file.stem.split('_')[1]
            print(f"검증 중: {type_code}")
            results[type_code] = validate_type_codebooks(type_code)

    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # 요약 출력
    total = sum(len(v) for v in results.values())
    passed = sum(1 for v in results.values() for r in v if r.get('passed', False))
    print(f"\n검증 완료: {passed}/{total} 통과")

if __name__ == "__main__":
    main()
```

### 5.3 검증 기준

| 심각도 | 조치 |
|--------|------|
| error | 코드북 재생성 필수 |
| warning | 사람 검토 후 결정 |
| info | 로그만, 무시 가능 |

**자동 재생성 트리거:**
- 미해석 QID > 10%
- 빈도 역전 > 5건
- 누락 필수값 존재

---

## 6. 실행 계획

### 6.1 Phase 1: 인프라 구축 (1일)

1. `batch_codebook.py` 구현
2. `codebook_validator.py` 구현
3. JSON 표준 포맷 적용하여 `stage4_codebook.py` 수정

### 6.2 Phase 2: 파일럿 실행 (1일)

5개 주요 타입으로 전체 파이프라인 검증:
- 0x00 인간 (12.5M, 복잡)
- 0x0C 항성 (3.6M, 천체 특수)
- 0x1C 정주지 (580K, 지리)
- 0x2C 조직 (530K, 조직)
- 0x33 영화 (335K, 창작물)

### 6.3 Phase 3: 전체 실행 (2일)

1. 카테고리별 순차 실행
2. 병렬도 4로 실행
3. 실패 타입 수동 분석 및 수정

### 6.4 Phase 4: 검증 및 마무리 (1일)

1. LLM 검증 전체 실행
2. 검토 필요 항목 수동 확인
3. 최종 보고서 작성

---

## 7. 예상 소요 시간

| 타입 규모 | 예상 시간/타입 | 타입 수 | 총 시간 |
|-----------|---------------|---------|---------|
| 10M+ | 15분 | 1 | 15분 |
| 1M-10M | 10분 | 8 | 80분 |
| 100K-1M | 5분 | 25 | 125분 |
| 10K-100K | 3분 | 15 | 45분 |
| <10K | 2분 | 10 | 20분 |

**총 예상: 약 4.5시간 (병렬 4 기준 1.5시간)**

---

## 8. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| DB 타임아웃 | 스테이지 실패 | LIMIT 조절, 재시도 로직 |
| 메모리 부족 | 프로세스 kill | 청크 처리, 스트리밍 |
| LLM API 제한 | 검증 지연 | 배치 지연, 로컬 캐싱 |
| 코드북 충돌 | 품질 저하 | Stage 5에서 탐지, 수동 조정 |

---

## 9. 산출물 목록

1. `scripts/run_all_stages.py` - 오케스트레이터
2. `scripts/batch_codebook.py` - 배치 코드북 생성
3. `scripts/codebook_validator.py` - LLM 검증
4. `templates/codebook_verify_prompt.txt` - 검증 프롬프트
5. `output/codebooks/*.json` - 59개 타입 코드북
6. `output/quantization/*.json` - 공유 양자화 규칙
7. `output/codebooks/index.json` - 통합 인덱스
8. `output/validation_results.json` - 검증 결과
9. `output/reports/codebook_automation_report.md` - 최종 보고서

---

## 10. 다음 단계

이 계획 승인 후:
1. Phase 1 스크립트 구현 시작
2. 파일럿 5개 타입으로 테스트
3. 결과에 따라 조정 후 전체 실행
