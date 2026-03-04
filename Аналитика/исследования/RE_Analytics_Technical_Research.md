# Real Estate Analytics & Valuation System — Technical Research Report

**Date**: 2026-03-01
**Scope**: Russia (Perm region focus), MVP architecture, data sources, valuation algorithms

---

## Table of Contents

1. [Data Sources for Russia](#1-data-sources-for-russia)
2. [Technical Architecture for MVP](#2-technical-architecture-for-mvp)
3. [Valuation Algorithm Design](#3-valuation-algorithm-design)
4. [Existing Open Source Tools](#4-existing-open-source-tools)
5. [n8n Feasibility Assessment](#5-n8n-feasibility-assessment)
6. [Recommended MVP Roadmap](#6-recommended-mvp-roadmap)

---

## 1. Data Sources for Russia

### 1.1 Avito (avito.ru)

**Type**: Classifieds marketplace (largest in Russia)
**Official API**: No public real estate API. Avito has an official API only for professional sellers (Avito Pro), not for data consumers.
**Scraping feasibility**: HIGH — multiple proven solutions exist.

**Available approaches**:
- **Apify scrapers**: Multiple ready-made actors (ScrapStorm, FatihTahta, SongD). Cost ~$4/1k listings. Return JSON with price, location, description, seller info, images, publication date.
- **Custom scraping**: Avito uses client-side rendering + anti-bot (fingerprinting, rate limits, captcha). Requires: rotating residential proxies, Playwright/Puppeteer with stealth plugins, realistic delays (3-10 sec between requests).
- **RSS/search feeds**: Avito provides RSS for saved searches — lightweight alternative for monitoring new listings, but limited data per listing.

**Data fields available**: Title, price, address (often district-level, not exact), rooms, area (sqm), floor/total floors, description text, photos, publication date, seller type (owner/agent), views count.

**Perm region coverage**: Good. Avito is the primary platform for secondary market in Perm. Expect 2,000-5,000 active RE listings at any time.

**Limitations**:
- No exact coordinates (only city/district)
- Prices are asking prices, not transaction prices
- No historical sold prices
- Anti-bot protection is moderate but increasing (as of 2025-2026)
- Legal gray area for scraping

---

### 1.2 CIAN (cian.ru)

**Type**: Specialized real estate portal (largest in Russia for RE)
**Official API**: No public API for data consumers. CIAN uses internal microservice APIs documented with Swagger for their own frontend, but these are undocumented externally and subject to change.
**Scraping feasibility**: MEDIUM-HIGH

**Available approaches**:
- **Apify scrapers**: `igolaizola/cian-ru-scraper` — extracts apartments, houses, commercial across all regions
- **ZenRows**: Dedicated CIAN scraper with anti-bot bypass
- **Custom scraping**: CIAN uses React SSR. Internal API endpoints can be reverse-engineered from network requests (e.g., `https://api.cian.ru/search-offers/v2/search-offers-desktop/`). Anti-bot protection is moderate (Cloudflare-like).

**Data fields available**: Price, exact address, coordinates (lat/lng), rooms, total area, living area, kitchen area, floor/total floors, building type (panel/brick/monolith), year built, ceiling height, renovation type, balcony, bathroom, photos, description, agent/owner flag, price history (sometimes), mortgage calculator data.

**Key advantage over Avito**: CIAN provides **exact coordinates** and more structured property attributes. Also has **price history** for some listings (price changes over time).

**Perm region coverage**: Good but smaller than Avito. CIAN is stronger in Moscow/SPb, but has decent coverage in Perm (1,000-3,000 active listings).

**Limitations**:
- Anti-bot protection is tighter than Avito
- Rate limiting is aggressive
- No transaction/sold price data (only asking prices)
- Internal API structure changes frequently

---

### 1.3 Rosreestr (rosreestr.gov.ru)

**Type**: Federal Service for State Registration, Cadastre and Cartography — the **official land registry** of Russia.

**Public data available**:
- **EGRN extracts** (Выписки ЕГРН): Ownership data, encumbrances, transaction history — BUT requires paid requests (250-2000 RUB per extract). Not suitable for bulk data collection.
- **Public Cadastral Map** (PKK): See section 1.4
- **Cadastral value** (кадастровая стоимость): Publicly available per cadastral number. Updated every 3-5 years by region.

**API availability**:
- `rosreestr.gov.ru/api` — limited, mostly for searching objects by address
- `pkk.rosreestr.ru/api` — unofficial but functional (see 1.4)
- `rosreestr.gov.ru/wps/portal/p/cc_egrn_5` — EGRN extracts (paid, XML response)

**FIAS (Federal Information Address System)**:
- Replaced KLADR since January 1, 2018
- Full database downloadable from `fias.nalog.ru/Updates.aspx` (~5GB)
- Contains: all addresses in Russia, FIAS GUID, house numbers, postal codes
- Does NOT contain coordinates (addresses only)
- Update frequency: ~daily
- **Python library**: `gar-reader` for parsing FIAS/GAR XML dumps

**Practical use for valuation**:
- **Cadastral value** — free baseline for any property (often 20-40% below market, but useful as floor estimate)
- **FIAS** — address normalization and deduplication (matching addresses across sources)
- **EGRN bulk** — not practical due to per-request cost and no bulk API

---

### 1.4 Public Cadastral Map (PKK — pkk.rosreestr.ru)

**Type**: Interactive map with cadastral data for all registered real estate in Russia.

**Data available per cadastral number**:
- Cadastral number (e.g., 59:01:4410601:123)
- Object type (land plot, building, apartment, etc.)
- Address
- Cadastral value (in RUB)
- Area (sqm)
- Permitted use (for land plots)
- Category of land
- Registration date
- GeoJSON boundaries (polygon geometry for land plots)

**API access**:
- `https://pkk.rosreestr.ru/api/features/{type}?text={cadastral_number}` — search by cadastral number
- `https://pkk.rosreestr.ru/api/features/{type}?sq={"type":"Point","coordinates":[lon,lat]}` — search by coordinates
- Types: 1=land plots, 5=buildings, etc.

**Python tools**:
- `rosreestr-api` (GregEremeev, 60+ stars) — works with both rosreestr.ru/api and pkk.rosreestr.ru/api
- `getpkk` (rendrom) — computes parcel coordinates by cadastral number, updated 2025
- `rosreestr_loader` (ArtUshak) — bulk data loading from Rosreestr API

**Perm region**: Full coverage. All registered properties in Perm Oblast (region code 59) are in the system.

**Limitations**:
- Rate limiting (IP-based, ~1 req/sec sustainable)
- No official API documentation (reverse-engineered)
- Cadastral values are outdated in many regions (last mass assessment varies)
- No market/transaction prices — only cadastral (tax) values
- API endpoints may change without notice

---

### 1.5 torgi.gov.ru (Government Auctions)

**Type**: Official government auction platform for state/municipal property.

**Data structure**:
- **Categories**: Real estate (code 22), land plots, vehicles, other assets
- **Lot data**: Object description, starting price, step %, deposit amount, auction date/time, organizer, legal basis, region, status
- **Open data endpoint**: `torgi.gov.ru/opendata/` — XML format
- **Excel export**: `torgi.gov.ru/new/api/public/lotcards/export/excel?catCode=22&...`
- **Bulk download**: `torgi.zip` file with all current lots, updated several times daily
- **Individual lot JSON**: Available via lot URL + API

**Scraping feasibility**: HIGH — the platform actively provides open data.

**Practical use**:
- Starting prices for auctions (often 10-30% below cadastral value)
- Property descriptions and documentation
- Historical auction results (sold/not sold, final prices)
- Regional filtering available

**Perm region coverage**: Moderate. State property auctions in Perm Oblast appear regularly, but volume is much lower than classifieds (dozens vs thousands).

---

### 1.6 Bankruptcy Platforms (tbankrot.ru, bankrot.fedresurs.ru)

**Type**: Platforms aggregating bankruptcy proceedings and asset sales.

**tbankrot.ru**:
- Aggregator of bankruptcy lot data, likely scrapes EFRSB (Единый федеральный реестр сведений о банкротстве)
- No public API
- Scraping feasibility: MEDIUM (standard server-rendered HTML)
- Data: lot descriptions, starting prices, auction platform links, debtor info

**bankrot.fedresurs.ru (EFRSB)**:
- Official federal resource for bankruptcy information
- Has an API: `https://bankrot.fedresurs.ru/api/` (limited documentation)
- Contains: all auction messages, debtor info, asset descriptions
- More reliable than tbankrot.ru but harder to parse

**Practical use for RE valuation**:
- Distressed properties typically sell at 20-50% discount to market
- Useful for finding deals, not for market valuation baseline
- Helps estimate "liquidation value" vs "market value" spread

---

### 1.7 DomClick (domclick.ru)

**Type**: Sberbank's real estate platform (largest bank-affiliated RE portal).

**Unique data advantages**:
- **EGRN verification status** — DomClick verifies listings against Rosreestr
- **Mortgage pre-approval data** — knows what banks will finance
- **AI renovation scores** — automated property condition assessment
- **Seller phone numbers** (unmasked)
- **Discount history** — tracks price reductions

**Scraping feasibility**: MEDIUM
- Apify has dedicated `domclick-search-scraper`
- Anti-bot protection: moderate (browser fingerprinting)
- Data quality is higher than Avito due to Sberbank verification

**Perm region coverage**: Good — Sberbank is present everywhere.

---

### 1.8 Yandex Realty (realty.ya.ru, formerly realty.yandex.ru)

**Type**: Yandex's real estate vertical.

**API access**: Semi-public internal API:
```
https://realty.yandex.ru/gate/react-page/get/?rgid=187&type=SELL&category=APARTMENT&_format=react&page=1
```
Requires cookies from a browser session.

**Scraping feasibility**: MEDIUM
- `yarealty` (GitHub, mixartemev) — Yandex Realty crawler in PHP
- Standard web scraping with session cookies works
- Anti-bot: moderate (Yandex SmartCaptcha)

**Unique data**: Yandex has its own price prediction model ("Оценка Яндекса") — visible on listing pages. Interesting for benchmarking your own model.

**Perm region coverage**: Lower than Avito/CIAN. Yandex Realty is weakest in regions.

---

### 1.9 Data Source Summary Table

| Source | Official API | Scraping | Asking Price | Sold Price | Coordinates | Perm Coverage | Priority |
|--------|-------------|----------|--------------|------------|-------------|---------------|----------|
| Avito | No | High | Yes | No | No (district) | High | **P0** |
| CIAN | No | Medium-High | Yes | No | Yes | Medium | **P0** |
| PKK/Rosreestr | Unofficial | High | No | No (cadastral) | Yes | Full | **P1** |
| DomClick | No | Medium | Yes | No | Yes | Good | P1 |
| torgi.gov.ru | XML/Excel | High | Yes (start) | Yes (result) | No | Low volume | P2 |
| EFRSB | Limited | Medium | Yes (start) | Yes (result) | No | Low volume | P2 |
| Yandex Realty | Unofficial | Medium | Yes | No | Yes | Low | P3 |
| FIAS | Download | N/A | N/A | N/A | No | Full | P1 (addresses) |

---

## 2. Technical Architecture for MVP

### 2.1 Recommended Stack

```
┌─────────────────────────────────────────────────────┐
│                   DATA COLLECTION                     │
│  Python (Scrapy + Playwright) → Scheduler (cron)      │
│  Sources: Avito, CIAN, DomClick, PKK                  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                   DATA PIPELINE                       │
│  Address normalization (DaData API)                   │
│  Deduplication (fuzzy matching + geo proximity)       │
│  Feature extraction (NLP on descriptions)             │
│  Geocoding (DaData / Yandex Geocoder)                │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                   STORAGE                             │
│  PostgreSQL + PostGIS                                 │
│  Tables: properties, price_history, sources,          │
│          districts, buildings, valuations             │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                   ANALYTICS                           │
│  Python (pandas, scikit-learn, XGBoost)              │
│  Comparable sales engine                              │
│  Price per sqm heatmaps                              │
│  Valuation model (gradient boosting)                 │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                   OUTPUT                              │
│  Telegram bot (alerts, reports)                       │
│  Web dashboard (Streamlit / Grafana)                 │
│  n8n (orchestration, notifications)                  │
└─────────────────────────────────────────────────────┘
```

### 2.2 Database Choice: PostgreSQL + PostGIS

**Why PostgreSQL + PostGIS** (not MongoDB):
- **Spatial queries** are critical for RE (find comparable properties within 500m radius, district-level aggregations, heatmaps)
- PostGIS handles `ST_DWithin`, `ST_Distance`, `ST_Contains` natively
- Strong typing prevents data quality issues (important when ingesting from multiple sources)
- JSONB columns for semi-structured data (descriptions, raw scrape data) give MongoDB-like flexibility where needed
- Better analytical query performance (window functions for price trends, CTEs for complex comparisons)
- Mature ecosystem: pgAdmin, psql, great Python drivers (asyncpg, psycopg2)

**MongoDB alternative**: Only consider if data schema is extremely unstable in early exploration phase. Not recommended for production analytics.

### 2.3 Database Schema Design

```sql
-- Core property table
CREATE TABLE properties (
    id              BIGSERIAL PRIMARY KEY,

    -- Identity & dedup
    canonical_id    UUID NOT NULL DEFAULT gen_random_uuid(),  -- stable ID after dedup
    source          VARCHAR(20) NOT NULL,  -- 'avito', 'cian', 'domclick', 'pkk'
    source_id       VARCHAR(100) NOT NULL, -- ID on source platform
    source_url      TEXT,

    -- Address (normalized)
    raw_address     TEXT,
    normalized_address TEXT,          -- from DaData
    fias_id         VARCHAR(36),      -- FIAS GUID
    cadastral_number VARCHAR(25),     -- e.g., 59:01:4410601:123
    region          VARCHAR(100),     -- 'Пермский край'
    city            VARCHAR(100),     -- 'Пермь'
    district        VARCHAR(100),     -- 'Ленинский район'
    microdistrict   VARCHAR(200),     -- 'Центр', 'Парковый'
    street          VARCHAR(200),
    house_number    VARCHAR(20),
    apartment_number VARCHAR(20),

    -- Geolocation
    location        GEOMETRY(Point, 4326),  -- PostGIS point (SRID 4326 = WGS84)
    lat             DECIMAL(9,6),
    lng             DECIMAL(9,6),

    -- Property attributes
    property_type   VARCHAR(30),  -- 'apartment', 'house', 'land', 'commercial'
    rooms           SMALLINT,
    total_area_sqm  DECIMAL(8,2),
    living_area_sqm DECIMAL(8,2),
    kitchen_area_sqm DECIMAL(8,2),
    floor           SMALLINT,
    total_floors    SMALLINT,
    building_type   VARCHAR(30),  -- 'panel', 'brick', 'monolith', 'wood'
    year_built      SMALLINT,
    renovation      VARCHAR(30),  -- 'cosmetic', 'euro', 'designer', 'none', 'rough'
    balcony         VARCHAR(30),  -- 'balcony', 'loggia', 'none'
    bathroom        VARCHAR(30),  -- 'combined', 'separate'
    ceiling_height  DECIMAL(3,2),

    -- Pricing
    asking_price    BIGINT,       -- in RUB
    price_per_sqm   BIGINT GENERATED ALWAYS AS (
        CASE WHEN total_area_sqm > 0
             THEN asking_price / total_area_sqm
             ELSE NULL END
    ) STORED,
    cadastral_value BIGINT,       -- from Rosreestr

    -- Metadata
    seller_type     VARCHAR(20),  -- 'owner', 'agent', 'developer'
    listing_date    DATE,
    last_seen_date  DATE,
    is_active       BOOLEAN DEFAULT TRUE,
    description     TEXT,
    photos_count    SMALLINT,

    -- Raw data
    raw_data        JSONB,        -- original scraped JSON

    -- Timestamps
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (source, source_id)
);

-- Spatial index
CREATE INDEX idx_properties_location ON properties USING GIST (location);
-- Search indexes
CREATE INDEX idx_properties_city ON properties (city);
CREATE INDEX idx_properties_type ON properties (property_type);
CREATE INDEX idx_properties_price ON properties (asking_price);
CREATE INDEX idx_properties_active ON properties (is_active) WHERE is_active = TRUE;
CREATE INDEX idx_properties_canonical ON properties (canonical_id);

-- Price history (track changes over time)
CREATE TABLE price_history (
    id              BIGSERIAL PRIMARY KEY,
    property_id     BIGINT REFERENCES properties(id),
    price           BIGINT NOT NULL,
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Deduplication mapping (same property across sources)
CREATE TABLE property_matches (
    id              BIGSERIAL PRIMARY KEY,
    canonical_id    UUID NOT NULL,
    property_id     BIGINT REFERENCES properties(id),
    confidence      DECIMAL(3,2),  -- 0.00 to 1.00
    match_method    VARCHAR(30),   -- 'address_exact', 'geo_fuzzy', 'cadastral'
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (property_id)
);

-- District/neighborhood aggregates (materialized for performance)
CREATE MATERIALIZED VIEW district_stats AS
SELECT
    city,
    district,
    property_type,
    rooms,
    COUNT(*) as listing_count,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_sqm) as median_price_sqm,
    AVG(price_per_sqm) as avg_price_sqm,
    MIN(price_per_sqm) as min_price_sqm,
    MAX(price_per_sqm) as max_price_sqm,
    STDDEV(price_per_sqm) as stddev_price_sqm
FROM properties
WHERE is_active = TRUE AND price_per_sqm IS NOT NULL
GROUP BY city, district, property_type, rooms;

-- Valuations log
CREATE TABLE valuations (
    id              BIGSERIAL PRIMARY KEY,
    property_id     BIGINT REFERENCES properties(id),
    estimated_value BIGINT,
    confidence_low  BIGINT,       -- 10th percentile
    confidence_high BIGINT,       -- 90th percentile
    method          VARCHAR(30),  -- 'comparable_sales', 'ml_model', 'price_sqm'
    comparables     JSONB,        -- array of comparable property IDs + adjustments
    model_version   VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.4 Cross-Source Deduplication

Same property appears on Avito, CIAN, and DomClick simultaneously. Deduplication strategy:

**Level 1 — Exact match (cheapest)**:
- Match by `cadastral_number` (if available from DomClick/PKK)
- Match by exact normalized address + apartment number

**Level 2 — Fuzzy address match**:
- Normalize addresses via DaData API (returns FIAS GUID)
- Match by `fias_id` (building-level GUID)
- Within same building: match by floor + area + rooms

**Level 3 — Geo-proximity + attributes**:
```sql
-- Find potential duplicates within 100m with similar attributes
SELECT a.id, b.id, ST_Distance(a.location, b.location) as dist
FROM properties a, properties b
WHERE a.id < b.id
  AND ST_DWithin(a.location::geography, b.location::geography, 100)
  AND a.rooms = b.rooms
  AND ABS(a.total_area_sqm - b.total_area_sqm) < 3
  AND ABS(a.asking_price - b.asking_price) / GREATEST(a.asking_price, 1) < 0.15;
```

**Level 4 — NLP on descriptions**:
- TF-IDF or sentence embeddings on description text
- Cosine similarity > 0.85 between listings at same address = likely duplicate

**Recommended approach**: Pipeline: L1 → L2 → L3 → manual review for L4. Start with L1+L2, add L3 when you have geo data.

### 2.5 Address Normalization & Geocoding

**Primary tool: DaData.ru API**

- **Pricing**: Free tier = 10,000 requests/day (address suggestions). Paid plans from ~$65/year.
- **Capabilities**:
  - Input: messy Russian address string (e.g., "Пермь, Компрос 48, кв 12")
  - Output: structured fields (region, city, street, house, apartment, postal code, FIAS GUID, OKATO, OKTMO)
  - Geocoding: returns lat/lng coordinates
  - Quality score: confidence level of parsing
- **Python client**: `pip install dadata` (official, by hflabs)

**Alternative: Yandex Geocoder API**
- 1,000 free requests/day, then paid
- Better geocoding accuracy than DaData for some edge cases
- Does not do address normalization (only forward/reverse geocoding)

**Alternative: Nominatim (OpenStreetMap)**
- Free and self-hostable
- Russian address support is historically **poor** (diverse nomenclature, informal formats)
- Not recommended as primary geocoder for Russia. Useful as fallback only.

**FIAS database** (offline, for normalization without API):
- Download full dump from `fias.nalog.ru`
- Import into PostgreSQL (~5GB, ~30M address records)
- Use for offline address validation and FIAS GUID lookup
- No coordinates — must combine with geocoding API

**Recommended approach**:
1. DaData API for normalization + geocoding (primary)
2. FIAS local database for validation and fallback
3. Yandex Geocoder as secondary geocoder for failed DaData lookups

---

## 3. Valuation Algorithm Design

### 3.1 Comparable Sales Approach (Automated)

The comparable sales method is the most practical starting point for RE valuation. Here is how to automate it:

**Step 1: Select comparables**
```python
def find_comparables(target_property, db_connection, max_distance_m=1500, max_results=10):
    """
    Find comparable properties for valuation.
    Priority: same building > same microdistrict > same district
    """
    query = """
    SELECT p.*,
           ST_Distance(p.location::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) as distance_m,
           ABS(p.total_area_sqm - %s) / GREATEST(%s, 1) as area_diff_pct,
           CASE WHEN p.rooms = %s THEN 0 ELSE 1 END as room_diff
    FROM properties p
    WHERE p.is_active = TRUE
      AND p.property_type = %s
      AND p.city = %s
      AND ST_DWithin(p.location::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)
      AND p.total_area_sqm BETWEEN %s * 0.7 AND %s * 1.3
      AND p.id != %s
    ORDER BY
        room_diff ASC,
        distance_m ASC,
        area_diff_pct ASC
    LIMIT %s
    """
    # Execute with target property parameters
    return execute(query, params)
```

**Step 2: Calculate adjustment coefficients**
```python
ADJUSTMENT_FACTORS = {
    'floor': {
        'first': -0.05,      # -5% for ground floor
        'last': -0.03,       # -3% for top floor (leaks risk)
        'middle': 0.0,       # baseline
    },
    'renovation': {
        'designer': +0.15,   # +15%
        'euro': +0.08,
        'cosmetic': 0.0,     # baseline
        'none': -0.10,
        'rough': -0.15,
    },
    'building_type': {
        'monolith': +0.05,
        'brick': +0.03,
        'panel': 0.0,        # baseline
        'wood': -0.10,
    },
    'balcony': {
        'loggia': +0.02,
        'balcony': +0.01,
        'none': -0.02,
    },
    'area_per_sqm_adjustment': 0.0003,  # per sqm difference from target
    'floor_distance_adjustment': 0.005,  # per floor difference
    'age_adjustment': -0.002,            # per year of building age
}

def adjust_comparable_price(comparable, target, factors=ADJUSTMENT_FACTORS):
    """Apply adjustment coefficients to comparable's price."""
    adjusted_price_sqm = comparable.price_per_sqm
    adjustments = {}

    # Floor adjustment
    target_floor_type = classify_floor(target.floor, target.total_floors)
    comp_floor_type = classify_floor(comparable.floor, comparable.total_floors)
    if target_floor_type != comp_floor_type:
        adj = factors['floor'][target_floor_type] - factors['floor'][comp_floor_type]
        adjusted_price_sqm *= (1 + adj)
        adjustments['floor'] = adj

    # Renovation adjustment
    if target.renovation != comparable.renovation:
        adj = (factors['renovation'].get(target.renovation, 0) -
               factors['renovation'].get(comparable.renovation, 0))
        adjusted_price_sqm *= (1 + adj)
        adjustments['renovation'] = adj

    # Building type adjustment
    if target.building_type != comparable.building_type:
        adj = (factors['building_type'].get(target.building_type, 0) -
               factors['building_type'].get(comparable.building_type, 0))
        adjusted_price_sqm *= (1 + adj)
        adjustments['building_type'] = adj

    # Area difference adjustment (larger area = slightly lower per sqm)
    area_diff = target.total_area_sqm - comparable.total_area_sqm
    adj = -area_diff * factors['area_per_sqm_adjustment']
    adjusted_price_sqm *= (1 + adj)
    adjustments['area'] = adj

    return adjusted_price_sqm, adjustments
```

**Step 3: Weighted average of adjusted comparables**
```python
def estimate_value(target, comparables):
    """
    Final valuation = weighted average of adjusted comparable prices.
    Weight = inverse of (distance + attribute difference).
    """
    results = []
    for comp in comparables:
        adj_price_sqm, adjustments = adjust_comparable_price(comp, target)

        # Weight: closer + more similar = higher weight
        similarity = 1.0 / (1.0 + comp.distance_m / 500 + comp.area_diff_pct)
        results.append({
            'comparable_id': comp.id,
            'original_price_sqm': comp.price_per_sqm,
            'adjusted_price_sqm': adj_price_sqm,
            'weight': similarity,
            'adjustments': adjustments,
        })

    total_weight = sum(r['weight'] for r in results)
    estimated_price_sqm = sum(
        r['adjusted_price_sqm'] * r['weight'] / total_weight
        for r in results
    )

    estimated_value = estimated_price_sqm * target.total_area_sqm

    # Confidence interval (based on spread of comparables)
    prices = [r['adjusted_price_sqm'] for r in results]
    std = statistics.stdev(prices) if len(prices) > 1 else prices[0] * 0.1
    confidence_low = (estimated_price_sqm - 1.65 * std) * target.total_area_sqm
    confidence_high = (estimated_price_sqm + 1.65 * std) * target.total_area_sqm

    return {
        'estimated_value': round(estimated_value),
        'confidence_low': round(max(confidence_low, 0)),
        'confidence_high': round(confidence_high),
        'price_per_sqm': round(estimated_price_sqm),
        'comparables_used': len(results),
        'details': results,
    }
```

### 3.2 Feature Engineering for RE Valuation

**Numeric features** (direct from listing):
| Feature | Source | Importance |
|---------|--------|-----------|
| `total_area_sqm` | listing | Very high |
| `rooms` | listing | High |
| `floor` | listing | Medium |
| `total_floors` | listing | Medium |
| `kitchen_area_sqm` | listing | Medium |
| `year_built` | listing/PKK | Medium |
| `ceiling_height` | listing | Low-medium |
| `photos_count` | listing | Low (proxy for quality) |

**Derived features** (calculated):
| Feature | Formula | Rationale |
|---------|---------|-----------|
| `is_first_floor` | floor == 1 | Significant price impact |
| `is_last_floor` | floor == total_floors | Roof leak risk |
| `floor_ratio` | floor / total_floors | Relative position |
| `building_age` | 2026 - year_built | Depreciation proxy |
| `area_per_room` | total_area / rooms | Layout quality indicator |
| `kitchen_ratio` | kitchen_area / total_area | Layout quality indicator |
| `is_studio` | rooms == 0 or rooms == 1 and area < 30 | Different market segment |

**Location features** (from geocoding + external data):
| Feature | Source | Importance |
|---------|--------|-----------|
| `distance_to_center` | PostGIS | Very high |
| `district_median_price_sqm` | calculated | Very high |
| `nearest_metro_distance` | OSM/Yandex | High (if metro exists) |
| `nearest_school_distance` | OSM | Medium |
| `nearest_park_distance` | OSM | Medium |
| `road_noise_proximity` | OSM (highways) | Low-medium |

**Categorical features** (one-hot encode or ordinal):
| Feature | Values | Encoding |
|---------|--------|----------|
| `building_type` | panel, brick, monolith, wood | one-hot |
| `renovation` | designer, euro, cosmetic, none, rough | ordinal (0-4) |
| `balcony` | loggia, balcony, none | ordinal (0-2) |
| `bathroom` | separate, combined | binary |
| `seller_type` | owner, agent, developer | one-hot |

**NLP features from description** (advanced):
- Mention of "вид на реку/парк" (view) → +premium
- Mention of "ремонт" details → renovation quality proxy
- Mention of "торг"/"срочно" → motivated seller → potential discount
- Sentiment/urgency score (simple keyword matching, no ML needed for MVP)

### 3.3 Price per SQM Analysis by Micro-Location

```sql
-- Micro-location price analysis using H3 hexagonal grid
-- (Or simpler: group by microdistrict/street)

-- Option A: By microdistrict
SELECT
    microdistrict,
    rooms,
    COUNT(*) as sample_size,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price_per_sqm)) as p25,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY price_per_sqm)) as median,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price_per_sqm)) as p75,
    ROUND(AVG(price_per_sqm)) as mean
