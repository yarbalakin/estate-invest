# PropTech APIs, Tools & Open Source — Практический справочник

*Дата: 2026-03-01*

---

## 1. Real Estate APIs (рабочие)

### Сравнительная таблица

| API | Free Tier | Min Paid | Coverage | Best For |
|-----|-----------|----------|----------|----------|
| **RentCast** | 50 calls/mo | ~$12/mo | 140M props | MVP/Rental |
| **Parcl Labs** | 1,000 credits/mo | Dashboard | 70K markets | Market analytics |
| **HouseCanary** | -- | $79/mo | 75+ metrics | Forecasting |
| **ATTOM** | 30-day trial | ~$95/mo | 158M props | Enterprise |
| **BatchData** | -- | $0.01/call | 155M props | Scale/Skip tracing |
| **Homesage.ai** | -- | ~$200/mo | 140M props | Investment analytics |

### ATTOM Data API
- **URL**: api.developer.attomdata.com/docs
- **Coverage**: 158M+ US properties, 9,000+ fields, 70B rows
- **Key Endpoints**: `/avm/detail`, `/property/snapshot`, `/assessment/detail`, `/sale/snapshot`, `/transaction/salestrend`
- **Pricing**: ~$95/month, enterprise $850-$2,000/month. 30-day free trial.

### RentCast API
- **URL**: developers.rentcast.io
- **Coverage**: 140M+ US property records
- **50 free API calls/month**. Plans from $12/month.
- **Best for MVP/prototyping** -- generous free tier.

### Parcl Labs API
- **URL**: docs.parcllabs.com
- **Unique**: Daily price-per-square-foot estimates across 70,000+ US markets
- **1,000 free monthly credits**
- **Python SDK**: `pip install parcllabs`
- **Cookbook**: github.com/ParclLabs/parcllabs-cookbook

### HouseCanary API
- **URL**: api-docs.housecanary.com
- **75+ data points**, forecasting up to 36 months
- **From $79/month**. Usage fees: $0.30-$6.00 per endpoint
- **Python SDK**: github.com/housecanary/hc-api-python

### PriceHubble API (Europe)
- **URL**: docs.pricehubble.com
- **11 countries** (CH, FR, DE, AT, UK, JP, NL, BE, CZ, SK, US)
- Up to 50 valuations per call
- Base URL: `https://api.pricehubble.com/api/v1/`

### Zillow / Bridge API
- **Status**: Old Zillow API deprecated. Now Bridge Interactive API (invite-only).
- **Hard to access** for small teams. Consider ATTOM or RentCast instead.

---

## 2. Open Datasets

### Золотой стандарт

| Dataset | Country | Format | Size | Cost | Key |
|---------|---------|--------|------|------|-----|
| **UK Land Registry PPD** | UK | CSV | 4.3 GB | Free | 20M+ actual sale prices since 1995 |
| **France DVF** | France | CSV/SQL/GeoPackage | Large | Free | All transactions since 2019, with API |
| **GREIX** | Germany | Download | 19 cities | Free | 2M+ transactions since 1960 |
| **NYC PLUTO** | US (NYC) | CSV/SHP | 870K lots | Free | 80+ attributes per tax lot |
| **Zillow Research** | US | CSV | Market-level | Free | ZHVI, ZORI, inventory, price cuts |
| **Redfin Data Center** | US | TSV | Market-level | Free | Sale prices, DOM, inventory |
| **US Census ACS** | US | API/CSV | National | Free | Demographics, housing stats |

### UK Land Registry
- **Download**: gov.uk/government/statistical-data-sets/price-paid-data-downloads
- **SPARQL**: landregistry.data.gov.uk/landregistry/query (400M+ triples)
- **Fields**: Price, Date, Postcode, Property Type, Old/New, Freehold/Leasehold, Full Address
- **License**: Open Government Licence

