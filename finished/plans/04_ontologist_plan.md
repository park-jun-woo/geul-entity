# GEUL Entity SIDX 온톨로지 검증 계획

> **역할**: Ontologist
> **버전**: v1.0
> **작성일**: 2026-02-01

---

## 1. 분류 체계 검증 (MECE 원칙)

### 1.1 상호배타성(Mutually Exclusive) 검토

현재 64개 타입은 9개 카테고리로 분류되어 있으며, 각 타입이 단일 카테고리에만 속하도록 설계되어 있다. 그러나 다음 경계 사례들은 두 타입에 모두 속할 가능성이 있어 검증이 필요하다.

#### 경계 사례 목록

| 사례 | 충돌 타입 | 문제 설명 | 권장 처리 |
|------|-----------|-----------|-----------|
| 대학교 | School(0x26) vs Organization(0x2C) | 건물이자 조직 | **Organization 우선** (건물은 별도 개체로 분리) |
| 박물관 | Building(0x24) vs Organization(0x2C) | 루브르 박물관은 건물이자 기관 | **Organization 우선** (건물 포함 속성으로 처리) |
| 교회 조직 | Church(0x25) vs Organization(0x2C) | 바티칸, 대한예수교장로회 등 | Church=건물, **종교 조직은 Organization** |
| 국립공원 관리청 | Park(0x22) vs Organization(0x2C) | 관리 조직 vs 지역 | **Park**=지역, 관리 조직은 별도 Organization |
| 미생물 | Taxon(0x01) vs Chemical(0x08) | 바이러스(생물 vs 화학 물질 논쟁) | **Taxon** (ICTV 분류 체계 따름) |
| 합성 생물학 산물 | Taxon(0x01) vs Chemical(0x08) | 합성 DNA, 인공 세포 | [CONSULT] 전문가 협의 필요 |
| 방송국 | Building(0x24) vs Organization(0x2C) | KBS 여의도 사옥 vs KBS | 건물/조직 분리, **Organization 우선** |
| 경기장 | SportsVenue(0x29) vs Organization(0x2C) | FC 바르셀로나 홈구장 | **SportsVenue** (건축물 카테고리) |
| 다큐멘터리 | Film(0x33) vs TVSeries(0x38)/TVEpisode(0x36) | 방영 매체에 따라 | 극장 개봉=Film, TV방영=TVEpisode |
| 웹툰/웹소설 | LiteraryWork(0x32) vs Website(0x3B) | 디지털 네이티브 콘텐츠 | **LiteraryWork** (콘텐츠 본질 기준) |
| 가상 아이돌 | FictionalCharacter(0x07) vs Human(0x00) | 하츠네 미쿠, 에스파 아이 | **FictionalCharacter** |
| AI 에이전트 | Human(0x00) vs Software(0x3A) | ChatGPT, Claude | **Software** (인간 아님) |
| 우주정거장 | Structure(0x28) vs Moon(0x13) | ISS - 인공 위성 | **Structure** (인공물) |

#### [CONSULT] 전문 검토 필요 항목

1. **바이러스 분류**: 생물학적으로 "생물"인지 논쟁 중. 현재는 Taxon으로 분류하나, 화학적 관점(단백질+핵산 복합체)도 유효함.

2. **가상 화폐/NFT**: 현재 분류에 없음. Document(0x31)? Chemical(디지털 자산)?

3. **인공지능 창작물**: AI가 그린 그림은 Painting(0x30)으로 분류 가능한가?

### 1.2 전체포괄성(Collectively Exhaustive) 검토

위키데이터 P31(instance of) 통계 기준, 100K 이상 개체를 가진 타입 중 현재 분류에서 **누락된 타입** 목록:

