# UID (Unified Identifier) 명세서

**버전:** v0.1  
**작성일:** 2026-01-26  
**목적:** GEUL 시스템의 통합 식별자 구조 정의

---

## 1. 개요

### 1.1 정의

**UID (Unified Identifier)**는 GEUL 시스템에서 모든 개체를 고유하게 식별하는 64비트 식별자이다.

**핵심 질문:** "이것이 무엇인가?" (What is this?)

### 1.2 설계 원칙

| 원칙 | 설명 |
|------|------|
| **통합성** | 다양한 외부 ID 체계를 하나로 통합 |
| **확장성** | Standard + Extension 이중 구조 |
| **효율성** | 고빈도 타입에 비트 절약 |
| **즉시 분기** | 첫 비트로 Lane 판별 |

### 1.3 ID 계층에서의 위치

```
UID  → "이것이 무엇인가?" (What)
  ↓
SIDX → "어떤 상태인가?" (State)
  ↓
PIDX → "어떤 패턴인가?" (Pattern)
```

UID는 최상위 식별자로, 개체의 **정체성**을 정의한다.

---

## 2. 비트 레이아웃

### 2.1 최상위 구조

```
64-bit UID:
┌─────────┬─────────────────────────────────────────────────┐
│ Lane    │ Payload                                         │
│ (1 bit) │ (63 bits)                                       │
└─────────┴─────────────────────────────────────────────────┘
```

| bit 1 | Lane |
|-------|------|
| 0 | **Standard** (GEUL 공식) |
| 1 | **Extension** (확장) |

### 2.2 Standard Lane (bit 1 = 0)

**99%의 일반적 사용 케이스.**

```
┌───┬───────┬──────────────────────────────────────────────┐
│ 0 │ Type  │ Payload                                      │
│   │ (2b)  │ (61 bits)                                    │
└───┴───────┴──────────────────────────────────────────────┘
 b1   b2-3    b4-64
```

**타입 코드 (bit 2-3):**

| 코드 | 타입 | 출처 | 설명 |
|------|------|------|------|
| 00 | **Q-ID** | 위키데이터 | Item (개체) |
| 01 | **P-ID** | 위키데이터 | Property (속성) |
| 10 | **Synset** | 워드넷 | 동의어 집합 |
| 11 | **G-ID** | GEUL | 내부 생성 ID |

**총 헤더: 3비트** (Lane 1 + Type 2)

### 2.3 Extension Lane (bit 1 = 1)

**외부 온톨로지, 도메인 특화, 사용자 정의.**

```
┌───┬─────────┬────────────────────────────────────────────┐
│ 1 │ Type    │ Payload                                    │
│   │ (3b)    │ (60 bits)                                  │
└───┴─────────┴────────────────────────────────────────────┘
 b1   b2-4      b5-64
```

**타입 코드 (bit 2-4):**

| 코드 | 타입 | 용도 |
|------|------|------|
| 000 | **Schema.org** | 웹 표준 스키마 |
| 001 | **SNOMED-CT** | 의료 온톨로지 |
| 010 | **ICD** | 질병 분류 |
| 011 | **Legal** | 법률 온톨로지 |
| 100 | **Financial** | 금융 (FIBO 등) |
| 101 | **Custom** | 사용자 정의 |
| 110 | **Temp** | 임시 ID |
| 111 | **Reserved** | 향후 확장 |

**총 헤더: 4비트** (Lane 1 + Type 3)

---

## 3. Standard Lane 상세

### 3.1 Q-ID (위키데이터 Item)

**고유 개체 식별.**

```
┌───┬────┬────────────────┬─────────────────────────────────┐
│ 0 │ 00 │ Entity Type    │ Q-ID Number                     │
│   │    │ (4 bits)       │ (57 bits)                       │
└───┴────┴────────────────┴─────────────────────────────────┘
 b1  b2-3  b4-7             b8-64
```

**Entity Type (bit 4-7):**

