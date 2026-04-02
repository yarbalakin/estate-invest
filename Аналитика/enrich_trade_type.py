#!/usr/bin/env python3
"""
Обогащение existing лотов source=efrsb: парсинг price_schedule из priceReduction.
Для лотов trade_type='public_offer' без price_schedule — запрашивает ЕФРСБ заново.

Запуск: python3 enrich_trade_type.py [--limit 50]
"""
import argparse
import json
import os
import subprocess
import sys
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("enrich_tt")

# Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://eeahxalvnvbroswzyfjx.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

BASE = "https://fedresurs.ru/backend"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
COOKIE_FILE = "/tmp/enrich_tt_cookies.txt"


# ── Supabase helpers ───────────────────────────────────────────────────────────

def get_sb():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_lots_to_enrich(sb, limit):
    """Лоты source=efrsb, trade_type='public_offer', без price_schedule."""
    resp = (
        sb.table("properties")
        .select("id, lot_id, url, price")
        .eq("source", "efrsb")
        .eq("trade_type", "public_offer")
        .is_("price_schedule", "null")
        .limit(limit)
        .execute()
    )
    return resp.data or []


# ── ЕФРСБ API ─────────────────────────────────────────────────────────────────

def init_session():
    if os.path.exists(COOKIE_FILE):
        os.remove(COOKIE_FILE)
    r = subprocess.run(
        ["curl", "-s", "-c", COOKIE_FILE, "-o", "/dev/null", "-w", "%{http_code}",
         "-H", f"User-Agent: {UA}", "--max-time", "15", "https://fedresurs.ru/biddings"],
        capture_output=True, text=True, timeout=30,
    )
    ok = r.stdout.strip() == "200"
    log.info(f"Session init: HTTP {r.stdout.strip()}")
    return ok


def curl_get(url, referer="https://fedresurs.ru/biddings"):
    import tempfile
    tmp = tempfile.mktemp(suffix=".json")
    try:
        subprocess.run(
            ["curl", "-s", "-b", COOKIE_FILE, "-c", COOKIE_FILE,
             "-H", f"User-Agent: {UA}", "-H", f"Referer: {referer}",
             "-H", "Accept: application/json, text/plain, */*",
             "-o", tmp, "--max-time", "15", url],
            capture_output=True, text=True, timeout=30,
        )
        if os.path.exists(tmp):
            with open(tmp, "r") as f:
                return f.read().strip()
        return ""
    except Exception as e:
        log.error(f"curl_get error: {e}")
        return ""
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def guid_from_url(url):
    """https://fedresurs.ru/biddings/XXXX → XXXX"""
    if url:
        return url.rstrip("/").split("/")[-1]
    return None


def fetch_efrsb_price_reduction(bidding_guid):
    """
    Возвращает список lotTable записей с priceReduction для данного bidding.
    """
    # Шаг 1: detail
    raw = curl_get(f"{BASE}/biddings/{bidding_guid}",
                   referer=f"https://fedresurs.ru/biddings/{bidding_guid}")
    if not raw:
        return []
    try:
        detail = json.loads(raw)
    except json.JSONDecodeError:
        return []

    msg_guid = detail.get("message", {}).get("guid", "")
    if not msg_guid:
        return []

    time.sleep(1)

    # Шаг 2: message
    raw = curl_get(f"{BASE}/bankruptcy-messages/{msg_guid}",
                   referer=f"https://fedresurs.ru/bankruptmessages/{msg_guid}")
    if not raw:
        return []
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return []

    mc = msg.get("content", {}).get("messageInfo", {}).get("messageContent", {})
    lots = mc.get("lotTable", [])
    add_text = mc.get("additionalText", "")

    return [(lot, add_text) for lot in lots]


# ── Парсинг price_schedule (импортируем из efrsb_supabase_patch) ───────────────

def _load_parser():
    """Пробуем импортировать parse_price_schedule из efrsb_supabase_patch."""
    try:
        sys.path.insert(0, "/opt/torgi-proxy")
        from efrsb_supabase_patch import parse_price_schedule, _extract_min_price
        return parse_price_schedule, _extract_min_price
    except ImportError:
        log.error("Не удалось импортировать efrsb_supabase_patch")
        return None, None


# ── Основная логика ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    parse_price_schedule, extract_min_price = _load_parser()
    if not parse_price_schedule:
        sys.exit(1)

    sb = get_sb()
    lots = fetch_lots_to_enrich(sb, args.limit)
    log.info(f"Лотов для обогащения: {len(lots)}")

    if not lots:
        return

    if not init_session():
        log.error("Session init failed")
        sys.exit(1)

    ok_count = 0
    for lot in lots:
        lot_id = lot["lot_id"]
        url = lot.get("url", "")
        start_price = lot.get("price")
        guid = guid_from_url(url)

        if not guid:
            log.warning(f"  {lot_id}: не удалось извлечь GUID из URL {url}")
            continue

        log.info(f"  {lot_id} (guid={guid})")
        lot_rows = fetch_efrsb_price_reduction(guid)

        if not lot_rows:
            log.warning(f"  {lot_id}: нет данных lotTable")
            time.sleep(1)
            continue

        # Берём первый лот (или ищем по startPrice)
        best_row = None
        for lot_data, add_text in lot_rows:
            pr = lot_data.get("priceReduction", "")
            if pr:
                best_row = (lot_data, add_text)
                break

        if not best_row:
            log.info(f"  {lot_id}: priceReduction пустой")
            time.sleep(1)
            continue

        lot_data, add_text = best_row
        pr_text = lot_data.get("priceReduction", "")
        schedule = parse_price_schedule(pr_text, add_text, float(start_price) if start_price else None)

        if not schedule:
            log.info(f"  {lot_id}: не удалось распарсить schedule (текст: {pr_text[:100]!r})")
            time.sleep(1)
            continue

        min_price = extract_min_price(pr_text)
        update = {"price_schedule": schedule}
        if min_price:
            update["min_price"] = min_price

        sb.table("properties").update(update).eq("lot_id", lot_id).execute()
        log.info(f"  {lot_id}: записан schedule ({len(schedule)} этапов)")
        ok_count += 1
        time.sleep(2)

    log.info(f"=== Done: {ok_count}/{len(lots)} лотов обогащено ===")


if __name__ == "__main__":
    main()
