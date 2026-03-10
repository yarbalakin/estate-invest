#!/usr/bin/env python3
"""
Генератор карты объектов Estate Invest.
Извлекает данные из реализация-сводка.html, геокодирует через DaData и ПКК,
генерирует objects-map.html.
"""

import re
import html as htmllib
import json
import time
import requests
import sys

DADATA_TOKEN = "04143a2e63d9dd14241088e18e89d4ee34fdd8b1"
DADATA_SECRET = "8e40f11034823d741339058fbbeadfd545039157"

INPUT_FILE = "реализация-сводка.html"
OUTPUT_FILE = "objects-map.html"


def clean(text):
    return htmllib.unescape(re.sub(r'<[^>]+>', '', text)).strip()


def parse_properties(html):
    cards = re.split(r'<div class="property-card">', html)[1:]
    properties = []
    for card in cards:
        def g(pattern, group=1, default=''):
            m = re.search(pattern, card)
            return clean(m.group(group)) if m else default

        ip_num = g(r'<span class="ip-num">(.*?)</span>')
        ip_name = g(r'<span class="ip-name">(.*?)</span>')
        kadastr = g(r'<span class="kadastr-value">(.*?)</span>')
        address = g(r'<span class="address-value">(.*?)</span>')
        type_tag = g(r'<span class="type-tag">(.*?)</span>')
        area_tag = g(r'<span class="area-tag">(.*?)</span>')
        status_m = re.search(r'<span class="badge badge-(active|collect)">(.*?)</span>', card)
        status = clean(status_m.group(2)) if status_m else ''
        responsible = g(r'<span class="responsible">(.*?)</span>')
        roi = g(r'<span class="roi">(.*?)</span>')
        date_info = g(r'<span class="date-info">(.*?)</span>')

        fin_values = re.findall(r'<div class="fin-value(?:[^"]*)?">([^<]*(?:<[^/][^<]*>)?[^<]*)</div>', card)
        fin_values = [clean(v) for v in fin_values]

        price_buy = fin_values[0] if len(fin_values) > 0 else ''
        price_sell = fin_values[1] if len(fin_values) > 1 else ''
        profit = fin_values[2] if len(fin_values) > 2 else ''

        avito_links = re.findall(r'<a href="(https://www\.avito\.ru[^"]+)"[^>]+>([^<]+)</a>', card)

        # Первый кадастровый номер (если их несколько через /)
        cn_primary = kadastr.split('/')[0].strip()
        cn_primary = re.sub(r'^[^0-9]*', '', cn_primary).strip()
        # Очистить от мусора типа "уч. 13: "
        cn_match = re.search(r'(\d{2}:\d{2,6}:\d+:\d+)', cn_primary)
        cn_clean = cn_match.group(1) if cn_match else cn_primary

        properties.append({
            'id': ip_num,
            'name': ip_name,
            'cadastral': kadastr,
            'cadastral_primary': cn_clean,
            'address': address,
            'type': type_tag,
            'area': area_tag,
            'status': status,
            'responsible': responsible,
            'roi': roi,
            'date_info': date_info,
            'price_buy': price_buy,
            'price_sell': price_sell,
            'profit': profit,
            'avito_links': avito_links,
            'lat': None,
            'lon': None,
        })
    return properties


def geocode_dadata(address):
    """Геокодирование через DaData Suggestions API"""
    # Пробуем оригинальный адрес и укороченные варианты
    queries = [address]
    # Убираем "Российская Федерация," если есть
    short = re.sub(r'^Российская Федерация,\s*', '', address).strip()
    if short != address:
        queries.append(short)
    # Ещё короче — только последние части
    parts = [p.strip() for p in short.split(',')]
    if len(parts) >= 3:
        queries.append(', '.join(parts[-3:]))
    if len(parts) >= 2:
        queries.append(', '.join(parts[-2:]))

    for q in queries:
        if not q:
            continue
        try:
            r = requests.post(
                'https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address',
                headers={
                    'Authorization': f'Token {DADATA_TOKEN}',
                    'Content-Type': 'application/json',
                },
                json={'query': q, 'count': 1},
                timeout=10
            )
            data = r.json()
            suggestions = data.get('suggestions', [])
            if suggestions:
                d = suggestions[0]['data']
                lat = d.get('geo_lat')
                lon = d.get('geo_lon')
                if lat and lon:
                    return float(lat), float(lon)
        except Exception as e:
            print(f"  DaData error: {e}")
    return None, None


