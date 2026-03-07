# DB Schema Cache

Generated: 2026-01-31

## Databases

| DB | Connection | Permission |
|---|---|---|
| geuldev | `postgresql://geul_reader:test1224@localhost:5432/geuldev` | READ ONLY |
| geulwork | `postgresql://geul_writer:test1224@localhost:5432/geulwork` | READ/WRITE |

---

## geuldev 테이블 목록 (26개)

### 대용량 테이블 (추정치 기준)

| Table | Estimated Rows | Description |
|-------|---------------:|-------------|
| entity_descriptions | ~3.3B | 엔티티 설명 (언어별) |
| triples | ~1.7B | 위키데이터 트리플 (subject, property, object) |
| entity_labels | ~725M | 엔티티 레이블 (언어별) |
| triple_qualifiers | ~428M | 트리플 한정자 |
| entity_aliases | ~181M | 엔티티 별명 |
| entities | ~117M | 위키데이터 엔티티 (Q-ID) |
| property_object_stats | ~60M | 속성별 object 값 통계 |

### 중형 테이블

| Table | Estimated Rows | Description |
|-------|---------------:|-------------|
| cc_news_sentences | ~12M | CC News 문장 분리 |
| cc_news | ~707K | Common Crawl 뉴스 기사 |
| wordnet_synset_relations | ~276K | synset 간 관계 (hypernym 등) |
| wordnet_multilingual | ~207K | 다국어 WordNet |
| wordnet_lemmas | ~207K | 레마 (단어 형태) |
| wordnet_factorized_qualifiers | ~154K | 동사 의미소 한정자 |
| wordnet_synsets | ~118K | WordNet synset |

### 소형 테이블

| Table | Rows | Description |
|-------|-----:|-------------|
| wordnet_factorized_participants | ~43K | 동사 의미소 참여자 |
| wordnet_verb_frames | ~42K | 동사 프레임 |
| wordnet_factorized_sememes | ~33K | 동사 의미소 |
| verb_hypernym_ltree | 13,767 | 동사 상위어 트리 (ltree) |
| properties_meta | 12,872 | 위키데이터 속성 메타 |
| property_usage_stats | 12,315 | 속성 사용 통계 |

### 빈 테이블

| Table | Description |
|-------|-------------|
| hierarchy | 계층 관계 (비어 있음) |
| stats | 통계 정보 (비어 있음) |
| triple_references | 트리플 참조 (비어 있음) |
| wordnet_lemma_relations | 레마 관계 (비어 있음) |
| wordnet_metadata | WordNet 메타 (비어 있음) |
| wordnet_wikidata_mapping | WordNet-Wikidata 매핑 (비어 있음) |

---

## 주요 테이블 스키마

### entities
```sql
id          TEXT PRIMARY KEY  -- Q-ID (예: Q5)
type        TEXT NOT NULL     -- item/property
created_at  TIMESTAMP
```
- Index: `idx_entities_type` (type)

### triples
```sql
id            BIGINT PRIMARY KEY (auto)
subject       TEXT NOT NULL     -- Q-ID
property      TEXT NOT NULL     -- P-ID
object_value  TEXT              -- Q-ID 또는 리터럴
object_type   TEXT              -- wikibase-entityid, string, time 등
rank          TEXT DEFAULT 'normal'
```
- Index: `idx_triples_subject`, `idx_triples_property`, `idx_triples_object_value`, `idx_triples_subject_property`

### entity_labels
```sql
entity_id  TEXT NOT NULL      -- Q-ID
language   TEXT NOT NULL      -- en, ko, ja 등
label      TEXT NOT NULL
PRIMARY KEY (entity_id, language)
```
- Index: `idx_entity_labels_label`, `idx_entity_labels_label_lower`

### entity_descriptions
```sql
entity_id    TEXT NOT NULL
language     TEXT NOT NULL
description  TEXT
PRIMARY KEY (entity_id, language)
```

### entity_aliases
```sql
entity_id    TEXT NOT NULL
language     TEXT NOT NULL
alias        TEXT NOT NULL
alias_order  INTEGER DEFAULT 0
PRIMARY KEY (entity_id, language, alias_order)
```

### properties_meta
```sql
property_id     TEXT PRIMARY KEY  -- P-ID
datatype        TEXT              -- wikibase-item, string, time, quantity 등
label_en        TEXT
description_en  TEXT
usage_count     BIGINT DEFAULT 0
```

