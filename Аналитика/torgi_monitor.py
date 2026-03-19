#!/usr/bin/env python3
"""
Монитор торгов torgi.gov.ru — недвижимость Пермский край
Cron: каждые 4 часа. Новые лоты → оценка рынка → Telegram + Google Sheets.
"""
import requests
import json
import time
import re
import os
import logging
import statistics
from datetime import datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/opt/torgi-proxy/torgi_monitor.log"),
    ],
)
log = logging.getLogger("torgi")

# === Config ===
PROXY_URL = "http://127.0.0.1:8080/api/torgi"
PROXY_API_KEY = "ei-torgi-2026-mvp"
CAT_CODES = "2,3,4,5,7,8,10,11,47"
DYN_SUBJ_RF = "28"  # Пермский край
SEEN_FILE = "/opt/torgi-proxy/torgi_seen.json"

# ads-api.ru (оценка рынка)
ADS_API_USER = os.environ.get("ADS_API_USER", "yabalakin@yandex.ru")
ADS_API_TOKEN = os.environ.get("ADS_API_TOKEN", "de5f6b208f2348f909fa7c3eb8793d95")
ADS_API_URL = "https://ads-api.ru/main/api"
ADS_API_DELAY = 5  # секунд между запросами

# DaData (геокодирование для координатной фильтрации аналогов)
DADATA_TOKEN = os.environ.get("DADATA_TOKEN", "04143a2e63d9dd14241088e18e89d4ee34fdd8b1")
DADATA_SECRET = os.environ.get("DADATA_SECRET", "8e40f11034823d741339058fbbeadfd545039157")
DADATA_CLEAN_URL = "https://cleaner.dadata.ru/api/v1/clean/address"

_ADS_API_KEYS_LOGGED = False  # однократный вывод структуры ответа ads-api

# Telegram
TG_BOT_TOKEN = "8650381430:AAFKGNZbjQmhAd3ogse9gOWs7_2xoypuo-A"
TG_CHAT_PERSONAL = "191260933"
TG_CHAT_CHANNEL = "-1003759471621"  # @topparsing

# Маппинг категорий torgi → ads-api.ru category_id
# ads-api.ru category_id (числовые)
ADS_CATEGORY_MAP = {
    "Земля": 5,       # Земельные участки
    "Нежилое": 7,     # Коммерческая недвижимость
    "Гараж": 6,       # Гаражи и машиноместа
    "Квартира": 2,    # Квартиры
    "Дом": 4,         # Дома, дачи, коттеджи
    "Прочее": 7,      # fallback → коммерческая
}

# Серверные param_id площади для ads-api.ru (по категориям)
ADS_AREA_PARAMS = {
    5: "4616",   # Земля — площадь в сотках
    7: "4920",   # Коммерция — площадь кв.м
    2: "2313",   # Квартиры — площадь кв.м
    4: "2313",   # Дома — площадь кв.м
    6: None,     # Гаражи — нет серверного фильтра
}

# Фильтр biddType
SKIP_BIDD_TYPES = ["Реализация имущества должников"]


# === Дедупликация ===
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return {}


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f)


def clean_seen(seen, days=30):
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    return {k: v for k, v in seen.items() if v > cutoff}


# === Запрос лотов ===
def fetch_lots():
    try:
        r = requests.get(
            PROXY_URL,
            params={
                "catCode": CAT_CODES,
                "dynSubjRF": DYN_SUBJ_RF,
                "size": "100",
                "page": "0",
                "sort": "firstVersionPublicationDate,desc",
                "lotStatus": "PUBLISHED,APPLICATIONS_SUBMISSION",
                "enrich": "true",
            },
            headers={"X-API-Key": PROXY_API_KEY},
            timeout=120,
        )
        if r.status_code != 200:
            log.error(f"Proxy error: {r.status_code}")
            return []
        data = r.json()
        lots = data.get("content", [])
        log.info(f"Fetched {len(lots)} lots from torgi.gov.ru")
        return lots
    except Exception as e:
        log.error(f"Fetch error: {e}")
        return []