FROM properties
WHERE city = 'Пермь' AND is_active = TRUE AND property_type = 'apartment'
GROUP BY microdistrict, rooms
HAVING COUNT(*) >= 5
ORDER BY median DESC;

-- Option B: By PostGIS grid cells (500m hexagons)
-- Requires ST_HexagonGrid or custom grid overlay
```

**Visualization**: Use Plotly/Folium to create interactive heatmaps of price_per_sqm overlaid on Perm city map.

### 3.4 ML Model vs Rule-Based for MVP

| Approach | Pros | Cons | When to Use |
|----------|------|------|-------------|
| **Rule-based** (adjustment coefficients) | Interpretable, works with small data, no training needed, easy to explain to users | Coefficients are subjective, doesn't capture complex interactions, need manual tuning | **MVP (Phase 1)** — start here |
| **Linear Regression** | Simple, interpretable coefficients, fast | Assumes linear relationships, poor with non-linear patterns | Phase 2 baseline |
| **Random Forest** | Handles non-linear, feature importance built-in, robust | Less interpretable, needs 1000+ samples | Phase 2 |
| **XGBoost / LightGBM** | Best accuracy (proven in RE), handles missing data, SHAP for explanability | Needs tuning, requires 2000+ samples | **Phase 3 (production)** |

**Recommended progression**:
1. **MVP**: Rule-based comparable sales + price/sqm by district
2. **V2**: Train XGBoost on accumulated data (need 2000+ listings with all features)
3. **V3**: Ensemble (XGBoost + rule-based), retrain weekly, A/B test against manual valuations

**Research benchmark**: XGBoost on 1.2M residential properties in Germany achieved the best performance vs Random Forest and traditional comparable sales (Tandfonline, 2022).

### 3.5 Auction Property Discount Estimation

For properties from torgi.gov.ru and bankruptcy auctions:

**General Russian market discount ranges**:
| Auction Type | Typical Discount vs Market | Notes |
|-------------|---------------------------|-------|
| Municipal property auction | 10-25% | Starting price often near cadastral value |
| Bankruptcy (1st auction) | 15-30% | Starting price set by appraiser |
| Bankruptcy (2nd auction) | 25-40% | -10% from 1st auction starting price |
| Bankruptcy (public offer) | 30-60% | Progressive price reduction |
| Foreclosure (by bank) | 10-25% | Bank wants to recover loan amount |

**Discount estimation algorithm**:
```python
def estimate_auction_discount(lot):
    """Estimate expected discount for auction property."""

    # Base discount by auction type
    base_discounts = {
        'municipal': 0.15,
        'bankruptcy_first': 0.22,
        'bankruptcy_second': 0.33,
        'bankruptcy_public_offer': 0.45,
        'foreclosure': 0.18,
    }
    base = base_discounts.get(lot.auction_type, 0.20)

    # Adjustments
    adjustments = 0

    # Condition unknown → additional discount
    if lot.condition_unknown:
        adjustments += 0.05

    # Legal complexity (encumbrances, tenants)
    if lot.has_encumbrances:
        adjustments += 0.05
    if lot.has_tenants:
        adjustments += 0.08

    # Location factor (less desirable = bigger discount)
    if lot.location_score < 0.3:  # rural or remote
        adjustments += 0.05

    # Time on market (longer = more desperate)
    if lot.days_listed > 180:
        adjustments += 0.03

    total_discount = base + adjustments

    # Estimated market value
    if lot.starting_price and lot.cadastral_value:
        # Use higher of: (starting_price / (1-discount)) or cadastral * markup
        est_from_starting = lot.starting_price / (1 - total_discount)
        est_from_cadastral = lot.cadastral_value * 1.3  # cadastral typically 70-80% of market
        estimated_market = max(est_from_starting, est_from_cadastral)

    return {
        'estimated_discount': total_discount,
        'estimated_market_value': estimated_market,
        'expected_buy_price_low': estimated_market * (1 - total_discount - 0.05),
        'expected_buy_price_high': estimated_market * (1 - total_discount + 0.10),
    }
