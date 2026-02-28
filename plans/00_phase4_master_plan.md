# Phase 4: 64개 EntityType 48비트 전체 할당 마스터 계획

**버전**: v1.0
**작성일**: 2026-02-01
**목표**: 5개 파일럿 타입 기반으로 나머지 59개 타입의 48비트 스키마 설계

---

## 1. 현황 분석

### 1.1 완료된 작업

| 항목 | 상태 | 내용 |
|------|------|------|
| EntityType 64개 정의 | 완료 | `entity_types_64.json` |
| 파일럿 5개 타입 스키마 | 완료 | Human, Star, Settlement, Organization, Film |
| 양자화 규칙 | 완료 | `quantization_rules.json` v0.2 |
| 파이프라인 정의 | 완료 | Stage 1-5 정의됨 |

### 1.2 파일럿 스키마 패턴 분석

**공통 필드 유형 (5개 파일럿에서 추출)**:

| 필드 유형 | 비트 | 용도 | 사용 타입 |
|----------|------|------|----------|
| country | 8 | 국가/국적 | Human, Settlement, Organization, Film |
| era | 4 | 시대 | Human, Organization |
| year | 7 | 연도 (1900+) | Film |
| lat_zone | 4 | 위도 구역 | Settlement, Star |
| lon_zone | 4 | 경도 구역 | Settlement, Star |
| genre | 6 | 장르 | Film |
| language | 6-8 | 언어 | Human, Film |
| notability | 3 | 저명도 | Human |
| subclass | 4-8 | 하위 타입 | 공통 |

### 1.3 카테고리별 개체 수 분포

| 범위 | 카테고리 | 타입 수 | 총 개체수 | 최대 타입 |
|------|----------|---------|----------|----------|
| 0x00-0x07 | 생물/인물 | 8 | 19.6M | Human (12.5M) |
| 0x08-0x0B | 화학/물질 | 4 | 2.4M | Chemical (1.3M) |
| 0x0C-0x13 | 천체 | 8 | 6.2M | Star (3.6M) |
| 0x14-0x1B | 지형/자연 | 8 | 1.9M | Mountain (518K) |
| 0x1C-0x23 | 장소/행정 | 8 | 2.2M | Street (710K) |
| 0x24-0x2B | 건축물 | 8 | 1.5M | Building (292K) |
| 0x2C-0x2F | 조직 | 4 | 0.9M | Organization (531K) |
| 0x30-0x3B | 창작물 | 12 | 48.1M | Document (45M) |
| 0x3C-0x3F | 이벤트/예약 | 4 | 0.2M | SportsSeason (183K) |

---

## 2. 카테고리별 공통 필드 패턴

### 2.1 생물/인물 (0x00-0x07)

**공통 템플릿** (24비트 핵심):
```
[0:7]   taxonomy     8비트   분류 계통 (생물) / 소분류 (인물)
[8:11]  era          4비트   시대
[12:19] region       8비트   지역/서식지
[20:23] status       4비트   상태/생존여부
```

| 타입 | 특화 필드 (24비트) |
|------|-------------------|
| 0x00 Human | occupation(6), gender(2), notability(3), language(6), birth_region(6), activity_field(4) - **완료** |
| 0x01 Taxon | kingdom(3), phylum(4), conservation(3), habitat(4), body_size(3), lifespan(3), diet(2), locomotion(2) |
| 0x02 Gene | organism(6), chromosome(5), gene_type(4), function(5), expression(4) |
| 0x03 Protein | organism(6), structure(4), function(5), location(4), interaction(5) |
| 0x04 CellLine | organism(6), tissue(5), disease(5), immortalized(2), culture_type(3), contamination(3) |
| 0x05 FamilyName | origin_lang(6), origin_country(8), meaning_type(4), frequency(3), script(3) |
| 0x06 GivenName | origin_lang(6), gender_assoc(2), popularity(4), religious(3), length(2), origin_era(4), script(3) |
| 0x07 FictionalChar | medium(4), role(3), species(4), powers(4), alignment(3), gender(2), notability(4) |

### 2.2 화학/물질 (0x08-0x0B)

**공통 템플릿** (20비트 핵심):
```
[0:7]   molecular_type  8비트   분자 유형/분류
[8:15]  properties      8비트   물리화학적 특성
[16:19] safety          4비트   안전/규제 등급
```

