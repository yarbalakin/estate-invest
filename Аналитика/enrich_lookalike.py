#!/usr/bin/env python3
"""
enrich_lookalike.py — Lookalike-скоринг лотов по профилю проданных объектов.

Логика: берём объекты со статусом "завершен" из Google Sheets,
строим «ДНК успешной сделки» и сравниваем новые лоты из Supabase.

Запуск:
  cd /opt/torgi-proxy && source venv/bin/activate
  python enrich_lookalike.py

Добавляет в Supabase колонки:
  lookalike_score        — 0-100, схожесть с проданными объектами
  lookalike_match_reason — текстовое пояснение совпадений
"""

import logging
import os
import re

import requests
import pandas as pd
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

# Google Sheets — лист "Объекты" (gid=1464507984)
SPREADSHEET_ID = "1dWTjYF8sEc20SKeyl-e6PomBFq3VlfX-m8K2ZRopZJ0"
OBJECTS_GID = 1464507984


# ---------------------------------------------------------------------------
# Fallback-профиль на основе известных данных Estate Invest
# Используется если Google Sheets недоступен с сервера
# ---------------------------------------------------------------------------
FALLBACK_PROFILE = {
    "type_freq": {"apartment": 35, "commercial": 12, "house": 5, "land": 2},
    "top_type": "apartment",
    "area_min": 18.0,
    "area_max": 350.0,
    "area_median": 52.0,
    "price_min": 120_000.0,
    "price_max": 8_000_000.0,
    "price_median": 1_400_000.0,
    "roi_min": 12.0,
    "roi_max": 85.0,
    "roi_median": 28.0,
    "cities": {
        "калининград": 18, "пермь": 12, "чебоксары": 4,
        "ижевск": 3, "тюмень": 3, "уфа": 2, "казань": 2
    },
}


# ---------------------------------------------------------------------------
# 1. Загрузка проданных объектов из Google Sheets
# ---------------------------------------------------------------------------

def parse_number(value):
    """Парсинг русского числового формата: '5 242 922,06' -> 5242922.06"""
    if pd.isna(value):
        return None
    s = str(value).strip()
    for suffix in ("р.", "₽", "€", "$", "%"):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
            break
    s = s.replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def load_sold_objects() -> list[dict]:
    """Загружает завершённые объекты из Google Sheets."""
    url = (
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
        f"/export?format=csv&gid={OBJECTS_GID}"
    )
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        log.error("Не удалось загрузить Google Sheets: %s", e)
        return []

    from io import StringIO
    # Пропускаем первые 3 строки (шапка по документации header_row=3)
    df = pd.read_csv(StringIO(resp.text), skiprows=3, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]

    # Ищем нужные колонки по частичному совпадению
    col_map = {}
    for col in df.columns:
        cl = col.lower()
        if "стадия" in cl:
            col_map["стадия"] = col
        elif "тип" in cl and "тип" not in col_map:
            col_map["тип"] = col
        elif "площадь" in cl and "площадь" not in col_map:
            col_map["площадь"] = col
        elif "покупки в рублях" in cl or ("покупки" in cl and "руб" in cl):
            col_map["цена_покупки"] = col
        elif "продажи в рублях" in cl or ("продажи" in cl and "руб" in cl):
            col_map["цена_продажи"] = col
        elif "roi" in cl:
            col_map["roi"] = col
        elif "название объекта" in cl or "название" in cl:
            col_map["название"] = col
        elif "срок" in cl and "реализ" in cl and "макс" in cl:
            col_map["срок_макс"] = col

    log.info("Найдены колонки: %s", col_map)

    sold = []
    stage_col = col_map.get("стадия")
    if not stage_col:
        log.warning("Колонка 'Стадия объекта' не найдена")
        return []

    for _, row in df.iterrows():
        stage = str(row.get(stage_col, "")).strip().lower()
        if "завершен" not in stage:
            continue

        obj = {"название": str(row.get(col_map.get("название", ""), "")).strip()}

        # Тип объекта
        raw_type = str(row.get(col_map.get("тип", ""), "")).lower()
        if "коммерч" in raw_type or "нежилое" in raw_type:
            obj["property_type"] = "commercial"
        elif "земл" in raw_type:
            obj["property_type"] = "land"
        elif "дом" in raw_type or "ижс" in raw_type or "коттедж" in raw_type:
            obj["property_type"] = "house"
        else:
            obj["property_type"] = "apartment"  # по умолчанию

        obj["area"] = parse_number(row.get(col_map.get("площадь", ""), None))
        obj["buy_price"] = parse_number(row.get(col_map.get("цена_покупки", ""), None))
        obj["sell_price"] = parse_number(row.get(col_map.get("цена_продажи", ""), None))
        obj["roi"] = parse_number(row.get(col_map.get("roi", ""), None))
        obj["срок_макс"] = parse_number(row.get(col_map.get("срок_макс", ""), None))

        # Извлекаем город из названия объекта
        name = obj["название"]
        city_match = re.match(r"^([^,]+),", name)
        obj["city"] = city_match.group(1).strip() if city_match else ""

        # ROI: если не распарсили — считаем по ценам
        if obj["roi"] is None and obj["buy_price"] and obj["sell_price"] and obj["buy_price"] > 0:
            obj["roi"] = round((obj["sell_price"] - obj["buy_price"]) / obj["buy_price"] * 100, 1)

        sold.append(obj)

    log.info("Загружено %d завершённых объектов", len(sold))
    return sold


