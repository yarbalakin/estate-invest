# Технический Deep Dive — API, парсеры, AVM

> Дата: 2026-03-01
> Дополнение к RESEARCH.md — конкретные эндпоинты, код, библиотеки

---

## 1. API торговых площадок

### 1.1 torgi.gov.ru — REST API (главный источник)

```
# Поиск лотов недвижимости (банкротство)
GET https://torgi.gov.ru/new/api/public/lotcards/search
  ?catCode=2              # недвижимость
  &auctionType=BANKRUPT   # банкротство
  &size=100&page=0
  &sort=firstVersionPublicationDate,desc
  &dynSubjRF=59           # Пермский край
  &lotStatus=PUBLISHED,APPLICATIONS_SUBMISSION
  &byFirstVersion=true
  &withFacets=true

# Детали лота
GET https://torgi.gov.ru/new/api/public/lotcards/{lotId}
```

**Ответ JSON**: lotName, lotDescription, startPrice, depositAmount, biddStartTime/EndTime, auctionStartDate, characteristics[] (адрес, площадь, кадастровый номер), lotStatus, etpUrl, biddType, attachments[].

**Rate limit**: ~60-120 req/min. Задержки 1-3 сек достаточно.

```python
import requests, time

BASE = "https://torgi.gov.ru/new/api/public/lotcards/search"
params = {"catCode": "2", "auctionType": "BANKRUPT", "dynSubjRF": "59",
          "size": 100, "page": 0, "sort": "firstVersionPublicationDate,desc"}
headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

all_lots = []
while True:
    data = requests.get(BASE, params=params, headers=headers).json()
    lots = data.get("content", [])
    if not lots: break
    all_lots.extend(lots)
    params["page"] += 1
    time.sleep(2)
```

### 1.2 Федресурс — POST API + CAPTCHA

```
POST https://bankrot.fedresurs.ru/api/TradeSearch
Content-Type: application/json

{"propertyType": 4, "regionCode": null, "offset": 0, "limit": 15,
 "datePublishStart": "2026-01-01", "datePublishEnd": "2026-03-01"}
```

`propertyType`: 4 = недвижимое имущество.

Требует **Playwright** + обход Яндекс SmartCaptcha (rucaptcha.com, ~30 руб/1000).

### 1.3 PKK Росреестра — кадастровые данные

```
# Земельный участок (type=1) или ОКС (type=5)
GET https://pkk.rosreestr.ru/api/features/5/59:01:4410851:123
Headers: Referer: https://pkk.rosreestr.ru/
```

Возвращает: cn, address, area_value, cad_cost (кадастровая стоимость), coordinates, category_type, status.

**Rate limit**: агрессивный, ~10-20 req/min. Кешировать результаты.

```python
def get_cadastral(cad_num, obj_type=5):
    url = f"https://pkk.rosreestr.ru/api/features/{obj_type}/{cad_num}"
    resp = requests.get(url, headers={"Referer": "https://pkk.rosreestr.ru/"}, timeout=10)
    attrs = resp.json().get("feature", {}).get("attrs", {})
    return {"address": attrs.get("address"), "area": attrs.get("area_value"),
            "cad_cost": attrs.get("cad_cost"), "coords": resp.json().get("feature", {}).get("center")}
```

---

## 2. Парсинг рыночных данных

### 2.1 ЦИАН — внутренний JSON API

```
POST https://api.cian.ru/search-offers/v2/search-offers-desktop/
Content-Type: application/json

{"_type": "flatsale", "region": 4694, "engine_version": 2, "page": 1,
 "room": {"type": "room", "value": [1,2,3]}}
```

**Антибот**: Cloudflare TLS fingerprinting + JS Challenge. Решение: **CloudScraper** (Python), пауза 4-5 сек.

**GitHub парсеры**:
- `lenarsaitov/cianparser` — PyPI `pip install cianparser`, HTML-парсинг
- `andrepopoff/cian-parser` — JSON API напрямую (**рекомендуется**)
- `petuhovskiy/cian-search` — Go, экспорт в Sheets

### 2.2 Авито — скрейпинг (наш опыт)

Аналогично гитарам в СКАУТ. Специфика недвижимости:
- Кадастровый номер из описания: `re.search(r'(\d{2}:\d{2}:\d{6,7}:\d{1,5})', text)`
- Точный адрес скрыт — извлекать из описания
- Нужен residential proxy для объёма

