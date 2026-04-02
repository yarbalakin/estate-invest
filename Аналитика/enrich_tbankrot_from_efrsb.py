#!/usr/bin/env python3
"""
Обогащение tbankrot лотов данными из ЕФРСБ:
  - trade_type (auction/public_offer/contest)
  - price_schedule JSONB (для public_offer)
  - min_price

Стратегия: ищем лот в ЕФРСБ по кадастровому номеру через /backend/biddings?searchString=
Среди результатов выбираем active/recent public_offer, берём priceReduction из сообщения.

Запуск:
  python3 enrich_tbankrot_from_efrsb.py [--limit 50] [--dry-run] [--only-schedule]

Флаги:
  --limit N        сколько лотов обработать (default 100)
  --dry-run        не писать в Supabase, только печатать
  --only-schedule  только лоты с trade_type='public_offer' без price_schedule
                   (иначе — все tbankrot с кадастром без price_schedule)
"""
import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("enrich_tb_efrsb")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://eeahxalvnvbroswzyfjx.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
BASE = "https://fedresurs.ru/backend"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
COOKIE_FILE = "/tmp/enrich_tb_efrsb_cookies.txt"

# Статусы, при которых торги ещё могут быть активны
ACTIVE_STATUSES = {"TradeInProcess", "TradeBiddingOpen", "TradeApplicationsOpen"}


# ── Supabase ──────────────────────────────────────────────────────────────────

def get_sb():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_lots(sb, limit, only_schedule):
    q = (
        sb.table("properties")
        .select("id, lot_id, cadastral_number, price, trade_type")
        .eq("source", "tbankrot")
        .not_.is_("cadastral_number", "null")
        .is_("price_schedule", "null")
    )
    if only_schedule:
        q = q.eq("trade_type", "public_offer")
    return (q.limit(limit).execute()).data or []


# ── ЕФРСБ сессия ─────────────────────────────────────────────────────────────

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
    if ok:
        time.sleep(3)  # Qrator: без паузы первый API-запрос возвращает пустой ответ
    return ok


def curl_get(url, referer="https://fedresurs.ru/biddings"):
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
            with open(tmp) as f:
                return f.read().strip()
        return ""
    except Exception as e:
        log.error(f"curl_get error: {e}")
        return ""
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ── ЕФРСБ поиск ──────────────────────────────────────────────────────────────

def search_by_cadastral(cadastral):
    """Ищет торги ЕФРСБ по кадастровому номеру. Возвращает список лотов."""
    encoded = urllib.parse.quote(cadastral)
    url = f"{BASE}/biddings?limit=5&offset=0&searchString={encoded}"
    raw = curl_get(url)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data.get("pageData", [])
    except json.JSONDecodeError:
        return []


def pick_best_bidding(results):
    """
    Выбирает лучший результат из списка торгов ЕФРСБ.
    Приоритет: активное публичное предложение > любое публичное > активный аукцион > первый.
    """
    def type_name(b):
        t = b.get("type", "")
        return t.get("name", "") if isinstance(t, dict) else str(t)

    def status_code(b):
        s = b.get("status", "")
        return s.get("code", "") if isinstance(s, dict) else str(s)

    public_active = [b for b in results
                     if "Публичн" in type_name(b) and status_code(b) in ACTIVE_STATUSES]
    if public_active:
        return public_active[0]

    public_any = [b for b in results if "Публичн" in type_name(b)]
    if public_any:
        return public_any[0]

    active_any = [b for b in results if status_code(b) in ACTIVE_STATUSES]
    if active_any:
        return active_any[0]

    return results[0] if results else None