| 코드 | 분류 | 예시 |
|------|------|------|
| 0x0 | Human | 아인슈타인, 손흥민 |
| 0x1 | Organization | Apple, UN |
| 0x2 | Location | 서울, 에펠탑 |
| 0x3 | Event | 월드컵, 지진 |
| 0x4 | Work | 해리포터, 모나리자 |
| 0x5 | Product | iPhone, 코카콜라 |
| 0x6 | Species | 호랑이, 장미 |
| 0x7 | Substance | 물, 철 |
| 0x8 | Concept | 민주주의, 사랑 |
| 0x9 | Quantity | 3개, 50% |
| 0xA | Time | 2024년 |
| 0xB | Unit | 킬로그램, 달러 |
| 0xC | Attribute | 빨강, 크다 |
| 0xD | Activity | 축구, 요리 |
| 0xE | State | 행복, 고장 |
| 0xF | Reserved | 확장용 |

**Q-ID Number (bit 8-64):**
- 57비트 = 최대 1.4 × 10^17 개체
- 위키데이터 현재 ~1.1억 (Q100000000 수준)
- 충분한 여유

**예시:**
```
Q312 (Apple Inc.)
→ Lane: 0, Type: 00, EntityType: 0x1 (Org), QID: 312
→ 0b0_00_0001_...000000100111000
```

### 3.2 P-ID (위키데이터 Property)

**관계/속성 식별.**

```
┌───┬────┬────────────────┬─────────────────────────────────┐
│ 0 │ 01 │ Property Type  │ P-ID Number                     │
│   │    │ (4 bits)       │ (57 bits)                       │
└───┴────┴────────────────┴─────────────────────────────────┘
 b1  b2-3  b4-7             b8-64
```

**Property Type (bit 4-7):**

| 코드 | 분류 | 예시 |
|------|------|------|
| 0x0 | Identity | P31 (instance of) |
| 0x1 | Hierarchy | P279 (subclass of) |
| 0x2 | Temporal | P580 (start time) |
| 0x3 | Spatial | P625 (coordinate) |
| 0x4 | Relation | P127 (owned by) |
| 0x5 | Quantity | P1082 (population) |
| 0x6 | Reference | P854 (reference URL) |
| 0x7-F | Reserved | 확장용 |

**예시:**
```
P127 (owned by)
→ Lane: 0, Type: 01, PropType: 0x4 (Relation), PID: 127
```

### 3.3 Synset (워드넷)

**범주/개념 식별.**

```
┌───┬────┬──────┬─────────────┬──────────────────────────────┐
│ 0 │ 10 │ POS  │ Lex Domain  │ Synset Offset                │
│   │    │ (3b) │ (5 bits)    │ (53 bits)                    │
└───┴────┴──────┴─────────────┴──────────────────────────────┘
 b1  b2-3  b4-6   b7-11         b12-64
```

**POS (Part of Speech, bit 4-6):**

| 코드 | 품사 |
|------|------|
| 000 | Noun |
| 001 | Verb |
| 010 | Adjective |
| 011 | Adverb |
| 100 | Adjective Satellite |
| 101-111 | Reserved |

**Lex Domain (bit 7-11):**
- 워드넷 어휘 도메인 (45개)
- 5비트로 32개 커버 (주요 도메인)

**예시:**
```
eat.v.01
→ Lane: 0, Type: 10, POS: 001 (Verb), Domain: ..., Offset: ...
```

### 3.4 G-ID (GEUL 내부)

**GEUL 시스템 자체 생성 ID.**

```
┌───┬────┬────────────────┬─────────────────────────────────┐
│ 0 │ 11 │ G-Type         │ Sequence                        │
│   │    │ (4 bits)       │ (57 bits)                       │
└───┴────┴────────────────┴─────────────────────────────────┘
 b1  b2-3  b4-7             b8-64
```

**G-Type (bit 4-7):**

| 코드 | 용도 | 설명 |
|------|------|------|
| 0x0 | Context | WMS Context 노드 |
| 0x1 | Claim | WMS Claim 노드 |
| 0x2 | Rule | RuleDB 룰 ID |
| 0x3 | Pattern | PIDX 패턴 |
| 0x4 | Session | 세션 ID |
| 0x5 | User | 사용자 ID |
| 0x6 | Document | 문서 ID |
| 0x7 | Annotation | 주석 ID |
| 0x8-F | Reserved | 확장용 |

**Sequence (bit 8-64):**
- Snowflake 스타일 또는 UUID 기반
- 시간 + 머신 + 시퀀스 조합 권장