### 2.3 ads-api.ru — РЕКОМЕНДУЕТСЯ для MVP

Агрегатор ЦИАН + Авито + Домклик:
- **14 дней бесплатно**, затем ~3000 руб/мес
- Структурированные данные, без антибот-проблем
- Быстрый старт без написания парсеров

### 2.4 Реальные цены сделок

- Практический подход: цена объявления минус 5-15% = примерная цена сделки
- Росреестр "Мониторинг рынка" (portal.rosreestr.ru) — часто заниженные цены
- ЕГРН выписки через ktotam.pro (~125 руб/шт, есть API)

---

## 3. Нормализация и дедупликация

### 3.1 DaData — геокодирование и нормализация

```
POST https://cleaner.dadata.ru/api/v1/clean/address
Authorization: Token <API_KEY>
X-Secret: <SECRET>
Content-Type: application/json

["Пермь, ул. Ленина 15, кв. 42"]
```

Возвращает: fias_id (GUID), координаты, район, кадастровая стоимость.

**Лимиты**: 10 000 запросов/день бесплатно, 20 req/sec.

### 3.2 Алгоритм дедупликации

1. DaData → нормализация → `fias_id` (GUID здания)
2. Точный матч: `fias_id` + номер квартиры = один объект
3. Fuzzy: улица+дом+квартира + площадь (±2 м²) + этаж + комнаты
4. Координатный: расстояние <50м + площадь + этаж

Скоринг: fias_id=50, площадь=20, этаж=15, комнаты=10, квартира=30. **Порог 60+ = совпадение**.

### 3.3 Извлечение данных из описаний (NLP/Regex)

```python
import re

def extract_lot_data(text):
    result = {}
    # Кадастровый номер
    m = re.search(r'(\d{2}:\d{2}:\d{6,7}:\d{1,5})', text)
    if m: result['cadastral'] = m.group(1)
    # Площадь
    m = re.search(r'площад\w*\s*[:\-—]?\s*([\d\s,\.]+)\s*(?:кв\.?\s*м|м²)', text, re.I)
    if m: result['area'] = float(m.group(1).replace(',', '.').replace(' ', ''))
    # Тип объекта
    for name, pat in [('квартира', r'квартир[аыу]'), ('дом', r'(?:жилой\s+)?дом'),
                       ('земля', r'земельн\w+\s+участ'), ('помещение', r'помещени[еяй]')]:
        if re.search(pat, text, re.I): result['type'] = name; break
    return result
```

Для сложных описаний — LLM через OpenRouter (Llama 3.3 70B free).

---

## 4. Модель оценки (AVM)

### 4.1 Стек

```
pip install lightgbm scikit-learn shap pandas numpy optuna fastapi uvicorn joblib
```

Опционально: `pip install openavmkit` (готовый AVM-фреймворк).

### 4.2 Обучение модели

```python
import lightgbm as lgb
from sklearn.model_selection import cross_val_score
import shap, joblib

features = ['area_m2', 'rooms', 'floor', 'total_floors', 'year_built',
            'lat', 'lon', 'distance_metro_m', 'building_type', 'condition']
categorical = ['building_type', 'condition']

X = df[features].copy()
for col in categorical: X[col] = X[col].astype('category')
y = df['price']

model = lgb.LGBMRegressor(
    n_estimators=1000, learning_rate=0.05, max_depth=7, num_leaves=31,
    min_child_samples=20, subsample=0.8, colsample_bytree=0.8,
    reg_alpha=0.1, reg_lambda=0.1, verbose=-1)

scores = cross_val_score(model, X, y, cv=5, scoring='neg_mean_absolute_percentage_error')
print(f"MAPE: {-scores.mean():.2%}")  # целевое: 8-15%

model.fit(X, y)
joblib.dump(model, 'avm_model.pkl')
```

### 4.3 FastAPI сервис

```python
from fastapi import FastAPI
import joblib, shap

app = FastAPI()
model = joblib.load('avm_model.pkl')
explainer = shap.TreeExplainer(model)

@app.post("/predict")
async def predict(data: dict):
    df = pd.DataFrame([data])
    price = model.predict(df)[0]
    sv = explainer.shap_values(df)
    contributions = dict(zip(df.columns, sv[0]))
    return {"price": round(price), "confidence": {"low": round(price*0.85), "high": round(price*1.15)},
            "factors": {k: round(v) for k, v in sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)}}

@app.post("/roi")
async def roi(data: dict):
    total = data['purchase_price'] + data.get('renovation', 0) + data.get('legal', 0)
    sell = data['market_price'] * 0.92
    profit = (sell - total) * 0.87  # минус НДФЛ 13%
    return {"roi_pct": round(profit / total * 100, 1), "net_profit": round(profit)}
```

