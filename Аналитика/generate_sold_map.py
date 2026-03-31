#!/usr/bin/env python3
"""
generate_sold_map.py — Генератор карты проданных объектов Estate Invest.

Читает Монитор объектов (Google Sheets), геокодирует через geocache + НСПД,
генерирует sold-map.html (Яндекс Карты).

Запуск:
  python generate_sold_map.py
"""

import json
import re
import time
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# === Конфиг ===
SA_KEY = "/Users/yaroslavbalakin/Downloads/powerful-hall-488221-t2-b83babe8f926.json"
MONITOR_ID = "1oTRqpqS5GIunhi26TO8X6quWR5wWIWoTe0LzFqEGrDs"
GEOCACHE_FILE = "geocache.json"
OUTPUT_FILE = "sold-map.html"

# НСПД для геокодинга по кадастру
NSPD_URL = "https://nspd.gov.ru/api/geoportal/v2/search/geoportal"
NSPD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://nspd.gov.ru/map?thematic=PKK",
}

# DaData для геокодинга по адресу
DADATA_TOKEN = "04143a2e63d9dd14241088e18e89d4ee34fdd8b1"

# Кадастры из облака (OCR + docx + выписки ЕГРН)
CADASTRAL_MAP = {
    12: "59:01:1713303:740",
    14: "59:01:1713129:250",
    15: "59:01:3911449:2",
    16: "59:18:3630207:42",
    21: "59:01:4413637:573",
    23: "59:32:3290001:3223",
    25: "59:32:3020003:1151",
    26: "59:32:3020003:1145",
    28: "59:01:0910221:289",
    29: "78:13:0007438:3113",
    33: "63:22:1602010:1023",
    34: "59:07:0010102:48",
    36: "59:18:3630101:4235",
    37: "59:18:3630101:4235",
    38: "39:05:010211:221",
    39: "39:05:010211:222",
    41: "63:32:0104002:460",
    42: "63:09:0201060:3523",
    43: "59:32:3250001:19596",
    44: "59:32:3250001:19597",
    45: "63:10:0105021:1125",
    46: "63:09:0301136:1988",
    47: "59:01:4713912:434",
    48: "63:22:1503010:2447",
    49: "47:23:1803003:48",
    51: "47:15:0111009:70",
    52: "59:01:4416002:13",
    53: "63:32:0000000:11210",
    54: "59:01:4219248:4453",
    55: "63:01:0637003:803",
    56: "59:32:3290001:13597",
    57: "39:05:050302:263",
    59: "59:01:4410696:1",
    61: "59:01:4410946:5231",
    66: "59:32:3020003:3946",
    67: "63:26:2204004:593",
    68: "63:01:0815001:963",
    69: "59:32:0660001:3492",
    71: "59:32:3020003:3377",
    72: "39:05:030402:539",
    98: "63:01:0513004:1237",
    100: "39:05:050102:628",
}


