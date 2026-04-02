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


def calc_invest_score(lot: dict) -> tuple[int, list]:
    """Инвестиционная привлекательность 0-100. Возвращает (score, breakdown)."""
    score = 0
    reasons = []

    # --- Дисконт к рынку (главный фактор, 60 очков) ---
    discount = lot.get("discount")
    if discount is None:
        score += 5
        reasons.append({"factor": "Дисконт к рынку", "pts": 5, "max": 60, "note": "Нет рыночной оценки"})
    elif discount >= 50:
        score += 60
        reasons.append({"factor": "Дисконт к рынку", "pts": 60, "max": 60, "note": f"Дисконт {discount:.0f}% (>50%)"})
    elif discount >= 40:
        score += 50
        reasons.append({"factor": "Дисконт к рынку", "pts": 50, "max": 60, "note": f"Дисконт {discount:.0f}% (40-50%)"})
    elif discount >= 30:
        score += 40
        reasons.append({"factor": "Дисконт к рынку", "pts": 40, "max": 60, "note": f"Дисконт {discount:.0f}% (30-40%)"})
    elif discount >= 20:
        score += 28
        reasons.append({"factor": "Дисконт к рынку", "pts": 28, "max": 60, "note": f"Дисконт {discount:.0f}% (20-30%)"})
    elif discount >= 10:
        score += 15
        reasons.append({"factor": "Дисконт к рынку", "pts": 15, "max": 60, "note": f"Дисконт {discount:.0f}% (10-20%)"})
    else:
        score += 5
        reasons.append({"factor": "Дисконт к рынку", "pts": 5, "max": 60, "note": f"Дисконт {discount:.0f}% (<10%)"})

    # --- Качество оценки (10 очков) ---
    confidence = lot.get("confidence", "")
    analogs = lot.get("analogs_count") or 0
    if confidence == "кадастр":
        pts = 0
        reasons.append({"factor": "Качество оценки", "pts": 0, "max": 10, "note": "Только кадастр, нет аналогов"})
    elif confidence == "высокая" and analogs >= 10:
        pts = 10; score += 10
        reasons.append({"factor": "Качество оценки", "pts": 10, "max": 10, "note": f"Высокая, {analogs} аналогов"})
    elif confidence in ("высокая", "средняя") and analogs >= 3:
        pts = 6; score += 6
        reasons.append({"factor": "Качество оценки", "pts": 6, "max": 10, "note": f"{confidence}, {analogs} аналогов"})
    elif analogs >= 1:
        pts = 3; score += 3
        reasons.append({"factor": "Качество оценки", "pts": 3, "max": 10, "note": f"{analogs} аналог(ов)"})
    else:
        reasons.append({"factor": "Качество оценки", "pts": 0, "max": 10, "note": "Нет аналогов"})

    # --- Кадастровое подтверждение (10 очков) ---
    cad_ratio = lot.get("cadastral_price_ratio")
    if cad_ratio is not None:
        if cad_ratio < 0.7:
            score += 10
            reasons.append({"factor": "Кадастровое подтверждение", "pts": 10, "max": 10, "note": f"Цена/кадастр = {cad_ratio:.1%}"})
        elif cad_ratio < 1.0:
            score += 6
            reasons.append({"factor": "Кадастровое подтверждение", "pts": 6, "max": 10, "note": f"Цена/кадастр = {cad_ratio:.1%}"})
        elif cad_ratio < 1.5:
            score += 3
            reasons.append({"factor": "Кадастровое подтверждение", "pts": 3, "max": 10, "note": f"Цена/кадастр = {cad_ratio:.1%}"})
        else:
            reasons.append({"factor": "Кадастровое подтверждение", "pts": 0, "max": 10, "note": f"Цена/кадастр = {cad_ratio:.1%} (>150%)"})
    else:
        reasons.append({"factor": "Кадастровое подтверждение", "pts": 0, "max": 10, "note": "Нет данных"})

    # --- Тип объекта (5 очков) ---
    ptype = lot.get("property_type", "")
    type_map = {"apartment": (5, "Квартира — макс. ликвидность"), "house": (3, "Дом"), "commercial": (3, "Коммерция"), "land": (1, "Земля — низкая ликвидность")}
    pts, note = type_map.get(ptype, (0, ptype or "Неизвестный тип"))
    score += pts
    reasons.append({"factor": "Тип объекта", "pts": pts, "max": 5, "note": note})

    # --- Локация (5 очков) ---
    loc_pts = 0
    loc_notes = []
    if lot.get("district"):
        loc_pts += 3; loc_notes.append(f"район: {lot['district']}")
    if lot.get("lat") and lot.get("lon"):
        loc_pts += 2; loc_notes.append("есть координаты")
    score += loc_pts
    reasons.append({"factor": "Локация", "pts": loc_pts, "max": 5, "note": ", ".join(loc_notes) if loc_notes else "Нет данных о локации"})

    # --- Тип торгов (5 очков) ---
    bidd = lot.get("bidd_type", "")
    if "реализация имущества должников" in bidd.lower():
        score += 5
        reasons.append({"factor": "Тип торгов", "pts": 5, "max": 5, "note": "Арест — обычно дешевле"})
    elif "приватизац" in bidd.lower():
        score += 3
        reasons.append({"factor": "Тип торгов", "pts": 3, "max": 5, "note": "Приватизация"})
    else:
        reasons.append({"factor": "Тип торгов", "pts": 0, "max": 5, "note": bidd[:50] if bidd else "Неизвестно"})

    # --- Цена: слишком маленькая (< 50к) или явно ошибка ---
    price = lot.get("price") or 0
    if price < 50_000:
        penalty = min(score, 15)
        score = max(0, score - 15)
        reasons.append({"factor": "Штраф: низкая цена", "pts": -penalty, "max": 0, "note": f"Цена {price:,.0f} руб (<50к)"})

    final = min(100, max(0, score))
    return final, reasons


