#!/usr/bin/env python3
"""
enrich_lookalike.py v2 — Lookalike-скоринг с оценкой рыночной цены.

Логика:
  1. Загружаем объекты Estate Invest из реализация-сводка.html (локальный файл)
     (тип, площадь, город, цена покупки, цена продажи)
  2. Для каждого нового лота из Supabase:
     - Берём ТОЛЬКО объекты ТОГО ЖЕ ТИПА
     - Считаем схожесть с каждым (0-100) по: площадь, город, ценовой диапазон
     - Применяем поправки по типу (этаж, коммуникации, вход и т.д.)
     - Берём топ-3 самых похожих
     - lookalike_price = взвешенное среднее их цен продажи
     - lookalike_score = средняя схожесть топ-3
  3. Сохраняем в Supabase: lookalike_score, lookalike_price,
     lookalike_matches, lookalike_match_reason

Запуск:
  cd /root/projects/estate-invest/Аналитика
  python3 enrich_lookalike.py
"""

import html as htmllib
import json
import logging
import os
import re

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

# Путь к реализация-сводка.html относительно этого скрипта
SVODKA_HTML = os.path.join(
    os.path.dirname(__file__), "..", "Реализация", "реализация-сводка.html"
)

TOP_N = 3  # сколько аналогов брать для расчёта цены


# ---------------------------------------------------------------------------
# 1. Загрузка объектов Estate Invest из реализация-сводка.html (локальный файл)
# ---------------------------------------------------------------------------

def _html_clean(text: str) -> str:
    return htmllib.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def _parse_price(raw: str | None) -> float | None:
    """Парсит цены вида '2.1 млн ₽', '845 тыс ₽', '1 200 000'."""
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


def load_sold_objects() -> list[dict]:
    """Парсит реализация-сводка.html и возвращает список объектов Estate Invest."""
    path = os.path.abspath(SVODKA_HTML)
    if not os.path.exists(path):
        log.warning("реализация-сводка.html не найден: %s", path)
        return []

    with open(path, encoding="utf-8") as f:
        html = f.read()

    parts = re.split(r'(?=<div class="property-card")', html)
    cards = [p for p in parts if 'property-card' in p[:50]]

    objects = []
    for card in cards:
        city_m = re.search(r'data-city="([^"]+)"', card)
        type_m = re.search(r'data-type="([^"]+)"', card)
        city = city_m.group(1).strip().lower() if city_m else ""
        raw_type = type_m.group(1).lower() if type_m else ""

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

        # Приоритет: фактическая цена выхода > целевая цена продажи
        effective_sell = exit_p if (exit_p and buy and exit_p > buy) else sell

        if buy and effective_sell and buy > 10_000 and effective_sell > buy:
            roi = round((effective_sell - buy) / buy * 100, 1)
            objects.append({
                "property_type": ptype,
                "area": area,
                "city": city,
                "buy_price": buy,
                "sell_price": effective_sell,
                "roi": roi,
                "название": f"{city.title()}, {raw_type}",
            })

    log.info("Загружено %d объектов из реализация-сводка.html", len(objects))
    return objects


# ---------------------------------------------------------------------------
# 2. Расчёт схожести лота с проданным объектом
# ---------------------------------------------------------------------------

def area_similarity(lot_area: float, sold_area: float) -> tuple[int, str]:
    """Схожесть по площади (0-50 очков)."""
    if not lot_area or not sold_area or sold_area <= 0:
        return 0, ""
    ratio = lot_area / sold_area
    if 0.9 <= ratio <= 1.1:
        return 50, f"площадь {lot_area:.0f}≈{sold_area:.0f} м² (±10%)"
    elif 0.8 <= ratio <= 1.25:
        return 42, f"площадь {lot_area:.0f}≈{sold_area:.0f} м² (±25%)"
    elif 0.6 <= ratio <= 1.5:
        return 30, f"площадь {lot_area:.0f} vs {sold_area:.0f} м² (±50%)"
    elif 0.4 <= ratio <= 2.0:
        return 15, f"площадь {lot_area:.0f} vs {sold_area:.0f} м² (×2)"
    else:
        return 0, ""