| 타입 | 특화 필드 (28비트) |
|------|-------------------|
| 0x08 Chemical | phase(2), toxicity(3), flammability(3), reactivity(3), mol_weight(5), solubility(4), boiling(4), melting(4) |
| 0x09 Compound | bond_type(3), organic(1), functional_group(5), stereochem(3), polymer(2), charge(3), mol_weight(5), ring_count(3), heteroatom(3) |
| 0x0A Mineral | crystal_system(3), hardness(4), luster(3), color(4), streak(3), cleavage(3), specific_gravity(4), transparency(2), magnetism(2) |
| 0x0B Drug | drug_class(6), route(4), schedule(3), indication(6), side_effect(4), interaction(3), patent_status(2) |

### 2.3 천체 (0x0C-0x13)

**공통 템플릿** (24비트 핵심):
```
[0:6]   constellation   7비트   별자리/위치
[7:10]  ra_zone         4비트   적경
[11:14] dec_zone        4비트   적위
[15:18] magnitude       4비트   등급
[19:23] distance        5비트   거리 구간
```

| 타입 | 특화 필드 (24비트) |
|------|-------------------|
| 0x0C Star | spectral(4), luminosity(3), flags(6), radial_vel(5), redshift(5), pm_class(2) - **완료** |
| 0x0D Galaxy | morphology(4), size(4), luminosity(4), activity(3), group(4), color(3), bar(2) |
| 0x0E Asteroid | orbit_type(4), family(5), composition(4), rotation(4), albedo(4), size(3) |
| 0x0F Quasar | redshift(5), luminosity(4), radio(3), variability(3), host_galaxy(4), jet(3), absorption(2) |
| 0x10 Planet | planet_type(4), mass(4), atmosphere(4), rings(2), moons(4), habitability(3), orbit(3) |
| 0x11 Nebula | nebula_type(4), size(4), brightness(4), emission(4), age(3), associated_star(5) |
| 0x12 StarCluster | cluster_type(3), age(4), star_count(4), metallicity(3), tidal_radius(4), core_density(3), color(3) |
| 0x13 Moon | parent_planet(4), size(4), orbit(4), surface(4), atmosphere(2), tidal(3), composition(3) |

### 2.4 지형/자연 (0x14-0x1B)

**공통 템플릿** (24비트 핵심):
```
[0:7]   country         8비트   소속 국가
[8:11]  lat_zone        4비트   위도 구역
[12:15] lon_zone        4비트   경도 구역
[16:19] admin           4비트   행정구역 레벨
[20:23] climate         4비트   기후대
```

| 타입 | 특화 필드 (24비트) |
|------|-------------------|
| 0x14 Mountain | elevation(5), prominence(4), range(5), volcano(2), climbing(3), snow(2), isolation(3) |
| 0x15 Hill | elevation(4), type(3), prominence(3), vegetation(4), protected(2), use(4), isolation(4) |
| 0x16 River | length(4), basin(5), discharge(4), source_elev(4), mouth_type(3), navigable(2), dams(2) |
| 0x17 Lake | area(4), depth(4), type(3), salinity(2), elevation(4), outflow(2), origin(3), fish(2) |
| 0x18 Stream | order(3), length(3), gradient(3), type(3), permanence(2), watershed(5), substrate(3), fish(2) |
| 0x19 Island | area(4), type(3), population(4), elevation(4), sovereignty(3), climate(3), vegetation(3) |
| 0x1A Bay | area(4), depth(4), type(3), enclosed(2), tidal(3), port(2), protected(2), use(4) |
| 0x1B Cave | length(4), depth(4), type(3), formation(3), protected(2), tourist(2), difficulty(3), fauna(3) |

### 2.5 장소/행정 (0x1C-0x23)

**공통 템플릿** (28비트 핵심):
```
[0:7]   country         8비트   국가
[8:11]  admin_level     4비트   행정 레벨
[12:19] admin_code      8비트   행정구역 코드
[20:23] lat_zone        4비트   위도
[24:27] lon_zone        4비트   경도
```