def calc_risk_score(lot: dict) -> tuple[int, list]:
    """Уровень риска 0-100 (выше = рискованнее). Возвращает (score, breakdown)."""
    risk = 20
    reasons = [{"factor": "Базовый риск", "pts": 20, "note": "Минимальный риск любой сделки"}]

    if not lot.get("lat") or not lot.get("lon"):
        risk += 15
        reasons.append({"factor": "Нет координат", "pts": 15, "note": "Нельзя проверить на карте"})

    cad = lot.get("cadastral_number") or ""
    if not cad or len(cad) < 5:
        risk += 20
        reasons.append({"factor": "Нет кадастрового номера", "pts": 20, "note": "Нельзя проверить в Росреестре"})

    if lot.get("market_price") is None:
        risk += 20
        reasons.append({"factor": "Нет рыночной оценки", "pts": 20, "note": "Неизвестная реальная стоимость"})
    elif (lot.get("analogs_count") or 0) < 3:
        risk += 10
        reasons.append({"factor": "Мало аналогов", "pts": 10, "note": f"{lot.get('analogs_count') or 0} аналогов — оценка ненадёжна"})

    price = lot.get("price") or 0
    if 0 < price < 50_000:
        risk += 25
        reasons.append({"factor": "Подозрительная цена", "pts": 25, "note": f"{price:,.0f} руб — возможно доля или ошибка"})

    if lot.get("has_encumbrances"):
        risk += 15
        reasons.append({"factor": "Обременения", "pts": 15, "note": "Зарегистрированы обременения"})
    enc_type = (lot.get("encumbrance_type") or "").lower()
    if "долевая" in enc_type or "общедолевая" in enc_type:
        risk += 10
        reasons.append({"factor": "Долевая собственность", "pts": 10, "note": "Общедолевая собственность"})

    name = (lot.get("name") or "").lower()
    if "доля" in name or "доли" in name:
        risk += 15
        reasons.append({"factor": "Доля в праве", "pts": 15, "note": "В названии упоминается доля"})

    ptype = lot.get("property_type", "")
    district = lot.get("district") or ""
    if ptype == "land" and not district:
        risk += 10
        reasons.append({"factor": "Земля вне города", "pts": 10, "note": "Район неизвестен — возможно удалённый участок"})

    final = min(100, max(0, risk))
    return final, reasons


