-- 위키데이터 대량 로드용 테이블 생성 (인덱스 없음)
-- PRIMARY KEY와 FOREIGN KEY 제약도 제거하여 최대 성능

-- 1. 엔티티 기본 테이블
CREATE TABLE entities (
    id TEXT NOT NULL,  -- Q123, P456
    type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 라벨 테이블
CREATE TABLE entity_labels (
    entity_id TEXT NOT NULL,
    language TEXT NOT NULL,
    label TEXT NOT NULL
);

-- 3. 설명 테이블
CREATE TABLE entity_descriptions (
    entity_id TEXT NOT NULL,
    language TEXT NOT NULL,
    description TEXT
);

-- 4. 별칭 테이블
CREATE TABLE entity_aliases (
    entity_id TEXT NOT NULL,
    language TEXT NOT NULL,
    alias TEXT NOT NULL,
    alias_order INT DEFAULT 0
);

-- 5. 트리플 테이블
CREATE TABLE triples (
    id BIGSERIAL,  -- 시퀀스는 유지 (자동 증가)
    subject TEXT NOT NULL,
    property TEXT NOT NULL,
    object_value TEXT,
    object_type TEXT,
    rank TEXT DEFAULT 'normal'
);

-- 6. 한정자 테이블
CREATE TABLE triple_qualifiers (
    triple_id BIGINT NOT NULL,
    property TEXT NOT NULL,
    value TEXT,
    datatype TEXT
);

-- 7. 참조 테이블
CREATE TABLE triple_references (
    triple_id BIGINT NOT NULL,
    property TEXT NOT NULL,
    value TEXT,
    source_type TEXT
);

-- 8. 계층 구조 전용 테이블 (P31/P279)
CREATE TABLE hierarchy (
    child TEXT NOT NULL,
    parent TEXT NOT NULL,
    property TEXT NOT NULL
);

-- 9. 속성 메타데이터 테이블
CREATE TABLE properties_meta (
    property_id TEXT NOT NULL,
    datatype TEXT,
    label_en TEXT,
    description_en TEXT,
    usage_count BIGINT DEFAULT 0
);

-- 10. 통계 테이블
CREATE TABLE stats (
    stat_name TEXT NOT NULL,
    stat_value BIGINT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);





-- 1. 엔티티 기본 테이블
ALTER TABLE entities 
ADD CONSTRAINT pk_entities PRIMARY KEY (id);

-- 2. 라벨 테이블
ALTER TABLE entity_labels 
ADD CONSTRAINT pk_entity_labels PRIMARY KEY (entity_id, language);

-- 3. 설명 테이블
ALTER TABLE entity_descriptions 
ADD CONSTRAINT pk_entity_descriptions PRIMARY KEY (entity_id, language);

-- 5. 트리플 테이블 (이미 id가 BIGSERIAL이므로)
ALTER TABLE triples 
ADD CONSTRAINT pk_triples PRIMARY KEY (id);

-- 6. 한정자 테이블 (복합키 - 중복 가능하므로 모든 컬럼 포함)
-- 한정자는 중복이 있을 수 있어서 PRIMARY KEY 대신 인덱스만 추가하는 것이 나을 수 있음
-- 필요하면 surrogate key 추가 고려

-- 7. 참조 테이블 (복합키 - 중복 가능하므로 모든 컬럼 포함)
-- 참조도 중복이 있을 수 있어서 PRIMARY KEY 대신 인덱스만 추가하는 것이 나을 수 있음

-- 8. 계층 구조 전용 테이블
ALTER TABLE hierarchy 
ADD CONSTRAINT pk_hierarchy PRIMARY KEY (child, parent, property);

-- 9. 속성 메타데이터 테이블
ALTER TABLE properties_meta 
ADD CONSTRAINT pk_properties_meta PRIMARY KEY (property_id);

-- 10. 통계 테이블
ALTER TABLE stats 
ADD CONSTRAINT pk_stats PRIMARY KEY (stat_name);


-- ### 1. entities 테이블 인덱스 ###
-- 'type' 컬럼을 기준으로 item과 property를 빠르게 필터링하기 위한 필수 인덱스
-- (사용자께서 겪으신 풀스캔 문제를 직접적으로 해결합니다)
CREATE INDEX idx_entities_type ON entities(type);

-- ### 2. 라벨, 설명, 별칭 테이블 인덱스 ###
-- entity_id를 기준으로 특정 엔티티의 라벨, 설명, 별칭을 빠르게 조회하기 위한 인덱스
-- (PK가 이미 있지만, 단일 컬럼 인덱스가 더 효율적일 수 있습니다)
CREATE INDEX idx_entity_labels_entity_id ON entity_labels(entity_id);
CREATE INDEX idx_entity_descriptions_entity_id ON entity_descriptions(entity_id);
CREATE INDEX idx_entity_aliases_entity_id ON entity_aliases(entity_id);

-- 텍스트(라벨, 별칭)를 기준으로 엔티티를 검색하는 경우를 위한 인덱스 (예: '소크라테스'라는 라벨을 가진 엔티티 찾기)
CREATE INDEX idx_entity_labels_label ON entity_labels(label);


-- ### 5. triples 테이블 인덱스 (가장 중요) ###
-- 특정 주체(subject)의 모든 관계를 빠르게 조회하기 위한 인덱스 (가장 흔한 사용 사례)
CREATE INDEX idx_triples_subject ON triples(subject);

-- 특정 속성(property)을 가진 모든 트리플을 빠르게 조회하기 위한 인덱스 (예: '직업(P106)'을 가진 모든 트리플 찾기)
CREATE INDEX idx_triples_property ON triples(property);

-- 특정 객체(object)와 관계된 모든 주체를 빠르게 조회하기 위한 인덱스 (역방향 탐색)
CREATE INDEX idx_triples_object_value ON triples(object_value);

-- 복합 인덱스: 특정 주체가 특정 속성을 가지는지 빠르게 확인할 때 매우 유용
CREATE INDEX idx_triples_subject_property ON triples(subject, property);


-- ### 6. 한정자(Qualifiers) 및 7. 참조(References) 테이블 인덱스 ###
-- triple_id를 기준으로 특정 트리플에 속한 한정자나 참조를 빠르게 조회하기 위한 인덱스
CREATE INDEX idx_triple_qualifiers_triple_id ON triple_qualifiers(triple_id);
CREATE INDEX idx_triple_references_triple_id ON triple_references(triple_id);


-- ### 8. hierarchy 테이블 인덱스 ###
-- 특정 자식(child)의 모든 부모를 빠르게 조회하기 위한 인덱스
CREATE INDEX idx_hierarchy_child ON hierarchy(child);

-- 특정 부모(parent)의 모든 자식을 빠르게 조회하기 위한 인덱스
CREATE INDEX idx_hierarchy_parent ON hierarchy(parent);


ALTER TABLE entity_aliases
ADD CONSTRAINT pk_entity_aliases PRIMARY KEY (entity_id, language, alias_order);

-- alias를 포함한 전체 조합의 고유성을 보장하기 위해, alias를 해싱한 UNIQUE 인덱스를 생성합니다.
CREATE UNIQUE INDEX idx_entity_aliases_unique_combination_hash
ON entity_aliases (entity_id, language, md5(alias), alias_order);


-- 2. idx_entity_aliases_alias 인덱스 재생성
-- alias 텍스트 값으로 엔티티를 검색하기 위한 해시 인덱스를 생성합니다.
CREATE INDEX idx_entity_aliases_alias_hash ON entity_aliases (md5(alias));

CREATE INDEX idx_entity_labels_label_lower ON entity_labels (LOWER(label));