# ---------------------------------------------------------------------------
# 2. Построение «ДНК» успешных сделок
# ---------------------------------------------------------------------------

def build_profile(sold: list[dict]) -> dict:
    """Строит статистический профиль проданных объектов."""
    if not sold:
        return {}

    profile = {}

    # Распределение по типам
    types = [o["property_type"] for o in sold if o.get("property_type")]
    type_counts = {}
    for t in types:
        type_counts[t] = type_counts.get(t, 0) + 1
    profile["type_freq"] = type_counts
    profile["top_type"] = max(type_counts, key=type_counts.get) if type_counts else "apartment"

    # Диапазоны площади
    areas = [o["area"] for o in sold if o.get("area") and o["area"] > 0]
    if areas:
        profile["area_min"] = min(areas)
        profile["area_max"] = max(areas)
        profile["area_median"] = sorted(areas)[len(areas) // 2]
    else:
        profile["area_min"] = 0
        profile["area_max"] = 10000
        profile["area_median"] = 50

    # Диапазоны цены покупки
    buy_prices = [o["buy_price"] for o in sold if o.get("buy_price") and o["buy_price"] > 0]
    if buy_prices:
        profile["price_min"] = min(buy_prices)
        profile["price_max"] = max(buy_prices)
        profile["price_median"] = sorted(buy_prices)[len(buy_prices) // 2]
    else:
        profile["price_min"] = 0
        profile["price_max"] = 50_000_000
        profile["price_median"] = 2_000_000

    # ROI успешных сделок
    rois = [o["roi"] for o in sold if o.get("roi") is not None]
    if rois:
        profile["roi_min"] = min(rois)
        profile["roi_max"] = max(rois)
        profile["roi_median"] = sorted(rois)[len(rois) // 2]
    else:
        profile["roi_min"] = 0
        profile["roi_max"] = 100
        profile["roi_median"] = 20

    # Города
    cities = [o["city"].lower() for o in sold if o.get("city")]
    city_counts = {}
    for c in cities:
        city_counts[c] = city_counts.get(c, 0) + 1
    profile["cities"] = city_counts

    log.info("Профиль: %d типов, площадь %.0f-%.0f м², цена %.0f-%.0f руб, ROI %.0f-%.0f%%",
             len(type_counts),
             profile.get("area_min", 0), profile.get("area_max", 0),
             profile.get("price_min", 0), profile.get("price_max", 0),
             profile.get("roi_min", 0), profile.get("roi_max", 0))

    return profile


# ---------------------------------------------------------------------------
# 3. Расчёт lookalike-скора для лота
# ---------------------------------------------------------------------------

def calc_lookalike(lot: dict, profile: dict) -> tuple[int, str]:
    """
    Возвращает (score 0-100, reason str).
    Логика: сравниваем лот с профилем успешных сделок по 5 факторам.
    """
    if not profile:
        return 0, "Нет данных о проданных объектах"

    score = 0
    reasons = []

    # --- Фактор 1: Тип объекта (25 очков) ---
    ptype = lot.get("property_type", "")
    type_freq = profile.get("type_freq", {})
    total_sold = sum(type_freq.values()) or 1
    type_share = type_freq.get(ptype, 0) / total_sold

    if type_share >= 0.5:
        score += 25
        reasons.append(f"тип '{ptype}' — в {int(type_share*100)}% наших сделок")
    elif type_share >= 0.2:
        score += 15
        reasons.append(f"тип '{ptype}' — продавали")
    elif type_share > 0:
        score += 7
        reasons.append(f"тип '{ptype}' — редко продавали")
    else:
        reasons.append(f"тип '{ptype}' — не продавали раньше")

    # --- Фактор 2: Площадь (20 очков) ---
    area = lot.get("area") or 0
    a_min = profile.get("area_min", 0)
    a_max = profile.get("area_max", 10000)
    a_med = profile.get("area_median", 50)

    if area > 0:
        if a_min <= area <= a_max:
            # В нашем диапазоне — ближе к медиане = лучше
            deviation = abs(area - a_med) / (a_max - a_min + 1)
            pts = round(20 * (1 - deviation))
            score += max(5, pts)
            reasons.append(f"площадь {area:.0f} м² — в нашем диапазоне ({a_min:.0f}-{a_max:.0f})")
        elif area < a_min * 0.5 or area > a_max * 2:
            reasons.append(f"площадь {area:.0f} м² — сильно вне нашего диапазона")
        else:
            score += 5
            reasons.append(f"площадь {area:.0f} м² — близко к нашему диапазону")

    # --- Фактор 3: Ценовой диапазон (25 очков) ---
    price = lot.get("price") or 0
    p_min = profile.get("price_min", 0)
    p_max = profile.get("price_max", 50_000_000)
    p_med = profile.get("price_median", 2_000_000)

    if price > 0:
        if p_min <= price <= p_max:
            deviation = abs(price - p_med) / (p_max - p_min + 1)
            pts = round(25 * (1 - deviation))
            score += max(5, pts)
            reasons.append(f"цена {price/1e6:.1f}М — в нашем ценовом диапазоне")
        elif price > p_max * 3:
            reasons.append(f"цена {price/1e6:.1f}М — слишком дорого для нашей модели")
        else:
            score += 5
            reasons.append(f"цена {price/1e6:.1f}М — около нашего диапазона")

    # --- Фактор 4: Потенциальный ROI (20 очков) ---
    estimated_roi = lot.get("estimated_roi")
    r_min = profile.get("roi_min", 10)
    r_max = profile.get("roi_max", 100)
    r_med = profile.get("roi_median", 20)

    if estimated_roi is not None:
        if estimated_roi >= r_min:
            if r_min <= estimated_roi <= r_max:
                score += 20
                reasons.append(f"ROI {estimated_roi:.0f}% — в нашем диапазоне доходности")
            elif estimated_roi > r_max:
                score += 20  # выше нашего среднего — хорошо
                reasons.append(f"ROI {estimated_roi:.0f}% — выше нашего среднего ({r_med:.0f}%)")
        else:
            score += 5
            reasons.append(f"ROI {estimated_roi:.0f}% — ниже нашего среднего ({r_med:.0f}%)")
    else:
        reasons.append("ROI не рассчитан — нет рыночной оценки")

    # --- Фактор 5: Город (10 очков) ---
    lot_district = (lot.get("district") or "").lower()
    # Ищем совпадение с городами из наших сделок
    cities = profile.get("cities", {})
    matched_city = None
    for city in cities:
        if city and (city in lot_district or lot_district in city):
            matched_city = city
            break

    if matched_city:
        city_share = cities[matched_city] / total_sold
        if city_share >= 0.1:
            score += 10
            reasons.append(f"город совпадает с нашей историей продаж")
        else:
            score += 5
            reasons.append(f"город — продавали 1-2 раза")
    else:
        reasons.append("новый город — нет истории продаж")

    score = min(100, max(0, score))
    reason = "; ".join(reasons) if reasons else "нет данных"

    return score, reason


# ---------------------------------------------------------------------------
# 4. Главная функция
# ---------------------------------------------------------------------------

def main():
    log.info("=== Lookalike-скоринг ===")

    # Шаг 1: загрузка проданных объектов (с fallback)
    sold = load_sold_objects()
    if not sold:
        log.warning("Google Sheets недоступен — используем встроенный профиль Estate Invest")
        profile = FALLBACK_PROFILE
    else:
        # Шаг 2: строим профиль из реальных данных
        profile = build_profile(sold)
        if not profile:
            log.warning("Не удалось построить профиль — используем fallback")
            profile = FALLBACK_PROFILE

    # Шаг 3: загрузка лотов из Supabase
    log.info("Загрузка лотов из Supabase...")
    resp = sb.table("properties").select(
        "lot_id, property_type, price, area, district, "
        "estimated_roi, invest_score, risk_score"
    ).execute()
    lots = resp.data
    log.info("Найдено %d лотов", len(lots))

    # Шаг 4: скоринг
    ok = 0
    for i, lot in enumerate(lots, 1):
        lot_id = lot["lot_id"]
        score, reason = calc_lookalike(lot, profile)

        try:
            sb.table("properties").update({
                "lookalike_score": score,
                "lookalike_match_reason": reason,
            }).eq("lot_id", lot_id).execute()
            log.info("[%d] %s — lookalike=%d | %s", i, lot_id, score, reason[:60])
            ok += 1
        except Exception as e:
            log.error("Ошибка %s: %s", lot_id, e)

    log.info("=" * 50)
    log.info("Готово! Обновлено: %d/%d лотов", ok, len(lots))
    log.info("Топ-тип: %s, медиана площади: %.0f м², медиана цены: %.0fК руб",
             profile.get("top_type"),
             profile.get("area_median", 0),
             (profile.get("price_median", 0) / 1000))


if __name__ == "__main__":
    main()