---

## 4. Extension Lane 상세

### 4.1 Schema.org (코드: 000)

```
┌───┬─────┬────────────────────────────────────────────────┐
│ 1 │ 000 │ Schema.org Type ID                             │
│   │     │ (60 bits)                                      │
└───┴─────┴────────────────────────────────────────────────┘
```

**용도:** 웹 구조화 데이터 호환

**예시:**
- schema:Person
- schema:Organization
- schema:Event

### 4.2 SNOMED-CT (코드: 001)

```
┌───┬─────┬────────────────────────────────────────────────┐
│ 1 │ 001 │ SNOMED Concept ID                              │
│   │     │ (60 bits)                                      │
└───┴─────┴────────────────────────────────────────────────┘
```

**용도:** 의료 도메인 정밀 표현

**예시:**
- 73211009 (Diabetes mellitus)
- 84114007 (Heart failure)

### 4.3 Custom (코드: 101)

```
┌───┬─────┬──────────────┬─────────────────────────────────┐
│ 1 │ 101 │ Namespace    │ Local ID                        │
│   │     │ (16 bits)    │ (44 bits)                       │
└───┴─────┴──────────────┴─────────────────────────────────┘
```

**Namespace:** 사용자/조직별 네임스페이스 할당
**Local ID:** 해당 네임스페이스 내 고유 ID

---

## 5. 연산

### 5.1 Lane 판별

```python
def get_lane(uid: int) -> str:
    """첫 비트로 Lane 판별"""
    if uid >> 63 == 0:
        return "Standard"
    else:
        return "Extension"
```

### 5.2 Type 추출

```python
def get_type(uid: int) -> tuple:
    """Lane과 Type 추출"""
    lane = uid >> 63
    
    if lane == 0:  # Standard
        type_code = (uid >> 61) & 0b11  # bit 2-3
        type_names = ["Q-ID", "P-ID", "Synset", "G-ID"]
        return ("Standard", type_names[type_code])
    else:  # Extension
        type_code = (uid >> 60) & 0b111  # bit 2-4
        type_names = ["Schema.org", "SNOMED", "ICD", "Legal", 
                      "Financial", "Custom", "Temp", "Reserved"]
        return ("Extension", type_names[type_code])
```

### 5.3 Q-ID 생성

```python
def make_qid(q_number: int, entity_type: int) -> int:
    """Q-ID로 UID 생성"""
    uid = 0  # Lane = 0
    uid |= (0b00 << 61)  # Type = Q-ID
    uid |= (entity_type << 57)  # Entity Type (4 bits)
    uid |= q_number  # Q-ID number
    return uid

# 예: Apple Inc. (Q312, Organization)
apple_uid = make_qid(312, 0x1)
```

### 5.4 Synset 생성

```python
def make_synset(pos: int, offset: int, domain: int = 0) -> int:
    """Synset으로 UID 생성"""
    uid = 0  # Lane = 0
    uid |= (0b10 << 61)  # Type = Synset
    uid |= (pos << 58)  # POS (3 bits)
    uid |= (domain << 53)  # Domain (5 bits)
    uid |= offset  # Synset offset
    return uid

# 예: eat.v.01
eat_uid = make_synset(pos=0b001, offset=1, domain=0)
```

---

## 6. SIDX와의 관계

### 6.1 UID → SIDX

UID는 **정체성**, SIDX는 **상태**를 포함한다.

```
UID (64-bit):  "이것은 Apple Inc.다"
     ↓
SIDX (64-bit): "2024년 1월 기준 Apple Inc.의 상태"
               (시가총액, CEO, 직원수 등 반영)
```

### 6.2 인코딩 관계

```
SIDX 구조:
┌─────────────────┬────────────────────────────────────────┐
│ UID 핵심부      │ State Qualifiers                       │
│ (상위 ~40 bits) │ (하위 ~24 bits)                        │
└─────────────────┴────────────────────────────────────────┘
```

SIDX의 상위 비트는 UID에서 파생되며, 하위 비트에 상태 정보 추가.

---

## 7. TID (Temporary ID)와의 관계

### 7.1 정의

**TID**는 스트림 내 임시 참조용 16비트 ID.