Деплой: Railway.app / Render.com (бесплатный tier для MVP).

### 4.4 Доверительные интервалы — Quantile Regression

```python
model_lo = lgb.LGBMRegressor(objective='quantile', alpha=0.1)  # 10-й перцентиль
model_hi = lgb.LGBMRegressor(objective='quantile', alpha=0.9)  # 90-й перцентиль
# → 80% CI: [lo_predict, hi_predict]
```

### 4.5 Дисконты банкротных торгов

```python
discounts = {
    'auction_stage': {'first': 0.90, 'second': 0.80, 'public_offer': 0.50},
    'condition': {'good': 1.0, 'cosmetic': 0.90, 'renovation_needed': 0.75, 'poor': 0.60},
    'encumbrances': {'none': 1.0, 'rental': 0.95, 'residents': 0.85, 'disputed': 0.70}
}
```

---

## 5. Схема БД (PostgreSQL)

```sql
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    address_raw TEXT, address_norm TEXT, fias_id UUID,
    cadastral_num TEXT, lat DECIMAL(9,6), lon DECIMAL(9,6),
    property_type TEXT, rooms INT, total_area DECIMAL(8,2),
    living_area DECIMAL(8,2), floor INT, total_floors INT,
    building_year INT, building_type TEXT, district TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE listings (
    id SERIAL PRIMARY KEY,
    property_id UUID REFERENCES properties(id),
    platform TEXT NOT NULL, external_id TEXT NOT NULL,
    url TEXT, price BIGINT, price_per_sqm INT,
    seller_type TEXT, description TEXT, raw_data JSONB,
    first_seen TIMESTAMPTZ DEFAULT NOW(), last_seen TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(platform, external_id)
);

CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    listing_id INT REFERENCES listings(id),
    price BIGINT, recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE auction_lots (
    id SERIAL PRIMARY KEY,
    property_id UUID REFERENCES properties(id),
    source TEXT, external_id TEXT, lot_name TEXT,
    start_price BIGINT, deposit BIGINT,
    auction_date TIMESTAMPTZ, bid_end_date TIMESTAMPTZ,
    auction_type TEXT, status TEXT, etp_url TEXT,
    market_estimate BIGINT, discount_pct DECIMAL(5,2),
    roi_estimate DECIMAL(5,2), raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source, external_id)
);
```

---

## 6. Open-source ресурсы

| Проект | Что | Ссылка |
|--------|-----|--------|
| OpenAVMKit | Библиотека AVM (LightGBM/XGBoost/CatBoost) | github.com/larsiusprime/openavmkit |
| Cook County AVM | Production AVM (Чикаго), LightGBM | github.com/ccao-data/model-res-avm |
| cianparser | Парсер ЦИАН (PyPI) | github.com/lenarsaitov/cianparser |
| cian-parser | ЦИАН JSON API | github.com/andrepopoff/cian-parser |
| address-normalizer | Локальная ФИАС-база | github.com/shigabeev/address-normalizer |
| Kaggle House Prices | Топ решения, стекинг | kaggle.com/competitions/house-prices-advanced-regression-techniques |

---

## 7. Архитектура MVP

```
┌──────────── СБОР ДАННЫХ ────────────────┐
│ torgi.gov.ru API ──┐                    │
│ Федресурс ─────────┤ n8n / Python       │
│ tbankrot.ru ───────┘                    │
│ ЦИАН ──────────────┐ ads-api.ru         │
│ Авито ─────────────┘ или парсеры        │
└────────────────┬────────────────────────┘
                 ▼
┌──────────── НОРМАЛИЗАЦИЯ ───────────────┐
│ DaData → ФИАС GUID + координаты        │
│ PKK → кадастровая стоимость             │
│ Regex/LLM → тип, площадь из описания    │
│ Дедупликация по ФИАС + площадь + этаж   │
└────────────────┬────────────────────────┘
                 ▼
┌──────────── ХРАНЕНИЕ ───────────────────┐
│ properties / listings / price_history   │
│ auction_lots                            │
│ Google Sheets (MVP) → PostgreSQL (v2)   │
└────────────────┬────────────────────────┘
                 ▼
┌──────────── ОЦЕНКА (AVM) ───────────────┐
│ Python FastAPI:                         │
│ /predict → цена + CI + SHAP            │
│ /comps → K аналогов                     │
│ /roi → расчёт ROI                       │
│ LightGBM, переобучение ежеквартально    │
└────────────────┬────────────────────────┘
                 ▼
┌──────────── ВЫХОД ──────────────────────┐
│ Telegram: лоты с дисконтом > 30%        │
│ Sheets: полная база с оценками          │
└─────────────────────────────────────────┘
```