| 타입 | 특화 필드 (20비트) |
|------|-------------------|
| 0x1C Settlement | population(4), timezone(5), elevation(5), settlement_type(4), coastal(2) - **완료** |
| 0x1D Village | population(3), elevation(4), type(3), agriculture(3), facilities(4), access(3) |
| 0x1E Hamlet | population(3), elevation(4), type(3), isolation(3), infrastructure(3), origin(4) |
| 0x1F Street | length(4), width(3), type(4), surface(3), traffic(3), pedestrian(2), year(4) |
| 0x20 Cemetery | area(4), type(3), religion(4), era(4), capacity(3), heritage(2) |
| 0x21 AdminRegion | level(4), population(4), area(4), capital(4), established(4) |
| 0x22 Park | area(4), type(4), facilities(4), entrance(2), protected(3), biodiversity(3) |
| 0x23 ProtectedArea | area(5), iucn_cat(3), established(4), type(3), threats(3), enforcement(2) |

### 2.6 건축물 (0x24-0x2B)

**공통 템플릿** (24비트 핵심):
```
[0:7]   country         8비트   국가
[8:15]  location        8비트   위치 (행정구역)
[16:19] era             4비트   건립 시대
[20:23] style           4비트   건축 양식
```

| 타입 | 특화 필드 (24비트) |
|------|-------------------|
| 0x24 Building | height(4), floors(4), use(5), material(4), heritage(3), status(2), area(2) |
| 0x25 Church | denomination(5), size(3), style(4), heritage(3), active(2), diocese(4), organ(2), bells(1) |
| 0x26 School | level(4), type(4), size(4), public(2), specialty(4), accreditation(3), gender(2), boarding(1) |
| 0x27 House | type(4), size(4), style(4), material(3), heritage(3), floors(3), era(3) |
| 0x28 Structure | type(5), height(4), material(4), purpose(4), heritage(3), status(2), span(2) |
| 0x29 SportsVenue | sport(5), capacity(4), surface(3), indoor(1), tier(3), multi(2), built(4), renovation(2) |
| 0x2A Castle | type(4), size(3), era(4), condition(3), heritage(3), tourism(2), fortification(3), moat(2) |
| 0x2B Bridge | type(4), length(4), span(4), material(3), lanes(3), heritage(3), status(2), clearance(1) |

### 2.7 조직 (0x2C-0x2F)

**공통 템플릿** (26비트 핵심):
```
[0:7]   country         8비트   본사 국가
[8:11]  org_type        4비트   조직 유형
[12:17] legal_form      6비트   법인 형태
[18:25] industry        8비트   산업 분류
```

| 타입 | 특화 필드 (22비트) |
|------|-------------------|
| 0x2C Organization | era(4), size(4), hq_region(6), status(3), ideology(3), sector(2) - **완료** |
| 0x2D Business | era(4), size(4), employees(4), revenue(4), public(2), multinational(2), subsidiary(2) |
| 0x2E PoliticalParty | era(4), ideology(4), size(3), seats(4), coalition(2), active(2), spectrum(3) |
| 0x2F SportsTeam | sport(5), league(5), tier(3), era(4), titles(3), stadium(2) |

### 2.8 창작물 (0x30-0x3B)

**공통 템플릿** (24비트 핵심):
```
[0:7]   country         8비트   제작국/출판국
[8:14]  year            7비트   연도 (1900+)
[15:20] genre           6비트   장르
[21:23] notability      3비트   저명도
```

| 타입 | 특화 필드 (24비트) |
|------|-------------------|
| 0x30 Painting | style(5), medium(4), size(3), subject(4), location(4), artist_fame(4) |
| 0x31 Document | doc_type(5), language(6), length(4), format(3), access(3), citations(3) |
| 0x32 LiteraryWork | form(4), language(6), length(4), audience(3), awards(3), translations(4) |
| 0x33 Film | language(8), color(2), duration(4), director_fame(4), cast_tier(3), rating(3), format(3) - **완료** |
| 0x34 Album | format(3), language(4), tracks(4), duration(4), label(4), charts(3), certification(2) |
| 0x35 MusicalWork | form(4), language(4), duration(4), instruments(4), key(4), tempo(2), voices(2) |
| 0x36 TVEpisode | season(4), episode(5), duration(4), series_pop(4), rating(3), format(2), finale(2) |
| 0x37 VideoGame | platform(5), mode(3), esrb(3), developer_fame(4), franchise(3), multiplayer(2), online(2), vr(2) |
| 0x38 TVSeries | seasons(4), episodes(5), duration(4), network(4), status(2), format(3), rating(2) |
| 0x39 Patent | ipc_class(6), status(3), citations(4), family(3), priority(4), claims(4) |
| 0x3A Software | type(4), platform(4), license(4), language(4), maturity(3), users(3), active(2) |
| 0x3B Website | type(4), language(4), traffic(4), monetization(3), age(4), https(1), cdn(1), responsive(1), accessibility(2) |

