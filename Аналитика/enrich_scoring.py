#!/usr/bin/env python3
"""
enrich_scoring.py — Расчёт инвестиционного скоринга для всех лотов в Supabase.

Запуск на VPS:
  cd /opt/torgi-proxy && source venv/bin/activate
  python enrich_scoring.py

Считает три оценки (0-100) и текстовую рекомендацию:
  invest_score    — привлекательность для покупки
  risk_score      — уровень риска (чем ниже — тем лучше)
  liquidity_score — ликвидность (как быстро можно перепродать)
  recommendation  — текстовая рекомендация
  estimated_profit     — ожидаемая прибыль (руб)
  estimated_roi        — ROI (%)
  estimated_sell_time  — срок продажи (мес)
"""

import logging
import os

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

# Расходы при покупке/продаже: налог (13%), регистрация, агент — итого ~12%
TRANSACTION_COSTS = 0.12


def calc_invest_score(lot: dict) -> int:
    """Инвестиционная привлекательность 0-100."""
    score = 0

    # --- Дисконт к рынку (главный фактор, 60 очков) ---
    discount = lot.get("discount")
    if discount is None:
        # Нет рыночной оценки — базовый балл только за факт наличия данных
        score += 5
    elif discount >= 50:
        score += 60
    elif discount >= 40:
        score += 50
    elif discount >= 30:
        score += 40
    elif discount >= 20:
        score += 28
    elif discount >= 10:
        score += 15
    else:
        score += 5  # дисконт < 10% — почти нет смысла

    # --- Качество оценки (10 очков) ---
    confidence = lot.get("confidence", "")
    analogs = lot.get("analogs_count") or 0
    if confidence == "кадастр":
        score += 0  # кадастровый фаллбек — нет реальных аналогов
    elif confidence == "высокая" and analogs >= 10:
        score += 10
    elif confidence in ("высокая", "средняя") and analogs >= 3:
        score += 6
    elif analogs >= 1:
        score += 3

    # --- Кадастровое подтверждение (10 очков) ---
    cad_ratio = lot.get("cadastral_price_ratio")
    if cad_ratio is not None:
        # Если цена лота < 70% от кадастровой — это хорошо
        if cad_ratio < 0.7:
            score += 10
        elif cad_ratio < 1.0:
            score += 6
        elif cad_ratio < 1.5:
            score += 3

    # --- Тип объекта (5 очков) ---
    ptype = lot.get("property_type", "")
    if ptype == "apartment":
        score += 5  # самый ликвидный
    elif ptype in ("house", "commercial"):
        score += 3
    elif ptype == "land":
        score += 1

    # --- Локация (5 очков) ---
    if lot.get("district"):
        score += 3  # знаем район
    if lot.get("lat") and lot.get("lon"):
        score += 2  # есть координаты

    # --- Тип торгов (5 очков) ---
    bidd = lot.get("bidd_type", "")
    if "реализация имущества должников" in bidd.lower():
        score += 5  # арестованное — обычно дешевле
    elif "приватизац" in bidd.lower():
        score += 3

    # --- Цена: слишком маленькая (< 100к) или явно ошибка ---
    price = lot.get("price") or 0
    if price < 50_000:
        score = max(0, score - 15)  # скорее всего доля или ошибка

    return min(100, max(0, score))


def calc_risk_score(lot: dict) -> int:
    """Уровень риска 0-100 (выше = рискованнее)."""
    risk = 20  # базовый риск

    # --- Нет координат — нельзя проверить объект (+15) ---
    if not lot.get("lat") or not lot.get("lon"):
        risk += 15

    # --- Нет кадастрового номера — нельзя проверить в Росреестре (+20) ---
    cad = lot.get("cadastral_number") or ""
    if not cad or len(cad) < 5:
        risk += 20

    # --- Нет рыночной оценки — неизвестная стоимость (+20) ---
    if lot.get("market_price") is None:
        risk += 20
    elif (lot.get("analogs_count") or 0) < 3:
        risk += 10  # мало аналогов — оценка ненадёжна

    # --- Очень маленькая цена (< 50к) — возможно доля или мусор (+25) ---
    price = lot.get("price") or 0
    if 0 < price < 50_000:
        risk += 25

    # --- Известные обременения ---
    if lot.get("has_encumbrances"):
        risk += 15
    enc_type = (lot.get("encumbrance_type") or "").lower()
    if "долевая" in enc_type or "общедолевая" in enc_type:
        risk += 10

    # --- Доля в праве — сложнее продать ---
    name = (lot.get("name") or "").lower()
    if "доля" in name or "доли" in name:
        risk += 15

    # --- Земля вне города — низкая ликвидность ---
    ptype = lot.get("property_type", "")
    district = lot.get("district") or ""
    if ptype == "land" and not district:
        risk += 10

    return min(100, max(0, risk))