---

## 8. Раунд 3 — Уточнённые инструменты (2026-03-02)

### 8.1 ads-api.ru — детали

**Тарифы**:
- Тестовый: бесплатно 14 дней (телефоны замаскированы, цена=0, макс 50 объявлений/запрос)
- API без телефонов: **2 000 руб/мес** (достаточно для нас)
- API с телефонами: 3 000 руб/мес

**Покрытие**: Avito (1), Яндекс.Недвижимость (3), ЦИАН (4), SOB (5), Юла (6), DomClick (11)

**API**: `GET https://ads-api.ru/main/api?user=EMAIL&token=TOKEN&category_id=...&city=Пермь`
- Rate limit: 1 запрос в 5 сек
- Макс 1000 объявлений/запрос, пагинация через `startid`
- Поля: id, url, title, description, price, city, address, coords, images[], params, source

**Альтернативы**:
- **INPARS.ru** — полигональный поиск по координатам, история цен
- **rest-app.net** — 4 000 руб/мес, экспорт от 3 руб/1000
- **auto-parser.ru** — отслеживание снятий и изменений цен

### 8.2 torgi.gov.ru — уточнённые параметры

Подтверждено: `catCode=110` (не 2!) для недвижимости, `subjectRFCode=59` для Перми.

```
GET https://torgi.gov.ru/new/api/public/lotcards/search
  ?catCode=110&subjectRFCode=59&lotStatus=PUBLISHED&size=100
  &sort=firstVersionPublicationDate,desc&byFirstVersion=true
```

Также есть Excel-экспорт:
```
GET https://torgi.gov.ru/new/api/public/lotcards/export/excel
  ?lotStatus=PUBLISHED&catCode=110&subjectRFCode=59
```

Ответ Spring Data JSON: `content[]`, `pageable.totalElements`, `pageable.totalPages`.

### 8.3 DaData — полный список полей

Стандартизация (clean): **0.20 руб/адрес** (не бесплатно!). Подсказки (suggestions): 10K/день бесплатно.

**Ключевые поля из clean/address**:
- `fias_id` — GUID здания
- `house_cadnum` — кадастровый номер здания
- `flat_cadnum` — кадастровый номер квартиры
- `flat_area` — площадь квартиры
- `square_meter_price` — рыночная цена за м²
- `flat_price` — полная оценка квартиры
- `geo_lat`, `geo_lon` — координаты
- `metro[]` — до 3 ближайших станций (имя, линия, расстояние км)
- `house_flat_count` — количество квартир в доме
- `qc` (0-3) — качество распознавания

**НЕ возвращает**: кадастровую стоимость, год постройки, этажность, материал стен.

### 8.4 Хостинг модели — Google Cloud Run (БЕСПЛАТНО)

**Лучший вариант** для <100 предсказаний/день:

| Параметр | Free tier |
|----------|-----------|
| Запросы | 2M/мес |
| vCPU-sec | 180K/мес (~50 ч CPU) |
| GiB-sec | 360K/мес |
| Наш расход | ~10 сек CPU/день = 0.005% лимита |

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

`gcloud run deploy avm-api --source . --region us-central1 --allow-unauthenticated`

Альтернативы: Railway ($5/мес, нет сна), Render (free но сон 15 мин), Modal ($30 кредитов/мес).

### 8.5 Supabase Free — PostgreSQL + PostGIS

| Параметр | Значение |
|----------|----------|
| Storage | 500 MB |
| PostGIS | Да (расширение) |
| pg_trgm | Да (fuzzy search) |
| pg_cron | Да (периодические SQL) |
| Edge Functions | 500K/мес (Deno, НЕ Python) |
| Пауза | 7 дней неактивности |
| n8n нода | `n8n-nodes-base.supabase` (CRUD) |