| QID | 라벨 | 개체수 | 현재 상태 | 권장 조치 |
|-----|------|--------|-----------|-----------|
| Q13442814 | scholarly article | 45,216,368 | Document에 통합 | O (Document 0x31에 포함) |
| Q4167836 | Wikimedia category | 5,698,822 | 제외 | O (메타데이터, 제외 정당) |
| Q67206691 | infrared source | 2,621,805 | Star 하위? | [REVIEW] Star 속성으로 처리 |
| Q4167410 | Wikimedia disambiguation page | 1,517,308 | 제외 | O (메타데이터, 제외 정당) |
| Q11266439 | Wikimedia template | 830,519 | 제외 | O (메타데이터, 제외 정당) |
| Q3331189 | version/edition/translation | 729,756 | Document? | [REVIEW] Document 하위 타입으로 |
| Q13433827 | encyclopedia article | 642,974 | Document에 통합 | O |
| Q13100073 | village of PRC | 592,626 | Village에 통합 | O |
| Q871232 | editorial | 513,039 | Document에 통합 | O |
| Q2668072 | collection | 504,230 | 누락 | [ADD] 새 타입 또는 Other |
| Q1931185 | astronomical radio source | 396,880 | Star 속성? | [REVIEW] Star 플래그로 처리 |
| Q30612 | clinical trial | 391,919 | Event? Document? | [CONSULT] 의료/과학 전문가 |
| Q13406463 | Wikimedia list article | 378,180 | 제외 | O (메타데이터) |
| Q2342494 | collectible | 371,472 | 누락 | [REVIEW] 도자기/동전 등 포함 |
| Q2247863 | high proper-motion star | 306,766 | Star 속성 | O (플래그로 처리) |
| Q1457376 | eclipsing binary star | 298,485 | Star 속성 | O (플래그로 처리) |
| Q17633526 | Wikinews article | 296,002 | Document에 통합 | O |
| Q113813711 | coin type | 214,456 | 누락 | [ADD] Artifact/Collectible 필요 |
| Q47150325 | calendar day | 201,356 | 제외 | O (시간 개념, Entity 아님) |
| Q1080794 | public school | 188,771 | School에 통합 | O |
| Q2782326 | case report | 187,462 | Document에 통합 | O |
| Q19389637 | biographical article | 181,805 | Document에 통합 | O |
| Q355304 | watercourse | 174,789 | River/Stream에 통합 | O |
| Q47461344 | written work | 170,007 | LiteraryWork 상위 | O |
| Q98276829 | porcelain ware | 163,839 | 누락 | [ADD] Artifact 필요 |
| Q29654788 | Unicode character | 161,479 | 제외 | O (추상 개념) |
| Q1580166 | dictionary entry | 158,057 | Document에 통합 | O |
| Q2154519 | astrophysical X-ray source | 157,565 | Star 속성 | O |
| Q191067 | article | 155,529 | Document에 통합 | O |
| Q56436498 | village in India | 154,095 | Village에 통합 | O |
| Q59199015 | group of stereoisomers | 148,411 | Chemical에 통합 | O |
| Q11060274 | print | 144,901 | Painting과 구분? | [REVIEW] Artwork 통합? |
| Q115595777 | taxonomy template | 140,524 | 제외 | O (메타데이터) |
| Q39816 | valley | 134,922 | 지형/자연 누락 | [ADD] 0x14-0x1B에 추가 |
| Q27686 | hotel | 131,503 | Building에 통합 | O |
| Q61443690 | branch post office | 129,183 | Building에 통합 | O |
| Q4164871 | position | 128,080 | 제외 | O (역할, Entity 아님) |
| Q860861 | sculpture | 125,054 | Painting과 구분 | [REVIEW] Artwork 통합 필요 |
| Q93184 | drawing | 122,863 | Painting에 통합 | [REVIEW] |
| Q23038290 | fossil taxon | 116,450 | Taxon에 통합 | O |
| Q134556 | single (음악) | 115,325 | Album/MusicalWork | O |
| Q55488 | railway station | 113,556 | Structure에 통합 | O |

#### 누락 타입 추가 제안

1. **Artifact (공예품/수집품)**: 동전, 도자기, 조각품, 판화 등 통합
   - 현재 Painting(0x30)에서 분리 필요
   - 개체수: ~70만 (collectible + porcelain + sculpture + print)

2. **Valley (계곡/골짜기)**: 지형/자연 카테고리에 추가
   - 개체수: 134,922
   - 현재 0x14-0x1B 중 예약 슬롯 사용 가능

3. **ClinicalTrial (임상시험)**: Event 또는 Document 하위
   - 개체수: 391,919
   - [CONSULT] 의료 도메인 전문가와 협의 필요

---

## 2. 이진 트리 구조 검증

### 2.1 6비트 EntityType 구조 분석

```
비트 5-4-3: 대분류 (8개 그룹)
비트 2-1-0: 소분류 (그룹 내 8개)
```

