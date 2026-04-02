#!/usr/bin/env python3
"""
Backfill trade_type для существующих tbankrot лотов в Supabase.
Скрапит detail страницу tbankrot.ru для каждого лота без trade_type.

Запуск: python3 tbankrot_backfill_trade_type.py [--limit 50] [--dry-run]
"""
import argparse
import os
import sys
import time
import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("tb_backfill")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://eeahxalvnvbroswzyfjx.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
BASE_URL = "https://tbankrot.ru"


def get_sb():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_lots(sb, limit):
    resp = (
        sb.table("properties")
        .select("id, lot_id, url")
        .eq("source", "tbankrot")
        .is_("trade_type", "null")
        .limit(limit)
        .execute()
    )
    return resp.data or []


def parse_trade_type_from_html(html):
    """Возвращает 'auction' | 'public_offer' | 'contest' | None."""
    # Основной блок: class="lot_type"> (Открытый аукцион)
    lot_type_m = re.search(r'lot_type">\s*\(([^)]+)\)', html, re.I)
    if lot_type_m:
        raw = lot_type_m.group(1).lower()
        if "публичн" in raw:
            return "public_offer"
        if "конкурс" in raw:
            return "contest"
        # "Открытый аукцион", "Закрытый аукцион", "Другое" и прочие → auction
        return "auction"

    # Запасной вариант: скобки в тексте
    trade_m = re.search(
        r"\((Открытый аукцион|Публичное предложение|Конкурс|Закрытый аукцион)\)",
        html, re.I,
    )
    if trade_m:
        raw = trade_m.group(1).lower()
        if "публичн" in raw:
            return "public_offer"
        if "конкурс" in raw:
            return "contest"
        return "auction"

    if re.search(r"публичн\w*\s+предложени", html, re.I):
        return "public_offer"

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Импортируем SafeClient из tbankrot_scraper
    try:
        sys.path.insert(0, "/opt/torgi-proxy")
        from tbankrot_scraper import SafeClient, DELAY_DETAIL
    except ImportError as e:
        log.error(f"Не удалось импортировать tbankrot_scraper: {e}")
        sys.exit(1)

    sb = get_sb()
    lots = fetch_lots(sb, args.limit)
    log.info(f"Лотов для обогащения: {len(lots)}")

    if not lots:
        log.info("Ничего нет — всё уже обогащено")
        return

    client = SafeClient()
    stats = {"ok": 0, "not_found": 0, "err": 0}

    for i, lot in enumerate(lots):
        lot_id = lot["lot_id"]
        url = lot.get("url", "")

        # Извлекаем tbankrot ID из URL
        tb_id_m = re.search(r"id=(\d+)", url)
        if not tb_id_m:
            log.warning(f"  {lot_id}: не удалось извлечь ID из {url}")
            stats["err"] += 1
            continue

        detail_url = f"{BASE_URL}/item?id={tb_id_m.group(1)}"
        resp = client.get(detail_url, delay_range=DELAY_DETAIL)

        if not resp:
            log.warning(f"  {lot_id}: нет ответа от tbankrot")
            stats["err"] += 1
            continue

        trade_type = parse_trade_type_from_html(resp.text)

        if trade_type is None:
            log.info(f"  {lot_id}: тип не определён")
            stats["not_found"] += 1
            continue

        log.info(f"  {lot_id}: {trade_type}")

        if not args.dry_run:
            sb.table("properties").update({"trade_type": trade_type}).eq("lot_id", lot_id).execute()

        stats["ok"] += 1

        if (i + 1) % 20 == 0:
            log.info(f"Прогресс: {i+1}/{len(lots)} | ok={stats['ok']} nf={stats['not_found']} err={stats['err']}")

    log.info(f"=== Готово: ok={stats['ok']} not_found={stats['not_found']} err={stats['err']} (из {len(lots)}) ===")
    if args.dry_run:
        log.info("(--dry-run: в БД не записано)")


if __name__ == "__main__":
    main()