def geocode_all(properties):
    total = len(properties)
    for i, prop in enumerate(properties):
        print(f"[{i+1}/{total}] {prop['id']}: {prop['address'][:50] if prop['address'] else prop['cadastral_primary']}...")

        lat, lon = None, None

        if prop['address']:
            lat, lon = geocode_dadata(prop['address'])
            if lat:
                print(f"  OK: {lat:.4f}, {lon:.4f}")
            else:
                print(f"  FAILED")

        prop['lat'] = lat
        prop['lon'] = lon
        time.sleep(0.15)  # Не спамим API

    found = sum(1 for p in properties if p['lat'])
    print(f"\nГеокодировано: {found}/{total}")
    return properties


def generate_html(properties):
    # Центр карты — средние координаты объектов
    coords = [(p['lat'], p['lon']) for p in properties if p['lat']]
    if coords:
        center_lat = sum(c[0] for c in coords) / len(coords)
        center_lon = sum(c[1] for c in coords) / len(coords)
    else:
        center_lat, center_lon = 57.9908, 56.2502  # Пермь

    # Сериализуем данные для JS
    props_json = json.dumps(properties, ensure_ascii=False, indent=2)

    html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Карта объектов — Estate Invest</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
:root {{
  --bg: #0a0b14; --bg2: #0f1120; --bg3: #161829;
  --card: rgba(22,24,41,0.95);
  --border: rgba(99,102,241,0.18); --border2: rgba(99,102,241,0.35);
  --accent: #6366f1; --accent2: #818cf8;
  --green: #10b981; --amber: #f59e0b; --blue: #60a5fa; --purple: #a78bfa;
  --red: #ef4444;
  --text: #e2e8f0; --text2: #94a3b8; --text3: #64748b;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg); color: var(--text);
  height: 100vh; display: flex; flex-direction: column; overflow: hidden;
}}

header {{
  flex-shrink: 0;
  background: rgba(10,11,20,0.95); backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
  padding: 0 20px; height: 52px;
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  z-index: 1000; position: relative;
}}
.logo {{ display: flex; align-items: center; gap: 10px; font-size: 15px; font-weight: 600; }}
.logo-dot {{
  width: 26px; height: 26px; border-radius: 7px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700;
}}
.header-stats {{ display: flex; gap: 20px; }}
.hstat {{ display: flex; flex-direction: column; align-items: center; }}
.hstat-v {{ font-size: 15px; font-weight: 700; }}
.hstat-l {{ font-size: 10px; color: var(--text2); text-transform: uppercase; letter-spacing: 0.4px; }}
.hstat-v.green {{ color: var(--green); }}
.hstat-v.blue {{ color: var(--blue); }}
.hstat-v.amber {{ color: var(--amber); }}

.map-container {{ flex: 1; position: relative; }}

#map {{
  position: absolute; inset: 0;
  background: #0f1120;
}}

/* Popup стиль */
.leaflet-popup-content-wrapper {{
  background: var(--card) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 12px !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important;
  color: var(--text) !important;
  backdrop-filter: blur(20px);
  max-width: 320px;
}}
.leaflet-popup-tip {{ background: rgba(22,24,41,0.95) !important; }}
.leaflet-popup-content {{ margin: 0 !important; }}

.popup {{
  padding: 14px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 13px;
  color: var(--text);
}}
.popup-header {{ margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }}
.popup-id {{
  display: inline-block; font-size: 10px; font-weight: 700;
  background: var(--accent); color: white; padding: 2px 8px;
  border-radius: 5px; margin-bottom: 6px;
}}
.popup-name {{ font-size: 12px; font-weight: 600; line-height: 1.4; color: var(--text); margin-bottom: 6px; }}
.popup-tags {{ display: flex; gap: 5px; flex-wrap: wrap; }}
.tag {{ font-size: 10px; padding: 2px 7px; border-radius: 4px; }}
.tag-type {{ background: rgba(96,165,250,0.15); color: var(--blue); border: 1px solid rgba(96,165,250,0.25); }}
.tag-status-active {{ background: rgba(16,185,129,0.15); color: var(--green); border: 1px solid rgba(16,185,129,0.25); }}
.tag-status-collect {{ background: rgba(245,158,11,0.15); color: var(--amber); border: 1px solid rgba(245,158,11,0.25); }}
.tag-responsible {{ background: rgba(167,139,250,0.1); color: var(--purple); border: 1px solid rgba(167,139,250,0.2); }}