def city_similarity(lot_district: str, sold_city: str) -> tuple[int, str]:
    """Схожесть по городу (0-30 очков)."""
    if not lot_district or not sold_city:
        return 0, ""
    ld = lot_district.lower()
    sc = sold_city.lower()
    if sc in ld or ld in sc or any(w in ld for w in sc.split()):
        return 30, f"город совпадает ({sold_city})"
    return 0, ""


def price_fit(lot_price: float, sold_buy_price: float) -> tuple[int, str]:
    """Попадает ли цена лота в ценовой диапазон наших покупок (0-20 очков)."""
    if not lot_price or not sold_buy_price or sold_buy_price <= 0:
        return 0, ""
    ratio = lot_price / sold_buy_price
    if 0.7 <= ratio <= 1.5:
        return 20, f"цена {lot_price/1e6:.1f}М ≈ нашей покупке {sold_buy_price/1e6:.1f}М"
    elif 0.4 <= ratio <= 2.5:
        return 10, f"цена {lot_price/1e6:.1f}М близко к нашей {sold_buy_price/1e6:.1f}М"
    else:
        return 0, ""


def type_specific_adjustment(lot: dict) -> float:
    """Поправочный коэффициент к цене по параметрам лота (0.70–1.10)."""
    ptype = lot.get("property_type", "")
    adjustment = 1.0

    if ptype == "apartment":
        apt = lot.get("apartment") or {}
        floor = apt.get("floor") if isinstance(apt, dict) else None
        floors_total = apt.get("floors_total") if isinstance(apt, dict) else None
        balcony = apt.get("balcony") if isinstance(apt, dict) else None
        condition = apt.get("condition") if isinstance(apt, dict) else None

        # Первый или последний этаж — дешевле
        if floor and floors_total:
            if floor == 1:
                adjustment -= 0.05
            elif floor == floors_total:
                adjustment -= 0.03

        if balcony is False:
            adjustment -= 0.02

        if condition:
            cond = condition.lower()
            if any(w in cond for w in ("плохое", "аварийн", "без ремонт")):
                adjustment -= 0.10
            elif any(w in cond for w in ("хорошее", "отличн", "ремонт")):
                adjustment += 0.05

    elif ptype == "commercial":
        comm = lot.get("commercial") or {}
        entrance = comm.get("entrance") if isinstance(comm, dict) else None
        comm_type = comm.get("commercial_type") if isinstance(comm, dict) else None

        if entrance and "отдельн" in str(entrance).lower():
            adjustment += 0.05
        elif entrance and "общ" in str(entrance).lower():
            adjustment -= 0.08

        # Склад/производство дешевле торгового
        if comm_type:
            ct = comm_type.lower()
            if any(w in ct for w in ("склад", "производств")):
                adjustment -= 0.10
            elif any(w in ct for w in ("торгов", "магазин")):
                adjustment += 0.05

    elif ptype == "land":
        land = lot.get("land") or {}
        if isinstance(land, dict):
            has_electricity = land.get("has_electricity")
            has_gas = land.get("has_gas")
            has_water = land.get("has_water")
            category = land.get("land_category") or ""

            comms = sum([
                1 for v in [has_electricity, has_gas, has_water] if v is True
            ])
            adjustment += comms * 0.03  # +3% за каждую коммуникацию

            if "промышленн" in category.lower():
                adjustment += 0.05  # промышленная земля дороже

    elif ptype == "house":
        house = lot.get("house") or {}
        if isinstance(house, dict):
            garage = house.get("garage_on_site")
            bathhouse = house.get("bathhouse")
            if garage:
                adjustment += 0.03
            if bathhouse:
                adjustment += 0.02

    return max(0.50, min(1.30, adjustment))


def similarity_score(lot: dict, sold: dict) -> tuple[int, list[str]]:
    """
    Считает схожесть лота с проданным объектом.
    Возвращает (score 0-100, список причин).
    """
    score = 0
    reasons = []

    # Площадь (50 очков)
    pts, reason = area_similarity(lot.get("area") or 0, sold.get("area") or 0)
    score += pts
    if reason:
        reasons.append(reason)

    # Город (30 очков)
    pts, reason = city_similarity(lot.get("district") or "", sold.get("city") or "")
    score += pts
    if reason:
        reasons.append(reason)

    # Цена (20 очков)
    pts, reason = price_fit(lot.get("price") or 0, sold.get("buy_price") or 0)
    score += pts
    if reason:
        reasons.append(reason)

    return min(100, score), reasons