def load_geocache() -> dict:
    try:
        with open(GEOCACHE_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_geocache(cache: dict):
    with open(GEOCACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def read_monitor() -> list[dict]:
    """Читает все объекты из Монитора."""
    creds = Credentials.from_service_account_file(
        SA_KEY, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)
    result = service.spreadsheets().values().get(
        spreadsheetId=MONITOR_ID, range="'Монитор объектов'!A2:AG200"
    ).execute()
    rows = result.get("values", [])

    objects = []
    for r in rows:
        if len(r) < 3 or not r[1].strip():
            continue
        status = r[2].strip().lower()
        if status not in ("завершен", "завершён", "реализация", "сбор средств"):
            continue

        name = r[1].strip()
        # Извлекаем адрес: после "ИП XX "
        addr_match = re.match(r"ИП\s+\d+\s+(.*)", name)
        address = addr_match.group(1) if addr_match else name
        # Чистим мусор из адреса
        address = re.sub(r"^[_\s]+|[_\s]+$", "", address)
        address = address.replace("_", " ").strip()

        # Извлекаем кадастровый номер из названия или адреса
        cn_match = re.search(r"(\d{2}:\d{2}:\d{5,7}:\d+)", name)
        cadastral = cn_match.group(1) if cn_match else ""

        # Маппинг кадастров из облака (OCR + docx + выписки)
        ip_num_match = re.match(r"(\d+)", r[0] if r[0] else "")
        if ip_num_match and not cadastral:
            ip_n = int(ip_num_match.group(1))
            cadastral = CADASTRAL_MAP.get(ip_n, "")

        objects.append({
            "id": f"ИП {r[0]}" if r[0] else name[:20],
            "name": name,
            "address": address,
            "cadastral": cadastral,
            "status": "sold" if status in ("завершен", "завершён") else "active",
            "purchase": parse_money(r[4]) if len(r) > 4 else 0,
            "sale": parse_money(r[5]) if len(r) > 5 else 0,
            "profit_investors": parse_money(r[9]) if len(r) > 9 else 0,
            "roi": r[10].strip() if len(r) > 10 else "",
            "roi_annual": r[11].strip() if len(r) > 11 else "",
            "days": r[12].strip() if len(r) > 12 else "",
            "months": r[13].strip() if len(r) > 13 else "",
            "date_start": r[14].strip() if len(r) > 14 else "",
            "date_end": r[15].strip() if len(r) > 15 else "",
            "lat": None,
            "lon": None,
        })

    return objects


def parse_money(s: str) -> float:
    if not s:
        return 0.0
    cleaned = re.sub(r"[^\d,.]", "", s.replace("\xa0", "").replace(" ", ""))
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def geocode_nspd(cadastral: str) -> tuple[float, float] | None:
    """Геокодинг через НСПД по кадастровому номеру."""
    import math
    try:
        sess = requests.Session()
        sess.verify = False
        sess.headers.update(NSPD_HEADERS)
        resp = sess.get(NSPD_URL, params={"query": cadastral, "limit": 1}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("data", {}).get("features", [])
        if not features:
            return None
        geom = features[0].get("geometry")
        if not geom:
            return None
        coords = geom.get("coordinates", [])
        gtype = geom.get("type", "")
        if gtype == "Point" and len(coords) >= 2:
            x, y = coords[0], coords[1]
        elif gtype in ("Polygon", "MultiPolygon"):
            # Центроид
            if gtype == "MultiPolygon":
                ring = coords[0][0]
            else:
                ring = coords[0]
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            x, y = sum(xs) / len(xs), sum(ys) / len(ys)
        else:
            return None
        # EPSG:3857 → WGS-84
        lon = x * 180.0 / 20037508.34
        lat = math.atan(math.exp(y * math.pi / 20037508.34)) * 360.0 / math.pi - 90.0
        return (round(lat, 6), round(lon, 6))
    except Exception as e:
        print(f"  НСПД ошибка {cadastral}: {e}")
        return None


def geocode_dadata(address: str) -> tuple[float, float] | None:
    """Геокодинг через DaData по адресу."""
    try:
        resp = requests.post(
            "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address",
            json={"query": address, "count": 1},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Token {DADATA_TOKEN}",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        suggestions = data.get("suggestions", [])
        if suggestions:
            d = suggestions[0].get("data", {})
            lat = d.get("geo_lat")
            lon = d.get("geo_lon")
            if lat and lon:
                return (float(lat), float(lon))
    except Exception as e:
        print(f"  DaData ошибка: {e}")
    return None


def load_properties_geo() -> dict:
    """Загружает координаты из properties_geo.json (Реализация)."""
    try:
        import os
        geo_path = os.path.join(
            os.path.dirname(__file__), "..", "Реализация", "properties_geo.json"
        )
        with open(geo_path) as f:
            data = json.load(f)
        result = {}
        for obj in data:
            if obj.get("lat") and obj.get("lon"):
                # Ключ — ИП ID (например "ИП 22")
                result[obj["id"]] = (obj["lat"], obj["lon"])
        return result
    except Exception:
        return {}


def geocode_objects(objects: list[dict], cache: dict) -> int:
    """Геокодирует объекты. Возвращает кол-во новых геокодов."""
    # Загружаем координаты из Реализации
    geo_lookup = load_properties_geo()
    print(f"  properties_geo.json: {len(geo_lookup)} объектов с координатами")

    new = 0
    for obj in objects:
        # 0. Проверяем properties_geo.json по ID
        if obj["id"] in geo_lookup:
            obj["lat"], obj["lon"] = geo_lookup[obj["id"]]
            continue

        # 1. Проверяем geocache по кадастру
        if obj["cadastral"] and obj["cadastral"] in cache:
            coords = cache[obj["cadastral"]]
            obj["lat"], obj["lon"] = coords[0], coords[1]
            continue

        # 2. НСПД по кадастру
        if obj["cadastral"]:
            print(f"  НСПД: {obj['id']} — {obj['cadastral']}")
            result = geocode_nspd(obj["cadastral"])
            if result:
                obj["lat"], obj["lon"] = result
                cache[obj["cadastral"]] = list(result)
                new += 1
                time.sleep(1)
                continue
            time.sleep(1)

        # 3. DaData по адресу
        addr = obj["address"]
        # Чистим мусор: убираем ЗУ, КВ, КП, НП, ММ, ИП XX, номера лотов
        addr = re.sub(r"^(ЗУ\+?Дом|ЗУ\+?ЖД|ЗУ|КВ|КП|НП|ММ|Аренда\s+ЗУ)\s*", "", addr).strip()
        addr = re.sub(r"^ИП\s*\d+[/\s]*", "", addr).strip()
        addr = re.sub(r"^ИП\s*№?\d+[/\s]*", "", addr).strip()
        addr = re.sub(r",?\s*л\.?\s*\d+.*$", "", addr).strip()  # "л.12", "лот 3"
        addr = re.sub(r",?\s*лот\s*\d+.*$", "", addr).strip()
        addr = re.sub(r",?\s*уч\.?\s*\d+.*$", "", addr).strip()
        addr = re.sub(r",?\s*з/?у\s*\d+.*$", "", addr).strip()
        addr = re.sub(r",?\s*каб\.\s*[\d-]+.*$", "", addr).strip()
        addr = re.sub(r"\s*\(продано\)", "", addr).strip()
        if addr and len(addr) > 10:
            # Добавляем регион если нет
            if not any(w in addr.lower() for w in ("пермск", "москв", "петерб", "калинин", "турци", "чебокс", "самар", "ленин", "соликам")):
                addr = "Пермский край, " + addr
            cache_key = f"addr:{addr}"
            if cache_key in cache:
                coords = cache[cache_key]
                obj["lat"], obj["lon"] = coords[0], coords[1]
                continue

            print(f"  DaData: {obj['id']} — {addr}")
            result = geocode_dadata(addr)
            if result:
                obj["lat"], obj["lon"] = result
                cache[cache_key] = list(result)
                new += 1
                time.sleep(0.5)
                continue

        print(f"  Не геокодирован: {obj['id']} — {obj['address']}")

    return new


def generate_html(objects: list[dict]):
    """Генерирует sold-map.html."""
    sold = [o for o in objects if o["status"] == "sold" and o["lat"]]
    active = [o for o in objects if o["status"] == "active" and o["lat"]]

    def fmt(n):
        if not n:
            return "—"
        return f"{n:,.0f}".replace(",", " ")

    def obj_to_js(obj):
        return json.dumps({
            "id": obj["id"],
            "name": obj["name"],
            "address": obj["address"],
            "lat": obj["lat"],
            "lon": obj["lon"],
            "status": obj["status"],
            "purchase": obj["purchase"],
            "sale": obj["sale"],
            "profit_investors": obj["profit_investors"],
            "roi": obj["roi"],
            "roi_annual": obj["roi_annual"],
            "months": obj["months"],
            "date_start": obj["date_start"],
            "date_end": obj["date_end"],
        }, ensure_ascii=False)

    sold_js = ",\n    ".join(obj_to_js(o) for o in sold)
    active_js = ",\n    ".join(obj_to_js(o) for o in active)

    total_purchase = sum(o["purchase"] for o in sold if o["purchase"])
    total_sale = sum(o["sale"] for o in sold if o["sale"])
    total_profit = total_sale - total_purchase
    avg_roi = sum(float(o["roi"].replace(",", ".").replace("%", "")) for o in sold if o["roi"]) / max(len([o for o in sold if o["roi"]]), 1)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Проданные объекты — Estate Invest</title>
<script src="https://api-maps.yandex.ru/2.1/?lang=ru_RU"></script>
<style>
:root {{
  --bg: #0a0b14; --bg2: #0f1120; --bg3: #161829;
  --card: rgba(22,24,41,0.85);
  --border: rgba(99,102,241,0.18);
  --accent: #6366f1; --accent2: #818cf8;
  --green: #10b981; --yellow: #f59e0b; --red: #ef4444;
  --text: #e2e8f0; --text2: #94a3b8; --text3: #64748b;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Inter', -apple-system, sans-serif; background: var(--bg); color: var(--text); }}
header {{
  background: rgba(10,11,20,0.92); backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
  padding: 16px 24px; display: flex; align-items: center; justify-content: space-between;
}}
.logo {{ font-size: 17px; font-weight: 600; display: flex; align-items: center; gap: 10px; }}
.logo-dot {{
  width: 32px; height: 32px; border-radius: 8px;
  background: linear-gradient(135deg, var(--green), #059669);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: #fff;
}}
.stats {{ display: flex; gap: 24px; }}
.stat {{ text-align: center; }}
.stat-val {{ font-size: 16px; font-weight: 600; color: var(--green); }}
.stat-label {{ font-size: 11px; color: var(--text3); }}
.container {{ display: flex; height: calc(100vh - 64px); }}
#map {{ flex: 1; }}
.sidebar {{
  width: 380px; overflow-y: auto; padding: 16px;
  background: var(--bg2); border-left: 1px solid var(--border);
}}
.sidebar h3 {{ font-size: 14px; color: var(--text2); margin-bottom: 12px; }}
.obj-card {{
  background: var(--bg3); border: 1px solid var(--border);
  border-radius: 10px; padding: 12px; margin-bottom: 8px;
  cursor: pointer; transition: border-color 0.2s;
}}
.obj-card:hover {{ border-color: var(--accent); }}
.obj-card.sold {{ border-left: 3px solid var(--green); }}
.obj-card.active {{ border-left: 3px solid var(--yellow); }}
.obj-name {{ font-size: 13px; font-weight: 600; margin-bottom: 6px; }}
.obj-row {{ display: flex; justify-content: space-between; font-size: 12px; color: var(--text2); }}
.obj-row .val {{ color: var(--text); font-weight: 500; }}
.obj-roi {{ color: var(--green); font-weight: 600; }}
.badge {{ font-size: 10px; padding: 2px 8px; border-radius: 4px; font-weight: 600; }}
.badge-sold {{ background: rgba(16,185,129,0.15); color: var(--green); }}
.badge-active {{ background: rgba(245,158,11,0.15); color: var(--yellow); }}
.filter-row {{ display: flex; gap: 8px; margin-bottom: 16px; }}
.filter-btn {{
  padding: 6px 14px; border-radius: 8px; border: 1px solid var(--border);
  background: transparent; color: var(--text2); font-size: 12px;
  cursor: pointer; font-family: inherit; transition: all 0.2s;
}}
.filter-btn.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
</style>
</head>
<body>
<header>
  <div class="logo">
    <div class="logo-dot">EI</div>
    Проданные объекты
  </div>
  <div class="stats">
    <div class="stat">
      <div class="stat-val">{len(sold)}</div>
      <div class="stat-label">Продано</div>
    </div>
    <div class="stat">
      <div class="stat-val">{len(active)}</div>
      <div class="stat-label">В продаже</div>
    </div>
    <div class="stat">
      <div class="stat-val">{fmt(total_profit)}</div>
      <div class="stat-label">Общая прибыль</div>
    </div>
    <div class="stat">
      <div class="stat-val">{avg_roi:.1f}%</div>
      <div class="stat-label">Средний ROI</div>
    </div>
  </div>
</header>
<div class="container">
  <div id="map"></div>
  <div class="sidebar">
    <div class="filter-row">
      <button class="filter-btn active" onclick="setFilter('all')">Все</button>
      <button class="filter-btn" onclick="setFilter('sold')">Продано</button>
      <button class="filter-btn" onclick="setFilter('active')">В продаже</button>
    </div>
    <h3>Объекты</h3>
    <div id="cards"></div>
  </div>
</div>
<script>
const SOLD = [
    {sold_js}
];
const ACTIVE = [
    {active_js}
];
const ALL = [...SOLD, ...ACTIVE];

let map, currentFilter = 'all', placemarks = [];

ymaps.ready(function() {{
  map = new ymaps.Map('map', {{
    center: [58.0, 56.3],
    zoom: 10,
    controls: ['zoomControl']
  }});
  renderAll();
}});

function fmt(n) {{
  if (!n) return '—';
  return Math.round(n).toLocaleString('ru-RU');
}}

function setFilter(f) {{
  currentFilter = f;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  renderAll();
}}

function renderAll() {{
  // Clear
  placemarks.forEach(p => map.geoObjects.remove(p));
  placemarks = [];

  const items = currentFilter === 'all' ? ALL :
                currentFilter === 'sold' ? SOLD : ACTIVE;

  // Cards
  const container = document.getElementById('cards');
  container.innerHTML = '';
  items.forEach((obj, i) => {{
    const isSold = obj.status === 'sold';
    const card = document.createElement('div');
    card.className = 'obj-card ' + obj.status;
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
        <span class="obj-name">${{obj.id}}</span>
        <span class="badge ${{isSold ? 'badge-sold' : 'badge-active'}}">${{isSold ? 'Продан' : 'В продаже'}}</span>
      </div>
      <div style="font-size:11px;color:var(--text3);margin-bottom:6px">${{obj.address}}</div>
      <div class="obj-row"><span>Покупка</span><span class="val">${{fmt(obj.purchase)}}</span></div>
      <div class="obj-row"><span>Продажа</span><span class="val">${{fmt(obj.sale)}}</span></div>
      ${{obj.roi ? `<div class="obj-row"><span>ROI</span><span class="obj-roi">${{obj.roi}}</span></div>` : ''}}
      ${{obj.months ? `<div class="obj-row"><span>Срок</span><span class="val">${{obj.months}} мес</span></div>` : ''}}
    `;
    card.onclick = () => {{
      map.setCenter([obj.lat, obj.lon], 14, {{duration: 300}});
    }};
    container.appendChild(card);

    // Placemark
    const color = isSold ? '#10b981' : '#f59e0b';
    const pm = new ymaps.Placemark([obj.lat, obj.lon], {{
      balloonContentHeader: `<b>${{obj.id}}</b> <span style="color:${{color}}">${{isSold ? 'Продан' : 'В продаже'}}</span>`,
      balloonContentBody: `
        <div>${{obj.address}}</div>
        <div style="margin-top:6px">
          <b>Покупка:</b> ${{fmt(obj.purchase)}} руб<br>
          <b>Продажа:</b> ${{fmt(obj.sale)}} руб<br>
          ${{obj.roi ? `<b>ROI:</b> ${{obj.roi}}<br>` : ''}}
          ${{obj.months ? `<b>Срок:</b> ${{obj.months}} мес` : ''}}
        </div>
      `,
      hintContent: obj.id
    }}, {{
      preset: isSold ? 'islands#greenDotIcon' : 'islands#yellowDotIcon'
    }});
    map.geoObjects.add(pm);
    placemarks.push(pm);
  }});

  // Fit bounds
  if (placemarks.length > 1) {{
    const bounds = map.geoObjects.getBounds();
    if (bounds) map.setBounds(bounds, {{checkZoomRange: true, zoomMargin: 50}});
  }}
}}

// Подгрузка кадастровых границ из Supabase
async function loadBoundaries() {{
  try {{
    const resp = await fetch(
      'https://eeahxalvnvbroswzyfjx.supabase.co/rest/v1/properties?select=lot_id,cadastral_number,boundary_geojson&boundary_geojson=not.is.null',
      {{ headers: {{ apikey: 'sb_publishable_JO8ZrGiCpncWrffYQO9LoQ_OOAwQj2V' }} }}
    );
    const lots = await resp.json();
    lots.forEach(lot => {{
      if (!lot.boundary_geojson || !lot.boundary_geojson.coordinates) return;
      const coords = lot.boundary_geojson.coordinates[0].map(p => [p[1], p[0]]);
      const polygon = new ymaps.Polygon([coords], {{
        hintContent: lot.cadastral_number
      }}, {{
        fillColor: '#6366f120',
        strokeColor: '#6366f1',
        strokeWidth: 1,
        strokeStyle: 'dash'
      }});
      map.geoObjects.add(polygon);
    }});
    console.log('Загружено границ:', lots.length);
  }} catch(e) {{
    console.error('Ошибка загрузки границ:', e);
  }}
}}

// Чекбокс для границ
map.events.once('boundschange', () => loadBoundaries());
</script>
</body>
</html>"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nГотово: {OUTPUT_FILE}")
    print(f"  Продано: {len(sold)} (с координатами)")
    print(f"  В продаже: {len(active)} (с координатами)")
    print(f"  Без координат: {len([o for o in objects if not o['lat']])}")


def main():
    print("=== Карта проданных объектов Estate Invest ===\n")

    print("Читаю Монитор объектов...")
    objects = read_monitor()
    sold = [o for o in objects if o["status"] == "sold"]
    active = [o for o in objects if o["status"] == "active"]
    print(f"  Всего: {len(objects)} (продано: {len(sold)}, в продаже: {len(active)})")

    print("\nЗагружаю geocache...")
    cache = load_geocache()
    print(f"  Записей в кеше: {len(cache)}")

    print("\nГеокодирую...")
    new_geocodes = geocode_objects(objects, cache)
    print(f"  Новых геокодов: {new_geocodes}")

    save_geocache(cache)
    print(f"  Кеш сохранён: {len(cache)} записей")

    print("\nГенерирую HTML...")
    generate_html(objects)


if __name__ == "__main__":
    main()