| 비트 543 | 대분류 | 현재 범주 |
|----------|--------|-----------|
| 000 | 0x00-0x07 | 생물/인물 |
| 001 | 0x08-0x0F | 화학/물질 + 천체 전반 |
| 010 | 0x10-0x17 | 천체 후반 + 지형/자연 전반 |
| 011 | 0x18-0x1F | 지형/자연 후반 + 장소/행정 전반 |
| 100 | 0x20-0x27 | 장소/행정 후반 + 건축물 전반 |
| 101 | 0x28-0x2F | 건축물 후반 + 조직 |
| 110 | 0x30-0x37 | 창작물 |
| 111 | 0x38-0x3F | 창작물 후반 + 이벤트 |

### 2.2 상위 비트 마스킹 시 의미적 일관성

#### 문제 있는 마스킹 패턴

| 마스크 | 범위 | 포함 타입 | 의미적 일관성 |
|--------|------|-----------|---------------|
| 0x00-0x07 (000xxx) | 생물/인물 | Human, Taxon, Gene, Protein, CellLine, FamilyName, GivenName, FictionalCharacter | **불량** - 인간/생물/분자 혼합 |
| 0x08-0x0F (001xxx) | 화학+천체 | Chemical, Compound, Mineral, Drug, Star, Galaxy, Asteroid, Quasar | **불량** - 화학물질과 천체 혼합 |
| 0x30-0x37 (110xxx) | 창작물 | Painting, Document, LiteraryWork, Film, Album, MusicalWork, TVEpisode, VideoGame | **양호** - 모두 창작물 |

#### [REVIEW] 권장 재배치

현재 배치에서 상위 3비트 마스킹의 의미적 일관성이 떨어지는 영역:

1. **0x00-0x07 (생물/인물)**
   - Human(0x00), FictionalCharacter(0x07)은 "인물" 개념으로 일관
   - Taxon, Gene, Protein, CellLine은 "생물학적 개체"로 분리 권장
   - FamilyName, GivenName은 "명명" 개념으로 분리 권장

2. **0x08-0x0F (화학+천체 전반)**
   - 화학(0x08-0x0B)과 천체(0x0C-0x0F)가 혼합
   - 마스킹 시 "화학물질과 별"이 같은 그룹으로 묶임
   - **의미적 분리 권장**: 천체를 별도 상위 비트로

### 2.3 Human(0x00)과 FictionalCharacter(0x07)의 관계

```
0x00 = 000000 (Human)
0x07 = 000111 (FictionalCharacter)
```

- **공통 상위 3비트**: 000 (생물/인물 그룹)
- **마스크 0x38(상위 3비트)로 필터**: Human과 FictionalCharacter가 같은 그룹
- **의미적 관계**: 양호 - 둘 다 "인물" 개념
- **우아한 열화**: Human 쿼리 시 FictionalCharacter 제외 필요 → 하위 비트로 구분 가능

### 2.4 우아한 열화 테스트 시나리오

| 시작 타입 | 비트 마스크 | 열화 결과 | 의미 |
|-----------|-------------|-----------|------|
| 0x00 Human | 0x38 (상위 3비트) | 생물/인물 전체 | O |
| 0x33 Film | 0x38 | 창작물 전체 | O |
| 0x1C Settlement | 0x38 | 지형+장소 혼합 | **X** (불량) |
| 0x24 Building | 0x38 | 장소+건축 혼합 | **X** (불량) |

---

## 3. 누락 타입 분석

### 3.1 100K 이상 개체 중 미포함 타입

위키데이터 통계 기준, 현재 64개 타입에 포함되지 않았으나 의미 있는 타입:

| 우선순위 | QID | 타입명 | 개체수 | 추가 필요성 | 권장 코드 |
|----------|-----|--------|--------|-------------|-----------|
| HIGH | Q860861 | sculpture | 125,054 | 예술 작품 구분 | 0x30 하위 또는 신규 |
| HIGH | Q39816 | valley | 134,922 | 지형 완결성 | 0x1B 또는 예약 슬롯 |
| MEDIUM | Q113813711 | coin type | 214,456 | 수집품/화폐 | Other(0x3F) 또는 신규 |
| MEDIUM | Q2668072 | collection | 504,230 | 컬렉션 | Document 속성? |
| MEDIUM | Q30612 | clinical trial | 391,919 | 의료 이벤트 | Event(0x3D) 확장 |
| LOW | Q215380 | musical group | 95,816 | 조직 확장 | Organization(0x2C) 속성 |
| LOW | Q5633421 | scientific journal | 99,940 | 출판물 | Document(0x31) 속성 |

### 3.2 타입 추가 시 코드 할당 전략

현재 예약 슬롯:
- **0x3F (Other)**: 확장용으로 남겨둠