.popup-body {{ display: flex; flex-direction: column; gap: 7px; }}
.popup-row {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; }}
.popup-label {{ font-size: 10px; color: var(--text2); text-transform: uppercase; letter-spacing: 0.4px; }}
.popup-value {{ font-size: 12px; font-weight: 600; }}
.popup-value.green {{ color: var(--green); }}
.popup-value.purple {{ color: var(--purple); }}
.popup-value.amber {{ color: var(--amber); font-family: monospace; font-size: 11px; }}

.popup-kadastr {{ font-size: 10px; color: var(--text3); margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border); }}
.popup-address {{ font-size: 10px; color: var(--text3); margin-top: 2px; line-height: 1.4; }}

.popup-links {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border); }}
.popup-link {{
  font-size: 10px; color: var(--accent); text-decoration: none;
  background: rgba(99,102,241,0.1); padding: 2px 8px; border-radius: 4px;
  border: 1px solid rgba(99,102,241,0.2);
}}
.popup-link:hover {{ background: rgba(99,102,241,0.2); }}

/* Легенда */
.legend {{
  position: absolute; bottom: 20px; right: 20px; z-index: 500;
  background: var(--card); border: 1px solid var(--border);
  border-radius: 10px; padding: 12px 14px;
  font-size: 11px; backdrop-filter: blur(20px);
  min-width: 160px;
}}
.legend-title {{ font-weight: 600; font-size: 11px; color: var(--text2); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }}
.legend-item {{ display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }}
.legend-dot {{ width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }}

/* Фильтры */
.filters {{
  position: absolute; top: 12px; left: 60px; z-index: 500;
  display: flex; gap: 6px; flex-wrap: wrap;
}}
.filter-btn {{
  font-size: 11px; padding: 4px 12px; border-radius: 16px; cursor: pointer;
  border: 1px solid var(--border2); background: var(--card);
  color: var(--text2); transition: all 0.2s; backdrop-filter: blur(10px);
}}
.filter-btn:hover, .filter-btn.active {{
  background: var(--accent); color: white; border-color: var(--accent);
}}

/* Кнопка ПКК слоя */
.layer-toggle {{
  position: absolute; top: 12px; right: 20px; z-index: 500;
  font-size: 11px; padding: 5px 12px; border-radius: 8px; cursor: pointer;
  border: 1px solid var(--border2); background: var(--card);
  color: var(--text2); transition: all 0.2s; backdrop-filter: blur(10px);
}}
.layer-toggle.active {{ background: rgba(99,102,241,0.2); color: var(--accent2); border-color: var(--accent); }}

.leaflet-control-zoom a {{
  background: var(--bg3) !important;
  color: var(--text) !important;
  border-color: var(--border) !important;
}}
.leaflet-control-zoom a:hover {{
  background: var(--bg2) !important;
}}
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-dot">EI</div>
    <span>Карта объектов</span>
  </div>
  <div class="header-stats" id="hstats">
    <div class="hstat"><div class="hstat-v blue" id="h-total">—</div><div class="hstat-l">Объектов</div></div>
    <div class="hstat"><div class="hstat-v green" id="h-active">—</div><div class="hstat-l">Реализация</div></div>
    <div class="hstat"><div class="hstat-v amber" id="h-collect">—</div><div class="hstat-l">Сбор</div></div>
    <div class="hstat"><div class="hstat-v" id="h-geodone">—</div><div class="hstat-l">На карте</div></div>
  </div>
</header>

