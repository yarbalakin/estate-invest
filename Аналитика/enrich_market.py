#!/usr/bin/env python3
"""
Батч-обогащение лотов рыночной ценой через ads-api.ru.

Загружает из Supabase лоты без market_price, оценивает через аналоги,
записывает результат обратно. Поддерживает resume (пропускает уже обогащённые).

Запуск:
  python3 enrich_market.py                    # все лоты без market_price
  python3 enrich_market.py --limit 10         # первые 10
  python3 enrich_market.py --type apartment   # только квартиры
  python3 enrich_market.py --type land --limit 5
"""
import argparse
import json
import logging
import os
import re
import statistics
import time
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2

import requests

# === CLI ===
_parser = argparse.ArgumentParser(description="Батч-обогащение рыночной ценой")
_parser.add_argument("--limit", type=int, default=0, help="Макс. кол-во лотов (0 = все)")
_parser.add_argument("--force", action="store_true", help="Переобогатить ВСЕ лоты, даже с market_price")
_parser.add_argument("--type", dest="prop_type", default="",
                     choices=["", "apartment", "land", "commercial", "house"],
                     help="Фильтр по property_type")
_args = _parser.parse_args()

# === Logging ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("enrich_market")

# === Config ===
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

ADS_API_USER = os.environ.get("ADS_API_USER", "yabalakin@yandex.ru")
ADS_API_TOKEN = os.environ.get("ADS_API_TOKEN", "de5f6b208f2348f909fa7c3eb8793d95")
ADS_API_URL = "https://ads-api.ru/main/api"
ADS_API_DELAY = 1.5  # секунд между запросами

DADATA_TOKEN = os.environ.get("DADATA_TOKEN", "")
DADATA_CLEAN_URL = "https://cleaner.dadata.ru/api/v1/clean/address"

# Маппинг property_type → ads-api category_id
PROPERTY_TYPE_TO_ADS = {
    "apartment": 2,
    "land": 5,
    "commercial": 7,
    "house": 4,
}

# Маппинг текстовой category → ads category (фаллбек если property_type=null)
CATEGORY_TEXT_TO_ADS = {
    "Здания": 7,
    "Нежилое": 7,
    "Гараж": 6,
    "Квартира": 2,
    "Земля": 5,
    "Дом": 4,
    "Прочее": 7,
}

# Маппинг текстовой category → property_type (для null property_type)
CATEGORY_TEXT_TO_TYPE = {
    "Здания": "commercial",
    "Нежилое": "commercial",
    "Гараж": "commercial",
    "Квартира": "apartment",
    "Земля": "land",
    "Дом": "house",
    "Прочее": "commercial",
}

# Серверные param_id площади (по ads category)
ADS_AREA_PARAMS = {
    5: "4616",   # Земля — площадь в СОТКАХ
    7: "4920",   # Коммерция — м²
    2: "2313",   # Квартиры — м²
    4: "2313",   # Дома — м²
    6: None,     # Гаражи — нет серверного фильтра
}

# Радиусы Haversine (м) по property_type
RADIUS_MAP = {
    "apartment": (1500, 1500),       # (город, село) — квартиры только в городе
    "commercial": (2000, 2000),
    "land": (2500, 10000),
    "house": (3000, 5000),
}

# Cap rate years для метода через аренду (коммерция)
CAP_RATE_MAP = {
    "стрит-ритейл": 8,
    "торгов": 8,
    "магазин": 8,
    "склад": 6,
    "складс": 6,
    "офис": 12,
    "гараж": 10,
    "бокс": 10,
}
DEFAULT_CAP_RATE = 10

# Торговая корректировка (цены предложения завышены на 5-15%)
BARGAIN_DISCOUNT = 0.9

# Кадастровый мультипликатор (фаллбек)
CADASTRAL_MULTIPLIER = {
    "apartment": 1.2,
    "land": 1.3,
    "commercial": 1.5,
    "house": 1.3,
}

# Известные города для extract_city
KNOWN_CITIES = [
    "Пермь", "Краснокамск", "Березники", "Соликамск", "Чайковский",
    "Лысьва", "Кунгур", "Чусовой", "Добрянка", "Чернушка",
    "Оса", "Верещагино", "Нытва", "Губаха", "Кизел",
    "Александровск", "Горнозаводск", "Очёр", "Суксун",
    "Калининград", "Советск", "Черняховск", "Балтийск", "Гусев",
    "Светлый", "Гурьевск", "Зеленоградск", "Светлогорск", "Пионерский",
    "Москва", "Санкт-Петербург", "Екатеринбург", "Новосибирск", "Казань",
    "Нижний Новгород", "Челябинск", "Самара", "Уфа", "Ростов-на-Дону",
    "Красноярск", "Воронеж", "Волгоград", "Краснодар", "Саратов",
    "Тюмень", "Тольятти", "Ижевск", "Барнаул", "Оренбург",
]


