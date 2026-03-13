#!/usr/bin/env python3
"""
enrich_cadastral.py — Массовое обогащение лотов кадастровыми данными из НСПД.

Запуск на VPS:
  cd /opt/torgi-proxy && source venv/bin/activate
  python enrich_cadastral.py

Что делает:
  1. Берёт из Supabase лоты с cadastral_number, но без cadastral_value
  2. Для каждого запрашивает НСПД API
  3. Обновляет Supabase: cadastral_value, cadastral_area, cadastral_category,
     cadastral_permitted_use, cadastral_price_ratio, encumbrance_type
  4. Для квартир — обновляет apartment.floor
"""

import json
import logging
import os
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

# --- Supabase ---
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- НСПД ---
NSPD_URL = "https://nspd.gov.ru/api/geoportal/v2/search/geoportal"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://nspd.gov.ru",
    "Referer": "https://nspd.gov.ru/map",
    "sec-ch-ua": '"Chromium";"v="120"',
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}
sess = requests.Session()
sess.verify = False
sess.headers.update(HEADERS)

DELAY = 2  # секунд между запросами (чтобы не блокировали)

import re
CN_PATTERN = re.compile(r"^\d{2}:\d{2}:\d{5,7}:\d+$")


def is_valid_cadastral(cn: str) -> bool:
    """Проверяет формат кадастрового номера XX:XX:XXXXXXX:XXXX."""
    return bool(CN_PATTERN.match(cn.strip()))


def split_cadastral(raw: str) -> list[str]:
    """Разделяет составные кадастровые номера (через | или ,)."""
    parts = re.split(r"\s*[|,]\s*", raw)
    return [p.strip() for p in parts if p.strip()]


def fetch_nspd(cad_num: str) -> dict | None:
    """Запрос НСПД по кадастровому номеру."""
    if not is_valid_cadastral(cad_num):
        log.warning("  Пропуск невалидного формата: %s", cad_num)
        return None

    try:
        sess.headers["Referer"] = f"https://nspd.gov.ru/map?search={cad_num}"
        resp = sess.get(NSPD_URL, params={"query": cad_num, "limit": 1}, timeout=15)

        if resp.status_code == 403:
            log.warning("  403 Forbidden — пауза 30 сек...")
            time.sleep(30)
            resp = sess.get(NSPD_URL, params={"query": cad_num, "limit": 1}, timeout=15)
            if resp.status_code == 403:
                log.error("  403 снова — пропускаем")
                return None

        resp.raise_for_status()
        data = resp.json()

        features = data.get("data", {}).get("features", [])
        if not features:
            return None

        props = features[0].get("properties", {})
        result = props.get("options", {})
        result["_categoryName"] = props.get("categoryName", "")
        return result

    except Exception as e:
        log.error("  НСПД ошибка %s: %s", cad_num, e)
        return None


def fetch_nspd_multi(raw_cad: str) -> dict | None:
    """Пробует каждый кадастровый номер из составного поля."""
    parts = split_cadastral(raw_cad)
    for cn in parts:
        result = fetch_nspd(cn)
        if result:
            return result
        time.sleep(1)
    return None


def parse_nspd(raw: dict, price: float) -> dict:
    """Парсинг ответа НСПД в поля для Supabase UPDATE."""
    update = {}

    # Кадастровая стоимость
    cv = raw.get("cost_value")
    if cv is not None:
        try:
            update["cadastral_value"] = float(cv)
        except (ValueError, TypeError):
            pass

    # Площадь
    area = raw.get("area")
    if area is not None:
        try:
            update["cadastral_area"] = float(area)
        except (ValueError, TypeError):
            pass

    # Назначение
    purpose = raw.get("purpose")
    if purpose:
        update["cadastral_category"] = purpose
    elif raw.get("_categoryName"):
        update["cadastral_category"] = raw["_categoryName"]

    # Тип объекта
    params_type = raw.get("params_type")
    if params_type:
        update["cadastral_permitted_use"] = params_type

    # Тип собственности
    ownership = raw.get("ownership_type")
    if ownership:
        update["encumbrance_type"] = ownership

    # Отношение цена / кадастровая стоимость
    cad_val = update.get("cadastral_value")
    if cad_val and cad_val > 0 and price and price > 0:
        update["cadastral_price_ratio"] = round(price / cad_val, 2)

    return update


def get_floor_from_nspd(raw: dict) -> int | None:
    """Извлечь этаж из ответа НСПД."""
    floor_info = raw.get("floor")
    if floor_info and isinstance(floor_info, list):
        for f in floor_info:
            if "/" in str(f):
                parts = str(f).split("/")
                try:
                    return int(parts[0])
                except ValueError:
                    pass
    return None


def main():
    # Берём лоты с кадастровым номером но без кадастровой стоимости
    log.info("Загрузка лотов из Supabase...")
    resp = (
        sb.table("properties")
        .select("lot_id, cadastral_number, price, property_type, apartment")
        .not_.is_("cadastral_number", "null")
        .neq("cadastral_number", "")
        .is_("cadastral_value", "null")
        .execute()
    )
    lots = resp.data
    log.info("Найдено %d лотов без кадастровых данных", len(lots))

    if not lots:
        log.info("Все лоты уже обогащены!")
        return

    ok = 0
    fail = 0
    skip = 0

    for i, lot in enumerate(lots, 1):
        cad = lot["cadastral_number"]
        lot_id = lot["lot_id"]
        log.info("[%d/%d] %s — %s", i, len(lots), lot_id, cad)

        raw = fetch_nspd_multi(cad)
        if not raw:
            log.warning("  Не найден в НСПД")
            fail += 1
            time.sleep(DELAY)
            continue

        update = parse_nspd(raw, lot.get("price", 0))
        if not update:
            log.warning("  Пустой результат парсинга")
            skip += 1
            time.sleep(DELAY)
            continue

        # Обновляем apartment.floor если это квартира
        floor = get_floor_from_nspd(raw)
        if floor and lot.get("property_type") == "apartment":
            apt = lot.get("apartment") or {}
            apt["floor"] = floor
            update["apartment"] = apt

        # Записываем в Supabase
        try:
            sb.table("properties").update(update).eq("lot_id", lot_id).execute()
            cv = update.get("cadastral_value", "?")
            ratio = update.get("cadastral_price_ratio", "?")
            log.info("  OK: стоимость=%s, цена/кадастр=%s", cv, ratio)
            ok += 1
        except Exception as e:
            log.error("  Ошибка записи: %s", e)
            fail += 1

        time.sleep(DELAY)

    log.info("=" * 50)
    log.info("Готово! OK: %d, не найдено: %d, пропущено: %d", ok, fail, skip)


if __name__ == "__main__":
    main()