타입 추가 시:
1. 해당 카테고리 내 예약 슬롯 우선 사용
2. 기존 타입의 subtype 속성으로 처리
3. Other(0x3F)에 임시 할당 후 다음 버전에서 정식 배치

---

## 4. 타입 간 속성 공유 패턴

### 4.1 공통 속성 분석

다수 타입에서 공유되는 위키데이터 Property:

| Property | 라벨 | 사용 타입 수 | 표준화 필요 |
|----------|------|--------------|-------------|
| P17 | country | 30+ | **필수** - 8비트 표준 코드 |
| P131 | admin territory | 20+ | **필수** - 국가 종속 계층 |
| P625 | coordinate | 25+ | **필수** - 양자화 규칙 적용 |
| P571 | inception | 20+ | **필수** - era+decade 표준 |
| P18 | image | 40+ | 제외 (외부 참조) |
| P373 | Commons category | 50+ | 제외 (메타데이터) |

### 4.2 공통 필드 표준화 방안

```
[공통 필드 템플릿]
├── country (8비트): 모든 국가 소속 타입 공통
├── era (4비트): 시간 관련 타입 공통
├── decade (4비트, era 종속): 시간 상세
├── lat_zone (4비트): 좌표 관련 타입 공통
├── lon_zone (4비트): 좌표 관련 타입 공통
└── notability (3비트): 저명도 (선택적)
```

### 4.3 타입별 필드 위치 일관성

| 필드 | Human | Settlement | Organization | Film | 일관성 |
|------|-------|------------|--------------|------|--------|
| country | offset 11 | offset 0 | offset 0 | offset 0 | **불량** |
| era | offset 19 | N/A | offset 26 | offset 8 (year) | **불량** |

**[REVIEW] 권장**: country를 모든 타입에서 offset 0에 배치하여 SIMD 필터링 최적화

---

## 5. 코드북 검증 기준

### 5.1 Era별 Polity 테이블 역사적 정확성

Era 코드(4비트, 16개 시대)에 대해 각 시대별 주요 정치체(Polity) 존재 여부 검증:

| Era | 범위 | 필수 포함 Polity | 검증 항목 |
|-----|------|------------------|-----------|
| 0 | Unknown | N/A | - |
| 1 | ~BC3000 | Egypt, Sumer | 고대 문명 초기 |
| 2 | BC3000~500 | Egypt, Greece, Persia, China(Zhou) | 고대 제국 |
| 3 | 500~1000 | Rome, Tang, Byzantine, Caliphate | 고전기 제국 |
| 4 | 1000~1500 | Goryeo, Song, Mongol, HRE | 중세 왕조 |
| 5 | 1500~1800 | Joseon, Ming/Qing, Ottoman, Spain | 근세 제국 |
| 6 | 1800~1900 | Joseon, Qing, British Empire, USA | 근대 국민국가 |
| 7~12 | 1900~ | 현대 국가 코드 (ISO 3166 기반) | - |

#### [CONSULT] 역사 전문가 검토 필요 항목

1. **시대 경계**: 500년(고대/고전), 1000년(고전/중세) 경계가 서양 중심적
   - 동아시아: 220년(한 멸망), 907년(당 멸망)이 더 적절할 수 있음

2. **정치체 코드 할당**:
   - 로마 제국 vs 서로마/동로마 분리?
   - 중국 왕조: 통일 왕조만 vs 분열기 정권도 포함?

### 5.2 직업 분류 일관성

Human(0x00) 타입의 occupation 필드(6비트, 64개):

| 대분류 | 세부 직업 | 검증 항목 |
|--------|-----------|-----------|
| 정치/행정 | 정치인, 관료, 외교관, 군인 | O |
| 학술/연구 | 과학자, 교수, 연구원 | O |
| 예술/창작 | 화가, 음악가, 작가, 배우 | O |
| 스포츠 | 축구선수, 야구선수, 올림픽 선수 | O |
| 종교 | 성직자, 승려, 이맘 | O |
| 비즈니스 | 기업인, CEO, 투자자 | O |

#### [REVIEW] 직업 분류 문제점

1. **다중 직업**: 아이유(가수+배우), 일론 머스크(기업인+엔지니어)
   - 권장: 주요 직업 1개만 인코딩, 세부는 Triple로

2. **역사적 직업**: 검투사, 연금술사 → 현대 분류에 매핑 필요

