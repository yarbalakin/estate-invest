#!/usr/bin/env python3
"""
enrich_lookalike.py v3 — Мультиоценка: внутренняя + арендная.

3 рыночных цены для каждого лота:
  1. internal_price  — из реальных сделок Estate Invest (proximity + type + area)
  2. market_price    — уже есть от enrich_market.py (не трогаем)
  3. rental_price    — для коммерции: аренда × 10 лет (cap rate ~10%)

Запуск:
  cd /opt/torgi-proxy
  python3 enrich_lookalike.py
"""

import html as htmllib
import json
import logging
import math
import os
import re
import time

import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

SVODKA_HTML = os.path.join(
    os.path.dirname(__file__), "..", "Реализация", "реализация-сводка.html"
)
CADASTRALS_JSON = os.path.join(
    os.path.dirname(__file__), "..", "Реализация", "cadastrals.json"
)
GEOCACHE_FILE = os.path.join(os.path.dirname(__file__), "ei_geocache.json")

TOP_N = 3

# ads-api для арендных аналогов
ADS_API_USER = os.environ.get("ADS_API_USER", "yabalakin@yandex.ru")
ADS_API_TOKEN = os.environ.get("ADS_API_TOKEN", "de5f6b208f2348f909fa7c3eb8793d95")
ADS_API_URL = "https://ads-api.ru/main/api"
ADS_API_DELAY = 5

# НСПД для геокодинга объектов EI
NSPD_URL = "https://nspd.gov.ru/api/geoportal/v2/search/geoportal"
NSPD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://nspd.gov.ru/map?thematic=PKK",
}

# Cap rate для арендной оценки
CAP_RATE = 0.10  # 10% — типичная ставка капитализации для РФ


# ===========================================================================
# Haversine
# ===========================================================================

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# ===========================================================================
# 1. Загрузка и геокодинг объектов Estate Invest
# ===========================================================================

def _html_clean(text: str) -> str:
    return htmllib.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def _parse_price(raw: str | None) -> float | None:
    if not raw:
        return None
    s = _html_clean(raw).lower()
    m = re.search(r"([\d][\d\s]*[,.]?\d*)\s*(млн|тыс)?", s)
    if not m:
        return None
    num_str = m.group(1).replace(" ", "").replace("\xa0", "").replace(",", ".")
    suffix = m.group(2) or ""
    try:
        val = float(num_str)
        if "млн" in suffix:
            val *= 1_000_000
        elif "тыс" in suffix:
            val *= 1_000
        return val if val > 1000 else None
    except ValueError:
        return None