### property_usage_stats
```sql
property_id  TEXT PRIMARY KEY
usage_count  BIGINT NOT NULL
updated_at   TIMESTAMP
```
- Index: `idx_property_usage_stats_count_desc`

### property_object_stats
```sql
property_id   TEXT NOT NULL
object_value  TEXT NOT NULL
usage_count   BIGINT NOT NULL
updated_at    TIMESTAMP
PRIMARY KEY (property_id, object_value)
```

### triple_qualifiers
```sql
triple_id  BIGINT NOT NULL  -- FK to triples.id
property   TEXT NOT NULL    -- P-ID
value      TEXT
datatype   TEXT
```
- Index: `idx_triple_qualifiers_triple_id`

### hierarchy
```sql
child     TEXT NOT NULL
parent    TEXT NOT NULL
property  TEXT NOT NULL     -- P279 (subclass of), P31 (instance of) 등
PRIMARY KEY (child, parent, property)
```

---

## WordNet 테이블

### wordnet_synsets
```sql
synset_id   VARCHAR PRIMARY KEY  -- 예: v01234567
pos         CHAR NOT NULL        -- n/v/a/r/s
lexname     VARCHAR              -- verb.motion 등
definition  TEXT
example     TEXT
gloss       TEXT
```

### wordnet_lemmas
```sql
lemma_id      INTEGER PRIMARY KEY (auto)
synset_id     VARCHAR NOT NULL
word          VARCHAR NOT NULL
lemma_key     VARCHAR
sense_number  INTEGER
tag_count     INTEGER DEFAULT 0
```

### wordnet_synset_relations
```sql
from_synset    VARCHAR NOT NULL
to_synset      VARCHAR NOT NULL
relation_type  VARCHAR NOT NULL  -- hypernym, hyponym, etc.
UNIQUE (from_synset, to_synset, relation_type)
```

### verb_hypernym_ltree
```sql
synset_id   VARCHAR PRIMARY KEY
definition  TEXT
tree_path   LTREE NOT NULL      -- 예: 'v00001740.v00109660.v01835496'
depth       INTEGER DEFAULT 0
```
- Index: `idx_verb_ltree_path_gist` (GIST)

### wordnet_verb_frames
```sql
synset_id   VARCHAR NOT NULL
frame_id    INTEGER NOT NULL
frame_text  TEXT
UNIQUE (synset_id, frame_id)
```

### wordnet_factorized_sememes
```sql
sememe_id      INTEGER PRIMARY KEY (auto)
synset_id      VARCHAR NOT NULL
frame_id       INTEGER NOT NULL
verb_type      VARCHAR          -- action, state, process 등
verb_property  VARCHAR
reasoning      TEXT
```

### wordnet_factorized_participants
```sql
participant_id  INTEGER PRIMARY KEY (auto)
sememe_id       INTEGER NOT NULL  -- FK to sememes
semantic_role   VARCHAR           -- Agent, Patient, Theme 등
value_type      VARCHAR
reasoning       TEXT
```

### wordnet_factorized_qualifiers
```sql
synset_id       VARCHAR NOT NULL
frame_id        INTEGER NOT NULL
qualifier_name  ENUM (custom)
value           VARCHAR
reasoning       TEXT
PRIMARY KEY (synset_id, frame_id, qualifier_name)
```

---

## geulwork (작업용 DB)

현재 테이블 없음. 분석 결과 저장용.

---

## 유용한 쿼리 패턴

### 엔티티 정보 조회
```sql
SELECT e.id, l.label, d.description
FROM entities e
LEFT JOIN entity_labels l ON e.id = l.entity_id AND l.language = 'en'
LEFT JOIN entity_descriptions d ON e.id = d.entity_id AND d.language = 'en'
WHERE e.id = 'Q5';
```

### 속성별 사용 빈도 TOP N
```sql
SELECT p.property_id, p.label_en, u.usage_count
FROM property_usage_stats u
JOIN properties_meta p ON u.property_id = p.property_id
ORDER BY u.usage_count DESC
LIMIT 20;
```

### 특정 타입의 엔티티 샘플
```sql
SELECT t.subject, l.label
FROM triples t
JOIN entity_labels l ON t.subject = l.entity_id AND l.language = 'en'
WHERE t.property = 'P31' AND t.object_value = 'Q5'  -- instance of human
LIMIT 10;
```

### 동사 상위어 트리 탐색
```sql
SELECT * FROM verb_hypernym_ltree
WHERE tree_path <@ 'v00001740'  -- 특정 루트 아래 모든 동사
ORDER BY depth;
```