50K строк × 20 полей ≈ 50-150 MB — впишется в 500 MB.

Ежедневный скрейпинг не даст БД заснуть.

**Upsert**: нативной поддержки в n8n ноде нет → HTTP Request к Supabase REST API с `Prefer: resolution=merge-duplicates`.

### 8.6 n8n Cloud — ограничения

- **Code Node (JS)**: нет внешних npm-модулей (CloudScraper НЕ работает)
- **Code Node (Python)**: Pyodide (WebAssembly), есть pandas, numpy, requests, beautifulsoup4, httpx, lxml. Нет cianparser, cloudscraper, selenium
- **Execute Command**: **ОТКЛЮЧЕН** на n8n Cloud
- **Вывод**: n8n Cloud — только оркестрация (HTTP Request, Supabase нода, Code для простой логики). Тяжёлая работа — на FastAPI (Cloud Run/Railway)

### 8.7 Feature engineering для Перми

**Центр Перми**: `58.0105, 56.2502` (площадь у администрации)

**Overpass API (OSM)** — бесплатно, без регистрации:
```python
import overpy
api = overpy.Overpass()
result = api.query('[out:json];node["amenity"="school"](around:2000,58.0105,56.2502);out;')
for node in result.nodes:
    print(f"{node.tags.get('name')}: {node.lat}, {node.lon}")
```

Доступно для Перми: школы, детсады, больницы, магазины, парки, остановки, ж/д станции. Метро в Перми **нет**.

**2GIS API**: год постройки, этажность, материал стен — **платный** (по запросу). Бесплатный demo-ключ для тестирования.

### 8.8 Бенчмарки точности (Россия)

**Нижний Новгород** (9050 квартир, научная статья):

| Модель | MAPE | R² |
|--------|------|----|
| Random Forest | **8.1%** | **0.81** |
| Gradient Boosting | 8.6% | 0.78 |
| XGBoost | 9.0% | 0.78 |
| Linear Regression | 11.5% | 0.66 |

**Топ-фичи**: район (24%), год постройки (17%), территория (13%), этажность (10%), площадь (8%), ремонт (8%).

**Ожидание для Перми**: MAPE 8-12%, R² 0.75-0.85, нужно 3000-5000 объектов минимум.

**Kaggle "Russia Real Estate 2018-2021"**: 540K объектов по 85 регионам, Пермь включена. Грязные данные — нужна очистка.

### 8.9 QuickChart — графики в n8n

Встроенная нода `n8n-nodes-base.quickChart` — bar, line, pie, doughnut. Генерирует PNG → отправляется через Telegram sendPhoto. **Бесплатно**, не нужен Python.

### 8.10 Experiment tracking

**Git + JSON файл** — достаточно для соло-проекта. MLflow/W&B — overkill.

```python
experiments.append({
    "timestamp": datetime.now().isoformat(),
    "model": "lgbm_v3",
    "metrics": {"MAPE": 0.089, "R2": 0.82},
    "notes": "Добавлены фичи расстояния до школ"
})
```

---

## 9. Итоговый стек MVP (уточнённый)

### Фаза 1: $0/мес (2-3 недели)

```
n8n Cloud (оркестратор, уже есть)
  ├─ Schedule → HTTP Request → torgi.gov.ru API
  ├─ Code Node (JS) → парсинг, нормализация
  ├─ Google Sheets → хранение (до 10K строк)
  ├─ QuickChart → графики PNG
  └─ HTTP Request → Telegram алерты
```

Без ML. Простые правила: цена < X% от средней по району.

### Фаза 2: ~2000 руб/мес (ещё 2-3 недели)

```
n8n Cloud
  ├─ torgi.gov.ru API
  ├─ ads-api.ru (2000 руб/мес) → рыночные цены
  ├─ DaData suggestions (бесплатно) → координаты, ФИАС
  ├─ Supabase Free → PostGIS + pg_trgm
  └─ Telegram
```

### Фаза 3: ~2000 руб/мес + бесплатный Cloud Run

```
n8n Cloud
  ├─ Сбор данных (torgi + ads-api)
  ├─ HTTP Request → FastAPI на Cloud Run (бесплатно)
  │     ├─ /predict (LightGBM)
  │     ├─ /comps (KNN аналоги)
  │     └─ /roi (расчёт ROI)
  ├─ Supabase → полная база
  └─ Telegram с inline кнопками
```

**Итого production: ~2000 руб/мес** (только ads-api.ru)