def _load_geocache() -> dict:
    if os.path.exists(GEOCACHE_FILE):
        with open(GEOCACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_geocache(cache: dict):
    with open(GEOCACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


CN_PATTERN = re.compile(r"^\d{2}:\d{2}:\d{5,7}:\d+$")


def _geocode_cadastral(cad_num: str, cache: dict) -> tuple[float, float] | None:
    """Геокодинг по кадастровому номеру через НСПД."""
    if cad_num in cache:
        c = cache[cad_num]
        if c:
            return c["lat"], c["lon"]
        return None

    if not CN_PATTERN.match(cad_num.strip()):
        cache[cad_num] = None
        return None

    try:
        sess = requests.Session()
        sess.verify = False
        sess.headers.update(NSPD_HEADERS)
        resp = sess.get(
            NSPD_URL,
            params={"query": cad_num.strip(), "thematicSearchId": 1},
            timeout=15,
        )
        if resp.status_code != 200:
            cache[cad_num] = None
            return None

        data = resp.json()
        features = data.get("data", {}).get("features", [])
        if not features:
            cache[cad_num] = None
            return None

        geom = features[0].get("geometry", {})
        coords = geom.get("coordinates")
        if not coords:
            cache[cad_num] = None
            return None

        # EPSG:3857 → WGS-84
        def merc_to_wgs84(x, y):
            lon = x * 180 / 20037508.34
            lat = math.degrees(2 * math.atan(math.exp(y * math.pi / 20037508.34)) - math.pi / 2)
            return lat, lon

        gtype = geom.get("type", "")
        if gtype == "Point":
            lat, lon = merc_to_wgs84(coords[0], coords[1])
        elif gtype == "Polygon":
            ring = coords[0]
            cx = sum(p[0] for p in ring) / len(ring)
            cy = sum(p[1] for p in ring) / len(ring)
            lat, lon = merc_to_wgs84(cx, cy)
        elif gtype == "MultiPolygon":
            ring = coords[0][0]
            cx = sum(p[0] for p in ring) / len(ring)
            cy = sum(p[1] for p in ring) / len(ring)
            lat, lon = merc_to_wgs84(cx, cy)
        else:
            cache[cad_num] = None
            return None

        cache[cad_num] = {"lat": lat, "lon": lon}
        time.sleep(1)
        return lat, lon

    except Exception as e:
        log.warning("НСПД ошибка для %s: %s", cad_num, e)
        cache[cad_num] = None
        return None


# Координаты центров городов (для proximity когда нет точных координат)
CITY_COORDS = {
    "пермь": (58.0105, 56.2502),
    "краснокамск": (58.0754, 56.1632),
    "добрянка": (58.4666, 56.4166),
    "чайковский": (56.7688, 54.1153),
    "кунгур": (57.4308, 56.9444),
    "нытва": (57.9370, 56.3239),
    "березники": (59.4091, 56.8204),
    "соликамск": (59.6310, 56.7701),
    "лысьва": (58.1037, 57.8037),
    "чусовой": (58.2989, 57.8175),
    "оса": (57.2934, 55.4654),
    "калининград": (54.7104, 20.4522),
    "самара": (53.1959, 50.1002),
    "москва": (55.7558, 37.6173),
    "екатеринбург": (56.8389, 60.6057),
}


def load_ei_objects() -> list[dict]:
    """Загружает объекты EI из реализация-сводка.html + координаты из Supabase."""
    path = os.path.abspath(SVODKA_HTML)
    if not os.path.exists(path):
        log.warning("реализация-сводка.html не найден: %s", path)
        return []

    with open(path, encoding="utf-8") as f:
        html = f.read()

    # Загрузить кадастровые номера
    cadastrals = {}
    cad_path = os.path.abspath(CADASTRALS_JSON)
    if os.path.exists(cad_path):
        with open(cad_path, encoding="utf-8") as f:
            raw = json.load(f)
        for ip_num, info in raw.items():
            cn = info.get("cadastral", "")
            first = re.split(r"\s*[|/,]\s*", cn)[0].strip()
            if CN_PATTERN.match(first):
                cadastrals[ip_num] = first

    # Координаты из Supabase (уже геокодированы enrich_cadastral.py)
    coords_map = _load_coords_from_supabase(cadastrals)

    parts = re.split(r'(?=<div class="property-card")', html)
    cards = [p for p in parts if 'property-card' in p[:50]]

    objects = []
    for card in cards:
        city_m = re.search(r'data-city="([^"]+)"', card)
        type_m = re.search(r'data-type="([^"]+)"', card)
        ip_m = re.search(r'data-ip="(\d+)"', card)

        city = city_m.group(1).strip().lower() if city_m else ""
        raw_type = type_m.group(1).lower() if type_m else ""
        ip_num = ip_m.group(1) if ip_m else ""

        if any(w in raw_type for w in ("коммерч", "нежил", "здани", "помещен", "офис", "торгов", "склад", "хостел", "производств")):
            ptype = "commercial"
        elif any(w in raw_type for w in ("земел", "участок")):
            ptype = "land"
        elif any(w in raw_type for w in ("дом", "коттедж", "ижс")):
            ptype = "house"
        else:
            ptype = "apartment"

        area_m = re.search(r'<span class="area-tag">([^<]+)</span>', card)
        area_str = area_m.group(1) if area_m else ""
        area_n = re.search(r"([\d]+[,.]?\d*)", area_str)
        area = float(area_n.group(1).replace(",", ".")) if area_n else None

        buy_m = re.search(r'data-field="buy">([^<]+)<', card)
        sell_m = re.search(r'data-field="sell">([^<]+)<', card)
        exit_m = re.search(r'fin-exit"[^>]*>([^<]+)<', card)

        buy = _parse_price(buy_m.group(1) if buy_m else None)
        sell = _parse_price(sell_m.group(1) if sell_m else None)
        exit_p = _parse_price(exit_m.group(1) if exit_m else None)
        effective_sell = exit_p if (exit_p and buy and exit_p > buy) else sell

        if not (buy and effective_sell and buy > 10_000 and effective_sell > buy):
            continue

        roi = round((effective_sell - buy) / buy * 100, 1)

        # Координаты из Supabase (по кадастру)
        lat, lon = None, None
        if ip_num in coords_map:
            lat, lon = coords_map[ip_num]

        objects.append({
            "ip_num": ip_num,
            "property_type": ptype,
            "area": area,
            "city": city,
            "lat": lat,
            "lon": lon,
            "buy_price": buy,
            "sell_price": effective_sell,
            "sell_per_m2": (effective_sell / area) if (area and area > 0) else None,
            "roi": roi,
            "name": f"ИП{ip_num} {city.title()}, {raw_type}",
        })

    with_coords = sum(1 for o in objects if o["lat"])
    log.info("Загружено %d объектов EI (%d с координатами)", len(objects), with_coords)
    return objects


# ===========================================================================
# 2. Scoring: proximity → type → area → price
# ===========================================================================

def proximity_score(dist_km: float) -> int:
    """Очки за расстояние (0-40). Ближе = лучше."""
    if dist_km < 1:
        return 40
    elif dist_km < 3:
        return 35
    elif dist_km < 5:
        return 30
    elif dist_km < 10:
        return 20
    elif dist_km < 20:
        return 10
    elif dist_km < 50:
        return 5
    return 0


def type_score(lot_type: str, ei_type: str) -> int:
    """Очки за совпадение типа (0-25)."""
    if lot_type == ei_type:
        return 25
    # Частичное совпадение: дом ↔ земля (часто рядом)
    if {lot_type, ei_type} == {"house", "land"}:
        return 10
    return 0


def area_score(lot_area: float, ei_area: float) -> int:
    """Очки за схожесть площади (0-20)."""
    if not lot_area or not ei_area or ei_area <= 0:
        return 0
    ratio = lot_area / ei_area
    if 0.9 <= ratio <= 1.1:
        return 20
    elif 0.75 <= ratio <= 1.25:
        return 16
    elif 0.5 <= ratio <= 1.5:
        return 10
    elif 0.3 <= ratio <= 2.0:
        return 5
    return 0


def price_score(lot_price: float, ei_buy_price: float) -> int:
    """Очки за попадание в ценовой диапазон (0-15)."""
    if not lot_price or not ei_buy_price or ei_buy_price <= 0:
        return 0
    ratio = lot_price / ei_buy_price
    if 0.7 <= ratio <= 1.5:
        return 15
    elif 0.4 <= ratio <= 2.5:
        return 8
    return 0


def calc_similarity(lot: dict, ei_obj: dict) -> tuple[int, float | None, list[str]]:
    """
    Полный скоринг схожести. Возвращает (score, distance_km, reasons).
    """
    reasons = []
    total = 0

    # 1. Proximity (40 pts)
    dist_km = None
    lot_lat, lot_lon = lot.get("lat"), lot.get("lon")
    ei_lat, ei_lon = ei_obj.get("lat"), ei_obj.get("lon")
    if lot_lat and lot_lon and ei_lat and ei_lon:
        dist_km = haversine_km(lot_lat, lot_lon, ei_lat, ei_lon)
        pts = proximity_score(dist_km)
        total += pts
        if pts > 0:
            reasons.append(f"{dist_km:.1f} км")
    else:
        # Фолбек на город
        lot_city = (lot.get("district") or lot.get("address") or "").lower()
        ei_city = (ei_obj.get("city") or "").lower()
        if ei_city and (ei_city in lot_city or any(w in lot_city for w in ei_city.split())):
            total += 15  # Город совпадает, но точное расстояние неизвестно
            reasons.append(f"город {ei_obj['city']}")

    # 2. Type (25 pts)
    pts = type_score(lot.get("property_type", ""), ei_obj.get("property_type", ""))
    total += pts
    if pts > 0:
        reasons.append(f"тип={ei_obj['property_type']}")

    # 3. Area (20 pts)
    pts = area_score(lot.get("area") or 0, ei_obj.get("area") or 0)
    total += pts
    if pts > 0:
        reasons.append(f"площадь {ei_obj.get('area', 0):.0f}м²")

    # 4. Price (15 pts)
    pts = price_score(lot.get("price") or 0, ei_obj.get("buy_price") or 0)
    total += pts
    if pts > 0:
        reasons.append(f"цена ≈ покупке")

    return min(100, total), dist_km, reasons


# ===========================================================================
# 3. Internal price: из сделок EI
# ===========================================================================

def calc_internal_price(lot: dict, ei_objects: list[dict]) -> dict:
    """
    Находит ближайшие похожие объекты EI и рассчитывает internal_price.
    """
    scored = []
    for ei in ei_objects:
        sc, dist, reasons = calc_similarity(lot, ei)
        if sc >= 15:  # минимальный порог
            scored.append((sc, dist, ei, reasons))

    if not scored:
        return {"lookalike_score": 0, "internal_price": None,
                "lookalike_matches": None, "lookalike_match_reason": "нет похожих объектов EI"}

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:TOP_N]

    total_weight = sum(sc for sc, _, _, _ in top)
    if total_weight == 0:
        return {"lookalike_score": 0, "internal_price": None,
                "lookalike_matches": None, "lookalike_match_reason": "нулевые веса"}

    lot_area = lot.get("area") or 0

    # Взвешенная средняя цена
    # Если есть площадь — используем цену за м² × площадь лота
    # Иначе — среднюю абсолютную цену продажи
    if lot_area > 0:
        price_per_m2 = sum(
            sc * (ei.get("sell_per_m2") or ei["sell_price"] / max(ei.get("area") or 1, 1))
            for sc, _, ei, _ in top
        ) / total_weight
        internal_price = round(price_per_m2 * lot_area)
    else:
        internal_price = round(
            sum(sc * ei["sell_price"] for sc, _, ei, _ in top) / total_weight
        )

    avg_score = int(sum(sc for sc, _, _, _ in top) / len(top))
    if len(top) < 2:
        avg_score = min(avg_score, 70)

    matches = []
    for sc, dist, ei, reasons in top:
        matches.append({
            "name": ei.get("name", ""),
            "similarity": sc,
            "distance_km": round(dist, 1) if dist else None,
            "area": ei.get("area"),
            "city": ei.get("city"),
            "sell_price": ei.get("sell_price"),
            "buy_price": ei.get("buy_price"),
            "roi": ei.get("roi"),
        })

    reason_parts = top[0][3] if top else []
    reason = f"топ-{len(top)} EI: " + "; ".join(reason_parts[:4])

    return {
        "lookalike_score": avg_score,
        "internal_price": internal_price,
        "lookalike_matches": matches,
        "lookalike_match_reason": reason,
    }


# ===========================================================================
# 4. Rental price: аренда × 10 лет (только коммерция)
# ===========================================================================

def fetch_rental_analogs(city: str, area: float, lat: float, lon: float) -> list[dict]:
    """Запрашивает арендные аналоги через ads-api."""
    params = {
        "user": ADS_API_USER,
        "token": ADS_API_TOKEN,
        "category_id": 4,  # коммерческая аренда
        "type": 2,  # аренда
        "nedpigimost_type": 1,  # помещения
        "city_name": city,
        "params[1]": f"{area * 0.5:.0f}",  # площадь от
        "params[2]": f"{area * 2:.0f}",    # площадь до
        "date1": "2025-01-01",
        "date2": "2026-12-31",
    }
    try:
        resp = requests.get(ADS_API_URL, params=params, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if isinstance(data, dict) and "data" in data:
            return data["data"][:100]
        if isinstance(data, list):
            return data[:100]
        return []
    except Exception as e:
        log.warning("ads-api rental error: %s", e)
        return []


def _extract_rental_price(ad: dict) -> float | None:
    """Извлекает месячную арендную ставку из объявления."""
    price = ad.get("price")
    if price:
        try:
            return float(price)
        except (ValueError, TypeError):
            pass
    return None


def _extract_rental_area(ad: dict) -> float | None:
    """Извлекает площадь из объявления."""
    area = ad.get("area") or ad.get("square")
    if area:
        try:
            return float(area)
        except (ValueError, TypeError):
            pass
    # Попробовать params
    params = ad.get("params") or {}
    if isinstance(params, dict):
        for key in ("area", "square", "1"):
            val = params.get(key)
            if val:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    pass
    return None


def _extract_coords(ad: dict) -> tuple[float, float] | None:
    coords = ad.get("coords")
    if isinstance(coords, dict):
        la = coords.get("lat") or coords.get("latitude")
        lo = coords.get("lon") or coords.get("lng") or coords.get("longitude")
        if la and lo:
            try:
                return float(la), float(lo)
            except (ValueError, TypeError):
                pass
    for lat_key, lon_key in [("lat", "lon"), ("lat", "lng"), ("latitude", "longitude")]:
        la, lo = ad.get(lat_key), ad.get(lon_key)
        if la and lo:
            try:
                return float(la), float(lo)
            except (ValueError, TypeError):
                pass
    return None


def calc_rental_price(lot: dict) -> dict | None:
    """
    Для коммерческих объектов: находит арендные аналоги,
    считает среднюю аренду за м²/мес → годовая → × 10 лет.
    """
    if lot.get("property_type") != "commercial":
        return None

    area = lot.get("area")
    lat, lon = lot.get("lat"), lot.get("lon")
    if not area or area <= 0 or not lat or not lon:
        return None

    city = "Пермь"
    addr = (lot.get("address") or lot.get("district") or "").lower()
    if "калининград" in addr:
        city = "Калининград"
    elif "самар" in addr:
        city = "Самара"

    analogs = fetch_rental_analogs(city, area, lat, lon)
    if not analogs:
        return None

    time.sleep(ADS_API_DELAY)

    # Фильтруем по расстоянию
    valid = []
    for ad in analogs:
        rent = _extract_rental_price(ad)
        ad_area = _extract_rental_area(ad)
        ad_coords = _extract_coords(ad)
        if not rent or rent < 1000 or not ad_area or ad_area < 5:
            continue

        rent_per_m2 = rent / ad_area

        # Проверка расстояния
        if ad_coords:
            dist = haversine_km(lat, lon, ad_coords[0], ad_coords[1])
            if dist > 5:  # 5 км радиус для аренды
                continue
            valid.append({"rent_per_m2": rent_per_m2, "distance": dist, "rent": rent, "area": ad_area})
        else:
            valid.append({"rent_per_m2": rent_per_m2, "distance": None, "rent": rent, "area": ad_area})

    if len(valid) < 2:
        return None

    # IQR фильтр выбросов
    prices = sorted(v["rent_per_m2"] for v in valid)
    q1 = prices[len(prices) // 4]
    q3 = prices[3 * len(prices) // 4]
    iqr = q3 - q1
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    filtered = [v for v in valid if low <= v["rent_per_m2"] <= high]
    if not filtered:
        filtered = valid

    median_rent_m2 = sorted(v["rent_per_m2"] for v in filtered)[len(filtered) // 2]
    annual_rent = median_rent_m2 * area * 12
    rental_price = round(annual_rent / CAP_RATE)

    return {
        "rental_price": rental_price,
        "rental_analogs_count": len(filtered),
        "rental_per_m2_month": round(median_rent_m2),
    }


# ===========================================================================
# 5. Главная функция
# ===========================================================================

def main():
    log.info("=== Lookalike v3 — мультиоценка EI ===")

    ei_objects = load_ei_objects()
    if not ei_objects:
        log.error("Нет данных об объектах EI — прерываем")
        return

    by_type = {}
    for obj in ei_objects:
        by_type.setdefault(obj["property_type"], []).append(obj)
    log.info("Объекты EI по типам: %s", {t: len(v) for t, v in by_type.items()})

    # Загрузка лотов с пагинацией
    log.info("Загрузка лотов из Supabase...")
    COLS = (
        "lot_id, property_type, price, area, district, address, lat, lon, "
        "apartment, building, land, house, commercial, rental, infra"
    )
    PAGE = 1000
    lots = []
    offset = 0
    while True:
        resp = sb.table("properties").select(COLS).range(offset, offset + PAGE - 1).execute()
        batch = resp.data or []
        lots.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    log.info("Найдено %d лотов", len(lots))

    ok = 0
    rental_ok = 0
    for i, lot in enumerate(lots, 1):
        lot_id = lot["lot_id"]

        # Internal price (из сделок EI)
        result = calc_internal_price(lot, ei_objects)

        # Rental price (для коммерции)
        rental = calc_rental_price(lot)
        if rental:
            result["rental_price"] = rental["rental_price"]
            result["rental_analogs_count"] = rental["rental_analogs_count"]
            result["rental_per_m2_month"] = rental["rental_per_m2_month"]
            rental_ok += 1

        try:
            sb.table("properties").update(result).eq("lot_id", lot_id).execute()
            score = result.get("lookalike_score", 0)
            iprice = result.get("internal_price")
            rprice = result.get("rental_price")
            iprice_str = f"{iprice / 1e6:.1f}М" if iprice else "—"
            rprice_str = f"rent={rprice / 1e6:.1f}М" if rprice else ""
            reason = result.get("lookalike_match_reason", "")[:50]
            log.info("[%d/%d] %s — score=%d internal=%s %s | %s",
                     i, len(lots), lot_id[:30], score, iprice_str, rprice_str, reason)
            ok += 1
        except Exception as e:
            log.error("Ошибка %s: %s", lot_id, e)

    log.info("=" * 50)
    log.info("Готово! Обновлено: %d/%d, с арендной оценкой: %d", ok, len(lots), rental_ok)


if __name__ == "__main__":
    main()