<div class="map-container">
  <div id="map"></div>

  <div class="filters" id="filters">
    <button class="filter-btn active" data-filter="all">Все</button>
    <button class="filter-btn" data-filter="земельный участок">Земля</button>
    <button class="filter-btn" data-filter="квартира">Квартиры</button>
    <button class="filter-btn" data-filter="нежилое помещение">Нежилые</button>
  </div>

  <button class="layer-toggle" id="pkk-toggle">ПКК слой</button>

  <div class="legend">
    <div class="legend-title">Тип объекта</div>
    <div class="legend-item"><div class="legend-dot" style="background:#10b981"></div><span>Земельный участок</span></div>
    <div class="legend-item"><div class="legend-dot" style="background:#60a5fa"></div><span>Квартира</span></div>
    <div class="legend-item"><div class="legend-dot" style="background:#f59e0b"></div><span>Нежилое</span></div>
    <div class="legend-item"><div class="legend-dot" style="background:#a78bfa"></div><span>Другое</span></div>
    <div class="legend-item" style="margin-top:6px;padding-top:6px;border-top:1px solid rgba(99,102,241,0.18)">
      <div class="legend-dot" style="background:rgba(99,102,241,0.5);border:2px solid #6366f1"></div>
      <span style="color:#8b92a8">Сбор средств</span>
    </div>
  </div>
</div>

<script>
const PROPERTIES = {props_json};

// Цвет по типу
function typeColor(type) {{
  if (!type) return '#a78bfa';
  const t = type.toLowerCase();
  if (t.includes('земел') || t.includes('участок')) return '#10b981';
  if (t.includes('кварт') || t.includes('жил')) return '#60a5fa';
  if (t.includes('нежил') || t.includes('помещен') || t.includes('здани') || t.includes('офис')) return '#f59e0b';
  return '#a78bfa';
}}

