#!/usr/bin/env python3
"""
Генератор реализация-сводка.html из 3 Google Sheets:
1. Монитор объектов — финансы (покупка, продажа, ROI, даты, Avito)
2. Звонок по реализации — ответственный, город, еженедельные новости
3. Estate учёт (Объекты) — тип, площадь, Notion

Также парсит существующий HTML для кадастровых номеров и адресов.

Использование:
  python3 generate_svodka.py
"""

import re
import html as htmllib
import json
import datetime
import math
import os
import time
import google.oauth2.service_account
import googleapiclient.discovery

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _requests_ok = True
except ImportError:
    _requests_ok = False

# ─── Конфигурация ───────────────────────────────────────────────────
SERVICE_ACCOUNT_KEY = "/Users/yaroslavbalakin/Downloads/powerful-hall-488221-t2-b83babe8f926.json"

# Монитор объектов
MONITOR_ID = "1oTRqpqS5GIunhi26TO8X6quWR5wWIWoTe0LzFqEGrDs"

# Звонок по реализации
CALLS_ID = "1S8Jog2Qv29R75Mp8QORvFjBY8Qhxr7csVYS4EDKQzGg"
CALLS_SHEET = "Звонок 2026"

# Estate учёт
ESTATE_ID = "1dWTjYF8sEc20SKeyl-e6PomBFq3VlfX-m8K2ZRopZJ0"
ESTATE_OBJECTS_RANGE = "Объекты!A5:R200"

EXISTING_HTML = "реализация-сводка.html"
OUTPUT_HTML = "реализация-сводка.html"

# Сколько последних новостей показывать
MAX_NEWS = 8

# Файл кеша геокодинга (чтобы не запрашивать НСПД повторно)
GEOCACHE_FILE = os.path.join(os.path.dirname(__file__), "geocache.json")
NSPD_URL = "https://nspd.gov.ru/api/geoportal/v2/search/geoportal"


# ─── Геокодинг через НСПД ───────────────────────────────────────────
def _load_geocache():
    try:
        with open(GEOCACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_geocache(cache):
    with open(GEOCACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _epsg3857_to_wgs84(x, y):
    lon = x * 180.0 / 20037508.34
    lat = math.atan(math.exp(y * math.pi / 20037508.34)) * 360.0 / math.pi - 90.0
    return round(lat, 6), round(lon, 6)


def _extract_centroid(geom):
    """GeoJSON geometry (EPSG:3857) → (lat, lon) WGS-84 или None."""
    if not geom:
        return None
    gtype = geom.get("type", "")
    coords = geom.get("coordinates", [])
    if not coords:
        return None

    if gtype == "Point":
        ring = [coords] if isinstance(coords[0], (int, float)) else None
    elif gtype == "Polygon":
        ring = coords[0] if coords else None
    elif gtype == "MultiPolygon":
        try:
            ring = coords[0][0]
        except (IndexError, TypeError):
            return None
    else:
        return None

    if not ring:
        return None

    # Плоский массив [x, y, x, y, ...]
    if isinstance(ring[0], (int, float)):
        ring = [[ring[i], ring[i + 1]] for i in range(0, len(ring) - 1, 2)]
    # Вложенный ещё один уровень
    if ring and isinstance(ring[0], list) and ring[0] and isinstance(ring[0][0], list):
        ring = ring[0]

    if not ring:
        return None

    xs = [p[0] for p in ring if isinstance(p, (list, tuple)) and len(p) >= 2]
    ys = [p[1] for p in ring if isinstance(p, (list, tuple)) and len(p) >= 2]
    if not xs:
        return None
    lat, lon = _epsg3857_to_wgs84(sum(xs) / len(xs), sum(ys) / len(ys))
    return lat, lon


def geocode_nspd(cadastral_number, cache):
    """Кадастровый номер → (lat, lon) через НСПД. Использует кеш."""
    if not cadastral_number or not _requests_ok:
        return None, None

    # Берём первый номер из составного (через | , ;)
    cn = re.split(r"[\s|,;]+", cadastral_number.strip())[0].strip()
    if not re.match(r"^\d{2}:\d{2,6}:\d+:\d+$", cn):
        return None, None

    if cn in cache:
        cached = cache[cn]
        return (cached[0], cached[1]) if cached else (None, None)

    try:
        resp = requests.get(
            NSPD_URL,
            params={"query": cn, "limit": 1},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://nspd.gov.ru",
                "Referer": f"https://nspd.gov.ru/map?search={cn}",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
            },
            timeout=15,
            verify=False,
        )
        resp.raise_for_status()
        data = resp.json()
        features = data.get("data", {}).get("features", [])
        if not features:
            cache[cn] = None
            return None, None

        geom = features[0].get("geometry")
        result = _extract_centroid(geom)
        cache[cn] = list(result) if result else None
        return result if result else (None, None)

    except Exception as e:
        print(f"    НСПД {cn}: {e}")
        return None, None


# ─── Google Sheets API ──────────────────────────────────────────────
def get_sheets_service():
    creds = google.oauth2.service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_KEY,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    return googleapiclient.discovery.build("sheets", "v4", credentials=creds)


def read_sheet(service, spreadsheet_id, range_):
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_)
        .execute()
    )
    return result.get("values", [])


# ─── Кеш кадастровых номеров (переживает перегенерацию HTML) ────────
CADASTRALS_FILE = os.path.join(os.path.dirname(__file__), "cadastrals.json")

def _load_cadastrals():
    try:
        with open(CADASTRALS_FILE, encoding="utf-8") as f:
            raw = json.load(f)
            return {int(k): v for k, v in raw.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_cadastrals(data):
    with open(CADASTRALS_FILE, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in data.items()}, f, ensure_ascii=False, indent=2)


# ─── Парсинг существующего HTML (кадастр + адрес) ───────────────────
def parse_existing_html(filepath):
    """Извлекает кадастр и адрес из существующего HTML по номеру ИП.
    Найденные кадастры сохраняет в cadastrals.json — так они выживают после перегенерации."""
    saved = _load_cadastrals()

    try:
        with open(filepath, "r") as f:
            html_content = f.read()
    except FileNotFoundError:
        # HTML нет — возвращаем то, что есть в кеше
        return {k: {"cadastral": v.get("cadastral", ""), "address": v.get("address", "")} for k, v in saved.items()}

    static = {}
    cards = re.split(r'<div class="property-card"[^>]*>', html_content)[1:]
    for card in cards:
        ip_m = re.search(r'<span class="ip-num">(.*?)</span>', card)
        if not ip_m:
            continue
        ip_text = htmllib.unescape(re.sub(r"<[^>]+>", "", ip_m.group(1))).strip()
        ip_num = extract_ip_number(ip_text)
        if ip_num is None:
            continue

        kadastr_m = re.search(r'<span class="kadastr-value">(.*?)</span>', card)
        address_m = re.search(r'<span class="address-value">(.*?)</span>', card)

        kadastr = htmllib.unescape(kadastr_m.group(1)).strip() if kadastr_m else ""
        address = htmllib.unescape(address_m.group(1)).strip() if address_m else ""

        static[ip_num] = {"cadastral": kadastr, "address": address}

    # Обновляем кеш: только непустые кадастры
    merged = {**saved, **{k: v for k, v in static.items() if v.get("cadastral")}}
    _save_cadastrals(merged)

    # Возвращаем: JSON-кеш как база, HTML перезаписывает только если там есть данные
    result = dict(saved)
    for ip, data in static.items():
        if data.get("cadastral"):
            result[ip] = data
        elif ip not in result:
            result[ip] = data
    return result