def calc_liquidity_score(lot: dict) -> int:
    """Ликвидность 0-100 (выше = быстрее продаётся)."""
    score = 30  # базовый

    ptype = lot.get("property_type", "")
    area = lot.get("area") or 0
    price = lot.get("price") or 0

    # --- Тип объекта ---
    if ptype == "apartment":
        score += 30
    elif ptype == "house":
        score += 15
    elif ptype == "commercial":
        score += 10
    elif ptype == "land":
        score += 5

    # --- Площадь квартиры: типовая 25-90 м2 ---
    if ptype == "apartment":
        if 25 <= area <= 90:
            score += 15
        elif 90 < area <= 150:
            score += 8
        elif area > 150:
            score += 3  # большая квартира — уже сложнее продать
        elif 0 < area < 25:
            score += 5  # студия или доля

    # --- Ценовой сегмент ---
    if 0 < price <= 2_000_000:
        score += 15  # массовый сегмент
    elif price <= 5_000_000:
        score += 10
    elif price <= 10_000_000:
        score += 5
    # > 10 млн — ничего не добавляем

    # --- Локация: знаем район города (+10) ---
    district = lot.get("district") or ""
    if district:
        score += 10

    # --- Доля в праве — сложно продать ---
    name = (lot.get("name") or "").lower()
    if "доля" in name or "доли" in name:
        score = max(0, score - 20)

    return min(100, max(0, score))


def calc_estimated(lot: dict) -> dict:
    """Ожидаемая прибыль, ROI, срок продажи."""
    result = {}

    market = lot.get("market_price")
    price = lot.get("price") or 0
    ptype = lot.get("property_type", "")

    if market and price and price > 0:
        # Прибыль = рыночная цена - цена лота - транзакционные расходы
        costs = market * TRANSACTION_COSTS
        profit = market - price - costs
        result["estimated_profit"] = round(profit)
        result["estimated_roi"] = round(profit / price * 100, 1)

    # Срок продажи (месяцев) — по типу и ценовому сегменту
    price_m = price / 1_000_000 if price else 0
    if ptype == "apartment":
        if price_m <= 3:
            months = 2
        elif price_m <= 6:
            months = 4
        elif price_m <= 12:
            months = 6
        else:
            months = 10
    elif ptype == "house":
        months = 6 if price_m <= 5 else 12
    elif ptype == "commercial":
        months = 6 if price_m <= 5 else 18
    elif ptype == "land":
        months = 12 if price_m <= 2 else 24
    else:
        months = 12

    result["estimated_sell_time"] = months
    return result


def make_recommendation(invest: int, risk: int, liquidity: int, lot: dict) -> str:
    """Текстовая рекомендация на основе трёх оценок."""
    has_market = lot.get("market_price") is not None
    discount = lot.get("discount") or 0

    if not has_market:
        return "Нет рыночной оценки — требует ручной проверки"

    if invest >= 65 and risk <= 35:
        return "Отличная сделка — высокий дисконт, низкий риск"
    elif invest >= 65 and risk <= 55:
        return "Хороший вариант — проверить документы"
    elif invest >= 50 and risk <= 45:
        return "Интересный объект — стоит изучить"
    elif risk >= 65:
        return "Высокий риск — требует тщательной проверки"
    elif invest < 30 or discount < 10:
        return "Слабый дисконт — не рекомендуется"
    else:
        return "Средний вариант — анализировать дополнительно"


def main():
    log.info("Загрузка всех лотов из Supabase...")
    COLS = (
        "lot_id, property_type, price, market_price, discount, confidence, "
        "analogs_count, cadastral_number, cadastral_price_ratio, cadastral_value, "
        "has_encumbrances, encumbrance_type, bidd_type, area, district, lat, lon, name"
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
    for i, lot in enumerate(lots, 1):
        lot_id = lot["lot_id"]

        invest = calc_invest_score(lot)
        risk = calc_risk_score(lot)
        liquidity = calc_liquidity_score(lot)
        rec = make_recommendation(invest, risk, liquidity, lot)
        estimated = calc_estimated(lot)

        update = {
            "invest_score": invest,
            "risk_score": risk,
            "liquidity_score": liquidity,
            "recommendation": rec,
            **estimated,
        }

        try:
            sb.table("properties").update(update).eq("lot_id", lot_id).execute()
            log.info(
                "[%d] %s — инвест=%d риск=%d ликв=%d | %s",
                i, lot_id, invest, risk, liquidity, rec,
            )
            ok += 1
        except Exception as e:
            log.error("Ошибка %s: %s", lot_id, e)

    log.info("=" * 50)
    log.info("Готово! Обновлено: %d/%d", ok, len(lots))


if __name__ == "__main__":
    main()