3. **신생 직업**: 유튜버, 인플루언서, 데이터 과학자
   - 코드북 예약 영역 활용

### 5.3 장르/산업 분류 체계

#### Film(0x33) 장르 (6비트, 64개)

| 대분류 | 장르 | IMDb/Wikipedia 매핑 |
|--------|------|---------------------|
| 극영화 | 드라마, 로맨스, 코미디, 공포, SF, 액션 | O |
| 논픽션 | 다큐멘터리, 전기 | O |
| 애니메이션 | 2D, 3D, 스톱모션 | [REVIEW] 별도 분류? |

#### Organization(0x2C) 산업 (8비트, 256개)

| 대분류 | 산업 | ISIC/NAICS 매핑 |
|--------|------|-----------------|
| 1차 산업 | 농업, 광업, 어업 | O |
| 2차 산업 | 제조업, 건설업 | O |
| 3차 산업 | 서비스, 금융, IT | O |

**[REVIEW]** 산업 분류는 국제 표준(ISIC Rev.4)과 매핑 필요

---

## 6. 검증 실행 계획

### Phase 1: 자동 검증 (DB 쿼리)

1. 각 타입별 위키데이터 개체 수 vs entity_types_64.json 수치 비교
2. P31 다중 값 개체 추출 (경계 사례 후보)
3. 누락 타입 후보 추출 (100K 이상, 미매핑)

### Phase 2: 수동 검증 (전문가 리뷰)

1. 경계 사례 100개 샘플 검토
2. 역사적 Polity 코드북 검토 (역사학자)
3. 생물 분류 검토 (생물학자)

### Phase 3: 스트레스 테스트

1. 전체 개체 인코딩 시 충돌률 측정
2. 우아한 열화 쿼리 성능 테스트
3. 코드북 커버리지 검증 (Unknown 비율)

---

## 7. 미해결 이슈 요약

| 이슈 ID | 설명 | 태그 | 담당 |
|---------|------|------|------|
| ONT-001 | 화학+천체 혼합 영역(0x08-0x0F) | [REVIEW] | Ontologist |
| ONT-002 | 바이러스 분류 (Taxon vs Chemical) | [CONSULT] | 생물학 전문가 |
| ONT-003 | 시대 경계 서양 중심성 | [CONSULT] | 역사학 전문가 |
| ONT-004 | country 필드 offset 불일치 | [REVIEW] | Schema Designer |
| ONT-005 | Valley, Sculpture 등 누락 타입 | [ADD] | 전체 팀 |
| ONT-006 | 가상화폐/NFT 분류 | [CONSULT] | 도메인 전문가 |

---

## 부록: 타입 코드 전체 목록

```
생물/인물 (0x00-0x07)
  0x00 Human        0x04 CellLine
  0x01 Taxon        0x05 FamilyName
  0x02 Gene         0x06 GivenName
  0x03 Protein      0x07 FictionalCharacter

화학/물질 (0x08-0x0B)
  0x08 Chemical     0x0A Mineral
  0x09 Compound     0x0B Drug

천체 (0x0C-0x13)
  0x0C Star         0x10 Planet
  0x0D Galaxy       0x11 Nebula
  0x0E Asteroid     0x12 StarCluster
  0x0F Quasar       0x13 Moon

지형/자연 (0x14-0x1B)
  0x14 Mountain     0x18 Stream
  0x15 Hill         0x19 Island
  0x16 River        0x1A Bay
  0x17 Lake         0x1B Cave

장소/행정 (0x1C-0x23)
  0x1C Settlement   0x20 Cemetery
  0x1D Village      0x21 AdminRegion
  0x1E Hamlet       0x22 Park
  0x1F Street       0x23 ProtectedArea

건축물 (0x24-0x2B)
  0x24 Building     0x28 Structure
  0x25 Church       0x29 SportsVenue
  0x26 School       0x2A Castle
  0x27 House        0x2B Bridge

조직 (0x2C-0x2F)
  0x2C Organization 0x2E PoliticalParty
  0x2D Business     0x2F SportsTeam

창작물 (0x30-0x3B)
  0x30 Painting     0x36 TVEpisode
  0x31 Document     0x37 VideoGame
  0x32 LiteraryWork 0x38 TVSeries
  0x33 Film         0x39 Patent
  0x34 Album        0x3A Software
  0x35 MusicalWork  0x3B Website

이벤트/예약 (0x3C-0x3F)
  0x3C SportsSeason 0x3E Election
  0x3D Event        0x3F Other (예약)
```
