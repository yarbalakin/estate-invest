#!/usr/bin/env python3
"""
patch_cadastral_from_tbankrot.py — Дообогащение лотов tbankrot кадастровыми номерами.

Берёт лоты source=tbankrot без cadastral_number, парсит детальную страницу tbankrot.ru,
извлекает кадастровый номер (полный или частичный) и записывает в Supabase.

Запуск:
  SUPABASE_URL=... SUPABASE_KEY=... python3 patch_cadastral_from_tbankrot.py
"""

import json
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
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"}
DELAY = 1.0

# Полный: 59:22:0690101:123  Частичный: 59:22:0690101:ЗУ1
CAD_RE = re.compile(r"\d{2}:\d{2}:\d{5,7}:[\dА-Яа-яA-Za-z]+")


def fetch_cadastral_from_page(lot_id: str) -> str | None:
    """Скачать детальную страницу tbankrot и извлечь кадастровый номер."""
    tb_id = lot_id.replace("TB-", "")
    url = f"https://tbankrot.ru/item?id={tb_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            log.warning("  HTTP %d для %s", resp.status_code, tb_id)
            return None
        text = re.sub(r"<[^>]+>", " ", resp.text)
        cad = CAD_RE.search(text)
        return cad.group(0) if cad else None
    except Exception as e:
        log.error("  Ошибка %s: %s", tb_id, e)
        return None


def main():
    log.info("Загрузка лотов tbankrot без кадастра...")
    all_lots = []
    offset = 0
    while True:
        resp = sb.table("properties").select("lot_id").eq("source", "tbankrot").is_("cadastral_number", "null").range(offset, offset + 999).execute()
        batch = resp.data or []
        all_lots.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    log.info("Найдено %d лотов без кадастра", len(all_lots))

    ok = 0
    not_found = 0

    for i, lot in enumerate(all_lots, 1):
        lot_id = lot["lot_id"]
        cad = fetch_cadastral_from_page(lot_id)

        if cad:
            try:
                sb.table("properties").update({"cadastral_number": cad}).eq("lot_id", lot_id).execute()
                log.info("[%d/%d] %s → %s", i, len(all_lots), lot_id, cad)
                ok += 1
            except Exception as e:
                log.error("  Supabase ошибка: %s", e)
        else:
            not_found += 1
            if i <= 20 or i % 50 == 0:
                log.info("[%d/%d] %s — кадастр не найден", i, len(all_lots), lot_id)

        time.sleep(DELAY)

    log.info("=" * 50)
    log.info("Готово! Найден кадастр: %d, не найден: %d", ok, not_found)


if __name__ == "__main__":
    main()