# === Парсинг лота ===
def parse_lot(lot):
    lot_id = str(lot.get("id", ""))
    chars = lot.get("characteristics", [])

    address = ""
    area = ""
    cadastral_number = ""

    for c in chars:
        code = c.get("code", "")
        cname = (c.get("name", "") or "").lower()
        val = c.get("characteristicValue")
        if isinstance(val, list):
            val = ", ".join(v.get("name", "") or v.get("value", "") or "" for v in val)
        elif isinstance(val, dict):
            val = val.get("name", "") or val.get("value", "") or json.dumps(val)
        val = str(val or "")

        if not address and code in ("Address", "addressFIAS") or any(
            w in cname for w in ("адрес", "местоположение", "местонахожден")
        ):
            address = val
        if not area and code in ("Square", "SquareZU", "SquareZU_project", "TotalArea") or "площадь" in cname:
            area = val
        if not cadastral_number and (code == "CadastralNumber" or "кадастровый номер" in cname):
            cadastral_number = val

    # Fallback: estateAddress
    estate_addr = lot.get("estateAddress", "")
    if estate_addr and (not address or address == "Российская Федерация" or len(address) < 10):
        address = estate_addr

    lot_name = lot.get("lotName", "") or ""
    lot_desc = lot.get("lotDescription", "") or ""
    combined = lot_name + " " + lot_desc

    # Парсинг адреса из описания
    if not address or address == "Российская Федерация" or len(address) < 10:
        patterns = [
            r"адрес\s*:\s*(.+?)(?:\s*\(|$)",
            r"(?:по адресу|расположенн?(?:ый|ая|ое|ых)\s+по\s+адресу)\s*:?\s*(.+?)(?:,\s*(?:собственник|принадлежащ|категори|общей площадью|площадью|\()|$)",
            r"(?:местоположение|местонахождение)\s*:?\s*(.+?)(?:,\s*(?:собственник|принадлежащ|категори|общей площадью|площадью)|$)",
        ]
        for pat in patterns:
            m = re.search(pat, combined, re.IGNORECASE)
            if m and len(m.group(1).strip()) > 10:
                address = m.group(1).strip()
                break

    # Парсинг кадастрового номера из описания
    if not cadastral_number:
        m = re.search(r"кад\.?\s*(?:номер|№)?\s*:?\s*(\d{2}:\d{2}:\d{6,7}:\d+)", combined, re.IGNORECASE)
        if m:
            cadastral_number = m.group(1)

    # Парсинг площади из описания
    if not area:
        m = re.search(r"(?:пл(?:ощад[ьи]ю?)?|общ\.?\s*пл)\.?\s*:?\s*([\d\s,.]+?)\s*(?:кв\.?\s*м|м2)", combined, re.IGNORECASE)
        if m:
            area = m.group(1).replace(" ", "").replace(",", ".")

    # Очистка адреса
    if address:
        address = re.sub(r"^Российская Федерация,?\s*", "", address, flags=re.IGNORECASE)
        address = re.sub(r"^край Пермский,?\s*", "Пермский край, ", address, flags=re.IGNORECASE)
        address = re.sub(r"^,\s*", "", address)
        if len(address) > 150:
            address = address[:150] + "..."

    # Цена и задаток
    price = lot.get("startPrice") or lot.get("priceMin") or 0
    deposit = lot.get("deposit") or lot.get("depositAmount") or 0

    # Даты
    bidd_end = lot.get("biddEndTime") or lot.get("auctionStartDate") or ""
    app_end = lot.get("applicationEndDate") or lot.get("biddEndTime") or ""

    def fmt_date(s):
        if not s:
            return "не указана"
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.strftime("%d.%m.%Y")
        except Exception:
            return s[:10] if len(s) >= 10 else s

    # biddType
    bidd_type_raw = lot.get("biddType")
    if isinstance(bidd_type_raw, dict):
        bidd_type = bidd_type_raw.get("name", "")
    else:
        bidd_type = str(bidd_type_raw or "")

    # Категория
    category = ""
    cat_obj = lot.get("category")
    if isinstance(cat_obj, dict) and cat_obj.get("name"):
        cn = cat_obj["name"].lower()
        if "жил" in cn:
            category = "Квартира"
        elif "зем" in cn:
            category = "Земля"
        elif "нежил" in cn:
            category = "Нежилое"
        elif "гараж" in cn:
            category = "Гараж"

    if not category:
        nl = lot_name.lower()
        if any(w in nl for w in ("квартир", "комнат")):
            category = "Квартира"
        elif any(w in nl for w in ("земельн", "участок")):
            category = "Земля"
        elif any(w in nl for w in ("гараж", "бокс")):
            category = "Гараж"
        elif any(w in nl for w in ("дом", "коттедж", "домовлад")):
            category = "Дом"
        elif any(w in nl for w in ("нежил", "здани", "помещен")):
            category = "Нежилое"
        elif "право" in nl and "аренд" in nl:
            category = "Земля"
        else:
            category = "Прочее"

    is_land = category == "Земля"

    # Площадь: числовое значение
    area_num = 0
    if area:
        try:
            area_num = float(str(area).replace(",", ".").replace(" ", ""))
        except ValueError:
            pass

    # Цена за единицу
    price_per_unit = ""
    if price > 0 and area_num > 0:
        if is_land:
            sotki = area_num / 100
            if sotki > 0:
                price_per_unit = f"{int(price / sotki):,} руб/сотка".replace(",", " ")
        else:
            price_per_unit = f"{int(price / area_num):,} руб/м2".replace(",", " ")

    # Площадь форматированная
    area_fmt = ""
    if area_num > 0:
        if is_land:
            sotki = area_num / 100
            if sotki >= 100:
                area_fmt = f"{area_num / 10000:.2f} га"
            else:
                area_fmt = f"{sotki:.1f} сот."
        else:
            area_fmt = f"{area_num:,.1f} кв.м".replace(",", " ")

    etp_url = lot.get("etpUrl", "") or ""
    torgi_url = f"https://torgi.gov.ru/new/public/lots/lot/{lot_id}"
    short_name = (lot_name[:120] + "...") if len(lot_name) > 120 else (lot_name or "Объект")

    # Тип земли / вид коммерции (для фильтрации аналогов)
    land_type = extract_land_type(lot_name, lot_desc) if is_land else ""
    commercial_type = extract_commercial_type(lot_name, lot_desc) if category == "Нежилое" else ""

    return {
        "lotId": lot_id,
        "dateAdded": datetime.now().strftime("%Y-%m-%d"),
        "category": category,
        "name": short_name,
        "address": address,
        "area": area_fmt,
        "areaNum": area_num,
        "isLand": is_land,
        "price": price,
        "deposit": deposit,
        "cadastralNumber": cadastral_number,
        "auctionDate": fmt_date(bidd_end),
        "applicationEnd": fmt_date(app_end),
        "biddType": bidd_type,
        "pricePerUnit": price_per_unit,
        "etpUrl": etp_url,
        "status": lot.get("lotStatus", ""),
        "url": torgi_url,
        "landType": land_type,
        "commercialType": commercial_type,
        "lotName": lot_name,
        "lotDesc": lot_desc,
    }