# ─── Утилиты ────────────────────────────────────────────────────────
def extract_ip_number(name):
    """Извлекает номер ИП из строки вида 'ИП 19 ...' или 'ИП №19/...'"""
    m = re.search(r"ИП\s*[№#]?\s*(\d+)", name, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def parse_money(val):
    """'5 028 170,99' → 5028170.99"""
    if not val or not val.strip():
        return 0.0
    clean = val.replace("\xa0", "").replace(" ", "").replace("р.", "").replace(",", ".").replace("%", "").strip()
    try:
        return float(clean)
    except ValueError:
        return 0.0


def format_money(val):
    """5028170.99 → '5.0 млн ₽' или '845 тыс ₽'"""
    if val == 0:
        return "—"
    if val >= 1_000_000:
        return f"{val/1_000_000:.1f} млн ₽"
    if val >= 1000:
        return f"{val/1000:.0f} тыс ₽"
    return f"{val:.0f} ₽"


def format_pct(val):
    """'19,96%' → '19,96%' (passthrough с очисткой)"""
    if not val or not val.strip():
        return "—"
    return val.strip()


def format_area(val):
    """'18998' → '18998 м²' или '116,2' → '116.2 м²'"""
    if not val or not val.strip() or val.strip() == "0":
        return ""
    clean = val.replace(",", ".").strip()
    try:
        num = float(clean)
        if num == int(num):
            return f"{int(num)} м²"
        return f"{num} м²"
    except ValueError:
        return f"{val} м²"


def parse_date_str(val):
    """'19.05.2023' → datetime или None"""
    if not val or not val.strip():
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(val.strip(), fmt)
        except ValueError:
            continue
    return None


def nspdlink(cadastral):
    """Кадастровый номер → ссылка на Яндекс Карты (показывает геометрию участка)"""
    cn = re.search(r"(\d{2}:\d{2,6}:\d+:\d+)", cadastral)
    if cn:
        return f"https://yandex.ru/maps/?text={cn.group(1)}"
    return ""


# ─── Загрузка данных ────────────────────────────────────────────────
def load_monitor(service):
    """Монитор объектов → dict by IP number"""
    rows = read_sheet(service, MONITOR_ID, "A1:AG200")
    if not rows:
        return {}

    data = {}
    for row in rows[1:]:  # skip header
        if len(row) < 2 or not row[1].strip():
            continue
        ip_num = extract_ip_number(row[1])
        if ip_num is None:
            continue

        def col(i):
            return row[i].strip() if len(row) > i and row[i].strip() else ""

        avito_links = []
        avito_raw = col(16)
        if avito_raw and avito_raw.startswith("http"):
            # Может быть несколько через пробел/перенос
            for link in re.findall(r"https?://[^\s,]+", avito_raw):
                avito_links.append(link.strip())

        data[ip_num] = {
            "name": col(1),
            "status": col(2),
            "buy": parse_money(col(4)),
            "sell": parse_money(col(5)),
            "collection": parse_money(col(6)),
            "expenses": parse_money(col(7)),
            "revenue": parse_money(col(8)),
            "profit_investors": parse_money(col(9)),
            "roi_project": format_pct(col(10)),
            "roi_annual": format_pct(col(11)),
            "days": col(12),
            "months": col(13),
            "date_start": col(14),
            "date_end": col(15),
            "avito_links": avito_links,
            "status_raw": col(2),
            "vykhod": col(30),
            "agent_fee": col(31),
            "nyuansy": col(32),
        }
    return data


def load_calls(service):
    """Звонок по реализации → dict by IP number (ответственный, город, новости)"""
    # Сначала заголовки (даты)
    rows = read_sheet(service, CALLS_ID, f"'{CALLS_SHEET}'!A1:CV100")
    if not rows:
        return {}

    header = rows[0]
    # Даты начинаются с колонки E (index 4)
    date_cols = []
    for i, h in enumerate(header):
        if i >= 4 and h.strip():
            # Пытаемся распарсить дату
            dt = parse_date_str(h.strip().split()[0])  # "Передача инфы..." → берём первое слово
            if dt:
                date_cols.append((i, dt, h.strip()))

    data = {}
    for row in rows[1:]:
        if len(row) < 2 or not row[1].strip():
            continue
        ip_num = extract_ip_number(row[1])
        if ip_num is None:
            continue

        responsible = row[2].strip() if len(row) > 2 else ""
        city = row[3].strip() if len(row) > 3 else ""

        # Собираем новости (последние MAX_NEWS непустых)
        news = []
        for col_i, dt, date_str in date_cols:
            if len(row) > col_i and row[col_i].strip():
                text = row[col_i].strip()
                if len(text) > 3:  # Игнорируем совсем короткие
                    news.append((dt, date_str.split()[0], text))

        # Сортируем по дате (последние первые) и берём MAX_NEWS
        news.sort(key=lambda x: x[0], reverse=True)
        news = news[:MAX_NEWS]

        # Avito ссылки из ячеек (иногда есть в данных звонка)
        extra_avito = []
        for col_i, _, _ in date_cols:
            if len(row) > col_i:
                cell = row[col_i].strip() if len(row) > col_i else ""
                for link in re.findall(r"https?://www\.avito\.ru[^\s,\"']+", cell):
                    if link not in extra_avito:
                        extra_avito.append(link)

        data[ip_num] = {
            "responsible": responsible,
            "city": city,
            "news": [(d_str, text) for _, d_str, text in news],
            "extra_avito": extra_avito,
        }
    return data


def load_estate_objects(service):
    """Estate учёт (Объекты) → dict by IP number (тип, площадь, notion)"""
    rows = read_sheet(service, ESTATE_ID, ESTATE_OBJECTS_RANGE)
    if not rows:
        return {}

    data = {}
    for row in rows:
        if len(row) < 2 or not row[1].strip():
            continue
        ip_num = extract_ip_number(row[1])
        if not ip_num:
            # Попробуем из первой колонки
            try:
                ip_num = int(row[0].strip())
            except (ValueError, IndexError):
                continue

        def col(i):
            return row[i].strip() if len(row) > i and row[i].strip() else ""

        stage = col(9).strip()
        stage_lower = stage.lower()
        if "реализация" not in stage_lower and "сбор" not in stage_lower and ip_num not in {58, 65, 88}:
            continue

        data[ip_num] = {
            "type": col(4),
            "area": format_area(col(5)),
            "notion_link": col(17),
            "status": stage,
            "address": col(1),  # чистый адрес из Estate учёта (без "ИП N")
        }
    return data


# ─── Объединение данных ─────────────────────────────────────────────
def merge_data(monitor, calls, estate, static_html):
    """Объединяет все источники в единый список объектов."""
    all_ips = sorted(set(monitor.keys()) | set(calls.keys()) | set(estate.keys()))

    objects = []
    for ip in all_ips:
        mon = monitor.get(ip, {})
        cal = calls.get(ip, {})
        est = estate.get(ip, {})
        st = static_html.get(ip, {})

        # Включаем только объекты из Estate учёта (там фильтр по статусу — col 9)
        if not est:
            continue

        name = mon.get("name") or cal.get("name", f"ИП {ip}")
        status = est.get("status", mon.get("status_raw", "реализация"))

        # Собираем avito ссылки из всех источников
        avito = list(mon.get("avito_links", []))
        for link in cal.get("extra_avito", []):
            if link not in avito:
                avito.append(link)

        obj = {
            "ip_num": ip,
            "name": name,
            "status": status,
            "responsible": cal.get("responsible", ""),
            "city": cal.get("city", ""),
            "type": est.get("type", ""),
            "area": est.get("area", ""),
            "buy": mon.get("buy", 0),
            "sell": mon.get("sell", 0),
            "profit_investors": mon.get("profit_investors", 0),
            "roi_project": mon.get("roi_project", "—"),
            "roi_annual": mon.get("roi_annual", "—"),
            "date_start": mon.get("date_start", ""),
            "date_end": mon.get("date_end", ""),
            "avito_links": avito,
            "notion_link": est.get("notion_link", ""),
            "cadastral": st.get("cadastral", ""),
            "address": est.get("address", "") or st.get("address", ""),
            "news": cal.get("news", []),
            # Поля для риелторов
            "vykhod": mon.get("vykhod", ""),
            "agent_fee": mon.get("agent_fee", ""),
            "nyuansy": mon.get("nyuansy", ""),
            "cian_link": "",
            "lat": None,
            "lon": None,
        }
        objects.append(obj)

    return objects


# ─── Генерация HTML ─────────────────────────────────────────────────
def generate_html(objects):
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    # Статистика
    total = len(objects)
    active = sum(1 for o in objects if "реализация" in o["status"].lower())
    collecting = sum(1 for o in objects if "сбор" in o["status"].lower())
    sum_buy = sum(o["buy"] for o in objects)
    sum_sell = sum(o["sell"] for o in objects)

    # Группировка по ответственному
    groups = {}
    for obj in objects:
        resp = obj["responsible"] or "Не назначен"
        groups.setdefault(resp, []).append(obj)

    # Сортировка: Антонина первая, потом по количеству
    sorted_groups = sorted(
        groups.items(),
        key=lambda x: (-len(x[1]) if "Антонина" not in x[0] else -9999, x[0]),
    )

    # JSON для кнопки "Обновить" и карты
    objects_json = json.dumps(objects, ensure_ascii=False, default=str)

    cards_html = []
    for resp_name, resp_objects in sorted_groups:
        resp_objects.sort(key=lambda x: x["ip_num"])
        section = f'''
<section class="responsible-section">
  <h2 class="responsible-title">{esc(resp_name)} <span class="count-badge">{len(resp_objects)} объектов</span></h2>
  <div class="cards-grid">'''

        for obj in resp_objects:
            section += render_card(obj)

        section += "</div>\n</section>"
        cards_html.append(section)

    html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Estate Invest — Реализация объектов</title>
<style>
{CSS}
</style>
</head>
<body>

<div class="header">
  <div class="header-top">
    <div>
      <h1>Estate Invest — Реализация объектов</h1>
      <div class="subtitle">Обновлено {now}</div>
    </div>
    <div class="header-actions">
      <a class="map-open-btn" onclick="openMap(); return false;" href="#">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
        Карта
      </a>
      <button class="refresh-btn" onclick="refreshFinances()" id="refreshBtn">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
        Обновить финансы
      </button>
    </div>
  </div>
</div>

<div class="stats-bar">
  <div class="stat"><div class="stat-label">Всего активных</div><div class="stat-value blue" id="s-total">{total}</div></div>
  <div class="stat-divider"></div>
  <div class="stat"><div class="stat-label">Реализация</div><div class="stat-value" id="s-active">{active}</div></div>
  <div class="stat"><div class="stat-label">Сбор средств</div><div class="stat-value amber" id="s-collect">{collecting}</div></div>
  <div class="stat-divider"></div>
  <div class="stat"><div class="stat-label">Сумма покупки</div><div class="stat-value" id="s-buy">{format_money(sum_buy)}</div></div>
  <div class="stat"><div class="stat-label">Целевая продажа</div><div class="stat-value green" id="s-sell">{format_money(sum_sell)}</div></div>
</div>

<div class="filter-bar">
  <input type="text" id="searchInput" placeholder="Поиск по названию, адресу, кадастру..." oninput="filterCards()">
  <select id="cityFilter" onchange="filterCards()">
    <option value="">Все города</option>
  </select>
  <select id="typeFilter" onchange="filterCards()">
    <option value="">Все типы</option>
  </select>
  <select id="respFilter" onchange="filterCards()">
    <option value="">Все ответственные</option>
  </select>
</div>

<div class="main" id="mainContent">
{"".join(cards_html)}
</div>

<div class="generated">
  Сгенерировано из Google Sheets · Estate Invest · {total} активных объектов · {now}
</div>

<script>
const OBJECTS = {objects_json};
const MONITOR_SHEET_ID = "{MONITOR_ID}";

{JAVASCRIPT}
</script>
</body>
</html>'''
    return html


def esc(text):
    """HTML escape"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_card(obj):
    ip = obj["ip_num"]
    name = obj["name"]
    status = obj["status"].lower()
    badge_class = "badge-collect" if "сбор" in status else "badge-active"
    badge_text = "сбор средств" if "сбор" in status else "реализация"

    # Кадастр — кликабельный
    kadastr_html = ""
    if obj["cadastral"]:
        link = nspdlink(obj["cadastral"])
        if link:
            kadastr_html = f'<div class="kadastr-row"><span class="kadastr-label">Кадастр:</span> <a href="{link}" target="_blank" class="kadastr-link"><span class="kadastr-value">{esc(obj["cadastral"])}</span></a></div>'
        else:
            kadastr_html = f'<div class="kadastr-row"><span class="kadastr-label">Кадастр:</span> <span class="kadastr-value">{esc(obj["cadastral"])}</span></div>'

    # Адрес
    address_html = ""
    if obj["address"]:
        address_html = f'<div class="address-row"><span class="kadastr-label">Адрес:</span> <span class="address-value">{esc(obj["address"])}</span></div>'

    # Площадь
    area_html = f'<span class="area-tag">{esc(obj["area"])}</span>' if obj["area"] else ""

    # Ссылки (Авито, ЦИАН, Notion)
    links_html = ""
    link_items = []
    for i, link in enumerate(obj["avito_links"]):
        link_items.append(f'<a href="{esc(link)}" class="avito-link" target="_blank">Авито{f" {i+1}" if len(obj["avito_links"]) > 1 else ""} ↗</a>')
    if obj["cian_link"]:
        link_items.append(f'<a href="{esc(obj["cian_link"])}" class="cian-link" target="_blank">ЦИАН ↗</a>')
    if obj["notion_link"]:
        link_items.append(f'<a href="{esc(obj["notion_link"])}" class="notion-link" target="_blank">Notion ↗</a>')
    if link_items:
        links_html = f'<div class="card-links">{"".join(link_items)}</div>'

    # Финансы
    buy_str = format_money(obj["buy"])
    sell_str = format_money(obj["sell"])
    profit_str = format_money(obj["profit_investors"])

    # Выход мин/макс
    vykhod = obj.get("vykhod", "")
    exit_html = f'''
      <div class="fin-item">
        <div class="fin-label">Выход мин–макс</div>
        <div class="fin-value fin-exit">{esc(vykhod) if vykhod else "—"}</div>
      </div>'''

    # ROI
    roi_text = f"{obj['roi_project']} ({obj['roi_annual']}/год)" if obj["roi_annual"] != "—" else obj["roi_project"]

    # Даты
    date_html = ""
    if obj["date_start"] or obj["date_end"]:
        date_html = f'<span class="date-info">Старт: {obj["date_start"] or "—"} → Конец: {obj["date_end"] or "—"}</span>'

    # Агент
    agent_html = ""
    if obj.get("agent_fee"):
        agent_html = f'<div class="agent-row"><span class="agent-label">Агент:</span> <span class="agent-value">{esc(obj["agent_fee"])}</span></div>'
    else:
        agent_html = '<div class="agent-row"><span class="agent-label">Агент:</span> <span class="agent-empty">—</span></div>'

    # Комментарии
    comments_html = ""
    if obj.get("nyuansy"):
        comments_html = f'<div class="comments-row"><span class="comments-label">Нюансы:</span> <span class="comments-value">{esc(obj["nyuansy"])}</span></div>'
    else:
        comments_html = '<div class="comments-row"><span class="comments-label">Нюансы:</span> <span class="comments-empty">—</span></div>'

    # Новости
    news_html = ""
    if obj["news"]:
        items = "".join(
            f'<div class="news-item"><span class="news-date">{esc(d)}</span><span class="news-text">{esc(t[:150])}</span></div>'
            for d, t in obj["news"]
        )
        news_html = f'''<div class="news-block"><div class="news-title">Новости <span style="color:var(--accent);font-weight:700">{len(obj["news"])}</span></div><div class="news-scroll">{items}</div></div>'''
    else:
        news_html = '<div class="news-block"><div class="news-title">Новости</div><div class="no-news">Нет новостей</div></div>'

    return f'''
<div class="property-card" data-ip="{ip}" data-city="{esc(obj["city"])}" data-type="{esc(obj["type"])}" data-resp="{esc(obj["responsible"])}">
  <div class="card-header">
    <div class="card-title">
      <span class="ip-num">ИП {ip}</span>
      <span class="ip-name">{esc(name)}</span>
      <span class="badge {badge_class}">{badge_text}</span>
    </div>
    <div class="card-meta">
      {f'<span class="city-tag">{esc(obj["city"])}</span>' if obj["city"] else ""}
      {f'<span class="type-tag">{esc(obj["type"])}</span>' if obj["type"] else ""}
      {area_html}
      {f'<span class="responsible">{esc(obj["responsible"])}</span>' if obj["responsible"] else ""}
    </div>
    <div class="card-location">{kadastr_html}{address_html}</div>
  </div>
  <div class="card-body">
    <div class="financials">
      <div class="fin-item">
        <div class="fin-label">Вход (покупка)</div>
        <div class="fin-value" data-field="buy">{buy_str}</div>
      </div>
      <div class="fin-arrow">→</div>
      <div class="fin-item">
        <div class="fin-label">Целевая продажа</div>
        <div class="fin-value fin-target" data-field="sell">{sell_str}</div>
      </div>
      {exit_html}
      <div class="fin-item fin-profit">
        <div class="fin-label">Прибыль инвесторам</div>
        <div class="fin-value" data-field="profit">{profit_str}</div>
      </div>
    </div>
    {agent_html}
    {comments_html}
    <div class="card-extra">
      <span class="roi">ROI {roi_text}</span>
      {date_html}
    </div>
    {links_html}
    {news_html}
  </div>
</div>'''


# ─── CSS ─────────────────────────────────────────────────────────────
CSS = """:root {
    --bg: #0f1117;
    --surface: #1a1d29;
    --surface2: #232736;
    --border: #2d3250;
    --text: #e8eaf0;
    --text-muted: #8b92a8;
    --accent: #4f6ef7;
    --green: #34d399;
    --amber: #fbbf24;
    --blue: #60a5fa;
    --purple: #a78bfa;
    --red: #ef4444;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; line-height: 1.5; }

  .header { background: linear-gradient(135deg, #1a1d29 0%, #232736 100%); border-bottom: 1px solid var(--border); padding: 24px 32px; }
  .header-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; }
  .header h1 { font-size: 24px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
  .header .subtitle { color: var(--text-muted); font-size: 13px; }
  .header-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

  .refresh-btn { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; background: rgba(52,211,153,0.15); color: var(--green); border: 1px solid rgba(52,211,153,0.3); padding: 8px 16px; border-radius: 8px; cursor: pointer; transition: all .15s; font-family: inherit; }
  .refresh-btn:hover { background: rgba(52,211,153,0.25); }
  .refresh-btn.loading { opacity: 0.6; pointer-events: none; }
  .refresh-btn.loading svg { animation: spin 1s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  .stats-bar { display: flex; gap: 24px; padding: 20px 32px; background: var(--surface); border-bottom: 1px solid var(--border); flex-wrap: wrap; }
  .stat { display: flex; flex-direction: column; gap: 4px; }
  .stat-label { color: var(--text-muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
  .stat-value { font-size: 20px; font-weight: 700; color: var(--text); }
  .stat-value.green { color: var(--green); }
  .stat-value.blue { color: var(--blue); }
  .stat-value.amber { color: var(--amber); }
  .stat-divider { width: 1px; background: var(--border); }

  .filter-bar { display: flex; gap: 12px; padding: 16px 32px; background: var(--surface); border-bottom: 1px solid var(--border); flex-wrap: wrap; align-items: center; }
  .filter-bar input, .filter-bar select { background: var(--surface2); border: 1px solid var(--border); color: var(--text); padding: 8px 12px; border-radius: 8px; font-size: 13px; font-family: inherit; outline: none; transition: border-color .2s; }
  .filter-bar input { flex: 1; min-width: 200px; }
  .filter-bar input:focus, .filter-bar select:focus { border-color: var(--accent); }
  .filter-bar select { min-width: 140px; }

  .main { padding: 24px 32px; max-width: 1600px; }

  .responsible-section { margin-bottom: 40px; }
  .responsible-title { font-size: 18px; font-weight: 600; color: var(--text); padding: 12px 0; border-bottom: 2px solid var(--border); margin-bottom: 16px; display: flex; align-items: center; gap: 12px; }
  .count-badge { font-size: 12px; font-weight: 500; background: var(--surface2); color: var(--text-muted); padding: 2px 8px; border-radius: 12px; border: 1px solid var(--border); }

  .cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(480px, 1fr)); gap: 16px; }

  .property-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; transition: border-color 0.2s; }
  .property-card:hover { border-color: var(--accent); }
  .property-card.hidden { display: none; }

  .card-header { background: var(--surface2); padding: 14px 16px; border-bottom: 1px solid var(--border); }
  .card-title { display: flex; align-items: flex-start; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
  .ip-num { font-size: 11px; font-weight: 700; background: var(--accent); color: white; padding: 2px 8px; border-radius: 6px; white-space: nowrap; flex-shrink: 0; margin-top: 2px; }
  .ip-name { font-size: 13px; font-weight: 600; color: var(--text); flex: 1; line-height: 1.4; }

  .card-meta { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
  .city-tag { font-size: 11px; background: rgba(96, 165, 250, 0.15); color: var(--blue); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(96, 165, 250, 0.25); }
  .type-tag { font-size: 11px; background: rgba(167, 139, 250, 0.1); color: var(--purple); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(167, 139, 250, 0.2); }
  .area-tag { font-size: 11px; background: rgba(52, 211, 153, 0.1); color: var(--green); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(52, 211, 153, 0.2); font-weight: 600; }
  .responsible { font-size: 11px; color: var(--text-muted); }

  .card-location { margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border); }
  .kadastr-row, .address-row { font-size: 11px; color: var(--text-muted); margin-bottom: 2px; line-height: 1.4; }
  .kadastr-label { color: var(--text-muted); font-weight: 600; }
  .kadastr-value { color: var(--amber); font-family: 'SF Mono', 'Cascadia Code', monospace; font-size: 11px; }
  .kadastr-link { text-decoration: none; border-bottom: 1px dashed rgba(251,191,36,0.4); }
  .kadastr-link:hover { border-bottom-color: var(--amber); }
  .address-value { color: var(--text-muted); }

  .badge { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 4px; white-space: nowrap; margin-top: 2px; flex-shrink: 0; }
  .badge-active { background: rgba(52, 211, 153, 0.15); color: var(--green); border: 1px solid rgba(52, 211, 153, 0.3); }
  .badge-collect { background: rgba(251, 191, 36, 0.15); color: var(--amber); border: 1px solid rgba(251, 191, 36, 0.3); }

  .card-body { padding: 14px 16px; }

  .financials { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
  .fin-item { flex: 1; min-width: 90px; }
  .fin-arrow { color: var(--text-muted); font-size: 16px; flex-shrink: 0; }
  .fin-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 2px; }
  .fin-value { font-size: 15px; font-weight: 700; color: var(--text); }
  .fin-target { color: var(--green); }
  .fin-exit { color: var(--blue); font-size: 13px; }
  .fin-empty { color: var(--text-muted); font-size: 13px; font-weight: 400; }
  .fin-profit { border-left: 1px solid var(--border); padding-left: 10px; }

  .agent-row, .comments-row { font-size: 12px; margin-bottom: 6px; padding: 4px 0; }
  .agent-label, .comments-label { color: var(--text-muted); font-weight: 600; font-size: 11px; }
  .agent-value { color: var(--amber); }
  .agent-empty, .comments-empty { color: var(--text-muted); font-style: italic; font-size: 11px; }
  .comments-value { color: var(--text-muted); font-size: 12px; line-height: 1.4; }

  .card-extra { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; align-items: center; }
  .roi { font-size: 11px; background: rgba(167, 139, 250, 0.1); color: var(--purple); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(167, 139, 250, 0.2); }
  .date-info { font-size: 11px; color: var(--text-muted); }

  .card-links { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
  .avito-link, .cian-link, .notion-link { font-size: 11px; text-decoration: none; padding: 3px 10px; border-radius: 4px; }
  .avito-link { color: var(--accent); background: rgba(79, 110, 247, 0.1); border: 1px solid rgba(79, 110, 247, 0.2); }
  .avito-link:hover { background: rgba(79, 110, 247, 0.2); }
  .cian-link { color: #2196f3; background: rgba(33, 150, 243, 0.1); border: 1px solid rgba(33, 150, 243, 0.2); }
  .cian-link:hover { background: rgba(33, 150, 243, 0.2); }
  .notion-link { color: var(--text-muted); background: rgba(255,255,255,0.03); border: 1px solid var(--border); }
  .notion-link:hover { background: rgba(255,255,255,0.06); }

  .news-block { background: rgba(255,255,255,0.02); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
  .news-title { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.4px; padding: 8px 10px 6px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 6px; }
  .news-scroll { max-height: 160px; overflow-y: auto; padding: 6px 10px; scrollbar-width: thin; scrollbar-color: var(--border) transparent; }
  .news-scroll::-webkit-scrollbar { width: 4px; }
  .news-scroll::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
  .news-item { display: flex; gap: 10px; margin-bottom: 7px; font-size: 12px; }
  .news-item:last-child { margin-bottom: 0; }
  .news-date { color: var(--accent); white-space: nowrap; font-weight: 600; flex-shrink: 0; font-size: 11px; padding-top: 1px; }
  .news-text { color: var(--text-muted); line-height: 1.4; }
  .no-news { font-size: 12px; color: var(--text-muted); font-style: italic; padding: 8px 10px; }

  .generated { padding: 20px 32px; border-top: 1px solid var(--border); font-size: 12px; color: var(--text-muted); margin-top: 20px; }

  .map-open-btn { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; background: rgba(79,110,247,.18); color: var(--accent); border: 1px solid rgba(79,110,247,.35); padding: 8px 16px; border-radius: 8px; cursor: pointer; text-decoration: none; transition: background .15s; }
  .map-open-btn:hover { background: rgba(79,110,247,.32); }

  @media (max-width: 768px) {
    .header, .stats-bar, .main, .filter-bar { padding: 16px; }
    .cards-grid { grid-template-columns: 1fr; }
    .stats-bar { gap: 16px; }
  }"""


# ─── JavaScript ──────────────────────────────────────────────────────
JAVASCRIPT = """
// Заполняем фильтры
(function() {
  var cities = {}, types = {}, resps = {};
  OBJECTS.forEach(function(o) {
    if (o.city) cities[o.city] = 1;
    if (o.type) types[o.type] = 1;
    if (o.responsible) resps[o.responsible] = 1;
  });
  var citySel = document.getElementById('cityFilter');
  Object.keys(cities).sort().forEach(function(c) {
    var opt = document.createElement('option'); opt.value = c; opt.textContent = c;
    citySel.appendChild(opt);
  });
  var typeSel = document.getElementById('typeFilter');
  Object.keys(types).sort().forEach(function(t) {
    var opt = document.createElement('option'); opt.value = t; opt.textContent = t;
    typeSel.appendChild(opt);
  });
  var respSel = document.getElementById('respFilter');
  Object.keys(resps).sort().forEach(function(r) {
    var opt = document.createElement('option'); opt.value = r; opt.textContent = r;
    respSel.appendChild(opt);
  });
})();

function filterCards() {
  var q = document.getElementById('searchInput').value.toLowerCase();
  var city = document.getElementById('cityFilter').value;
  var type = document.getElementById('typeFilter').value;
  var resp = document.getElementById('respFilter').value;

  document.querySelectorAll('.property-card').forEach(function(card) {
    var show = true;
    if (q && card.textContent.toLowerCase().indexOf(q) === -1) show = false;
    if (city && card.dataset.city !== city) show = false;
    if (type && card.dataset.type !== type) show = false;
    if (resp && card.dataset.resp !== resp) show = false;
    card.classList.toggle('hidden', !show);
  });

  // Обновляем счётчики секций
  document.querySelectorAll('.responsible-section').forEach(function(sec) {
    var visible = sec.querySelectorAll('.property-card:not(.hidden)').length;
    var badge = sec.querySelector('.count-badge');
    if (badge) badge.textContent = visible + ' объектов';
    sec.style.display = visible === 0 ? 'none' : '';
  });
}

// Обновление финансов из Google Sheets (gviz API)
async function refreshFinances() {
  var btn = document.getElementById('refreshBtn');
  btn.classList.add('loading');
  btn.textContent = 'Загрузка...';

  try {
    var url = 'https://docs.google.com/spreadsheets/d/' + MONITOR_SHEET_ID + '/gviz/tq?tqx=out:csv';
    var resp = await fetch(url);
    var csv = await resp.text();
    var rows = parseCSV(csv);

    // Обновляем карточки
    var totalBuy = 0, totalSell = 0;
    rows.forEach(function(row) {
      if (row.length < 6) return;
      var name = row[1] || '';
      var m = name.match(/ИП\\s*[№#]?\\s*(\\d+)/i);
      if (!m) return;
      var ip = m[1];
      var status = (row[2] || '').toLowerCase();
      if (status.indexOf('реализация') === -1 && status.indexOf('сбор') === -1) return;

      var buy = parseMoney(row[4]);
      var sell = parseMoney(row[5]);
      var profit = parseMoney(row[9]);
      totalBuy += buy;
      totalSell += sell;

      var card = document.querySelector('[data-ip=\"' + ip + '\"]');
      if (!card) return;
      var buyEl = card.querySelector('[data-field=\"buy\"]');
      var sellEl = card.querySelector('[data-field=\"sell\"]');
      var profitEl = card.querySelector('[data-field=\"profit\"]');
      if (buyEl) buyEl.textContent = formatMoney(buy);
      if (sellEl) sellEl.textContent = formatMoney(sell);
      if (profitEl) profitEl.textContent = formatMoney(profit);
    });

    document.getElementById('s-buy').textContent = formatMoney(totalBuy);
    document.getElementById('s-sell').textContent = formatMoney(totalSell);
    document.querySelector('.subtitle').textContent = 'Финансы обновлены ' + new Date().toLocaleString('ru-RU');
  } catch(e) {
    alert('Ошибка обновления: ' + e.message);
  }

  btn.classList.remove('loading');
  btn.innerHTML = '<svg width=\"14\" height=\"14\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><path d=\"M23 4v6h-6\"/><path d=\"M1 20v-6h6\"/><path d=\"M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15\"/></svg> Обновить финансы';
}

function parseMoney(s) {
  if (!s) return 0;
  return parseFloat(s.replace(/\\s/g,'').replace(/р\\./g,'').replace(',','.')) || 0;
}

function formatMoney(v) {
  if (!v) return '—';
  if (v >= 1000000) return (v/1000000).toFixed(1) + ' млн ₽';
  if (v >= 1000) return Math.round(v/1000) + ' тыс ₽';
  return Math.round(v) + ' ₽';
}

function parseCSV(text) {
  var rows = [];
  var lines = text.split('\\n');
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i].trim();
    if (!line) continue;
    var cells = [];
    var inQuotes = false;
    var cell = '';
    for (var j = 0; j < line.length; j++) {
      var ch = line[j];
      if (ch === '\"') {
        if (inQuotes && j + 1 < line.length && line[j+1] === '\"') {
          cell += '\"';
          j++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (ch === ',' && !inQuotes) {
        cells.push(cell);
        cell = '';
      } else {
        cell += ch;
      }
    }
    cells.push(cell);
    rows.push(cells);
  }
  return rows;
}

// Карта объектов
window.openMap = function() {
  var props = [];
  document.querySelectorAll('.property-card').forEach(function(card) {
    var ipNum  = (card.querySelector('.ip-num') || {}).textContent || '';
    var ipName = (card.querySelector('.ip-name') || {}).textContent || '';
    var city   = (card.querySelector('.city-tag') || {}).textContent || '';
    var type   = (card.querySelector('.type-tag') || {}).textContent || '';
    var addr   = (card.querySelector('.address-value') || {}).textContent || '';
    var kadastr = (card.querySelector('.kadastr-value') || {}).textContent || '';
    kadastr = kadastr.split('/')[0].trim();
    var fins = card.querySelectorAll('.fin-value');
    var buy  = (fins[0] || {}).textContent || '';
    var sell = (fins[1] || {}).textContent || '';
    var roi  = (card.querySelector('.roi') || {}).textContent || '';
    // Берём координаты из данных объекта (pre-computed через НСПД)
    var ipN = parseInt((ipNum.match(/\\d+/) || [])[0]);
    var obj = OBJECTS.find(function(o) { return o.ip_num === ipN; });
    var lat = obj && obj.lat ? obj.lat : null;
    var lon = obj && obj.lon ? obj.lon : null;
    if (ipNum) props.push({ ipNum: ipNum.trim(), ipName: ipName.trim(), city: city.trim(), type: type.trim(), addr: addr.trim(), kadastr: kadastr, buy: buy.trim(), sell: sell.trim(), roi: roi.trim(), lat: lat, lon: lon });
  });
  try { localStorage.setItem('ei_map_props', JSON.stringify(props)); } catch(e) {}
  window.open('карта-объектов.html', '_blank');
};
"""


# ─── Таблица для риелторов ───────────────────────────────────────────
def generate_rieltory_html(objects):
    """Минималистичная таблица для риелторов — только объекты со статусом 'реализация'."""
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    EXCLUDE_IPS = {4, 7, 8, 9, 10, 11, 12, 13, 31, 73, 107, 113, 114, 119}
    # ИП с другим статусом, которые всё равно нужны в таблице
    FORCE_INCLUDE = {58, 65, 88}

    rieltory = [
        o for o in objects
        if (
            ("реализация" in o.get("status", "").lower() or o["ip_num"] in FORCE_INCLUDE)
            and o["ip_num"] not in EXCLUDE_IPS
        )
    ]
    rieltory.sort(key=lambda x: x["ip_num"])

    total = len(rieltory)
    with_avito = sum(1 for o in rieltory if o.get("avito_links"))

    rows_html = []
    for obj in rieltory:
        ip_num = obj["ip_num"]
        address = obj.get("address", "") or ""
        name = obj.get("name", f"ИП {ip_num}")
        cadastral = obj.get("cadastral", "")
        buy = obj.get("buy", 0)
        vykhod = obj.get("vykhod", "")
        agent_fee = obj.get("agent_fee", "")
        nyuansy = obj.get("nyuansy", "")
        avito_links = obj.get("avito_links", [])
        city = obj.get("city", "")
        obj_type = obj.get("type", "")

        # Адрес — ссылка на Авито если есть
        avito_url = avito_links[0] if avito_links else ""
        display_addr = address if address else name
        if avito_url:
            addr_cell = f'<a href="{esc(avito_url)}" target="_blank" class="avito-link">{esc(display_addr)}</a>'
            if city:
                addr_cell += f'<span class="city-hint">{esc(city)}</span>'
        else:
            addr_cell = f'<span class="no-link">{esc(display_addr)}</span>'
            if city:
                addr_cell += f'<span class="city-hint">{esc(city)}</span>'

        # Кадастровый номер — ссылка на НСПД
        if cadastral:
            nspd_url = nspdlink(cadastral)
            kadastr_cell = (
                f'<a href="{esc(nspd_url)}" target="_blank" class="kadastr-link">{esc(cadastral)}</a>'
                if nspd_url else esc(cadastral)
            )
        else:
            kadastr_cell = '<span class="empty">—</span>'

        buy_str = format_money(buy) if buy else "—"
        type_str = f'<span class="type-badge">{esc(obj_type)}</span>' if obj_type else ""

        rows_html.append(f"""    <tr data-ip="{ip_num}">
      <td class="ip-cell">ИП {ip_num}{type_str}</td>
      <td class="addr-cell">{addr_cell}</td>
      <td class="kadastr-cell">{kadastr_cell}</td>
      <td class="money-cell">{esc(buy_str)}</td>
      <td class="exit-cell">{esc(vykhod) if vykhod else '<span class="empty">—</span>'}</td>
      <td class="agent-cell">{esc(agent_fee) if agent_fee else '<span class="empty">—</span>'}</td>
      <td class="comment-cell">{esc(nyuansy) if nyuansy else '<span class="empty">—</span>'}</td>
    </tr>""")

    rows = "\n".join(rows_html)

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Estate Invest — Таблица для риелторов</title>
<style>
:root {{
  --bg: #0f1117;
  --surface: #1a1d29;
  --surface2: #232736;
  --border: #2d3250;
  --text: #e8eaf0;
  --muted: #8b92a8;
  --accent: #4f6ef7;
  --green: #34d399;
  --amber: #fbbf24;
  --red: #ef4444;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px; }}

.header {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 20px 28px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }}
.header h1 {{ font-size: 20px; font-weight: 700; }}
.header .meta {{ color: var(--muted); font-size: 12px; }}
.stats {{ display: flex; gap: 20px; }}
.stat {{ display: flex; flex-direction: column; }}
.stat-v {{ font-size: 18px; font-weight: 700; color: var(--green); }}
.stat-l {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.4px; }}

.search-bar {{ padding: 12px 28px; background: var(--surface); border-bottom: 1px solid var(--border); display: flex; gap: 10px; }}
.search-bar input {{ background: var(--surface2); border: 1px solid var(--border); color: var(--text); padding: 7px 12px; border-radius: 7px; font-size: 13px; font-family: inherit; outline: none; width: 300px; transition: border-color .2s; }}
.search-bar input:focus {{ border-color: var(--accent); }}
.search-bar input::placeholder {{ color: var(--muted); }}

.wrap {{ padding: 20px 28px; overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; }}
thead tr {{ background: var(--surface2); }}
th {{ padding: 10px 12px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); border-bottom: 2px solid var(--border); white-space: nowrap; cursor: pointer; user-select: none; }}
th:hover {{ color: var(--text); }}
th.sort-asc::after {{ content: ' ▲'; color: var(--accent); }}
th.sort-desc::after {{ content: ' ▼'; color: var(--accent); }}
tbody tr {{ border-bottom: 1px solid var(--border); transition: background .1s; }}
tbody tr:hover {{ background: var(--surface2); }}
tbody tr.hidden {{ display: none; }}
td {{ padding: 10px 12px; vertical-align: top; }}

.ip-cell {{ white-space: nowrap; font-weight: 600; color: var(--muted); font-size: 12px; min-width: 70px; }}
.type-badge {{ display: block; font-size: 10px; font-weight: 500; color: var(--accent); margin-top: 3px; }}
.addr-cell {{ min-width: 220px; max-width: 300px; }}
.avito-link {{ color: var(--green); text-decoration: none; font-weight: 500; }}
.avito-link:hover {{ text-decoration: underline; }}
.no-link {{ color: var(--text); }}
.city-hint {{ display: block; font-size: 11px; color: var(--muted); margin-top: 2px; }}
.kadastr-cell {{ min-width: 160px; white-space: nowrap; }}
.kadastr-link {{ color: var(--accent); text-decoration: none; font-size: 12px; }}
.kadastr-link:hover {{ text-decoration: underline; }}
.money-cell {{ white-space: nowrap; font-variant-numeric: tabular-nums; min-width: 100px; }}
.exit-cell {{ min-width: 160px; color: var(--amber); }}
.agent-cell {{ min-width: 140px; color: var(--green); white-space: nowrap; }}
.comment-cell {{ min-width: 200px; max-width: 320px; color: var(--muted); font-size: 12px; line-height: 1.5; }}
.empty {{ color: var(--border); }}

.legend {{ display: flex; gap: 20px; padding: 10px 28px; background: var(--surface); border-top: 1px solid var(--border); font-size: 11px; color: var(--muted); }}
.legend span {{ display: flex; align-items: center; gap: 5px; }}
.dot {{ width: 8px; height: 8px; border-radius: 50%; }}
.dot-green {{ background: var(--green); }}
.dot-amber {{ background: var(--amber); }}
.dot-accent {{ background: var(--accent); }}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>Estate Invest — Таблица для риелторов</h1>
    <div class="meta">Обновлено {now} · только статус «реализация»</div>
  </div>
  <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;">
    <div class="stats">
      <div class="stat"><div class="stat-v">{total}</div><div class="stat-l">объектов</div></div>
      <div class="stat"><div class="stat-v">{with_avito}</div><div class="stat-l">с Авито</div></div>
      <div class="stat"><div class="stat-v">{total - with_avito}</div><div class="stat-l">без Авито</div></div>
    </div>
    <button id="refreshBtn" onclick="doRefresh()" style="background:rgba(79,110,247,0.15);color:#4f6ef7;border:1px solid rgba(79,110,247,0.35);padding:8px 18px;border-radius:8px;font-size:13px;cursor:pointer;font-family:inherit;">
      Обновить данные
    </button>
  </div>
</div>

<div class="search-bar">
  <input type="text" id="searchInput" placeholder="Поиск по адресу, кадастру, комментарию..." oninput="filterTable()">
</div>

<div class="wrap">
<table id="mainTable">
  <thead>
    <tr>
      <th onclick="sortTable(0)">ИП</th>
      <th>Адрес / Авито</th>
      <th onclick="sortTable(2)">Кадастровый №</th>
      <th onclick="sortTable(3)">Вход</th>
      <th>Выход (мин–макс)</th>
      <th onclick="sortTable(5)">Вознаграждение агента</th>
      <th>Нюансы / Комментарии</th>
    </tr>
  </thead>
  <tbody id="tableBody">
{rows}
  </tbody>
</table>
</div>

<div class="legend">
  <span><span class="dot dot-green"></span> Адрес — ссылка на Авито</span>
  <span><span class="dot dot-accent"></span> Кадастр — открыть на карте НСПД</span>
  <span><span class="dot dot-amber"></span> Выход мин–макс</span>
</div>

<script>
function filterTable() {{
  var q = document.getElementById('searchInput').value.toLowerCase();
  document.querySelectorAll('#tableBody tr').forEach(function(tr) {{
    tr.classList.toggle('hidden', q && tr.textContent.toLowerCase().indexOf(q) === -1);
  }});
}}

var sortDir = {{}};
function sortTable(col) {{
  var tbody = document.getElementById('tableBody');
  var rows = Array.from(tbody.querySelectorAll('tr'));
  var asc = !sortDir[col];
  sortDir = {{}};
  sortDir[col] = asc;

  document.querySelectorAll('thead th').forEach(function(th, i) {{
    th.classList.remove('sort-asc', 'sort-desc');
    if (i === col) th.classList.add(asc ? 'sort-asc' : 'sort-desc');
  }});

  rows.sort(function(a, b) {{
    var av = a.cells[col] ? a.cells[col].textContent.trim() : '';
    var bv = b.cells[col] ? b.cells[col].textContent.trim() : '';
    // Числа
    var an = parseFloat(av.replace(/[^0-9.]/g, ''));
    var bn = parseFloat(bv.replace(/[^0-9.]/g, ''));
    if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
    return asc ? av.localeCompare(bv, 'ru') : bv.localeCompare(av, 'ru');
  }});
  rows.forEach(function(r) {{ tbody.appendChild(r); }});
}}

async function doRefresh() {{
  var btn = document.getElementById('refreshBtn');
  btn.textContent = 'Запускаю...';
  btn.disabled = true;
  try {{
    var resp = await fetch('/refresh', {{method: 'POST'}});
    var data = await resp.json();
    if (data.ok || data.running) {{
      btn.textContent = 'Обновляется (~2 мин)...';
      pollStatus();
    }} else {{
      btn.textContent = 'Обновить данные';
      btn.disabled = false;
      alert('Ошибка: ' + (data.msg || 'unknown'));
    }}
  }} catch(e) {{
    btn.textContent = 'Обновить данные';
    btn.disabled = false;
    alert('Сервер недоступен: ' + e.message);
  }}
}}

async function pollStatus() {{
  try {{
    var resp = await fetch('/refresh/status');
    var data = await resp.json();
    if (!data.running) {{
      document.getElementById('refreshBtn').textContent = 'Готово, перезагрузка...';
      setTimeout(function() {{ location.reload(); }}, 800);
    }} else {{
      setTimeout(pollStatus, 3000);
    }}
  }} catch(e) {{
    setTimeout(pollStatus, 5000);
  }}
}}
</script>
</body>
</html>"""


# ─── Main ────────────────────────────────────────────────────────────
def main():
    print("Подключаюсь к Google Sheets...")
    service = get_sheets_service()

    print("Загружаю Монитор объектов...")
    monitor = load_monitor(service)
    print(f"  → {len(monitor)} объектов")

    print("Загружаю Звонок по реализации...")
    calls = load_calls(service)
    print(f"  → {len(calls)} объектов")

    print("Загружаю Estate учёт (Объекты)...")
    estate = load_estate_objects(service)
    print(f"  → {len(estate)} объектов")

    print(f"Парсинг существующего HTML ({EXISTING_HTML})...")
    static_html = parse_existing_html(EXISTING_HTML)
    print(f"  → {len(static_html)} с кадастром/адресом")

    print("Объединяю данные...")
    objects = merge_data(monitor, calls, estate, static_html)
    print(f"  → {len(objects)} активных объектов")

    print("Геокодинг через НСПД...")
    geocache = _load_geocache()
    geocoded = 0
    for obj in objects:
        if obj["cadastral"] and obj["lat"] is None:
            lat, lon = geocode_nspd(obj["cadastral"], geocache)
            obj["lat"] = lat
            obj["lon"] = lon
            if lat:
                geocoded += 1
                print(f"  ИП {obj['ip_num']}: ({lat}, {lon})")
            time.sleep(0.3)
    _save_geocache(geocache)
    print(f"  → {geocoded} новых координат, всего в кеше: {len(geocache)}")

    print(f"Генерирую {OUTPUT_HTML}...")
    html = generate_html(objects)
    with open(OUTPUT_HTML, "w") as f:
        f.write(html)
    print(f"Готово! {OUTPUT_HTML} ({len(html)} байт, {len(objects)} объектов)")

    print("Генерирую риелторы.html...")
    rieltory_html = generate_rieltory_html(objects)
    with open("риелторы.html", "w") as f:
        f.write(rieltory_html)
    rieltory_count = sum(1 for o in objects if "реализация" in o.get("status", "").lower())
    print(f"Готово! риелторы.html ({len(rieltory_html)} байт, {rieltory_count} объектов)")


if __name__ == "__main__":
    main()
