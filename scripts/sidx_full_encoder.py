#!/usr/bin/env python3
"""
GEUL Entity SIDX Full 64-bit Encoder
64개 타입 × 48비트 속성 전체 인코딩

Usage:
    python scripts/sidx_full_encoder.py
"""

import json
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import sys
import os
import re

# 상수
SIDX_PREFIX = 0b0001001
DEFAULT_MODE = 0
BATCH_SIZE = 5000

# 필요한 모든 위키데이터 속성
ALL_PROPERTIES = [
    'P17', 'P21', 'P27', 'P31', 'P59', 'P101', 'P105', 'P106', 'P118', 'P131',
    'P135', 'P136', 'P140', 'P141', 'P149', 'P159', 'P171', 'P186', 'P215',
    'P223', 'P275', 'P277', 'P282', 'P306', 'P364', 'P400', 'P404', 'P407',
    'P437', 'P449', 'P452', 'P462', 'P495', 'P556', 'P569', 'P571', 'P577',
    'P580', 'P591', 'P625', 'P636', 'P641', 'P680', 'P681', 'P682', 'P703',
    'P814', 'P826', 'P921', 'P1050', 'P1057', 'P1082', 'P1083', 'P1088',
    'P1090', 'P1096', 'P1101', 'P1128', 'P1142', 'P1215', 'P1289', 'P1387',
    'P1412', 'P1454', 'P1909', 'P2043', 'P2044', 'P2046', 'P2047', 'P2048',
    'P2053', 'P2054', 'P2067', 'P2101', 'P2102', 'P2147', 'P2175', 'P2293',
    'P2386', 'P2660', 'P2868', 'P2974', 'P3450', 'P3489', 'P4007', 'P4511',
    'P5185', 'P6257', 'P6258', 'P8345', 'P10751', 'P421'
]