### 2.9 이벤트/예약 (0x3C-0x3F)

**공통 템플릿** (20비트 핵심):
```
[0:7]   country         8비트   개최국
[8:14]  year            7비트   연도
[15:18] scale           4비트   규모
[19]    recurring       1비트   반복 여부
```

| 타입 | 특화 필드 (28비트) |
|------|-------------------|
| 0x3C SportsSeason | sport(5), league(5), tier(3), teams(5), champion(5), matches(4), postponed(1) |
| 0x3D Event | type(5), duration(4), attendance(4), indoor(1), virtual(1), annual(1), participants(5), media(4), sponsors(3) |
| 0x3E Election | type(4), level(3), turnout(4), parties(4), winner_margin(4), controversy(2), runoff(1), electronic(2), observers(4) |
| 0x3F Other | reserved(28) - 확장용 |

---

## 3. 템플릿 기반 설계 전략

### 3.1 템플릿 계층

```
Level 0: 전역 공통 (없음 - 타입별 완전 독립)
Level 1: 카테고리 템플릿 (20-28비트 공통)
Level 2: 타입 특화 (20-28비트 개별)
```

### 3.2 설계 원칙

1. **카테고리 내 일관성**: 같은 카테고리 타입은 핵심 필드 위치 동일
2. **상위 비트 = 핵심 분류**: offset 0에 가장 중요한 분류 필드
3. **하위 비트 = 세부 속성**: 열화 시 자연스럽게 추상화
4. **8비트 정렬 권장**: SIMD 최적화를 위해 8비트 경계 활용
5. **종속 필드 DAG**: 부모 필드 값이 자식 코드북 결정

### 3.3 비트 예산 가이드

| 필드 유형 | 권장 비트 | 이유 |
|----------|----------|------|
| 국가 | 8 | 256개 주권국 커버 |
| 행정구역 | 8 | 국가 종속, 256개 충분 |
| 연도 | 7 | 1900+127년 = 2027까지 |
| 시대 | 4 | 16개 시대 구분 |
| 장르/분류 | 5-6 | 32-64개 |
| 좌표 구역 | 4+4 | 위도 8구역, 경도 16구역 |
| 저명도 | 3-4 | 8-16 등급 |
| 언어 | 6-8 | 64-256개 언어 |
| 규모 (인구/크기) | 4 | 로그 스케일 16구간 |
| 상태/플래그 | 2-3 | 4-8가지 상태 |

---

## 4. 우선순위 결정

### 4.1 우선순위 기준

1. **개체 수**: 많을수록 충돌 위험 높음
2. **복잡도**: 속성 다양성, 종속 관계
3. **사용 빈도**: LLM 인코딩 시 자주 사용
4. **파일럿 유사도**: 기존 템플릿 재사용 가능

### 4.2 티어별 분류

#### Tier 1: 우선 설계 (10개) - 개체 100만 이상 또는 전략적 중요

| 코드 | 타입 | 개체수 | 근거 |
|------|------|--------|------|
| 0x01 | Taxon | 3.8M | 생물분류 핵심 |
| 0x0D | Galaxy | 2.1M | Star 템플릿 확장 |
| 0x08 | Chemical | 1.3M | 화학 카테고리 대표 |
| 0x02 | Gene | 1.2M | 생명과학 핵심 |
| 0x09 | Compound | 1.1M | Chemical 템플릿 확장 |
| 0x30 | Painting | 1.0M | 창작물 카테고리 대표 |
| 0x03 | Protein | 1.0M | Gene 템플릿 확장 |
| 0x31 | Document | 45M* | 논문/기사 대량 |
| 0x1F | Street | 710K | 장소 카테고리 대표 |
| 0x05 | FamilyName | 662K | 인물 연결 핵심 |

*Document는 개체수 최대이나 동질적이라 설계 용이

#### Tier 2: 중순위 설계 (20개) - 개체 10만~100만