```

---

## 4. Existing Open Source Tools

### 4.1 Scraping Frameworks

| Tool | Language | Use Case | Stars | Link |
|------|----------|----------|-------|------|
| **Scrapy** | Python | Main scraping framework, async, pipelines, middleware | 53k+ | github.com/scrapy/scrapy |
| **Playwright** | Python/JS | Browser automation for JS-heavy sites (CIAN, DomClick) | 70k+ | github.com/microsoft/playwright |
| **scrapy-playwright** | Python | Scrapy + Playwright integration | 5k+ | github.com/scrapy-plugins/scrapy-playwright |
| **Patchright** | Python/JS | Playwright fork for anti-bot bypass | 2k+ | github.com/AresS31/patchright |
| **undetected-chromedriver** | Python | Selenium with anti-bot bypass | 10k+ | github.com/ultrafunkamsterdam/undetected-chromedriver |

### 4.2 Rosreestr / Cadastral Tools

| Tool | Language | Purpose | Link |
|------|----------|---------|------|
| **rosreestr-api** | Python | Query rosreestr.ru + pkk.rosreestr.ru APIs | github.com/GregEremeev/rosreestr-api |
| **getpkk** | Python | Get parcel coordinates by cadastral number | github.com/rendrom/getpkk |
| **rosreestr_loader** | Python | Bulk load addresses from Rosreestr API | github.com/ArtUshak/rosreestr_loader |
| **pkk.js** | JavaScript | JS client for Public Cadastral Map | github.com/stepankuzmin/pkk.js |
| **fias** (Ruby) | Ruby | FIAS database wrapper | github.com/evilmartians/fias |

### 4.3 Geocoding for Russia

| Tool | Type | Russia Quality | Cost | Link |
|------|------|---------------|------|------|
| **DaData** | API (SaaS) | Excellent | 10k free/day, then ~$65/yr | dadata.ru |
| **Yandex Geocoder** | API | Excellent | 1k free/day, then paid | yandex.ru/dev/geocode |
| **Nominatim** | Self-hosted | Poor-Medium | Free | nominatim.org |
| **Photon** | Self-hosted | Medium | Free | github.com/komoot/photon |

### 4.4 RE Price Prediction Models (GitHub)

| Repository | Approach | Notes |
|-----------|----------|-------|
| `topics/real-estate-price-prediction` | Various | 100+ repos, mostly Kaggle-style |
| `MYoussef885/House_Price_Prediction` | XGBoost | End-to-end with feature engineering |
| `chizeni24/ML-Property-Price-Predictions` | Voting Regressor | FastAPI deployment, 85% accuracy |
| `Arshdeep6840/House-Price-Prediction-Using-ML` | Ensemble (RF+GB+XGB) | Streamlit UI |
| `guraybaydur/Real-Estate-House-Price-Predictor` | Random Forest + chatbot | Data science + microservices |
| Kaggle: `house-prices-advanced-regression-techniques` | Competition | Best resource for feature engineering patterns |

**Note**: No production-grade open-source AVM (Automated Valuation Model) exists that is Russia-specific. All the above are educational/Kaggle projects. You will need to build your own model trained on Russian data.

### 4.5 Other Useful Libraries

| Library | Purpose |
|---------|---------|
| `pandas` | Data manipulation |
| `scikit-learn` | ML models, preprocessing |
| `xgboost` / `lightgbm` | Gradient boosting (best for RE valuation) |
| `shap` | Model explainability (why this price?) |
| `folium` | Map visualizations |
| `geopandas` | Geospatial data in pandas |
| `natasha` (Python) | Russian NLP (extract addresses, entities from descriptions) |
| `razdel` (Python) | Russian text tokenization |
| `pymorphy2` (Python) | Russian morphological analysis |

---

## 5. n8n Feasibility Assessment

### 5.1 What n8n CAN Do Well

| Task | n8n Suitability | Notes |
|------|----------------|-------|
| Scraping 50-100 listings/run | OK | HTTP Request node with delays |
| Scheduling scrape runs | Excellent | Cron triggers |
| Sending Telegram alerts | Excellent | Already proven in your workflows |
| Writing to Google Sheets | Excellent | Native node |
| Simple price comparisons | OK | Code node (JavaScript) |
| Webhook triggers | Excellent | For on-demand valuations |
| Notification pipeline | Excellent | Core n8n strength |

### 5.2 What n8n CANNOT Do Well

| Task | n8n Limitation | Better Tool |
|------|---------------|-------------|
| Scraping 5000+ listings | Memory limits, timeout, concurrency cap (5) | Python + Scrapy |
| Browser automation (Playwright) | No native support, can't run headless browser | Python + Playwright |
| PostGIS spatial queries | No PostgreSQL spatial support in n8n | Python + psycopg2 |
| ML model training | No ML capabilities | Python + scikit-learn/XGBoost |
| ML model inference (complex) | Code node has limited libraries | Python microservice |
| Address normalization pipeline | Possible but clunky for thousands of records | Python script |
| Deduplication (fuzzy matching) | Code node JS limitations | Python + dedupe library |
| Large dataset processing | n8n loads all items in memory | Python + pandas/streaming |
| Data visualization | No charting capability | Streamlit / Grafana |

### 5.3 Recommended Hybrid Architecture

```
┌──────────────────────────────────────────────────┐
│                  n8n (Orchestrator)                │
│                                                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│  │ Schedule  │───▶│ Trigger  │───▶│ Webhook  │    │
│  │ Triggers  │    │ Python   │    │ Results  │    │
│  └──────────┘    │ Scripts  │    │ to TG/   │    │
│                  └──────────┘    │ Sheets   │    │
│                                  └──────────┘    │
└──────────────────────────────────────────────────┘
         │                              ▲
         │ HTTP webhook                 │ HTTP callback
         ▼                              │