class SIDXEncoder:
    def __init__(self, ref_dir):
        # 스키마 로드
        with open(os.path.join(ref_dir, 'type_schemas.json'), 'r') as f:
            self.schemas = json.load(f)

        # 코드북 로드
        with open(os.path.join(ref_dir, 'codebooks_full.json'), 'r') as f:
            self.codebooks = json.load(f)

        # P31 매핑 로드
        with open(os.path.join(ref_dir, 'primary_mapping.json'), 'r') as f:
            mapping = json.load(f)

        self.type_map = {}
        for qid, info in mapping['primary_mappings'].items():
            self.type_map[qid] = int(info['code'], 16)
        for qid, info in mapping['subtype_mappings'].items():
            self.type_map[qid] = int(info['target'], 16)

        self.exclude_qids = set(mapping.get('exclude_qids', {}).keys())

        # 코드북 맵 빌드
        self.codebook_maps = self._build_codebook_maps()

        # 고정 맵들
        self._init_fixed_maps()

    def _build_codebook_maps(self):
        """코드북을 QID → code 매핑으로 변환"""
        maps = {}
        for name, cb in self.codebooks.get('codebooks', {}).items():
            qid_to_code = {}
            for entry in cb.get('values', []):
                qid = entry.get('qid')
                if qid:
                    qid_to_code[qid] = entry['code']
            maps[name] = qid_to_code
        return maps

    def _init_fixed_maps(self):
        """고정 코드 맵 초기화"""
        # Gender
        self.gender_map = {
            'Q6581097': 1,   # male
            'Q6581072': 2,   # female
            'Q1097630': 3,   # intersex
            'Q1052281': 3,   # transgender female
            'Q2449503': 3,   # transgender male
        }

        # Taxon rank
        self.rank_map = {
            'Q7432': 1,     # species
            'Q34740': 2,    # genus
            'Q35409': 3,    # family
            'Q36602': 4,    # order
            'Q37517': 5,    # class
            'Q38348': 6,    # phylum
            'Q36732': 7,    # kingdom
        }

        # Conservation status
        self.conservation_map = {
            'Q211005': 1,   # LC
            'Q719675': 2,   # NT
            'Q278113': 3,   # VU
            'Q11394': 4,    # EN
            'Q219127': 5,   # CR
            'Q239509': 6,   # EW
            'Q237350': 7,   # EX
        }

        # Constellation
        self.constellation_map = self.codebook_maps.get('constellation', {})

        # Spectral type
        self.spectral_map = {
            'O': 1, 'B': 2, 'A': 3, 'F': 4, 'G': 5, 'K': 6, 'M': 7,
            'L': 8, 'T': 9, 'Y': 10, 'C': 11, 'S': 12, 'W': 13,
        }

        # Galaxy morphology (Hubble)
        self.morphology_map = {
            'E': 1, 'S0': 2, 'Sa': 3, 'Sb': 4, 'Sc': 5, 'Sd': 6,
            'SBa': 7, 'SBb': 8, 'SBc': 9, 'Irr': 10,
        }

        # Architectural style
        self.style_map = self.codebook_maps.get('style', {})

        # Material
        self.material_map = self.codebook_maps.get('material', {})

        # Industry
        self.industry_map = self.codebook_maps.get('industry', {})

        # Legal form
        self.legal_form_map = self.codebook_maps.get('legal_form', {})

        # Sport
        self.sport_map = self.codebook_maps.get('sport', {})

        # Platform
        self.platform_map = self.codebook_maps.get('platform', {})

        # Programming language
        self.prog_lang_map = self.codebook_maps.get('prog_lang', {})

        # Religion
        self.religion_map = self.codebook_maps.get('religion', {})

    def _encode_era(self, year):
        """연도를 4비트 era 코드로"""
        if year is None:
            return 0
        if year < 0:
            return 1  # BCE
        elif year < 500:
            return 2  # 고대
        elif year < 1000:
            return 3  # 중세 초
        elif year < 1500:
            return 4  # 중세
        elif year < 1700:
            return 5  # 근세
        elif year < 1800:
            return 6  # 18c
        elif year < 1850:
            return 7  # 19c 전
        elif year < 1900:
            return 8  # 19c 후
        elif year < 1950:
            return 9  # 20c 전
        elif year < 1970:
            return 10 # 1950-70
        elif year < 1990:
            return 11 # 1970-90
        elif year < 2000:
            return 12 # 1990s
        elif year < 2010:
            return 13 # 2000s
        elif year < 2020:
            return 14 # 2010s
        else:
            return 15 # 2020s+

    def _parse_year(self, date_str):
        """위키데이터 날짜에서 연도 추출"""
        if not date_str:
            return None
        try:
            if date_str.startswith('+') or date_str.startswith('-'):
                return int(date_str[1:5])
            m = re.match(r'(\d{4})', date_str)
            if m:
                return int(m.group(1))
        except:
            pass
        return None

    def _parse_coords(self, coord_str):
        """좌표 파싱 → (lat, lon)"""
        if not coord_str:
            return None, None
        try:
            # Point(lon lat) 형식
            m = re.search(r'Point\(([-\d.]+)\s+([-\d.]+)\)', coord_str)
            if m:
                return float(m.group(2)), float(m.group(1))
        except:
            pass
        return None, None

    def _encode_lat_zone(self, lat):
        """위도를 4비트 존으로"""
        if lat is None:
            return 0
        if lat < -60:
            return 1
        elif lat < -30:
            return 2
        elif lat < -15:
            return 3
        elif lat < 0:
            return 4
        elif lat < 15:
            return 5
        elif lat < 30:
            return 6
        elif lat < 45:
            return 7
        elif lat < 60:
            return 8
        else:
            return 9

    def _encode_lon_zone(self, lon):
        """경도를 4비트 존으로"""
        if lon is None:
            return 0
        # -180 ~ 180을 16구역으로
        zone = int((lon + 180) / 22.5)
        return min(15, max(0, zone))

    def _encode_population(self, pop):
        """인구를 4비트 로그 스케일로"""
        if pop is None or pop <= 0:
            return 0
        import math
        log_pop = math.log10(pop)
        if log_pop < 2:
            return 1
        elif log_pop < 3:
            return 2
        elif log_pop < 4:
            return 3
        elif log_pop < 5:
            return 4
        elif log_pop < 6:
            return 5
        elif log_pop < 7:
            return 6
        elif log_pop < 8:
            return 7
        else:
            return 8

    def _encode_elevation(self, elev):
        """고도를 5비트로"""
        if elev is None:
            return 0
        if elev < 0:
            return 1
        elif elev < 100:
            return 2
        elif elev < 200:
            return 3
        elif elev < 500:
            return 4
        elif elev < 1000:
            return 5
        elif elev < 1500:
            return 6
        elif elev < 2000:
            return 7
        elif elev < 3000:
            return 8
        elif elev < 4000:
            return 9
        elif elev < 5000:
            return 10
        elif elev < 6000:
            return 11
        elif elev < 7000:
            return 12
        elif elev < 8000:
            return 13
        else:
            return 14

    def _encode_area(self, area):
        """면적을 4비트 로그 스케일로"""
        if area is None or area <= 0:
            return 0
        import math
        log_area = math.log10(area)
        return min(15, max(1, int(log_area) + 1))

    def _encode_length(self, length):
        """길이를 4비트로"""
        if length is None or length <= 0:
            return 0
        if length < 10:
            return 1
        elif length < 50:
            return 2
        elif length < 100:
            return 3
        elif length < 500:
            return 4
        elif length < 1000:
            return 5
        elif length < 5000:
            return 6
        else:
            return 7

    def _get_prop(self, triples, prop):
        """트리플에서 속성값 가져오기"""
        for p, v in triples:
            if p == prop:
                return v
        return None

    def _get_props(self, triples, prop):
        """트리플에서 모든 속성값 가져오기"""
        return [v for p, v in triples if p == prop]

    def _lookup_codebook(self, codebook_name, qid):
        """코드북에서 코드 조회"""
        cb = self.codebook_maps.get(codebook_name, {})
        return cb.get(qid, 0)

    def encode_human(self, triples):
        """0x00 Human: 48비트"""
        attrs = 0

        # subclass (5비트, offset 0) - 기본 0

        # occupation (6비트, offset 5)
        occ = self._get_prop(triples, 'P106')
        if occ:
            code = self._lookup_codebook('occupation', occ)
            attrs |= (code & 0x3F) << 5

        # country (8비트, offset 11)
        country = self._get_prop(triples, 'P27')
        if country:
            code = self._lookup_codebook('country', country)
            attrs |= (code & 0xFF) << 11

        # era (4비트, offset 19)
        birth = self._get_prop(triples, 'P569')
        year = self._parse_year(birth)
        attrs |= (self._encode_era(year) & 0xF) << 19

        # decade (4비트, offset 23)
        if year and year >= 1900:
            decade = min(15, (year - 1900) // 10)
            attrs |= (decade & 0xF) << 23

        # gender (2비트, offset 27)
        gender = self._get_prop(triples, 'P21')
        if gender and gender in self.gender_map:
            attrs |= (self.gender_map[gender] & 0x3) << 27

        # notability (3비트, offset 29) - 기본 0

        # language (6비트, offset 32)
        lang = self._get_prop(triples, 'P1412')
        if lang:
            code = self._lookup_codebook('language', lang)
            attrs |= (code & 0x3F) << 32

        # birth_region (6비트, offset 38)
        region = self._get_prop(triples, 'P19')
        if region:
            code = self._lookup_codebook('admin', region)
            attrs |= (code & 0x3F) << 38

        # activity_field (4비트, offset 44)
        field = self._get_prop(triples, 'P101')
        if field:
            code = self._lookup_codebook('occupation', field) & 0xF
            attrs |= code << 44

        return attrs

    def encode_taxon(self, triples):
        """0x01 Taxon: 48비트"""
        attrs = 0

        # kingdom, phylum, class, order, family는 P171 체인에서 유도 - 복잡
        # 간단히 rank와 conservation만 인코딩

        # rank (3비트, offset 26)
        rank = self._get_prop(triples, 'P105')
        if rank and rank in self.rank_map:
            attrs |= (self.rank_map[rank] & 0x7) << 26

        # conservation (3비트, offset 29)
        cons = self._get_prop(triples, 'P141')
        if cons and cons in self.conservation_map:
            attrs |= (self.conservation_map[cons] & 0x7) << 29

        return attrs

    def encode_gene(self, triples):
        """0x02 Gene: 48비트"""
        attrs = 0

        # organism (6비트, offset 0)
        org = self._get_prop(triples, 'P703')
        if org:
            code = self._lookup_codebook('organism', org)
            attrs |= (code & 0x3F)

        # chromosome (5비트, offset 6)
        chrom = self._get_prop(triples, 'P1057')
        if chrom:
            # Q-ID에서 숫자 추출 시도
            try:
                num = int(re.search(r'\d+', chrom).group()) % 32
                attrs |= (num & 0x1F) << 6
            except:
                pass

        return attrs

    def encode_protein(self, triples):
        """0x03 Protein: 48비트"""
        attrs = 0

        # organism (6비트, offset 0)
        org = self._get_prop(triples, 'P703')
        if org:
            code = self._lookup_codebook('organism', org)
            attrs |= (code & 0x3F)

        return attrs

    def encode_chemical(self, triples):
        """0x08 Chemical: 48비트"""
        attrs = 0
        # 화학물질은 수치 속성이 많아 복잡 - 기본값 사용
        return attrs

    def encode_star(self, triples):
        """0x0C Star: 48비트"""
        attrs = 0

        # constellation (7비트, offset 0)
        const = self._get_prop(triples, 'P59')
        if const:
            code = self.constellation_map.get(const, 0)
            attrs |= (code & 0x7F)

        # spectral_type (4비트, offset 7)
        spec = self._get_prop(triples, 'P215')
        if spec:
            for prefix in self.spectral_map:
                if spec.startswith(prefix):
                    attrs |= (self.spectral_map[prefix] & 0xF) << 7
                    break

        return attrs

    def encode_galaxy(self, triples):
        """0x0D Galaxy: 48비트"""
        attrs = 0

        # constellation (7비트, offset 0)
        const = self._get_prop(triples, 'P59')
        if const:
            code = self.constellation_map.get(const, 0)
            attrs |= (code & 0x7F)

        # morphology (4비트, offset 7)
        morph = self._get_prop(triples, 'P223')
        if morph:
            for key in self.morphology_map:
                if key in morph:
                    attrs |= (self.morphology_map[key] & 0xF) << 7
                    break

        return attrs

    def encode_settlement(self, triples):
        """0x1C Settlement (및 유사 지형): 48비트"""
        attrs = 0

        # country (8비트, offset 0)
        country = self._get_prop(triples, 'P17')
        if country:
            code = self._lookup_codebook('country', country)
            attrs |= (code & 0xFF)

        # admin (8비트, offset 8)
        admin = self._get_prop(triples, 'P131')
        if admin:
            code = self._lookup_codebook('admin', admin)
            attrs |= (code & 0xFF) << 8

        # coordinates → lat_zone, lon_zone
        coords = self._get_prop(triples, 'P625')
        lat, lon = self._parse_coords(coords)
        attrs |= (self._encode_lat_zone(lat) & 0xF) << 16
        attrs |= (self._encode_lon_zone(lon) & 0xF) << 20

        # population (4비트, offset 24)
        pop_str = self._get_prop(triples, 'P1082')
        if pop_str:
            try:
                pop = int(float(pop_str))
                attrs |= (self._encode_population(pop) & 0xF) << 24
            except:
                pass

        # elevation (5비트, offset 28)
        elev_str = self._get_prop(triples, 'P2044')
        if elev_str:
            try:
                elev = float(elev_str)
                attrs |= (self._encode_elevation(elev) & 0x1F) << 28
            except:
                pass

        return attrs

    def encode_building(self, triples):
        """0x24 Building: 48비트"""
        attrs = 0

        # country (8비트, offset 0)
        country = self._get_prop(triples, 'P17')
        if country:
            code = self._lookup_codebook('country', country)
            attrs |= (code & 0xFF)

        # admin (8비트, offset 8)
        admin = self._get_prop(triples, 'P131')
        if admin:
            code = self._lookup_codebook('admin', admin)
            attrs |= (code & 0xFF) << 8

        # era (4비트, offset 16)
        built = self._get_prop(triples, 'P571')
        year = self._parse_year(built)
        attrs |= (self._encode_era(year) & 0xF) << 16

        # style (4비트, offset 20)
        style = self._get_prop(triples, 'P149')
        if style:
            code = self.style_map.get(style, 0)
            attrs |= (code & 0xF) << 20

        return attrs

    def encode_organization(self, triples):
        """0x2C Organization: 48비트"""
        attrs = 0

        # country (8비트, offset 0)
        country = self._get_prop(triples, 'P17')
        if country:
            code = self._lookup_codebook('country', country)
            attrs |= (code & 0xFF)

        # legal_form (6비트, offset 8)
        form = self._get_prop(triples, 'P1454')
        if form:
            code = self.legal_form_map.get(form, 0)
            attrs |= (code & 0x3F) << 8

        # industry (8비트, offset 14)
        ind = self._get_prop(triples, 'P452')
        if ind:
            code = self.industry_map.get(ind, 0)
            attrs |= (code & 0xFF) << 14

        # founded era (4비트, offset 22)
        founded = self._get_prop(triples, 'P571')
        year = self._parse_year(founded)
        attrs |= (self._encode_era(year) & 0xF) << 22

        return attrs

    def encode_document(self, triples):
        """0x31 Document: 48비트"""
        attrs = 0

        # country (8비트, offset 0)
        country = self._get_prop(triples, 'P495')
        if country:
            code = self._lookup_codebook('country', country)
            attrs |= (code & 0xFF)

        # era (4비트, offset 8)
        pub = self._get_prop(triples, 'P577')
        year = self._parse_year(pub)
        attrs |= (self._encode_era(year) & 0xF) << 8

        # language (6비트, offset 12)
        lang = self._get_prop(triples, 'P407')
        if lang:
            code = self._lookup_codebook('language', lang)
            attrs |= (code & 0x3F) << 12

        # genre (6비트, offset 18)
        genre = self._get_prop(triples, 'P136')
        if genre:
            code = self._lookup_codebook('genre', genre)
            attrs |= (code & 0x3F) << 18

        return attrs

    def encode_creative_work(self, triples):
        """창작물 공통 (0x30 Painting, 0x32-0x38): 48비트"""
        attrs = 0

        # country (8비트, offset 0)
        country = self._get_prop(triples, 'P495')
        if country:
            code = self._lookup_codebook('country', country)
            attrs |= (code & 0xFF)

        # era (4비트, offset 8)
        pub = self._get_prop(triples, 'P577') or self._get_prop(triples, 'P571')
        year = self._parse_year(pub)
        attrs |= (self._encode_era(year) & 0xF) << 8

        # genre (6비트, offset 12)
        genre = self._get_prop(triples, 'P136')
        if genre:
            code = self._lookup_codebook('genre', genre)
            attrs |= (code & 0x3F) << 12

        # language (6비트, offset 18)
        lang = self._get_prop(triples, 'P407') or self._get_prop(triples, 'P364')
        if lang:
            code = self._lookup_codebook('language', lang)
            attrs |= (code & 0x3F) << 18

        return attrs

    def encode_video_game(self, triples):
        """0x37 VideoGame: 48비트"""
        attrs = self.encode_creative_work(triples)

        # platform (5비트, offset 24)
        platform = self._get_prop(triples, 'P400')
        if platform:
            code = self.platform_map.get(platform, 0)
            attrs |= (code & 0x1F) << 24

        return attrs

    def encode_software(self, triples):
        """0x3A Software: 48비트"""
        attrs = 0

        # country (8비트, offset 0)
        country = self._get_prop(triples, 'P495')
        if country:
            code = self._lookup_codebook('country', country)
            attrs |= (code & 0xFF)

        # era (4비트, offset 8)
        pub = self._get_prop(triples, 'P577')
        year = self._parse_year(pub)
        attrs |= (self._encode_era(year) & 0xF) << 8

        # prog_lang (5비트, offset 12)
        pl = self._get_prop(triples, 'P277')
        if pl:
            code = self.prog_lang_map.get(pl, 0)
            attrs |= (code & 0x1F) << 12

        return attrs

    def encode_sports_team(self, triples):
        """0x2F SportsTeam: 48비트"""
        attrs = 0

        # country (8비트, offset 0)
        country = self._get_prop(triples, 'P17')
        if country:
            code = self._lookup_codebook('country', country)
            attrs |= (code & 0xFF)

        # sport (5비트, offset 8)
        sport = self._get_prop(triples, 'P641')
        if sport:
            code = self.sport_map.get(sport, 0)
            attrs |= (code & 0x1F) << 8

        # founded era (4비트, offset 13)
        founded = self._get_prop(triples, 'P571')
        year = self._parse_year(founded)
        attrs |= (self._encode_era(year) & 0xF) << 13

        return attrs

    def encode_event(self, triples):
        """0x3D Event: 48비트"""
        attrs = 0

        # country (8비트, offset 0)
        country = self._get_prop(triples, 'P17')
        if country:
            code = self._lookup_codebook('country', country)
            attrs |= (code & 0xFF)

        # era (4비트, offset 8)
        start = self._get_prop(triples, 'P580')
        year = self._parse_year(start)
        attrs |= (self._encode_era(year) & 0xF) << 8

        return attrs

    def encode_attrs(self, entity_type, triples):
        """EntityType별 속성 인코딩 라우터"""
        # 트리플을 (property, value) 튜플 리스트로 변환
        triple_list = [(p, v) for s, p, v in triples]

        if entity_type == 0x00:  # Human
            return self.encode_human(triple_list)
        elif entity_type == 0x01:  # Taxon
            return self.encode_taxon(triple_list)
        elif entity_type == 0x02:  # Gene
            return self.encode_gene(triple_list)
        elif entity_type == 0x03:  # Protein
            return self.encode_protein(triple_list)
        elif entity_type == 0x08:  # Chemical
            return self.encode_chemical(triple_list)
        elif entity_type == 0x0C:  # Star
            return self.encode_star(triple_list)
        elif entity_type == 0x0D:  # Galaxy
            return self.encode_galaxy(triple_list)
        elif entity_type in [0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B]:  # 지형
            return self.encode_settlement(triple_list)
        elif entity_type in [0x1C, 0x1D, 0x1E, 0x1F, 0x20, 0x21, 0x22, 0x23]:  # 행정/장소
            return self.encode_settlement(triple_list)
        elif entity_type in [0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x2B]:  # 건축물
            return self.encode_building(triple_list)
        elif entity_type == 0x2C:  # Organization
            return self.encode_organization(triple_list)
        elif entity_type == 0x2D:  # Business
            return self.encode_organization(triple_list)
        elif entity_type == 0x2F:  # SportsTeam
            return self.encode_sports_team(triple_list)
        elif entity_type == 0x30:  # Painting
            return self.encode_creative_work(triple_list)
        elif entity_type == 0x31:  # Document
            return self.encode_document(triple_list)
        elif entity_type in [0x32, 0x33, 0x34, 0x35, 0x36, 0x38]:  # 창작물
            return self.encode_creative_work(triple_list)
        elif entity_type == 0x37:  # VideoGame
            return self.encode_video_game(triple_list)
        elif entity_type == 0x3A:  # Software
            return self.encode_software(triple_list)
        elif entity_type in [0x3C, 0x3D, 0x3E]:  # Event
            return self.encode_event(triple_list)
        else:
            return 0  # Other


def main():
    print("=" * 70)
    print("GEUL Entity SIDX 64비트 전체 인코딩")
    print("=" * 70)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ref_dir = os.path.join(base_dir, 'references')

    # 1. 인코더 초기화
    print("\n[1/5] 인코더 초기화...")
    encoder = SIDXEncoder(ref_dir)
    print(f"  - 타입 매핑: {len(encoder.type_map)}개")
    print(f"  - 코드북: {len(encoder.codebook_maps)}개")

    # 2. DB 연결
    print("\n[2/5] DB 연결...")
    read_conn = psycopg2.connect('postgresql://geul_reader:test1224@localhost:5432/geuldev')
    write_conn = psycopg2.connect('postgresql://geul_writer:test1224@localhost:5432/geulwork')
    read_cur = read_conn.cursor()
    write_cur = write_conn.cursor()

    # 전체 개체 수
    read_cur.execute("SELECT COUNT(*) FROM entities")
    total_count = read_cur.fetchone()[0]
    print(f"  - 전체 개체: {total_count:,}개")

    # 기존 테이블 초기화
    write_cur.execute("TRUNCATE TABLE entity_sidx")
    write_conn.commit()
    print("  - entity_sidx 테이블 초기화")

    # 3. 전체 인코딩
    print(f"\n[3/5] 전체 인코딩 시작 (배치 크기: {BATCH_SIZE:,})...")
    start_time = datetime.now()

    processed = 0
    encoded = 0
    skipped = 0
    with_attrs = 0
    offset = 0

    # 속성 문자열
    props_str = ','.join([f"'{p}'" for p in ALL_PROPERTIES])

    while True:
        # 엔티티 배치 가져오기
        read_cur.execute(f"""
            SELECT id FROM entities
            ORDER BY id
            OFFSET {offset} LIMIT {BATCH_SIZE}
        """)
        entities = [r[0] for r in read_cur.fetchall()]

        if not entities:
            break

        # P31 값 조회
        read_cur.execute("""
            SELECT subject, object_value
            FROM triples
            WHERE subject IN %s AND property = 'P31'
        """, (tuple(entities),))

        p31_map = {}
        for subj, obj in read_cur.fetchall():
            if subj not in p31_map:
                p31_map[subj] = []
            p31_map[subj].append(obj)

        # 모든 속성 조회
        read_cur.execute(f"""
            SELECT subject, property, object_value
            FROM triples
            WHERE subject IN %s AND property IN ({props_str})
        """, (tuple(entities),))

        triples_map = {}
        for subj, prop, obj in read_cur.fetchall():
            if subj not in triples_map:
                triples_map[subj] = []
            triples_map[subj].append((subj, prop, obj))

        # SIDX 생성
        results = []
        for qid in entities:
            p31_list = p31_map.get(qid, [])

            # EntityType 결정
            entity_type = 0x3F  # 기본 Other
            for p31 in p31_list:
                if p31 in encoder.exclude_qids:
                    entity_type = None
                    break
                if p31 in encoder.type_map:
                    entity_type = encoder.type_map[p31]
                    break

            if entity_type is None:
                skipped += 1
                continue

            # 속성 인코딩
            triples = triples_map.get(qid, [])
            attrs = encoder.encode_attrs(entity_type, triples)

            if attrs > 0:
                with_attrs += 1

            # SIDX 조립
            word1 = (SIDX_PREFIX << 9) | (DEFAULT_MODE << 6) | entity_type
            sidx = (word1 << 48) | attrs

            results.append((qid, sidx, entity_type, DEFAULT_MODE, attrs))
            encoded += 1

        # 벌크 인서트
        if results:
            execute_values(write_cur, """
                INSERT INTO entity_sidx (qid, sidx, entity_type, mode, attrs)
                VALUES %s
                ON CONFLICT (qid) DO NOTHING
            """, results, page_size=5000)
            write_conn.commit()

        processed += len(entities)
        offset += len(entities)

        # 진행률
        pct = processed / total_count * 100
        if processed % (BATCH_SIZE * 20) == 0 or processed >= total_count:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total_count - processed) / rate / 60 if rate > 0 else 0
            attr_pct = with_attrs / encoded * 100 if encoded > 0 else 0
            print(f"\r  [{pct:5.1f}%] {processed:,}/{total_count:,} | "
                  f"인코딩: {encoded:,} | 속성채움: {with_attrs:,} ({attr_pct:.1f}%) | "
                  f"속도: {rate:.0f}/s | ETA: {eta:.0f}분", end='', flush=True)

    # 4. 완료
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n\n[4/5] 인코딩 완료!")
    print("=" * 70)
    print(f"  처리: {processed:,}개")
    print(f"  인코딩: {encoded:,}개")
    print(f"  속성 채움: {with_attrs:,}개 ({with_attrs/encoded*100:.1f}%)")
    print(f"  제외(Wikimedia): {skipped:,}개")
    print(f"  소요시간: {elapsed/60:.1f}분 ({elapsed:.0f}초)")
    print(f"  평균속도: {processed/elapsed:.0f}개/초")

    # 5. 결과 확인
    print(f"\n[5/5] 결과 확인...")
    write_cur.execute("SELECT COUNT(*) FROM entity_sidx")
    final_count = write_cur.fetchone()[0]
    print(f"  entity_sidx 테이블: {final_count:,}개")

    write_cur.execute("SELECT COUNT(*) FROM entity_sidx WHERE attrs > 0")
    attrs_count = write_cur.fetchone()[0]
    print(f"  속성 있는 개체: {attrs_count:,}개 ({attrs_count/final_count*100:.1f}%)")

    # 타입별 통계
    write_cur.execute("""
        SELECT entity_type, COUNT(*) as cnt,
               SUM(CASE WHEN attrs > 0 THEN 1 ELSE 0 END) as with_attrs
        FROM entity_sidx
        GROUP BY entity_type
        ORDER BY cnt DESC
        LIMIT 10
    """)
    print("\n  상위 10개 타입:")
    for row in write_cur.fetchall():
        et, cnt, wa = row
        pct = wa/cnt*100 if cnt > 0 else 0
        print(f"    0x{et:02X}: {cnt:>12,}개 (속성: {wa:>10,}, {pct:>5.1f}%)")

    # 샘플
    print("\n  샘플 SIDX:")
    write_cur.execute("""
        SELECT qid, sidx, entity_type, attrs FROM entity_sidx
        WHERE attrs > 0
        LIMIT 5
    """)
    for qid, sidx, et, attrs in write_cur.fetchall():
        print(f"    {qid}: 0x{sidx:016X} (type=0x{et:02X}, attrs=0x{attrs:012X})")

    read_conn.close()
    write_conn.close()
    print("\n완료!")


if __name__ == '__main__':
    main()