# === Извлечение города из адреса ===
def extract_city(address):
    if not address:
        return "Пермь"
    addr_lower = address.lower()
    # "г. Город" или "г.Город" или "город Город"
    m = re.search(r"(?:г\.\s*|город\s+)([А-ЯЁа-яё\-]+)", address)
    if m:
        return m.group(1)
    # Известные города Пермского края
    cities = [
        "Пермь", "Краснокамск", "Березники", "Соликамск", "Чайковский",
        "Лысьва", "Кунгур", "Чусовой", "Добрянка", "Чернушка",
        "Оса", "Верещагино", "Нытва", "Губаха", "Кизел",
        "Александровск", "Горнозаводск", "Очёр", "Суксун",
    ]
    for city in cities:
        if city.lower() in addr_lower:
            return city
    # Район → ищем на уровне района
    m = re.search(r"(\w+)\s+(?:район|р-н|муниципальн)", address, re.IGNORECASE)
    if m:
        district = m.group(1)
        # Для сельских районов ищем по названию района
        return district
    return "Пермь"


# === Определение типа земли из описания лота ===
def extract_land_type(lot_name, lot_desc):
    """Определить назначение земельного участка → значение для param[4313]."""
    text = (lot_name + " " + lot_desc).lower()
    if any(w in text for w in ("ижс", "индивидуальное жилищное", "жилая застройка",
                                "жилой дом", "для жилищного")):
        return "Поселений (ИЖС)"
    if any(w in text for w in ("снт", "днп", "садовод", "огородничеств", "дачн",
                                "садовый", "дачный")):
        return "Сельхозназначения (СНТ, ДНП)"
    if any(w in text for w in ("промышлен", "производств", "промназначени", "промышленн")):
        return "Промназначения"
    return ""


# === Определение вида коммерческой недвижимости ===
def extract_commercial_type(lot_name, lot_desc):
    """Определить вид коммерции → значение для param[4869]."""
    text = (lot_name + " " + lot_desc).lower()
    if any(w in text for w in ("офис", "офисн")):
        return "Офисное помещение"
    if any(w in text for w in ("торгов", "магазин", "торговл")):
        return "Торговое помещение"
    if any(w in text for w in ("склад",)):
        return "Складское помещение"
    if any(w in text for w in ("производств", "цех")):
        return "Производственное помещение"
    if any(w in text for w in ("свободн", "универсальн")):
        return "Помещение свободного назначения"
    return ""