| 코드 | 타입 | 개체수 | 템플릿 기반 |
|------|------|--------|------------|
| 0x14 | Mountain | 518K | 지형 템플릿 |
| 0x16 | River | 427K | 지형 템플릿 |
| 0x32 | LiteraryWork | 395K | Film 템플릿 |
| 0x33 | Film | 336K | **완료** |
| 0x15 | Hill | 321K | Mountain 확장 |
| 0x34 | Album | 303K | Film 템플릿 |
| 0x20 | Cemetery | 298K | 장소 템플릿 |
| 0x17 | Lake | 292K | River 템플릿 |
| 0x39 | Patent | 289K | Document 템플릿 |
| 0x24 | Building | 292K | 건축 템플릿 |
| 0x25 | Church | 286K | Building 확장 |
| 0x0E | Asteroid | 249K | Star 템플릿 |
| 0x1D | Village | 245K | Settlement 확장 |
| 0x2D | Business | 242K | Organization 확장 |
| 0x26 | School | 242K | Building 확장 |
| 0x27 | House | 235K | Building 확장 |
| 0x28 | Structure | 216K | Building 확장 |
| 0x35 | MusicalWork | 195K | Album 확장 |
| 0x18 | Stream | 194K | River 템플릿 |
| 0x3C | SportsSeason | 183K | 이벤트 템플릿 |

#### Tier 3: 후순위 설계 (25개) - 개체 1만~10만

| 코드 | 타입 | 개체수 | 템플릿 기반 |
|------|------|--------|------------|
| 0x0F | Quasar | 178K | Star 템플릿 |
| 0x36 | TVEpisode | 177K | Film 템플릿 |
| 0x37 | VideoGame | 172K | Film 템플릿 |
| 0x04 | CellLine | 154K | Gene 템플릿 |
| 0x19 | Island | 153K | 지형 템플릿 |
| 0x1E | Hamlet | 148K | Village 확장 |
| 0x29 | SportsVenue | 145K | Building 확장 |
| 0x06 | GivenName | 128K | FamilyName 확장 |
| 0x21 | AdminRegion | 100K | Settlement 확장 |
| 0x07 | FictionalChar | 98K | Human 템플릿 |
| 0x2F | SportsTeam | 95K | Organization 확장 |
| 0x38 | TVSeries | 85K | Film 템플릿 |
| 0x0A | Mineral | 62K | Chemical 템플릿 |
| 0x22 | Park | 45K | 장소 템플릿 |
| 0x0B | Drug | 45K | Chemical 확장 |
| 0x2A | Castle | 42K | Building 확장 |
| 0x2B | Bridge | 38K | Structure 확장 |
| 0x23 | ProtectedArea | 35K | Park 확장 |
| 0x2E | PoliticalParty | 35K | Organization 확장 |
| 0x1A | Bay | 25K | 지형 템플릿 |
| 0x1B | Cave | 20K | 지형 템플릿 |
| 0x10 | Planet | 15K | Star 템플릿 |
| 0x3A | Software | 13K | Document 템플릿 |
| 0x3B | Website | 12K | Document 템플릿 |
| 0x3E | Election | 11K | 이벤트 템플릿 |

#### Tier 4: 최후순위 (4개) - 개체 1만 미만 또는 예약

| 코드 | 타입 | 개체수 | 비고 |
|------|------|--------|------|
| 0x3D | Event | 10K | 이벤트 템플릿 |
| 0x11 | Nebula | 8K | Star 템플릿 |
| 0x12 | StarCluster | 5K | Star 템플릿 |
| 0x13 | Moon | 3K | Planet 확장 |
| 0x3F | Other | 0 | 확장 예약 |

---

## 5. 단계별 실행 계획

### Phase 4-A: 템플릿 정형화 (1-2일)

**목표**: 카테고리별 템플릿 JSON 스키마 확정

**작업**:
1. 9개 카테고리 템플릿 공식화
2. 공통 필드 offset/bits 표준화
3. 종속 관계 DAG 명세
4. `references/category_templates.json` 생성

**산출물**:
- `references/category_templates.json`
- `output/phase4a_templates_report.md`

### Phase 4-B: Tier 1 스키마 설계 (3-4일)

**목표**: 10개 우선 타입 스키마 확정