┌──────────────────────────────────────────────────┐
│              Python Backend (VPS)                  │
│                                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Scrapers │  │ Data     │  │ Valuation│       │
│  │ (Scrapy) │  │ Pipeline │  │ Engine   │       │
│  └──────────┘  └──────────┘  └──────────┘       │
│        │              │              │            │
│        └──────────────┴──────────────┘            │
│                       │                           │
│               ┌──────────────┐                    │
│               │  PostgreSQL  │                    │
│               │  + PostGIS   │                    │
│               └──────────────┘                    │
└──────────────────────────────────────────────────┘
```

**n8n responsibilities** (keep):
- Scheduling (trigger scrape jobs via webhook to Python)
- Receiving results and pushing to Telegram/Google Sheets
- "New deal alert" pipeline (compare auction price vs valuation)
- Dashboard notifications
- User interaction via Telegram bot

**Python backend responsibilities** (new):
- All scraping (Scrapy + Playwright)
- Data pipeline (normalize, geocode, deduplicate)
- PostgreSQL/PostGIS storage and queries
- Valuation engine (comparable sales + ML model)
- Expose REST API for n8n to call

### 5.4 Minimum Viable Stack Decision

**Option A: n8n-only (Google Sheets as DB)**
- Feasible for: < 500 listings, no ML, no spatial queries, simple price/sqm comparisons
- Time to MVP: 1-2 weeks
- Ceiling: hits limits fast, unmaintainable beyond basic alerts
- **Verdict**: Only if you want quick proof-of-concept, not production

**Option B: Python-only**
- Feasible for everything but requires building scheduling, notifications, etc. from scratch
- Time to MVP: 4-6 weeks
- **Verdict**: Most flexible but most work

**Option C: Hybrid (n8n + Python) — RECOMMENDED**
- n8n handles what it does well (scheduling, notifications, Telegram)
- Python handles data-heavy work (scraping, DB, ML)
- Communication via webhooks (n8n → Python) and callbacks (Python → n8n webhook)
- Time to MVP: 3-4 weeks
- **Verdict**: Best balance of speed and capability

---

## 6. Recommended MVP Roadmap

### Phase 1: Data Collection (Week 1-2)
- [ ] Set up PostgreSQL + PostGIS on VPS (or local Docker)
- [ ] Build Avito scraper (Scrapy + Playwright) for Perm apartments
- [ ] Build CIAN scraper for Perm apartments
- [ ] DaData integration for address normalization + geocoding
- [ ] Basic deduplication (exact address match)
- [ ] n8n workflow: daily trigger → Python scraper → results to Sheets + Telegram

### Phase 2: Basic Analytics (Week 3)
- [ ] Price/sqm analysis by district (SQL materialized views)
- [ ] Rule-based comparable sales engine (adjustment coefficients)
- [ ] REST API endpoint: `POST /valuate` — returns estimated price for given property
- [ ] n8n workflow: new listing alert with valuation attached
- [ ] Telegram bot: send address → get valuation

### Phase 3: Enrichment (Week 4-5)
- [ ] PKK/Rosreestr integration (cadastral value, building data)
- [ ] torgi.gov.ru monitoring (auction lots for Perm region)
- [ ] Price history tracking (detect price drops)
- [ ] Auction discount estimator
- [ ] Streamlit dashboard: map + price heatmap + deal alerts

### Phase 4: ML Valuation (Week 6-8)
- [ ] Feature engineering pipeline
- [ ] Train XGBoost model on accumulated data (need 2000+ listings)
- [ ] SHAP explanations (why this price?)
- [ ] Model comparison: rule-based vs ML, track accuracy
- [ ] Retrain weekly, monitor drift

### Infrastructure Requirements

| Component | Recommended | Cost |
|-----------|------------|------|
| VPS (scraping + DB + Python) | Hetzner CX22 or similar (2 vCPU, 4GB RAM, 40GB SSD) | ~$5/mo |
| PostgreSQL + PostGIS | On same VPS (Docker) | included |
| DaData API | Free tier (10k/day) | $0 |
| Residential proxies | For Avito/CIAN (if needed) | $20-50/mo |
| n8n cloud | Already have | existing |
| Domain + SSL | For API endpoint | ~$10/yr |

**Total estimated cost: $25-60/month**

---

## Sources

- [Apify — Avito Offers Scraper](https://apify.com/scrapestorm/avito-offers-scraper-fast-and-cheap/api)
- [Apify — CIAN.ru Scraper](https://apify.com/igolaizola/cian-ru-scraper/api/python)
- [Apify — DomClick Search Scraper](https://apify.com/zen-studio/domclick-search-scraper)
- [GitHub — rosreestr-api (GregEremeev)](https://github.com/GregEremeev/rosreestr-api)
- [GitHub — getpkk (rendrom)](https://github.com/rendrom/getpkk)
- [GitHub — pkk.js](https://github.com/stepankuzmin/pkk.js/)
- [GitHub — rosreestr_loader](https://github.com/ArtUshak/rosreestr_loader)
- [GitHub — FIAS Ruby wrapper](https://github.com/evilmartians/fias)
- [GitHub — DaData Python client](https://github.com/hflabs/dadata-py)
- [GitHub — real-estate-price-prediction topic](https://github.com/topics/real-estate-price-prediction)
- [GitHub — House Price Prediction (XGBoost)](https://github.com/MYoussef885/House_Price_Prediction)
- [GitHub — ML Property Price Predictions](https://github.com/chizeni24/ML-Property-Price-Predictions)
- [GitHub — yarealty (Yandex Realty Crawler)](https://github.com/mixartemev/yarealty)
- [GitHub — openaddresses Russia issue](https://github.com/openaddresses/openaddresses/issues/127)
- [DaData — Address API](https://dadata.ru/api/clean/address/)
- [DaData — Geocoding API](https://dadata.ru/api/geocode/)
- [DaData — PyPI package](https://pypi.org/project/dadata/)
- [Nominatim — OpenStreetMap geocoding](https://nominatim.org/)
- [OSM Wiki — RU:Nominatim](https://wiki.openstreetmap.org/wiki/RU:Nominatim)
- [torgi.gov.ru — Open Data recommendations](https://www.torgi.gov.ru/opendata/recommendation.html)
- [torgi.gov.ru — Public portal](https://torgi.gov.ru/new/public)
- [vc.ru — torgi.gov.ru bulk export](https://vc.ru/u/415964-sergei-konovalov/395937-vse-aktualnye-loty-torgigovru-odnim-failom)
- [Rosreestr — Official site](https://rosreestr.gov.ru/en/about/)
- [MDPI — Comparable Sales Method Automation](https://www.mdpi.com/2071-1050/12/14/5679)
- [Tandfonline — Gradient Boosting for House Prices](https://www.tandfonline.com/doi/full/10.1080/09599916.2022.2070525)
- [PMC — From human business to ML in RE appraisals](https://pmc.ncbi.nlm.nih.gov/articles/PMC9294847/)
- [FHFA — REO Price Discount Primer](https://www.fhfa.gov/media/33006)
- [Tandfonline — Berlin Foreclosure Market Discounts](https://www.tandfonline.com/doi/full/10.1080/08965803.2025.2516889)
- [n8n Community — Large-scale web scraping discussion](https://community.n8n.io/t/anyone-using-n8n-for-large-scale-web-scraping/150535)
- [Contabo — n8n Web Scraping Guide](https://contabo.com/blog/the-ultimate-guide-to-n8n-web-scraping/)
- [Kaggle — House Prices Advanced Regression](https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques)
- [PostGIS Database Schema Gist](https://gist.github.com/SimonGoring/40450c1c4a86b22fa54afd9542f2a546)
- [Database Sample — Real Estate Schema](https://databasesample.com/database/real-estate-database)
- [MCPmarket — Rosreestr MCP Server](https://mcpmarket.com/server/rosreestr)