# === Извлечение района из адреса ===
def extract_district(address):
    """Извлечь район города из адреса (для фильтра metro в ads-api)."""
    if not address:
        return ""
    m = re.search(r"(?:р-н|район)\s+([А-ЯЁа-яё]+)", address, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"([А-ЯЁа-яё]+)\s+(?:р-н|район)", address, re.IGNORECASE)
    if m:
        return m.group(1)
    return ""


# === Поиск аналогов (ads-api.ru) ===
def _ads_api_request(params):
    """Выполнить запрос к ads-api.ru, вернуть список объявлений."""
    global _ADS_API_KEYS_LOGGED
    try:
        time.sleep(ADS_API_DELAY)
        r = requests.get(ADS_API_URL, params=params, timeout=30)
        if r.status_code != 200:
            log.error(f"ads-api.ru error: {r.status_code}")
            return []
        data = r.json()
        if isinstance(data, dict) and "data" in data:
            items = data["data"]
        elif isinstance(data, list):
            items = data
        else:
            return []
        # Однократно логируем структуру ответа (для диагностики наличия coords)
        if items and not _ADS_API_KEYS_LOGGED:
            sample = items[0]
            log.info(f"  ads-api sample keys: {sorted(sample.keys())}")
            for key in ("lat", "latitude", "lon", "longitude", "geo_lat", "geo_lon",
                        "coords", "coord", "location", "address"):
                if key in sample:
                    log.info(f"  ads-api field '{key}': {sample[key]!r}")
            _ADS_API_KEYS_LOGGED = True
        return items
    except Exception as e:
        log.error(f"ads-api.ru exception: {e}")
        return []


def fetch_analogs(parsed_lot):
    if not ADS_API_USER or not ADS_API_TOKEN:
        log.debug("ads-api.ru credentials not set, skipping market evaluation")
        return None

    category = parsed_lot["category"]
    ads_category = ADS_CATEGORY_MAP.get(category)
    if not ads_category:
        log.info(f"  ads-api: нет маппинга для категории '{category}', пропуск")
        return None

    area_num = parsed_lot["areaNum"]
    is_land = parsed_lot["isLand"]
    city = extract_city(parsed_lot["address"])
    district = extract_district(parsed_lot["address"])

    # Серверная площадь: для земли в сотках, для остального в м2
    area_param_id = ADS_AREA_PARAMS.get(ads_category)
    if is_land and area_num > 0:
        area_value = int(area_num / 100)  # м2 → сотки
    else:
        area_value = int(area_num) if area_num > 0 else 0

    # Доп. фильтры
    land_type = parsed_lot.get("landType", "")
    commercial_type = parsed_lot.get("commercialType", "")
    date_from = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    filters_desc = f"{category}, г.{city}"
    if district:
        filters_desc += f", р-н {district}"
    if land_type:
        filters_desc += f", {land_type}"
    if commercial_type:
        filters_desc += f", {commercial_type}"
    if area_value > 0:
        unit = "сот" if is_land else "м2"
        filters_desc += f", ~{area_value} {unit}"
    log.info(f"  ads-api: ищу аналоги — {filters_desc}")

    # === Базовые параметры ===
    # limit=100 — берём больше кандидатов, filter_analogs_by_proximity отберёт топ-10
    base_params = {
        "user": ADS_API_USER,
        "token": ADS_API_TOKEN,
        "category_id": ads_category,
        "city": city,
        "nedvigimost_type": "1",  # продажа
        "is_actual": "11,1",      # только актуальные
        "limit": "100",
        "sort": "desc",
    }

    # === Точный запрос (фильтр по площади и дате; район убран — фильтруем по coords) ===
    precise_params = dict(base_params)
    precise_params["date1"] = date_from

    if area_param_id and area_value > 0:
        precise_params[f"param[{area_param_id}]"] = str(area_value)

    if ads_category == 5 and land_type:
        precise_params["param[4313]"] = land_type

    if ads_category == 7 and commercial_type:
        precise_params["param[4869]"] = commercial_type

    # Примечание: metro (район) убран — координатная фильтрация в filter_analogs_by_proximity

    items = _ads_api_request(precise_params)
    log.info(f"  ads-api: точный запрос → {len(items)} объявлений")

    # === Fallback: если мало результатов, убираем узкие фильтры ===
    if len(items) < 5:
        relaxed_params = dict(base_params)
        # Оставляем площадь и дату, убираем назначение/вид/район
        if area_param_id and area_value > 0:
            relaxed_params[f"param[{area_param_id}]"] = str(area_value)
        relaxed_params["date1"] = date_from

        items2 = _ads_api_request(relaxed_params)
        log.info(f"  ads-api: расширенный запрос → {len(items2)} объявлений")
        if len(items2) > len(items):
            items = items2

    # === Fallback 2: без даты и площади ===
    if len(items) < 5:
        items3 = _ads_api_request(base_params)
        log.info(f"  ads-api: базовый запрос → {len(items3)} объявлений")
        if len(items3) > len(items):
            items = items3

    return items if items else None


