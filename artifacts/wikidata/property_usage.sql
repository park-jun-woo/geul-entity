-- 위키데이터 속성별 사용량 통계를 저장할 테이블 생성
CREATE TABLE property_usage_stats (
    property_id TEXT NOT NULL PRIMARY KEY, -- 속성 ID (예: P31, P279)
    usage_count BIGINT NOT NULL,           -- 트리플 테이블에서의 총 사용 횟수
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_property_id FOREIGN KEY (property_id) REFERENCES properties_meta(property_id)
);

-- 빠른 조회를 위한 usage_count 내림차순 인덱스 생성
CREATE INDEX idx_property_usage_stats_count_desc ON property_usage_stats(usage_count DESC);

COMMENT ON TABLE property_usage_stats IS '의미정렬 식별자 정의를 위해 각 위키데이터 속성이 얼마나 사용되었는지 집계한 통계 테이블';
COMMENT ON COLUMN property_usage_stats.property_id IS '위키데이터 속성 ID (P-number)';
COMMENT ON COLUMN property_usage_stats.usage_count IS 'triples 테이블에 해당 속성이 등장한 총 횟수';

-- 각 속성(Property)별로 어떤 목적어(Object)가 많이 사용되었는지 통계를 저장할 테이블
CREATE TABLE property_object_stats (
    property_id TEXT NOT NULL,                      -- 속성 ID (예: P31)
    object_value TEXT NOT NULL,                     -- 목적어로 사용된 개체 또는 속성 ID (예: Q5, P106)
    usage_count BIGINT NOT NULL,                    -- 해당 (속성, 목적어) 쌍이 사용된 횟수
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_property_object_stats PRIMARY KEY (property_id, object_value)
);

-- 특정 속성에 대해 가장 많이 사용된 목적어를 빠르게 조회하기 위한 복합 인덱스
CREATE INDEX idx_prop_obj_stats_count_desc ON property_object_stats(property_id, usage_count DESC);

COMMENT ON TABLE property_object_stats IS '각 위키데이터 속성의 목적어로 어떤 개체/속성이 얼마나 자주 사용되었는지 집계한 통계 테이블';
COMMENT ON COLUMN property_object_stats.property_id IS '기준이 되는 위키데이터 속성 ID (P-number)';
COMMENT ON COLUMN property_object_stats.object_value IS 'property_id의 목적어로 사용된 위키데이터 개체(Q-number) 또는 속성(P-number)';
COMMENT ON COLUMN property_object_stats.usage_count IS 'triples 테이블에 해당 (속성, 목적어) 쌍이 등장한 총 횟수';


-- triples 테이블에 존재하지만 properties_meta 테이블에는 없는
-- 모든 속성 ID를 찾아 properties_meta에 먼저 삽입합니다.
INSERT INTO properties_meta (property_id)
SELECT DISTINCT property
FROM triples
WHERE property NOT IN (SELECT property_id FROM properties_meta)
ON CONFLICT (property_id) DO NOTHING;


-- triples 테이블에서 속성별 사용량을 집계하여 property_usage_stats 테이블에 입력
INSERT INTO property_usage_stats (property_id, usage_count)
SELECT
    property,
    COUNT(*) AS usage_count
FROM
    triples
GROUP BY
    property
ORDER BY
    usage_count DESC;

-- 통계 테이블 업데이트 시간 기록 (선택적)
UPDATE stats 
SET stat_value = (SELECT COUNT(*) FROM property_usage_stats), updated_at = CURRENT_TIMESTAMP 
WHERE stat_name = 'total_unique_properties_in_use';


-- triples 테이블에서 (속성, 목적어) 쌍의 사용 빈도를 집계하여 property_object_stats 테이블에 입력
INSERT INTO property_object_stats (property_id, object_value, usage_count)
SELECT
    property,
    object_value,
    COUNT(*) AS usage_count
FROM
    triples
WHERE
    -- 목적어가 위키데이터 개체(Q) 또는 속성(P)인 경우만 집계
    object_value LIKE 'Q%' OR object_value LIKE 'P%'
GROUP BY
    property, object_value
ORDER BY
    -- 성능 향상을 위해 ORDER BY는 필수적이지 않으나, 진행 상황을 확인하고 싶을 때 유용할 수 있습니다.
    -- 대량 데이터 처리 시에는 제거하는 것을 권장합니다.
    property, usage_count DESC;