function makeIcon(color, status) {{
  const isCollect = status && status.includes('сбор');
  const size = 14;
  const opacity = isCollect ? 0.6 : 1;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="40" viewBox="0 0 32 40">
    <filter id="shadow">
      <feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.4"/>
    </filter>
    <path d="M16 0C7.163 0 0 7.163 0 16c0 8.837 16 24 16 24s16-15.163 16-24C32 7.163 24.837 0 16 0z"
      fill="${{color}}" opacity="${{opacity}}" filter="url(#shadow)"/>
    <circle cx="16" cy="15" r="6" fill="white" opacity="0.9"/>
    ${{isCollect ? '<circle cx="25" cy="6" r="5" fill="#f59e0b"/>' : ''}}
  </svg>`;
  return L.divIcon({{
    html: svg,
    className: '',
    iconSize: [32, 40],
    iconAnchor: [16, 40],
    popupAnchor: [0, -40],
  }});
}}

function makePopup(p) {{
  const statusClass = p.status && p.status.includes('сбор') ? 'tag-status-collect' : 'tag-status-active';
  const links = (p.avito_links || []).map(([url, text]) =>
    `<a href="${{url}}" class="popup-link" target="_blank">${{text}} ↗</a>`
  ).join('');
  return `<div class="popup">
    <div class="popup-header">
      <div class="popup-id">${{p.id}}</div>
      <div class="popup-name">${{p.name}}</div>
      <div class="popup-tags">
        ${{p.type ? `<span class="tag tag-type">${{p.type}}</span>` : ''}}
        ${{p.status ? `<span class="tag ${{statusClass}}">${{p.status}}</span>` : ''}}
        ${{p.responsible ? `<span class="tag tag-responsible">${{p.responsible.split(' ')[0]}}</span>` : ''}}
      </div>
    </div>
    <div class="popup-body">
      ${{p.price_buy ? `<div class="popup-row">
        <span class="popup-label">Покупка</span>
        <span class="popup-value">${{p.price_buy}}</span>
      </div>` : ''}}
      ${{p.price_sell ? `<div class="popup-row">
        <span class="popup-label">Целевая</span>
        <span class="popup-value green">${{p.price_sell}}</span>
      </div>` : ''}}
      ${{p.roi ? `<div class="popup-row">
        <span class="popup-label">ROI</span>
        <span class="popup-value purple">${{p.roi}}</span>
      </div>` : ''}}
      ${{p.area ? `<div class="popup-row">
        <span class="popup-label">Площадь</span>
        <span class="popup-value">${{p.area}}</span>
      </div>` : ''}}
    </div>
    ${{p.cadastral ? `<div class="popup-kadastr">Кадастр: <span style="color:var(--amber);font-family:monospace">${{p.cadastral}}</span></div>` : ''}}
    ${{p.address ? `<div class="popup-address">${{p.address}}</div>` : ''}}
    ${{links ? `<div class="popup-links">${{links}}</div>` : ''}}
  </div>`;
}}

// Инициализация карты
const map = L.map('map', {{
  center: [{center_lat:.4f}, {center_lon:.4f}],
  zoom: 9,
  zoomControl: true,
}});

// Яндекс тайлы (тёмные)
const yandexLayer = L.tileLayer(
  'https://core-renderer-tiles.maps.yandex.net/tiles?l=map&x={{x}}&y={{y}}&z={{z}}&lang=ru_RU',
  {{ attribution: '© Яндекс', maxZoom: 18, tileSize: 256 }}
).addTo(map);

// ПКК слой (кадастровые границы)
const pkkLayer = L.tileLayer(
  'https://pkk.rosreestr.ru/arcgis/rest/services/PKK6/CadastreObjects/MapServer/tile/{{z}}/{{y}}/{{x}}',
  {{ attribution: '© Росреестр ПКК', maxZoom: 20, opacity: 0.6 }}
);
let pkkActive = false;

document.getElementById('pkk-toggle').addEventListener('click', function() {{
  pkkActive = !pkkActive;
  if (pkkActive) {{ pkkLayer.addTo(map); this.classList.add('active'); }}
  else {{ map.removeLayer(pkkLayer); this.classList.remove('active'); }}
}});

// Маркеры
const markers = [];
const markerLayers = L.layerGroup().addTo(map);

let filterType = 'all';

function renderMarkers() {{
  markerLayers.clearLayers();
  const visible = PROPERTIES.filter(p => {{
    if (!p.lat || !p.lon) return false;
    if (filterType === 'all') return true;
    return p.type && p.type.toLowerCase().includes(filterType.toLowerCase());
  }});

  visible.forEach(p => {{
    const color = typeColor(p.type);
    const icon = makeIcon(color, p.status);
    const marker = L.marker([p.lat, p.lon], {{ icon }})
      .bindPopup(makePopup(p), {{ maxWidth: 320, className: 'dark-popup' }});
    markerLayers.addLayer(marker);
  }});
}}

// Фильтры
document.querySelectorAll('.filter-btn').forEach(btn => {{
  btn.addEventListener('click', function() {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    filterType = this.dataset.filter === 'all' ? 'all' : this.dataset.filter;
    renderMarkers();
  }});
}});

// Статистика в шапке
const total = PROPERTIES.length;
const withCoords = PROPERTIES.filter(p => p.lat).length;
const active = PROPERTIES.filter(p => p.status && p.status.includes('реализ')).length;
const collect = PROPERTIES.filter(p => p.status && p.status.includes('сбор')).length;

document.getElementById('h-total').textContent = total;
document.getElementById('h-active').textContent = active;
document.getElementById('h-collect').textContent = collect;
document.getElementById('h-geodone').textContent = withCoords;

renderMarkers();

// Кластеризация при зуме
map.on('zoomend', function() {{
  // При зуме < 10 показываем все, при > 14 увеличиваем маркеры
}});
</script>
</body>
</html>'''
    return html


def main():
    print(f"Читаю {INPUT_FILE}...")
    with open(INPUT_FILE, 'r') as f:
        html_content = f.read()

    print("Парсинг объектов...")
    properties = parse_properties(html_content)
    print(f"Найдено {len(properties)} объектов")

    # Проверяем нужно ли геокодировать
    cache_file = 'properties_geo.json'
    import os
    if os.path.exists(cache_file) and '--no-cache' not in sys.argv:
        print(f"Загружаю координаты из кеша ({cache_file})...")
        with open(cache_file) as f:
            cached = json.load(f)
        # Обновляем координаты из кеша
        cached_map = {p['id']: p for p in cached}
        for prop in properties:
            if prop['id'] in cached_map:
                prop['lat'] = cached_map[prop['id']].get('lat')
                prop['lon'] = cached_map[prop['id']].get('lon')
    else:
        print("Геокодирую...")
        properties = geocode_all(properties)
        print(f"Сохраняю кеш в {cache_file}...")
        with open(cache_file, 'w') as f:
            json.dump(properties, f, ensure_ascii=False, indent=2)

    print(f"Генерирую {OUTPUT_FILE}...")
    html = generate_html(properties)
    with open(OUTPUT_FILE, 'w') as f:
        f.write(html)

    found = sum(1 for p in properties if p['lat'])
    print(f"Готово! {found}/{len(properties)} объектов с координатами")
    print(f"Файл: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