# === Расчёт рыночной оценки ===
def calculate_market_price(analogs, parsed_lot):
    if not analogs or len(analogs) == 0:
        return None

    area_num = parsed_lot["areaNum"]
    is_land = parsed_lot["isLand"]
    lot_price = parsed_lot["price"]

    if area_num <= 0 or lot_price <= 0:
        log.info(f"  оценка: пропуск (площадь={area_num}, цена={lot_price})")
        return None

    # Площадь лота для фильтрации аналогов
    if is_land:
        lot_area_sotki = area_num / 100  # torgi.gov.ru хранит в м2, переводим в сотки
    else:
        lot_area_sotki = area_num  # для нежилого площадь в м2

    # Собираем цены за единицу (фильтруем по площади ±50%)
    unit_prices = []
    valid_analogs = []  # аналоги прошедшие фильтр площади
    for a in analogs:
        a_price = a.get("price", 0)
        if not a_price or a_price <= 0:
            continue

        # Площадь аналога (ads-api: для земли в сотках, для остального в м2)
        a_area = 0
        a_params = a.get("params", {})
        if isinstance(a_params, dict):
            for key, val in a_params.items():
                if "площадь" in key.lower():
                    try:
                        a_area = float(str(val).replace(",", ".").replace(" ", ""))
                    except (ValueError, TypeError):
                        pass
                    if a_area > 0:
                        break

        if a_area <= 0:
            continue

        # Фильтр по площади ±50% (клиентская сторона)
        if lot_area_sotki > 0:
            if a_area < lot_area_sotki * 0.5 or a_area > lot_area_sotki * 1.5:
                continue

        if is_land:
            unit_price = a_price / a_area  # руб/сотка
        else:
            unit_price = a_price / a_area  # руб/м2

        unit_prices.append(unit_price)
        valid_analogs.append((a, a_area, unit_price))

    if len(unit_prices) < 2:
        log.info(f"  оценка: мало аналогов с площадью ({len(unit_prices)} из {len(analogs)})")
        return None

    log.info(f"  оценка: {len(unit_prices)} аналогов с площадью из {len(analogs)} всего")

    # Убрать выбросы (IQR)
    unit_prices_sorted = sorted(unit_prices)
    n = len(unit_prices_sorted)
    q1 = unit_prices_sorted[n // 4] if n >= 4 else unit_prices_sorted[0]
    q3 = unit_prices_sorted[(3 * n) // 4] if n >= 4 else unit_prices_sorted[-1]
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    filtered_prices = []
    filtered_analogs = []
    for (a, a_area, up) in valid_analogs:
        if lower <= up <= upper:
            filtered_prices.append(up)
            filtered_analogs.append((a, a_area, up))

    if len(filtered_prices) < 2:
        filtered_prices = unit_prices
        filtered_analogs = valid_analogs  # fallback

    median_unit = statistics.median(filtered_prices)

    # Рыночная оценка
    if is_land:
        sotki = area_num / 100
        market_price = median_unit * sotki
        market_per_unit = f"{int(median_unit):,} руб/сотка".replace(",", " ")
    else:
        market_price = median_unit * area_num
        market_per_unit = f"{int(median_unit):,} руб/м2".replace(",", " ")

    # Скидка
    discount = ((market_price - lot_price) / market_price * 100) if market_price > 0 else 0

    # Confidence
    count = len(filtered_prices)
    if count < 3:
        confidence = "низкая"
    elif count <= 5:
        confidence = "средняя"
    else:
        confidence = "высокая"

    # Список аналогов с деталями (для карты и Telegram)
    analogs_list = []
    for (a, a_area, up) in filtered_analogs:
        a_url = a.get("url") or a.get("item_url") or a.get("link") or ""
        a_address = a.get("address") or a.get("location") or ""
        a_lat = a.get("lat") or a.get("latitude") or a.get("geo_lat")
        a_lon = a.get("lon") or a.get("longitude") or a.get("geo_lon")
        dist = a.get("_distance_m")
        analogs_list.append({
            "price": int(a.get("price", 0)),
            "area": round(a_area, 1),
            "pricePerUnit": int(up),
            "distance_m": dist,
            "address": a_address,
            "url": a_url,
            "lat": float(a_lat) if a_lat else None,
            "lon": float(a_lon) if a_lon else None,
        })

    result = {
        "marketPrice": int(market_price),
        "marketPricePerUnit": market_per_unit,
        "discount": round(discount, 1),
        "confidence": confidence,
        "analogsCount": count,
        "analogsMedianPrice": int(median_unit),
        "analogsMinPrice": int(min(filtered_prices)),
        "analogsMaxPrice": int(max(filtered_prices)),
        "analogsList": analogs_list,
    }
    mp_fmt = f"{int(market_price):,}".replace(",", " ")
    log.info(f"  оценка: рынок ~{mp_fmt} руб, скидка {result['discount']}%, аналогов {count} ({confidence})")
    return result


# === Геокодирование и пространственная фильтрация аналогов ===

from math import radians, sin, cos, sqrt, atan2

_SETTLEMENT_RE = re.compile(
    r"\b(?:дер\.|д\.|с\.|п\.|г\.п\.|с\.п\.|пос\.|деревня|село|посёлок)\s+([\w\-]+)",
    re.IGNORECASE,
)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние между двумя точками (WGS-84) в метрах."""
    R = 6_371_000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def extract_settlement(address: str) -> str | None:
    """Извлечь название нас. пункта (д., с., п.) из адреса."""
    m = _SETTLEMENT_RE.search(address or "")
    return m.group(1).lower() if m else None


def _proximity_radius_m(category: str, address: str) -> int:
    """Радиус поиска аналогов (м) по типу объекта и типу местности."""
    is_rural = bool(extract_settlement(address))
    cat = category.lower()
    if any(w in cat for w in ("квартир", "комнат")):
        return 1500
    if any(w in cat for w in ("нежил", "гараж", "здани", "помещен", "сооружен")):
        return 2000
    if any(w in cat for w in ("земл", "участ")):
        return 10_000 if is_rural else 2500
    if "дом" in cat:
        return 5000 if is_rural else 3000
    return 3000


def _geocode(address: str, cadastral_number: str | None = None) -> tuple[float | None, float | None]:
    """Геокодирование: НСПД по кадастру (приоритет) → DaData по адресу (fallback)."""
    # 1. НСПД по кадастровому номеру (бесплатно, без лимитов)
    if cadastral_number:
        try:
            from cadastral import geocode_by_cadastral
            lat, lon = geocode_by_cadastral(cadastral_number)
            if lat and lon:
                log.info(f"  NSPD geocode: ({lat:.6f}, {lon:.6f})")
                return lat, lon
        except Exception as e:
            log.debug(f"  NSPD geocode error: {e}")
    # 2. DaData по адресу (fallback)
    lat, lon = _dadata_geocode(address)
    if lat:
        log.info(f"  DaData geocode: ({lat:.4f}, {lon:.4f})")
    return lat, lon


def _dadata_geocode(address: str) -> tuple[float | None, float | None]:
    """Быстрое геокодирование адреса через DaData. Возвращает (lat, lon) или (None, None)."""
    if not DADATA_TOKEN or not address:
        return None, None
    try:
        r = requests.post(
            DADATA_CLEAN_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Token {DADATA_TOKEN}",
                "X-Secret": DADATA_SECRET,
            },
            json=[address],
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list):
                geo_lat = data[0].get("geo_lat")
                geo_lon = data[0].get("geo_lon")
                if geo_lat and geo_lon:
                    return float(geo_lat), float(geo_lon)
    except Exception as e:
        log.debug(f"  DaData geocode error: {e}")
    return None, None


def filter_analogs_by_proximity(
    analogs: list,
    lat: float | None,
    lon: float | None,
    category: str,
    address: str,
    top_n: int = 10,
) -> list:
    """Фильтрует аналоги по близости к объекту, возвращает max top_n ближайших.

    Стратегия:
      1. Если у объекта есть coords И у аналога есть coords → фильтр по радиусу.
      2. Для сельских объектов без coords аналога → матч по нас. пункту.
      3. Без coords → возвращает top_n без пространственного фильтра (деградация).

    Добавляет поле _distance_m к каждому аналогу.
    """
    radius_m = _proximity_radius_m(category, address)
    our_settlement = extract_settlement(address)
    has_our_coords = lat is not None and lon is not None

    result = []
    no_filter_list = []  # аналоги без возможности пространственного фильтра

    for raw_a in analogs:
        a = dict(raw_a)  # копия чтобы не мутировать исходный

        # Попытка взять coords аналога (разные поля в зависимости от API)
        a_lat = a.get("lat") or a.get("latitude") or a.get("geo_lat")
        a_lon = a.get("lon") or a.get("longitude") or a.get("geo_lon")

        if has_our_coords and a_lat and a_lon:
            try:
                dist = haversine_m(lat, lon, float(a_lat), float(a_lon))
                a["_distance_m"] = int(dist)
                if dist <= radius_m:
                    result.append(a)
            except (ValueError, TypeError):
                pass
            continue

        # Fallback: текстовый матч по нас. пункту (для сельских объектов)
        a_address = a.get("address") or a.get("location") or ""
        a_settlement = extract_settlement(a_address)

        if our_settlement and a_settlement:
            if our_settlement == a_settlement:
                a["_distance_m"] = None
                result.append(a)
        else:
            # Нет coords и нет нас. пункта → фильтруем по дистанции невозможно
            a["_distance_m"] = None
            no_filter_list.append(a)

    # Сортируем: с дистанцией — по дистанции, остальные в конце
    result.sort(key=lambda a: a.get("_distance_m") or 0)

    # Если пространственный фильтр ничего не дал — используем все кандидаты
    if not result:
        result = no_filter_list

    kept = result[:top_n]
    with_coords = sum(1 for a in kept if a.get("_distance_m") is not None)
    log.info(
        f"  близость: {len(kept)}/{len(analogs)} аналогов"
        f" (радиус {radius_m // 1000:.1f} км, {with_coords} с координатами)"
    )
    return kept


# === Форматирование Telegram ===
def format_telegram(parsed, market=None):
    cat = parsed["category"].upper()
    bidd_type = parsed["biddType"]
    name = parsed["name"]
    price = parsed["price"]
    deposit = parsed["deposit"]
    address = parsed["address"]
    area = parsed["area"]
    cadastral = parsed["cadastralNumber"]
    price_per_unit = parsed["pricePerUnit"]
    app_end = parsed["applicationEnd"]
    auction_date = parsed["auctionDate"]
    torgi_url = parsed["url"]
    etp_url = parsed["etpUrl"]

    price_fmt = f"{int(price):,}".replace(",", " ") if price else "0"
    deposit_fmt = f"{int(deposit):,}".replace(",", " ") if deposit else "0"

    msg = f"<b>{cat}</b>"
    if bidd_type:
        msg += f" | {bidd_type}"
    msg += f"\n\n{name}\n\n"

    if price > 0:
        msg += f"Цена: <b>{price_fmt} руб</b>"
        if price_per_unit:
            msg += f" ({price_per_unit})"
        msg += "\n"
    else:
        msg += "Цена: <b>по результатам торгов</b>\n"

    if area:
        msg += f"Площадь: {area}\n"
    if address:
        msg += f"Адрес: {address}\n"
    if cadastral:
        msg += f"Кадастр: {cadastral}\n"

    # Блок оценки рынка
    if market:
        mp = f"{market['marketPrice']:,}".replace(",", " ")
        disc = market["discount"]

        if disc > 40:
            label = "Отличная скидка"
        elif disc > 20:
            label = "Хорошая скидка"
        elif disc > 10:
            label = "Средняя скидка"
        elif disc > 0:
            label = "Слабая скидка"
        else:
            label = "Выше рынка"

        msg += f"\n<b>--- ОЦЕНКА РЫНКА ---</b>\n"
        msg += f"Рыночная: ~{mp} руб ({market['marketPricePerUnit']})\n"
        msg += f"Скидка: <b>{disc}%</b> — {label}\n"
        msg += f"Аналогов: {market['analogsCount']} ({market['confidence']} точность)\n"

    msg += f"\nПодача заявок до: {app_end}\n"
    msg += f"Торги: {auction_date}\n"
    msg += f"\n<b>Задаток: {deposit_fmt + ' руб' if deposit > 0 else 'не указан'}</b>\n"
    msg += f'\n<a href="{torgi_url}">Карточка на torgi.gov.ru</a>'
    if etp_url:
        msg += f'\n<a href="{etp_url}">Перейти на ЭТП</a>'

    return msg


# === Telegram ===
def send_telegram(text, chat_id):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if r.status_code == 200:
            return True
        log.error(f"Telegram error: {r.status_code} {r.text[:200]}")
        if r.status_code == 429:
            retry_after = r.json().get("parameters", {}).get("retry_after", 5)
            time.sleep(retry_after)
        return False
    except Exception as e:
        log.error(f"Telegram exception: {e}")
        return False


# === Google Sheets ===
GSHEET_ID = "1Wji_7UYqIRmxbsd1Ob52NutSrKThd3m37fkXDFuBfPk"
GSHEET_SA_FILE = "/opt/torgi-proxy/google-sa.json"
GSHEET_COLUMNS = [
    "lotId", "dateAdded", "category", "name", "address", "area",
    "price", "deposit", "cadastralNumber", "auctionDate", "applicationEnd",
    "biddType", "pricePerUnit", "etpUrl", "status", "url",
    "marketPrice", "marketPricePerUnit", "discount", "confidence", "analogsCount",
]

_gs_client = None


def _get_sheet():
    global _gs_client
    if _gs_client is None:
        creds = Credentials.from_service_account_file(
            GSHEET_SA_FILE,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        _gs_client = gspread.authorize(creds)
    spreadsheet = _gs_client.open_by_key(GSHEET_ID)
    try:
        ws = spreadsheet.worksheet("Лоты")
    except gspread.WorksheetNotFound:
        ws = spreadsheet.sheet1
        # Записать заголовки если лист пустой
        if not ws.row_values(1):
            ws.append_row(GSHEET_COLUMNS)
    return ws


def append_google_sheets(row):
    try:
        ws = _get_sheet()
        values = [row.get(col, "") for col in GSHEET_COLUMNS]
        ws.append_row(values, value_input_option="USER_ENTERED")
        log.info(f"  Google Sheets: записан лот {row.get('lotId', '?')}")
    except Exception as e:
        log.error(f"Google Sheets error: {e}")


# === Main ===
def main():
    log.info("=== Torgi Monitor start ===")

    lots = fetch_lots()
    if not lots:
        log.info("No lots fetched, exiting")
        return

    seen = load_seen()
    seen = clean_seen(seen)

    new_count = 0
    sent_count = 0
    first_run = len(seen) == 0

    for lot in lots:
        lot_id = str(lot.get("id", ""))
        if not lot_id:
            continue

        # Дедупликация
        if lot_id in seen:
            continue

        # Парсинг
        parsed = parse_lot(lot)

        # Фильтр: пропускаем арестованное имущество
        if any(skip in parsed["biddType"] for skip in SKIP_BIDD_TYPES):
            seen[lot_id] = datetime.now().isoformat()
            continue

        new_count += 1
        price_fmt = f"{int(parsed['price']):,}".replace(",", " ") if parsed["price"] else "0"
        log.info(f"[{new_count}] {parsed['category']} | {parsed['name'][:60]} | {price_fmt} руб")

        # Лимит на первый запуск (не спамить)
        if first_run and new_count > 10:
            seen[lot_id] = datetime.now().isoformat()
            continue

        # Оценка рынка (ads-api.ru)
        market = None
        analogs_raw = fetch_analogs(parsed)
        if analogs_raw:
            # Геокодирование: сначала НСПД по кадастру, потом DaData по адресу
            lot_lat, lot_lon = _geocode(parsed["address"], parsed.get("cadastralNumber"))
            # Фильтруем аналоги по близости → топ-10
            analogs = filter_analogs_by_proximity(
                analogs_raw, lot_lat, lot_lon,
                parsed.get("category", ""), parsed["address"],
            )
            if analogs:
                market = calculate_market_price(analogs, parsed)

        # Telegram
        msg = format_telegram(parsed, market)

        # Отправляем в личный чат и канал
        if send_telegram(msg, TG_CHAT_PERSONAL):
            sent_count += 1
        time.sleep(1)
        send_telegram(msg, TG_CHAT_CHANNEL)
        time.sleep(1)

        # Google Sheets
        row = {
            "lotId": parsed["lotId"],
            "dateAdded": parsed["dateAdded"],
            "category": parsed["category"],
            "name": parsed["name"],
            "address": parsed["address"],
            "area": parsed["area"],
            "price": str(parsed["price"]),
            "deposit": str(parsed["deposit"]),
            "cadastralNumber": parsed["cadastralNumber"],
            "auctionDate": parsed["auctionDate"],
            "applicationEnd": parsed["applicationEnd"],
            "biddType": parsed["biddType"],
            "pricePerUnit": parsed["pricePerUnit"],
            "etpUrl": parsed["etpUrl"],
            "status": parsed["status"],
            "url": parsed["url"],
        }
        if market:
            row["marketPrice"] = str(market["marketPrice"])
            row["marketPricePerUnit"] = market["marketPricePerUnit"]
            row["discount"] = str(market["discount"])
            row["confidence"] = market["confidence"]
            row["analogsCount"] = str(market["analogsCount"])

        append_google_sheets(row)

        seen[lot_id] = datetime.now().isoformat()

    save_seen(seen)

    log.info(f"=== Done: {new_count} new lots, {sent_count} messages sent ===")

    # Heartbeat если ничего нового
    if new_count == 0:
        send_telegram("Монитор торгов: проверка завершена, новых лотов нет.", TG_CHAT_PERSONAL)


if __name__ == "__main__":
    main()