### France DVF
- **Portal**: data.gouv.fr/datasets/demandes-de-valeurs-foncieres
- **Map**: app.dvf.etalab.gouv.fr
- **DVF+ (enriched)**: datafoncier.cerema.fr
- **API**: github.com/datagouv/api-dvf
- **License**: Licence Ouverte v2.0

### Germany GREIX
- **Download**: greix.de/download
- 19 cities, data back to 1960, 2M+ notarized transactions
- Published by Kiel Institute. Free.

### NYC PLUTO
- **Download**: nyc.gov/site/planning/data-maps/open-data/dwn-pluto-mappluto.page
- 870K+ properties, **80+ attributes**: land use, zoning, building class, area, floors, year built, assessed values, owner, FAR
- **Best single-city open RE dataset in the world**

### Zillow Research
- **URL**: zillow.com/research/data/
- ZHVI (home values), ZORI (rents), inventory, new listings, price cuts, days to pending
- Granularity: Neighborhood → ZIP → City → Metro → State → National

### Overture Maps -- Building Footprints
- **Download**: overturemaps.org/download/
- **2.3 billion** building footprints worldwide
- **Python CLI**: `pip install overturemaps`
- Format: GeoParquet

### Kaggle Datasets

| Dataset | Records | Features |
|---------|---------|----------|
| Ames Housing | 2,930 | 79 (the "MNIST of RE") |
| Redfin Housing Market | ~7M rows | Market metrics 2012-2021 |
| Zillow Home Value Index | Monthly | ZHVI by region |

---

## 3. Open-Source GitHub Projects

### Production-Grade AVM

**ccao-data/model-res-avm** (Cook County)
- **Lang**: R, **Model**: LightGBM
- Real government AVM in production (Chicago). ~25 features.
- **Excellent quality**: DVC pipeline, reproducible.
- Also: model-condo-avm for condos

**larsiusprime/openavmkit**
- **Lang**: Python 3.11
- **THE most important project**: FOSS mass appraisal toolkit
- Models: MRA, GWR, LightGBM, XGBoost, CatBoost (unified interface)
- Auto-downloads OSM features (distance to water, parks, schools)
- IAAO-compatible ratio studies (PDF/HTML)
- Overture Maps integration
- `pip install openavmkit` | openavmkit.com

### Scraping

**ZacharyHampton/HomeHarvest** (588 stars)
- Python. MLS listings scraper. By ZIP, city, address.
- `pip install homeharvest`

**brightdata/mls-scraper**
- Anti-bot bypass patterns for RE sites

### Deduplication

**dedupeio/dedupe**
- ML-powered fuzzy matching. Active learning. Production-ready.
- `pip install dedupe`

---

## 4. Geocoding & Mapping

### Для России

| Tool | Стоимость | Лучше всего для |
|------|-----------|-----------------|
| **Yandex Maps API** | По тарифу | Геокодинг русских адресов (лучшее покрытие) |
| **DaData API** | 10K/день free | Нормализация адресов + FIAS GUID |
| **Mapbox** | $0.75/1K | Визуализация карт (дешевле Google) |
| **Google Maps** | $5.00/1K | Точность (но дорого) |

### H3 (Uber's Hexagonal Grid)
- `pip install h3`
- **RE Use Cases**: Price heatmaps per hexagon, comparable selection by hex, neighborhood density

```python
import h3
# Resolution guide:
# res 7 (~5 km2) = city district level
# res 8 (~0.7 km2) = neighborhood level
# res 9 (~0.1 km2) = block level
h3_index = h3.latlng_to_cell(55.7558, 37.6173, 9)
neighbors = h3.grid_disk(h3_index, 2)  # 2-ring neighborhood
```

### Визуализация

| Tool | Лучше для | Install |
|------|-----------|---------|
| **Folium** | Quick maps, Streamlit/HTML | `pip install folium` |
| **Kepler.gl** | GPU-accelerated, millions of points | `pip install keplergl` |
| **deck.gl (pydeck)** | Advanced 3D maps | `pip install pydeck` |

---

## 5. ML/AI для Real Estate