def fetch_detail(guid):
    raw = curl_get(f"{BASE}/biddings/{guid}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def fetch_lot_data(msg_guid):
    """Возвращает (lotTable, additionalText) из сообщения ЕФРСБ."""
    raw = curl_get(
        f"{BASE}/bankruptcy-messages/{msg_guid}",
        referer=f"https://fedresurs.ru/bankruptmessages/{msg_guid}",
    )
    if not raw:
        return [], ""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return [], ""
    mc = msg.get("content", {}).get("messageInfo", {}).get("messageContent", {})
    return mc.get("lotTable", []), mc.get("additionalText", "")


def map_trade_type(type_name_str):
    t = (type_name_str or "").lower()
    if "публичн" in t:
        return "public_offer"
    if "конкурс" in t:
        return "contest"
    return "auction"


# ── Основной обработчик лота ──────────────────────────────────────────────────

def process_lot(lot, parse_price_schedule, extract_min_price, dry_run, sb):
    lot_id = lot["lot_id"]
    cadastral = lot.get("cadastral_number", "")
    start_price = lot.get("price")

    log.info(f"  {lot_id} | cadastral={cadastral}")

    # Поиск в ЕФРСБ
    results = search_by_cadastral(cadastral)
    if not results:
        log.info(f"    нет результатов в ЕФРСБ")
        return "not_found"
    time.sleep(1)

    bidding = pick_best_bidding(results)
    if not bidding:
        return "not_found"

    guid = bidding["guid"]
    t = bidding.get("type", "")
    type_name_str = t.get("name", "") if isinstance(t, dict) else str(t)
    trade_type = map_trade_type(type_name_str)
    log.info(f"    ЕФРСБ guid={guid} type={type_name_str} → {trade_type}")

    # Детали торгов (нужна дата начала для Format A)
    detail = fetch_detail(guid)
    if not detail:
        # Хотя бы trade_type записываем
        _patch(sb, lot_id, {"trade_type": trade_type}, dry_run)
        return "partial"
    time.sleep(1)

    # Дата начала для Format A
    ap = detail.get("applicationPeriod", {})
    if isinstance(ap, dict):
        start_dt = ap.get("startDate", "")
    else:
        start_dt = ""
    if start_dt:
        # Конвертируем "2026-03-17T09:00:00" → "17.03.2026" для parse_price_schedule
        try:
            dt = datetime.fromisoformat(start_dt[:10])
            date_hint = dt.strftime("%d.%m.%Y")
        except Exception:
            date_hint = ""
    else:
        date_hint = ""

    # Сообщение ЕФРСБ → priceReduction
    msg_guid = detail.get("message", {}).get("guid", "") if isinstance(detail.get("message"), dict) else ""
    if not msg_guid:
        _patch(sb, lot_id, {"trade_type": trade_type}, dry_run)
        return "partial"

    lot_table, add_text = fetch_lot_data(msg_guid)
    if not lot_table:
        _patch(sb, lot_id, {"trade_type": trade_type}, dry_run)
        return "partial"
    time.sleep(1)

    # Берём первый лот с непустым priceReduction
    pr_text = ""
    for lot_row in lot_table:
        pr = lot_row.get("priceReduction", "")
        if pr:
            pr_text = pr
            break

    if not pr_text and add_text:
        pr_text = add_text
        add_text = ""

    # Строим расширенный текст: дата начала + priceReduction + additionalText
    full_text = "\n".join(filter(None, [date_hint, pr_text, add_text]))

    update = {"trade_type": trade_type}

    if trade_type == "public_offer" and full_text:
        schedule = parse_price_schedule(full_text, "", float(start_price) if start_price else None)
        if schedule:
            update["price_schedule"] = schedule
            log.info(f"    schedule: {len(schedule)} этапов, первый {schedule[0]['date_start']} {schedule[0]['price']}")
        else:
            log.info(f"    schedule не распарсился (pr_text[:80]: {pr_text[:80]!r})")

        min_p = extract_min_price(pr_text) if pr_text else None
        if min_p:
            update["min_price"] = min_p

    _patch(sb, lot_id, update, dry_run)
    return "ok" if "price_schedule" in update else "trade_type_only"


def _patch(sb, lot_id, update, dry_run):
    if dry_run:
        log.info(f"    [dry-run] update {lot_id}: {list(update.keys())}")
        return
    sb.table("properties").update(update).eq("lot_id", lot_id).execute()
    log.info(f"    записано: {list(update.keys())}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only-schedule", action="store_true",
                        help="Только лоты с trade_type=public_offer без price_schedule")
    args = parser.parse_args()

    try:
        sys.path.insert(0, "/opt/torgi-proxy")
        from efrsb_supabase_patch import parse_price_schedule, _extract_min_price
    except ImportError as e:
        log.error(f"Не удалось импортировать efrsb_supabase_patch: {e}")
        sys.exit(1)

    sb = get_sb()
    lots = fetch_lots(sb, args.limit, args.only_schedule)
    log.info(f"Лотов для обогащения: {len(lots)}")

    if not lots:
        log.info("Нечего обрабатывать")
        return

    if not init_session():
        log.error("Не удалось инициализировать сессию ЕФРСБ")
        sys.exit(1)

    stats = {"ok": 0, "trade_type_only": 0, "partial": 0, "not_found": 0, "err": 0}

    for i, lot in enumerate(lots):
        try:
            result = process_lot(lot, parse_price_schedule, _extract_min_price, args.dry_run, sb)
            stats[result] = stats.get(result, 0) + 1
        except Exception as e:
            log.error(f"  {lot['lot_id']}: ошибка {e}")
            stats["err"] += 1

        time.sleep(2)

        if (i + 1) % 20 == 0:
            log.info(f"Прогресс {i+1}/{len(lots)}: {stats}")

    log.info(f"=== Готово: {stats} (из {len(lots)}) ===")
    if args.dry_run:
        log.info("(--dry-run: в БД не записано)")


if __name__ == "__main__":
    main()