# ============================================================
# Вспомогательные функции (портировано из torgi_monitor.py)
# ============================================================

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние между двумя точками (WGS-84) в метрах."""
    R = 6_371_000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


_SETTLEMENT_RE = re.compile(
    r"\b(?:дер\.|д\.|с\.|п\.|г\.п\.|с\.п\.|пос\.|деревня|село|посёлок)\s+([\w\-]+)",
    re.IGNORECASE,
)


def extract_settlement(address: str) -> str | None:
    """Извлечь название нас. пункта (д., с., п.) из адреса."""
    m = _SETTLEMENT_RE.search(address or "")
    return m.group(1).lower() if m else None


def extract_city(address: str) -> str:
    """Извлечь город из адреса."""
    if not address:
        return "Пермь"
    addr_lower = address.lower()

    # Сначала проверяем KNOWN_CITIES (надёжнее regex)
    for city in KNOWN_CITIES:
        if city.lower() in addr_lower:
            return city

    # "г.о. Чайковский" / "городской округ Чайковский" — извлекаем после "г.о."
    m = re.search(r"г\.о\.\s*([А-ЯЁа-яё\-]+)", address)
    if m:
        return m.group(1)

    # "г. Пермь" / "город Пермь" — но НЕ "г.о."
    m = re.search(r"(?<!\.)г\.\s*([А-ЯЁа-яё\-]+)", address)
    if m and m.group(1).lower() != "о":
        return m.group(1)
    m = re.search(r"город\s+([А-ЯЁа-яё\-]+)", address)
    if m:
        return m.group(1)

    # Район
    m = re.search(r"(\w+)\s+(?:район|р-н|муниципальн)", address, re.IGNORECASE)
    if m:
        return m.group(1)
    return "Пермь"


def _proximity_radius_m(prop_type: str, address: str) -> int:
    """Радиус поиска аналогов (м) по типу объекта и типу местности."""
    is_rural = bool(extract_settlement(address))
    radii = RADIUS_MAP.get(prop_type, (3000, 3000))
    return radii[1] if is_rural else radii[0]


def _get_cap_rate(name: str) -> int:
    """Определить cap rate (лет окупаемости) по названию/описанию."""
    text = (name or "").lower()
    for keyword, rate in CAP_RATE_MAP.items():
        if keyword in text:
            return rate
    return DEFAULT_CAP_RATE


# ============================================================
# Supabase
# ============================================================

_sb_client = None


def _get_supabase():
    global _sb_client
    if _sb_client is None:
        try:
            from supabase import create_client
            _sb_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            log.error(f"Supabase init error: {e}")
    return _sb_client


def fetch_lots_to_enrich(prop_type: str = "", limit: int = 0, force: bool = False) -> list:
    """Загрузить лоты из Supabase. force=True — все, иначе WHERE market_price IS NULL."""
    sb = _get_supabase()
    if not sb:
        return []

    query = sb.table("properties").select(
        "id, lot_id, name, category, property_type, address, area, area_unit, "
        "price, lat, lon, cadastral_number, cadastral_value, district"
    )

    if not force:
        query = query.is_("market_price", "null")

    if prop_type:
        query = query.eq("property_type", prop_type)

    # Supabase ограничивает 1000 строк по умолчанию; загрузим пакетами
    all_lots = []
    page_size = 1000
    offset = 0
    target = limit if limit > 0 else 999999

    while len(all_lots) < target:
        batch_size = min(page_size, target - len(all_lots))
        try:
            resp = query.range(offset, offset + batch_size - 1).execute()
            batch = resp.data or []
            all_lots.extend(batch)
            if len(batch) < batch_size:
                break
            offset += batch_size
        except Exception as e:
            log.error(f"Supabase fetch error: {e}")
            break

    log.info(f"Загружено {len(all_lots)} лотов для обогащения"
             + (f" (type={prop_type})" if prop_type else "")
             + (" [FORCE]" if force else ""))
    return all_lots


def update_lot_market(lot_id: str, data: dict) -> bool:
    """Обновить рыночные данные лота в Supabase."""
    sb = _get_supabase()
    if not sb:
        return False
    try:
        # Убираем None значения
        clean = {k: v for k, v in data.items() if v is not None}
        sb.table("properties").update(clean).eq("lot_id", lot_id).execute()
        return True
    except Exception as e:
        log.error(f"Supabase update error for {lot_id}: {e}")
        return False


# ============================================================
# ads-api.ru
# ============================================================

_ADS_KEYS_LOGGED = False


def _ads_api_request(params: dict) -> list:
    """Выполнить запрос к ads-api.ru, вернуть список объявлений."""
    global _ADS_KEYS_LOGGED
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
        if items and not _ADS_KEYS_LOGGED:
            sample = items[0]
            log.info(f"  ads-api sample keys: {sorted(sample.keys())}")
            # Логируем все поля с координатами для диагностики
            for k in ("lat", "lon", "latitude", "longitude", "geo_lat", "geo_lon", "coords", "gk_params"):
                if k in sample:
                    val = sample[k]
                    log.info(f"  ads-api sample[{k}] = {repr(val)[:200]}")
            _ADS_KEYS_LOGGED = True
        return items
    except Exception as e:
        log.error(f"ads-api.ru exception: {e}")
        return []


def fetch_analogs(lot: dict, ads_category: int, prop_type: str) -> list | None:
    """Запросить аналоги из ads-api.ru с 3 уровнями фаллбек."""
    area = lot.get("area") or 0
    is_land = (prop_type == "land")
    city = extract_city(lot.get("address", ""))
    address = lot.get("address", "")

    # Площадь для серверного фильтра
    area_param_id = ADS_AREA_PARAMS.get(ads_category)
    if is_land and area > 0:
        area_unit = lot.get("area_unit", "m2")
        if area_unit == "sotka":
            area_value = int(area)  # уже в сотках
        else:
            area_value = int(area / 100)  # м² → сотки
    else:
        area_value = int(area) if area > 0 else 0

    date_from = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

    log.info(f"  ads-api: г.{city}, cat={ads_category}, area={area_value}")

    # Базовые параметры
    base_params = {
        "user": ADS_API_USER,
        "token": ADS_API_TOKEN,
        "category_id": ads_category,
        "city": city,
        "nedvigimost_type": "1",  # продажа
        "is_actual": "11,1",
        "limit": "100",
        "sort": "desc",
    }

    # === Точный запрос ===
    precise_params = dict(base_params)
    precise_params["date1"] = date_from

    if area_param_id and area_value > 0:
        precise_params[f"param[{area_param_id}]"] = str(area_value)

    # Тип земли
    if ads_category == 5:
        land_type = _extract_land_type(lot.get("name", ""))
        if land_type:
            precise_params["param[4313]"] = land_type

    # Тип коммерции
    if ads_category == 7:
        comm_type = _extract_commercial_type(lot.get("name", ""))
        if comm_type:
            precise_params["param[4869]"] = comm_type

    items = _ads_api_request(precise_params)
    log.info(f"  ads-api: точный → {len(items)}")

    # === Мягкий (без типа) ===
    if len(items) < 5:
        relaxed = dict(base_params)
        relaxed["date1"] = date_from
        if area_param_id and area_value > 0:
            relaxed[f"param[{area_param_id}]"] = str(area_value)
        items2 = _ads_api_request(relaxed)
        log.info(f"  ads-api: мягкий → {len(items2)}")
        if len(items2) > len(items):
            items = items2

    # === Базовый (только город + категория) ===
    if len(items) < 5:
        items3 = _ads_api_request(base_params)
        log.info(f"  ads-api: базовый → {len(items3)}")
        if len(items3) > len(items):
            items = items3

    return items if items else None


def fetch_rental_analogs(lot: dict) -> list | None:
    """Запросить аналоги аренды для коммерции."""
    city = extract_city(lot.get("address", ""))
    area = lot.get("area") or 0
    area_value = int(area) if area > 0 else 0

    params = {
        "user": ADS_API_USER,
        "token": ADS_API_TOKEN,
        "category_id": 7,
        "city": city,
        "nedvigimost_type": "2",  # сдам (аренда)
        "is_actual": "11,1",
        "limit": "100",
        "sort": "desc",
        "date1": (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d"),
    }
    if area_value > 0:
        params["param[4920]"] = str(area_value)

    items = _ads_api_request(params)
    log.info(f"  ads-api: аренда → {len(items)}")
    return items if items else None


def _extract_land_type(name: str) -> str:
    text = (name or "").lower()
    if any(w in text for w in ("ижс", "индивидуальное жилищное", "жилая застройка")):
        return "Поселений (ИЖС)"
    if any(w in text for w in ("снт", "днп", "садовод", "огородничеств", "дачн")):
        return "Сельхозназначения (СНТ, ДНП)"
    if any(w in text for w in ("промышлен", "производств", "промназначени")):
        return "Промназначения"
    return ""


def _extract_commercial_type(name: str) -> str:
    text = (name or "").lower()
    if any(w in text for w in ("офис", "офисн")):
        return "Офисное помещение"
    if any(w in text for w in ("торгов", "магазин")):
        return "Торговое помещение"
    if "склад" in text:
        return "Складское помещение"
    if any(w in text for w in ("производств", "цех")):
        return "Производственное помещение"
    return ""


# ============================================================
# Пространственная фильтрация и дедупликация
# ============================================================

def deduplicate_analogs(analogs: list) -> list:
    """Дедупликация по address + area +-5%."""
    seen = []
    result = []
    for a in analogs:
        a_address = (a.get("address") or a.get("location") or "").strip().lower()
        a_area = _extract_area_from_analog(a)
        is_dup = False
        for (s_addr, s_area) in seen:
            if s_addr and a_address and s_addr == a_address:
                if s_area > 0 and a_area > 0:
                    if abs(a_area - s_area) / max(s_area, 1) < 0.05:
                        is_dup = True
                        break
        if not is_dup:
            result.append(a)
            seen.append((a_address, a_area))
    if len(analogs) != len(result):
        log.info(f"  дедупликация: {len(analogs)} → {len(result)}")
    return result


def filter_analogs_by_proximity(
    analogs: list,
    lat: float | None,
    lon: float | None,
    prop_type: str,
    address: str,
    radius_mult: float = 1.0,
    top_n: int = 10,
) -> list:
    """Фильтрует аналоги по близости, возвращает max top_n ближайших."""
    radius_m = int(_proximity_radius_m(prop_type, address) * radius_mult)
    our_settlement = extract_settlement(address)
    has_our_coords = lat is not None and lon is not None

    result = []
    no_filter_list = []
    _total_with_coords = 0
    _distances = []

    for raw_a in analogs:
        a = dict(raw_a)
        a_lat, a_lon = _extract_coords(a)

        if has_our_coords and a_lat and a_lon:
            _total_with_coords += 1
            try:
                dist = haversine_m(lat, lon, float(a_lat), float(a_lon))
                _distances.append(int(dist))
                a["_distance_m"] = int(dist)
                if dist <= radius_m:
                    result.append(a)
            except (ValueError, TypeError):
                pass
            continue

        a_address = a.get("address") or a.get("location") or ""
        a_settlement = extract_settlement(a_address)

        if our_settlement and a_settlement:
            if our_settlement == a_settlement:
                a["_distance_m"] = None
                result.append(a)
        else:
            a["_distance_m"] = None
            no_filter_list.append(a)

    # Диагностика расстояний
    if _distances:
        _distances.sort()
        log.info(
            f"  дистанции: {_total_with_coords} с coords, "
            f"мин {_distances[0]/1000:.1f} км, макс {_distances[-1]/1000:.1f} км, "
            f"в радиусе {radius_m/1000:.1f} км: {len(result)}"
        )

    result.sort(key=lambda a: a.get("_distance_m") or 0)

    if not result:
        result = no_filter_list

    kept = result[:top_n]
    with_coords = sum(1 for a in kept if a.get("_distance_m") is not None)
    log.info(
        f"  близость: {len(kept)}/{len(analogs)}"
        f" (радиус {radius_m / 1000:.1f} км, {with_coords} с coords)"
    )
    return kept


def _extract_coords(a: dict) -> tuple:
    """Извлечь координаты аналога из всех возможных мест в ответе ads-api."""
    # Прямые поля
    for lat_key, lon_key in [("lat", "lon"), ("lat", "lng"), ("latitude", "longitude"), ("geo_lat", "geo_lon")]:
        la, lo = a.get(lat_key), a.get(lon_key)
        if la and lo:
            try:
                return float(la), float(lo)
            except (ValueError, TypeError):
                pass
    # coords как dict {'lat': ..., 'lng': ...} (ads-api формат!)
    coords_obj = a.get("coords")
    if isinstance(coords_obj, dict):
        la = coords_obj.get("lat") or coords_obj.get("latitude")
        lo = coords_obj.get("lon") or coords_obj.get("lng") or coords_obj.get("longitude")
        if la and lo:
            try:
                return float(la), float(lo)
            except (ValueError, TypeError):
                pass
    # gk_params.coords (Яндекс.Недвижимость)
    gk = a.get("gk_params")
    if isinstance(gk, dict):
        coords = gk.get("coords")
        if isinstance(coords, dict):
            la = coords.get("lat")
            lo = coords.get("lon") or coords.get("lng")
            if la and lo:
                try:
                    return float(la), float(lo)
                except (ValueError, TypeError):
                    pass
    # coords как строка "lat,lon"
    coords_str = a.get("coords")
    if coords_str and isinstance(coords_str, str) and "," in coords_str:
        parts = coords_str.split(",")
        if len(parts) == 2:
            try:
                return float(parts[0].strip()), float(parts[1].strip())
            except (ValueError, TypeError):
                pass
    return None, None


# Кеш геокодинга адресов (в пределах одного запуска)
_geocode_cache: dict[str, tuple[float, float] | None] = {}


def _geocode_address(address: str, city: str) -> tuple[float, float] | None:
    """Геокодинг адреса через DaData Clean API. Возвращает (lat, lon) или None."""
    if not DADATA_TOKEN or not address:
        return None

    full_addr = f"{city}, {address}" if city else address
    if full_addr in _geocode_cache:
        return _geocode_cache[full_addr]

    try:
        resp = requests.post(
            DADATA_CLEAN_URL,
            json=[full_addr],
            headers={
                "Authorization": f"Token {DADATA_TOKEN}",
                "Content-Type": "application/json",
                "X-Secret": os.environ.get("DADATA_SECRET", ""),
            },
            timeout=10,
        )
        if resp.status_code != 200:
            _geocode_cache[full_addr] = None
            return None
        data = resp.json()
        if data and isinstance(data, list) and data[0]:
            lat = data[0].get("geo_lat")
            lon = data[0].get("geo_lon")
            if lat and lon:
                result = (float(lat), float(lon))
                _geocode_cache[full_addr] = result
                return result
    except Exception:
        pass

    _geocode_cache[full_addr] = None
    return None


def _extract_area_from_analog(a: dict) -> float:
    """Извлечь площадь аналога из params."""
    a_params = a.get("params", {})
    if isinstance(a_params, dict):
        for key, val in a_params.items():
            if "площадь" in key.lower():
                try:
                    return float(str(val).replace(",", ".").replace(" ", ""))
                except (ValueError, TypeError):
                    pass
    return 0


# ============================================================
# Расчёт рыночной цены
# ============================================================

def calculate_market_price(analogs: list, lot: dict, prop_type: str, city: str = "") -> dict | None:
    """Расчёт рыночной цены через аналоги продажи."""
    if not analogs:
        return None

    area = lot.get("area") or 0
    price = lot.get("price") or 0
    is_land = (prop_type == "land")

    if area <= 0:
        log.info("  оценка: пропуск (нет площади)")
        return None

    # Площадь лота для фильтрации (для земли в сотках)
    if is_land:
        area_unit = lot.get("area_unit", "m2")
        if area_unit == "sotka":
            lot_area_cmp = area
        else:
            lot_area_cmp = area / 100
    else:
        lot_area_cmp = area

    # Фильтр типа: отсеиваем аналоги несовместимой категории
    # ads-api category_id: 2=Квартиры, 4=Дома, 5=Земля, 6=Гаражи, 7=Коммерция
    _REJECT_CATS = {
        "land": {2, 7},         # земля: не квартиры и не коммерция
        "apartment": {5, 7},    # квартиры: не земля и не коммерция
    }
    reject_set = _REJECT_CATS.get(prop_type, set())
    if reject_set:
        before = len(analogs)
        analogs = [
            a for a in analogs
            if int(a.get("category_id") or 0) not in reject_set
        ]
        if len(analogs) != before:
            log.info(f"  фильтр типа: {before} → {len(analogs)} (отсеяны несовместимые категории)")
        if not analogs:
            log.info("  оценка: все аналоги отсеяны фильтром типа")
            return None

    # Собираем цены за единицу с фильтром площади +-50%
    unit_prices = []
    valid_analogs = []
    for a in analogs:
        a_price = a.get("price", 0)
        if not a_price or a_price <= 0:
            continue

        a_area = _extract_area_from_analog(a)
        if a_area <= 0:
            continue

        # Фильтр площади +-50%
        if lot_area_cmp > 0:
            if a_area < lot_area_cmp * 0.5 or a_area > lot_area_cmp * 1.5:
                continue

        unit_price = a_price / a_area
        unit_prices.append(unit_price)
        valid_analogs.append((a, a_area, unit_price))

    if len(unit_prices) < 2:
        # Повторяем без фильтра площади
        unit_prices = []
        valid_analogs = []
        for a in analogs:
            a_price = a.get("price", 0)
            if not a_price or a_price <= 0:
                continue
            a_area = _extract_area_from_analog(a)
            if a_area <= 0:
                continue
            unit_price = a_price / a_area
            unit_prices.append(unit_price)
            valid_analogs.append((a, a_area, unit_price))
        if len(unit_prices) < 2:
            log.info(f"  оценка: мало аналогов даже без фильтра площади ({len(unit_prices)})")
            return None
        log.info(f"  оценка: {len(unit_prices)} аналогов (без фильтра площади)")

    else:
        log.info(f"  оценка: {len(unit_prices)} аналогов с площадью")

    # IQR очистка выбросов
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
        filtered_analogs = valid_analogs

    median_unit = statistics.median(filtered_prices)

    # Рыночная оценка × корректировка на торг
    if is_land:
        area_unit = lot.get("area_unit", "m2")
        if area_unit == "sotka":
            market_price = median_unit * area * BARGAIN_DISCOUNT
        else:
            sotki = area / 100
            market_price = median_unit * sotki * BARGAIN_DISCOUNT
        market_per_unit = round(median_unit * BARGAIN_DISCOUNT, 2)
    else:
        market_price = median_unit * area * BARGAIN_DISCOUNT
        market_per_unit = round(median_unit * BARGAIN_DISCOUNT, 2)

    # Скидка
    discount = ((market_price - price) / market_price * 100) if market_price > 0 and price > 0 else 0

    # Confidence
    count = len(filtered_prices)
    radius_m = _proximity_radius_m(prop_type, lot.get("address", ""))
    if count >= 10 and radius_m < 2000:
        confidence = "высокая"
    elif count >= 3:
        confidence = "средняя"
    else:
        confidence = "низкая"

    # Формируем список top-10 аналогов
    analogs_list = []
    for (a, a_area, up) in filtered_analogs[:10]:
        a_url = a.get("url") or a.get("item_url") or a.get("link") or ""
        a_address = a.get("address") or a.get("location") or ""
        a_lat, a_lon = _extract_coords(a)
        dist = a.get("_distance_m")

        # Если нет координат — геокодим по адресу через DaData
        lot_lat, lot_lon = lot.get("lat"), lot.get("lon")
        if not a_lat and a_address and DADATA_TOKEN:
            geocoded = _geocode_address(a_address, city)
            if geocoded:
                a_lat, a_lon = geocoded
                # Пересчитываем расстояние
                if lot_lat and lot_lon:
                    dist = int(haversine_m(lot_lat, lot_lon, a_lat, a_lon))

        # Дата и актуальность
        a_date = a.get("time_source_updated") or a.get("time_source_created") or a.get("time") or ""
        if a_date and " " in a_date:
            a_date = a_date.split(" ")[0]  # только YYYY-MM-DD
        is_actual = a.get("is_actual")
        a_source = a.get("source") or ""

        analogs_list.append({
            "price": int(a.get("price", 0)),
            "area": round(a_area, 1),
            "pricePerUnit": int(up),
            "distance_m": dist,
            "address": a_address,
            "url": a_url,
            "lat": float(a_lat) if a_lat else None,
            "lon": float(a_lon) if a_lon else None,
            "date": a_date,
            "is_actual": is_actual == 11 or is_actual == "11",
            "source": a_source,
        })

    return {
        "market_price": round(market_price, 2),
        "market_price_per_unit": market_per_unit,
        "discount": round(discount, 1),
        "confidence": confidence,
        "analogs_count": count,
        "analogs_median_price": round(median_unit * BARGAIN_DISCOUNT, 2),
        "analogs_min_price": round(min(filtered_prices) * BARGAIN_DISCOUNT, 2),
        "analogs_max_price": round(max(filtered_prices) * BARGAIN_DISCOUNT, 2),
        "analogs_radius_m": radius_m,
        "analogs_source": "ads-api",
        "analogs_list": analogs_list,
    }


def calculate_rental_market_price(rental_analogs: list, lot: dict) -> dict | None:
    """Расчёт рыночной цены коммерции через аренду (доходный метод)."""
    if not rental_analogs:
        return None

    area = lot.get("area") or 0
    if area <= 0:
        return None

    # Собираем арендные ставки руб/м²/мес
    rent_rates = []
    for a in rental_analogs:
        a_price = a.get("price", 0)
        if not a_price or a_price <= 0:
            continue
        a_area = _extract_area_from_analog(a)
        if a_area <= 0:
            continue
        # Фильтр площади +-50%
        if a_area < area * 0.5 or a_area > area * 1.5:
            continue
        rent_rates.append(a_price / a_area)

    if len(rent_rates) < 2:
        return None

    # IQR очистка
    sorted_rates = sorted(rent_rates)
    n = len(sorted_rates)
    q1 = sorted_rates[n // 4] if n >= 4 else sorted_rates[0]
    q3 = sorted_rates[(3 * n) // 4] if n >= 4 else sorted_rates[-1]
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    filtered = [r for r in rent_rates if lower <= r <= upper]
    if len(filtered) < 2:
        filtered = rent_rates

    median_rent = statistics.median(filtered)  # руб/м²/мес

    cap_rate_years = _get_cap_rate(lot.get("name", ""))
    useful_area = area * 0.8  # полезная площадь
    annual_income = median_rent * useful_area * 12
    market_price_rent = annual_income * cap_rate_years

    log.info(
        f"  аренда: медиана {median_rent:.0f} руб/м²/мес, "
        f"доход {annual_income:,.0f}/год, cap={cap_rate_years}, "
        f"оценка {market_price_rent:,.0f}"
    )

    return {
        "market_price_rent": round(market_price_rent, 2),
        "rent_price_month": round(median_rent, 2),
        "annual_yield": round(annual_income, 2),
        "payback_years": cap_rate_years,
        "cap_rate": cap_rate_years,
        "rent_analogs_count": len(filtered),
    }


def cadastral_fallback(lot: dict, prop_type: str) -> dict | None:
    """Кадастровый фаллбек: cadastral_value * multiplier."""
    cad_val = lot.get("cadastral_value")
    if not cad_val or cad_val <= 0:
        return None

    multiplier = CADASTRAL_MULTIPLIER.get(prop_type, 1.3)
    market_price = cad_val * multiplier
    area = lot.get("area") or 0
    price = lot.get("price") or 0

    market_per_unit = (market_price / area) if area > 0 else 0
    discount = ((market_price - price) / market_price * 100) if market_price > 0 and price > 0 else 0

    log.info(f"  кадастровый фаллбек: {cad_val:,.0f} × {multiplier} = {market_price:,.0f}")

    return {
        "market_price": round(market_price, 2),
        "market_price_per_unit": round(market_per_unit, 2),
        "discount": round(discount, 1),
        "confidence": "кадастр",
        "analogs_count": 0,
        "analogs_median_price": None,
        "analogs_min_price": None,
        "analogs_max_price": None,
        "analogs_radius_m": None,
        "analogs_source": "cadastral-fallback",
        "analogs_list": None,
    }


# ============================================================
# Основной цикл
# ============================================================

def resolve_property_type(lot: dict) -> str | None:
    """Определить property_type; вернуть None если пропустить.

    ВАЖНО: property_type в Supabase может быть неверным (напр. "apartment" для
    "Земельный участок"). Приоритет: name/category текст > property_type из БД.
    """
    name = (lot.get("name") or "").lower()
    cat = (lot.get("category") or "").lower()
    text = name + " " + cat

    # Пропускаем не-недвижимость
    if "права требования" in text or "дебиторск" in text:
        return None

    # Приоритет 1: явные объекты в НАЗВАНИИ (name важнее category)
    # ВАЖНО: "нежил" перед "квартир" т.к. "многоквартирного" содержит "квартир"
    if any(w in name for w in ("нежил",)):
        return "commercial"
    if any(w in name for w in ("жилой дом", "коттедж", "дача", "дом,")):
        return "house"
    if any(w in name for w in ("квартир", "комнат")) and "многоквартирн" not in name:
        return "apartment"
    if any(w in name for w in ("помещен", "здани", "сооружен", "склад", "офис", "магазин")):
        return "commercial"
    if any(w in name for w in ("земельн", "участ", "з/у")):
        return "land"
    if any(w in name for w in ("гараж", "бокс")):
        return "commercial"

    # Приоритет 2: по общему тексту (name + category)
    if any(w in text for w in ("нежил",)):
        return "commercial"
    if any(w in text for w in ("жилой дом", "коттедж", "дача")):
        return "house"
    if any(w in text for w in ("квартир", "комнат", "жилое помещение", "жилых")) and "многоквартирн" not in text:
        return "apartment"
    if any(w in text for w in ("помещен", "здани", "сооружен", "склад", "офис", "магазин", "торгов")):
        return "commercial"
    if any(w in text for w in ("земельн", "участ", "участок", "з/у")):
        return "land"
    if any(w in text for w in ("дом ", "жилой дом", "коттедж", "дача")):
        return "house"
    if "гараж" in text or "бокс" in text:
        return "commercial"

    # Фаллбек на property_type из БД
    pt = lot.get("property_type")
    if pt and pt in PROPERTY_TYPE_TO_ADS:
        return pt

    return "commercial"  # default


def resolve_ads_category(prop_type: str, lot: dict) -> int | None:
    """ads-api category_id по property_type."""
    ads_cat = PROPERTY_TYPE_TO_ADS.get(prop_type)
    if ads_cat:
        return ads_cat

    # Фаллбек по текстовой category
    cat = lot.get("category", "")
    for key, val in CATEGORY_TEXT_TO_ADS.items():
        if key.lower() in cat.lower():
            return val

    return 7  # default коммерция


def enrich_lot(lot: dict) -> bool:
    """Обогатить один лот рыночной ценой. Возвращает True если обновлён."""
    lot_id = lot.get("lot_id", "?")
    name = (lot.get("name") or "")[:60]
    address = lot.get("address") or ""
    lat = lot.get("lat")
    lon = lot.get("lon")
    area = lot.get("area") or 0

    log.info(f"\n--- {lot_id}: {name}")

    # Проверки
    if lat is None or lon is None:
        log.warning(f"  SKIP: нет координат")
        return False
    if not area or area <= 0:
        log.warning(f"  SKIP: нет площади")
        return False

    prop_type = resolve_property_type(lot)
    if prop_type is None:
        log.warning(f"  SKIP: тип не подходит (Права требования и т.п.)")
        return False

    ads_category = resolve_ads_category(prop_type, lot)
    city = extract_city(address)
    log.info(f"  тип: {prop_type} (DB: {lot.get('property_type')}), ads_cat={ads_category}")

    # 1. Запрос аналогов продажи
    raw_analogs = fetch_analogs(lot, ads_category, prop_type)

    market_result = None
    if raw_analogs:
        # Дедупликация
        deduped = deduplicate_analogs(raw_analogs)

        # Пространственный фильтр с адаптивным расширением радиуса
        filtered = filter_analogs_by_proximity(deduped, lat, lon, prop_type, address, top_n=10)

        # Если 0 аналогов в радиусе — расширяем ×2, потом ×4
        if not filtered:
            log.info("  расширяем радиус ×2...")
            filtered = filter_analogs_by_proximity(
                deduped, lat, lon, prop_type, address, top_n=10, radius_mult=2.0
            )
        if not filtered:
            log.info("  расширяем радиус ×4...")
            filtered = filter_analogs_by_proximity(
                deduped, lat, lon, prop_type, address, top_n=10, radius_mult=4.0
            )

        # Расчёт
        market_result = calculate_market_price(filtered, lot, prop_type, city=city)

    # 2. Для коммерции — дополнительно метод через аренду
    rental_data = None
    if prop_type == "commercial":
        rental_analogs = fetch_rental_analogs(lot)
        if rental_analogs:
            rental_deduped = deduplicate_analogs(rental_analogs)
            rental_filtered = filter_analogs_by_proximity(
                rental_deduped, lat, lon, prop_type, address, top_n=10
            )
            if not rental_filtered:
                rental_filtered = filter_analogs_by_proximity(
                    rental_deduped, lat, lon, prop_type, address, top_n=10, radius_mult=3.0
                )
            rental_data = calculate_rental_market_price(rental_filtered, lot)

    # 3. Объединяем продажу + аренду (если оба метода)
    if market_result and rental_data:
        sale_price = market_result["market_price"]
        rent_price = rental_data["market_price_rent"]
        avg_price = (sale_price + rent_price) / 2
        market_result["market_price"] = round(avg_price, 2)
        # Пересчитываем discount
        price = lot.get("price") or 0
        if avg_price > 0 and price > 0:
            market_result["discount"] = round((avg_price - price) / avg_price * 100, 1)
        log.info(f"  среднее продажа+аренда: {avg_price:,.0f}")
    elif not market_result and rental_data:
        # Только аренда
        market_result = {
            "market_price": rental_data["market_price_rent"],
            "market_price_per_unit": None,
            "discount": 0,
            "confidence": "низкая",
            "analogs_count": rental_data["rent_analogs_count"],
            "analogs_median_price": None,
            "analogs_min_price": None,
            "analogs_max_price": None,
            "analogs_radius_m": None,
            "analogs_source": "rental",
            "analogs_list": None,
        }
        price = lot.get("price") or 0
        mp = rental_data["market_price_rent"]
        if mp > 0 and price > 0:
            market_result["discount"] = round((mp - price) / mp * 100, 1)

    # 4. Кадастровый фаллбек
    if not market_result or (market_result.get("analogs_count", 0) < 2):
        cad_result = cadastral_fallback(lot, prop_type)
        if cad_result:
            if not market_result:
                market_result = cad_result
            else:
                # Если были аналоги но мало — оставляем аналоги, меняем source
                market_result["analogs_source"] = "cadastral-fallback"
                market_result["confidence"] = "кадастр"

    if not market_result:
        log.warning(f"  НЕТ ОЦЕНКИ: нет аналогов и нет кадастровой стоимости")
        return False

    # 5. Записываем в Supabase
    update_data = {
        "market_price": market_result.get("market_price"),
        "market_price_per_unit": market_result.get("market_price_per_unit"),
        "discount": market_result.get("discount"),
        "confidence": market_result.get("confidence"),
        "analogs_count": market_result.get("analogs_count"),
        "analogs_median_price": market_result.get("analogs_median_price"),
        "analogs_min_price": market_result.get("analogs_min_price"),
        "analogs_max_price": market_result.get("analogs_max_price"),
        "analogs_radius_m": market_result.get("analogs_radius_m"),
        "analogs_source": market_result.get("analogs_source"),
        "analogs_list": market_result.get("analogs_list"),
    }

    # Rental block для коммерции
    if rental_data:
        update_data["rental"] = {
            "rent_price_month": rental_data["rent_price_month"],
            "annual_yield": rental_data["annual_yield"],
            "payback_years": rental_data["payback_years"],
            "cap_rate": rental_data["cap_rate"],
        }

    ok = update_lot_market(lot_id, update_data)
    if ok:
        mp_fmt = f"{market_result['market_price']:,.0f}".replace(",", " ")
        disc = market_result.get("discount", 0)
        src = market_result.get("analogs_source", "?")
        log.info(f"  OK: {mp_fmt} руб, скидка {disc}%, source={src}")
    return ok


def main():
    log.info("=== enrich_market.py START ===")
    lots = fetch_lots_to_enrich(prop_type=_args.prop_type, limit=_args.limit, force=_args.force)
    if not lots:
        log.info("Нечего обогащать")
        return

    ok_count = 0
    skip_count = 0
    err_count = 0

    for i, lot in enumerate(lots, 1):
        log.info(f"\n[{i}/{len(lots)}]")
        try:
            if enrich_lot(lot):
                ok_count += 1
            else:
                skip_count += 1
        except Exception as e:
            log.error(f"  ОШИБКА: {e}", exc_info=True)
            err_count += 1

    log.info(f"\n=== ИТОГО: обогащено {ok_count}, пропущено {skip_count}, ошибок {err_count} ===")


if __name__ == "__main__":
    main()