**작업 (타입당)**:
1. Stage 1: 위키데이터 속성 분포 분석
2. Stage 2: 종속 관계 탐지
3. Stage 3: 비트 할당
4. `type_schemas.json`에 추가

**병렬 가능**:
- 생물(Taxon, Gene, Protein): 1개 팀
- 화학(Chemical, Compound): 1개 팀
- 창작물(Painting, Document): 1개 팀
- 기타(Galaxy, Street, FamilyName): 1개 팀

**산출물**:
- `type_schemas.json` v0.3 (15개 타입)
- `output/phase4b_tier1_report.md`

### Phase 4-C: Tier 2 스키마 설계 (5-7일)

**목표**: 20개 중순위 타입 스키마 확정

**전략**: 템플릿 확장 패턴 활용
- Mountain/Hill/River/Lake/Stream: 지형 템플릿 + 특화
- Film/LiteraryWork/Album: 창작물 템플릿 + 특화
- Building/Church/School/House: 건축 템플릿 + 특화

**산출물**:
- `type_schemas.json` v0.4 (35개 타입)
- `output/phase4c_tier2_report.md`

### Phase 4-D: Tier 3+4 스키마 설계 (4-5일)

**목표**: 나머지 29개 타입 스키마 확정

**전략**: 기존 템플릿 기계적 확장
- 대부분 Tier 1-2 템플릿에서 파생
- 개체 수 적어 충돌 위험 낮음

**산출물**:
- `type_schemas.json` v1.0 (64개 타입)
- `output/phase4d_tier34_report.md`

### Phase 4-E: 코드북 생성 (3-4일)

**목표**: 64개 타입 전체 코드북

**작업**:
1. Stage 4 확장 실행
2. 종속 코드북 (국가별 행정구역 등) 생성
3. LLM 상식 검증

**산출물**:
- `output/codebooks/` (64개 타입)
- `output/phase4e_codebook_report.md`

### Phase 4-F: 통합 검증 (2-3일)

**목표**: 64개 타입 전체 검증

**작업**:
1. Stage 5 전체 실행
2. 충돌률 측정
3. SIMD 마스크 테스트
4. 열화 테스트

**산출물**:
- `output/phase4f_validation_report.md`
- `output/collision_matrix.csv`

---

## 6. 일정 요약

| 단계 | 기간 | 산출물 | 담당 |
|------|------|--------|------|
| Phase 4-A | 1-2일 | 템플릿 JSON | Architect |
| Phase 4-B | 3-4일 | Tier 1 스키마 10개 | Analyst + Builder |
| Phase 4-C | 5-7일 | Tier 2 스키마 20개 | Analyst + Builder |
| Phase 4-D | 4-5일 | Tier 3+4 스키마 29개 | Builder |
| Phase 4-E | 3-4일 | 코드북 64개 | Builder + Ontologist |
| Phase 4-F | 2-3일 | 검증 보고서 | Analyst + Architect |
| **합계** | **18-25일** | | |

---

## 7. 리스크 및 대응

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| 속성 데이터 부족 (일부 타입) | 중 | 중 | 범용 default_schema 사용 |
| 48비트 부족 (복잡 타입) | 낮음 | 높음 | 필드 우선순위 재조정 |
| 코드북 오버플로 | 중 | 중 | 비트 재할당 또는 상위 코드 통합 |
| DB 성능 이슈 | 중 | 중 | 샘플링 + 캐시 전략 |

---

## 8. 승인 체크리스트

### Phase 4 시작 전

- [ ] type_schemas.json v0.2 검토 완료
- [ ] 카테고리 템플릿 전략 승인
- [ ] 우선순위 티어 승인
- [ ] 일정 확정

### Phase 4 완료 후

- [ ] 64개 타입 스키마 완료
- [ ] 충돌률 목표 달성 (타입별 기준)
- [ ] 코드북 커버리지 80% 이상
- [ ] SIMD 쿼리 테스트 통과

---

## 9. 다음 단계

Phase 4 완료 후:
1. **Phase 5**: LLM 인코더 프로토타입 개발
2. **Phase 6**: 벤치마크 데이터셋 구축
3. **Phase 7**: 실사용 테스트 및 튜닝

---

*GEUL Entity Team - Phase 4 Master Plan*
*Date: 2026-02-01*
*Author: Architect*