```
TID (16-bit):
┌──────────┬────────────────────────┐
│ Type     │ Sequence               │
│ (4 bits) │ (12 bits)              │
└──────────┴────────────────────────┘
```

### 7.2 UID 참조

TID는 스트림 내에서 UID를 **축약 참조**:

```
스트림 헤더:
  TID 0x001 → UID (Apple Inc.)
  TID 0x002 → UID (iPhone)
  
스트림 본문:
  [PARTICIPANT: verb → TID:0x001, role=AGT]
```

---

## 8. 설계 근거

### 8.1 왜 Lane 분리인가?

| 이유 | 설명 |
|------|------|
| **빈도 최적화** | 99%는 Standard, 3비트로 처리 |
| **확장 격리** | Extension은 Standard에 영향 없음 |
| **즉시 분기** | 첫 비트만 보고 파싱 경로 결정 |

### 8.2 왜 2비트 Type (Standard)인가?

| 타입 | 필요성 |
|------|--------|
| Q-ID | 고유 개체 (필수) |
| P-ID | 관계/속성 (필수) |
| Synset | 범주/개념 (필수) |
| G-ID | 내부 생성 (필수) |

**4개면 충분.** 더 있으면 Extension으로.

### 8.3 왜 3비트 Type (Extension)인가?

8개 슬롯이면:
- 주요 외부 온톨로지 (3-4개)
- 사용자 정의 (1개)
- 임시 (1개)
- 예약 (1-2개)

**충분한 확장성.**

---

## 9. 예시

### 9.1 Standard Lane 예시

| 개체 | Lane | Type | 세부 | UID (이진) |
|------|------|------|------|------------|
| Apple Inc. (Q312) | 0 | 00 | Org(0x1), 312 | `0_00_0001_...` |
| owned by (P127) | 0 | 01 | Rel(0x4), 127 | `0_01_0100_...` |
| eat.v.01 | 0 | 10 | Verb, offset | `0_10_001_...` |
| Context_001 | 0 | 11 | Context(0x0), seq | `0_11_0000_...` |

### 9.2 Extension Lane 예시

| 개체 | Lane | Type | 세부 | UID (이진) |
|------|------|------|------|------------|
| schema:Person | 1 | 000 | Schema.org ID | `1_000_...` |
| SNOMED:73211009 | 1 | 001 | Diabetes | `1_001_...` |
| custom:mycompany:001 | 1 | 101 | NS + Local | `1_101_...` |

---

## 10. 마이그레이션

### 10.1 기존 Q-ID → UID

```python
def qid_to_uid(qid_string: str) -> int:
    """Q312 → UID"""
    q_number = int(qid_string[1:])  # "Q312" → 312
    entity_type = lookup_entity_type(q_number)  # 위키데이터 조회
    return make_qid(q_number, entity_type)
```

### 10.2 기존 Synset → UID

```python
def synset_to_uid(synset_string: str) -> int:
    """eat.v.01 → UID"""
    lemma, pos, sense = parse_synset(synset_string)
    offset = wordnet.synset(synset_string).offset()
    pos_code = {"n": 0, "v": 1, "a": 2, "r": 3}[pos]
    return make_synset(pos_code, offset)
```

---

## 부록 A: 비트 요약

### Standard Lane (bit 1 = 0)

```
bit 1:     0 (Standard)
bit 2-3:   Type (4개)
bit 4-7:   SubType (16개)
bit 8-64:  Payload (57 bits)

총 헤더: 3비트 (Lane + Type)
SubType 포함: 7비트
```

### Extension Lane (bit 1 = 1)

```
bit 1:     1 (Extension)
bit 2-4:   Type (8개)
bit 5-64:  Payload (60 bits)

총 헤더: 4비트 (Lane + Type)
```

---

## 부록 B: 참고 문서

- `SIDX.md` - 상태 포함 식별자
- `PIDX.md` - 패턴 인덱스
- `ID계층구조.md` - UID/SIDX/PIDX 관계
- `GEUL_비트명세.md` - 전체 비트 레이아웃
- `개체_상위_분류.md` - Entity Type 16개

---

**문서 종료**

**버전:** v0.1  
**작성일:** 2026-01-26