# ---------------------------------------------------------------------------
# 3. Расчёт lookalike для одного лота
# ---------------------------------------------------------------------------

def calc_lookalike(lot: dict, sold_by_type: dict) -> tuple[int, float | None, list[dict], str]:
    """
    Возвращает (score, lookalike_price, matches, reason).
    """
    ptype = lot.get("property_type", "")
    same_type = sold_by_type.get(ptype, [])

    if not same_type:
        return 0, None, [], f"нет проданных объектов типа '{ptype}'"

    # Считаем схожесть с каждым проданным объектом
    scored = []
    for sold in same_type:
        sc, reasons = similarity_score(lot, sold)
        if sc > 0:
            scored.append((sc, sold, reasons))

    if not scored:
        return 0, None, [], f"нет похожих объектов типа '{ptype}'"

    # Сортируем по убыванию схожести, берём топ-N
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:TOP_N]

    # Взвешенная средняя цена продажи
    total_weight = sum(sc for sc, _, _ in top)
    if total_weight == 0:
        return 0, None, [], "нулевые веса"

    adjustment = type_specific_adjustment(lot)
    raw_price = sum(sc * s["sell_price"] for sc, s, _ in top) / total_weight
    lookalike_price = round(raw_price * adjustment)

    # Итоговый score = среднее по топ-N (но не выше 95 если меньше 2 аналогов)
    avg_score = int(sum(sc for sc, _, _ in top) / len(top))
    if len(top) < 2:
        avg_score = min(avg_score, 70)

    # Формируем список matches для сохранения
    matches = []
    for sc, sold, _ in top:
        matches.append({
            "name": sold.get("название", ""),
            "similarity": sc,
            "area": sold.get("area"),
            "city": sold.get("city"),
            "sell_price": sold.get("sell_price"),
            "roi": sold.get("roi"),
        })

    # Описание
    top_reasons = top[0][2] if top else []
    adj_pct = round((adjustment - 1) * 100)
    adj_str = f" (поправка {adj_pct:+d}%)" if adj_pct != 0 else ""
    reason = "; ".join(top_reasons[:3]) + adj_str if top_reasons else f"{len(top)} аналогов найдено"

    return avg_score, lookalike_price, matches, reason


# ---------------------------------------------------------------------------
# 4. Главная функция
# ---------------------------------------------------------------------------

def main():
    log.info("=== Lookalike v2 — скоринг по реальным сделкам Estate Invest ===")

    # Загружаем объекты Estate Invest из локального HTML
    sold = load_sold_objects()
    if not sold:
        log.error("Нет данных об объектах — прерываем")
        return

    # Группируем по типу
    sold_by_type: dict[str, list] = {}
    for obj in sold:
        t = obj.get("property_type", "")
        sold_by_type.setdefault(t, []).append(obj)

    log.info("Проданные объекты по типам: %s",
             {t: len(v) for t, v in sold_by_type.items()})

    # Загружаем лоты из Supabase
    log.info("Загрузка лотов из Supabase...")
    resp = sb.table("properties").select(
        "lot_id, property_type, price, area, district, "
        "apartment, building, land, house, commercial, rental, infra"
    ).execute()
    lots = resp.data
    log.info("Найдено %d лотов", len(lots))

    ok = 0
    for i, lot in enumerate(lots, 1):
        lot_id = lot["lot_id"]
        score, price, matches, reason = calc_lookalike(lot, sold_by_type)

        update = {
            "lookalike_score": score,
            "lookalike_match_reason": reason,
            "lookalike_price": price,
            "lookalike_matches": matches if matches else None,
        }

        try:
            sb.table("properties").update(update).eq("lot_id", lot_id).execute()
            price_str = f"{price/1e6:.1f}М" if price else "—"
            log.info("[%d] %s — score=%d price=%s | %s",
                     i, lot_id[:30], score, price_str, reason[:60])
            ok += 1
        except Exception as e:
            log.error("Ошибка %s: %s", lot_id, e)

    log.info("=" * 50)
    log.info("Готово! Обновлено: %d/%d лотов", ok, len(lots))


if __name__ == "__main__":
    main()
