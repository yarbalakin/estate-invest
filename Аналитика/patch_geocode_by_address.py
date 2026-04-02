#!/usr/bin/env python3
"""
patch_geocode_by_address.py — Геокодинг лотов без координат через DaData (по адресу).

Берёт лоты без lat/lon и без cadastral_number (или с частичным), геокодирует
адрес через DaData Suggestions API и записывает lat/lon/district в Supabase.

Запуск:
  SUPABASE_URL=... SUPABASE_KEY=... DADATA_TOKEN=... python3 patch_geocode_by_address.py
"""

import logging
import os
import re
import time

import requests
from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
DADATA_TOKEN = os.environ.get("DADATA_TOKEN", "")
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

DADATA_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address"
DELAY = 0.5  # DaData быстрый, 0.5 сек хватит


def geocode_address(address: str) -> dict | None:
    """Геокодировать адрес через DaData. Возвращает {lat, lon, district} или None."""
    if not address or len(address) < 10:
        return None
    try:
        resp = requests.post(
            DADATA_URL,
            headers={"Content-Type": "application/json", "Authorization": f"Token {DADATA_TOKEN}"},
            json={"query": address, "count": 1},
            timeout=10,
        )
        if resp.status_code != 200:
            log.warning("  DaData HTTP %d", resp.status_code)
            return None
        suggestions = resp.json().get("suggestions", [])
        if not suggestions:
            return None
        data = suggestions[0]["data"]
        lat = data.get("geo_lat")
        lon = data.get("geo_lon")
        if not lat or not lon:
            return None
        district = data.get("city_district_with_type") or data.get("city_district") or ""
        return {"lat": float(lat), "lon": float(lon), "district": district or None}
    except Exception as e:
        log.error("  DaData ошибка: %s", e)
        return None


def main():
    log.info("Загрузка лотов без координат и без кадастра...")
    all_lots = []
    offset = 0
    while True:
        resp = (
            sb.table("properties")
            .select("lot_id, address, source")
            .is_("lat", "null")
            .is_("cadastral_number", "null")
            .not_.is_("address", "null")
            .neq("address", "")
            .range(offset, offset + 999)
            .execute()
        )
        batch = resp.data or []
        all_lots.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    log.info("Найдено %d лотов для геокодинга по адресу", len(all_lots))

    ok = 0
    not_found = 0

    for i, lot in enumerate(all_lots, 1):
        lot_id = lot["lot_id"]
        address = lot.get("address", "")

        geo = geocode_address(address)
        if geo:
            update = {"lat": geo["lat"], "lon": geo["lon"]}
            if geo.get("district"):
                update["district"] = geo["district"]
            try:
                sb.table("properties").update(update).eq("lot_id", lot_id).execute()
                log.info("[%d/%d] %s → lat=%.4f, lon=%.4f", i, len(all_lots), lot_id, geo["lat"], geo["lon"])
                ok += 1
            except Exception as e:
                log.error("  Supabase ошибка: %s", e)
        else:
            not_found += 1
            if i <= 10 or i % 20 == 0:
                log.info("[%d/%d] %s — не геокодирован (%s)", i, len(all_lots), lot_id, address[:60])

        time.sleep(DELAY)

    log.info("=" * 50)
    log.info("Готово! Геокодировано: %d, не найдено: %d", ok, not_found)


if __name__ == "__main__":
    main()