### LightGBM — рекомендуемые параметры для RE

```python
params = {
    'objective': 'regression',
    'metric': 'mape',
    'n_estimators': 1000,
    'learning_rate': 0.05,
    'max_depth': 8,
    'num_leaves': 127,
    'min_child_samples': 20,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'reg_alpha': 0.1,
    'reg_lambda': 1.0,
    'early_stopping_rounds': 50,
}
```

### SHAP для объяснения оценок

```python
import shap
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)
shap.plots.waterfall(explainer(X_test)[0])  # single property
shap.summary_plot(shap_values, X_test)      # global importance
```

### Sentence Transformers — матчинг объектов

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-mpnet-base-v2')
embeddings = model.encode([desc1, desc2])
# cosine_similarity > 0.85 = likely same property
```

### Computer Vision для фото недвижимости

| Tool | Возможности | Цена |
|------|-------------|------|
| **Restb.ai** | 700+ RE-тегов, состояние 1-10, комнаты, дефекты | По запросу |
| **HelloData.ai** | Room type, amenities, quality 1-10 | По запросу |
| **CLIP (free)** | Room classification, condition (DIY) | Бесплатно |

```python
# DIY room classification with CLIP
from transformers import CLIPProcessor, CLIPModel
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
room_types = ["kitchen", "bedroom", "bathroom", "living room", "exterior"]
# probs = model(images, text) -> softmax -> room probabilities
```

---

## 6. Инфраструктура MVP

### Supabase (PostgreSQL + PostGIS + Auth + API)
- Free: 500MB database, 1GB storage, 50K MAU
- PostGIS: Dashboard > Database > Extensions > "postgis"
- Auto-generated REST API (no backend code needed for CRUD)
- Real-time subscriptions

```sql
CREATE TABLE properties (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  address TEXT NOT NULL,
  price NUMERIC,
  area_sqm NUMERIC,
  rooms INT,
  location GEOGRAPHY(POINT),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_location ON properties USING GIST(location);
```

### Cheapest Stack

```
Supabase Free (DB + API + Auth)
+ Railway (Python workers: scraping, ML)
+ Vercel/Cloudflare Pages (frontend)
= $0-5/month for MVP
```

### n8n + Python Integration

**Pattern 1 (Recommended)**: n8n → HTTP Request → FastAPI service → return JSON
**Pattern 3 (Full pipeline)**: n8n Schedule → trigger FastAPI → scraping/ML → Supabase → n8n reads → Telegram

### Scraping Stack

- **Browser**: Playwright (auto-wait, multi-browser, stealth plugins)
- **Framework**: Scrapy + scrapy-playwright (`pip install scrapy scrapy-playwright`)
- **Proxies (MVP)**: ScraperAPI (pay per success)
- **Proxies (scale)**: Bright Data / Oxylabs

---

## 7. Практические рекомендации для российского MVP

1. **Геокодинг**: Yandex Maps API (лучшие данные для России)
2. **Парсинг**: Playwright + residential proxies для Avito/ЦИАН
3. **БД**: Supabase PostGIS (бесплатно до 500MB)
4. **ML**: CatBoost (лучше с русскими категориальными признаками) + SHAP
5. **Карты**: Yandex Maps (отображение) + H3 (аналитика)
6. **Features**: OSMnx для distance-to-amenities
7. **Dashboard**: Streamlit
8. **Автоматизация**: n8n + FastAPI microservice
9. **Стоимость**: $0-15/мес для MVP

---

*Sources: ATTOM API Docs, RentCast Docs, Parcl Labs Docs, HouseCanary API, PriceHubble Docs, UK Land Registry, France DVF, GREIX, NYC PLUTO, Zillow Research, Redfin Data Center, Overture Maps, ccao-data/model-res-avm, OpenAVMKit, HomeHarvest, dedupe, H3, Kepler.gl, SHAP, Sentence Transformers, Restb.ai, Supabase, Scrapy-Playwright*