def calc_liquidity_score(lot: dict) -> tuple[int, list]:
    """Ликвидность 0-100 (выше = быстрее продаётся). Возвращает (score, breakdown)."""
    score = 30
    reasons = [{"factor": "Базовая ликвидность", "pts": 30, "max": 30, "note": "Стартовый балл"}]

    ptype = lot.get("property_type", "")
    area = lot.get("area") or 0
    price = lot.get("price") or 0

    type_map = {"apartment": (30, "Квартира — макс. спрос"), "house": (15, "Дом"), "commercial": (10, "Коммерция"), "land": (5, "Земля — низкий спрос")}
    pts, note = type_map.get(ptype, (0, ptype or "Неизвестный тип"))
    score += pts
    reasons.append({"factor": "Тип объекта", "pts": pts, "max": 30, "note": note})

    if ptype == "apartment":
        if 25 <= area <= 90:
            score += 15
            reasons.append({"factor": "Площадь", "pts": 15, "max": 15, "note": f"{area:.0f} м² — типовая (25-90)"})
        elif 90 < area <= 150:
            score += 8
            reasons.append({"factor": "Площадь", "pts": 8, "max": 15, "note": f"{area:.0f} м² — большая (90-150)"})
        elif area > 150:
            score += 3
            reasons.append({"factor": "Площадь", "pts": 3, "max": 15, "note": f"{area:.0f} м² — элитная (>150)"})
        elif 0 < area < 25:
            score += 5
            reasons.append({"factor": "Площадь", "pts": 5, "max": 15, "note": f"{area:.0f} м² — студия (<25)"})

    if 0 < price <= 2_000_000:
        score += 15
        reasons.append({"factor": "Ценовой сегмент", "pts": 15, "max": 15, "note": f"{price/1e6:.1f} млн — массовый (<2М)"})
    elif price <= 5_000_000:
        score += 10
        reasons.append({"factor": "Ценовой сегмент", "pts": 10, "max": 15, "note": f"{price/1e6:.1f} млн — средний (2-5М)"})
    elif price <= 10_000_000:
        score += 5
        reasons.append({"factor": "Ценовой сегмент", "pts": 5, "max": 15, "note": f"{price/1e6:.1f} млн — высокий (5-10М)"})
    elif price > 10_000_000:
        reasons.append({"factor": "Ценовой сегмент", "pts": 0, "max": 15, "note": f"{price/1e6:.1f} млн — премиум (>10М)"})

    district = lot.get("district") or ""
    if district:
        score += 10
        reasons.append({"factor": "Локация", "pts": 10, "max": 10, "note": f"Район: {district}"})
    else:
        reasons.append({"factor": "Локация", "pts": 0, "max": 10, "note": "Район неизвестен"})

    name = (lot.get("name") or "").lower()
    if "доля" in name or "доли" in name:
        penalty = min(score, 20)
        score = max(0, score - 20)
        reasons.append({"factor": "Штраф: доля", "pts": -penalty, "max": 0, "note": "Доля — сложно продать"})

    final = min(100, max(0, score))
    return final, reasons


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

        invest, invest_reasons = calc_invest_score(lot)
        risk, risk_reasons = calc_risk_score(lot)
        liquidity, liq_reasons = calc_liquidity_score(lot)
        rec = make_recommendation(invest, risk, liquidity, lot)
        estimated = calc_estimated(lot)

        scoring_breakdown = {
            "invest": invest_reasons,
            "risk": risk_reasons,
            "liquidity": liq_reasons,
        }

        update = {
            "invest_score": invest,
            "risk_score": risk,
            "liquidity_score": liquidity,
            "recommendation": rec,
            "scoring_breakdown": scoring_breakdown,
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
