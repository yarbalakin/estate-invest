#!/usr/bin/env python3
"""
ЕФРСБ Монитор — парсинг банкротных торгов недвижимости (мультирегион)
Cron: каждые 4 часа. Новые лоты → Telegram + Google Sheets (лист "ЕФРСБ").
Запуск: python3 efrsb_monitor.py --region perm|kaliningrad
"""
import argparse
import subprocess
import json
import time
import os
import re
import logging
import requests
from datetime import datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials

try:
    from efrsb_supabase_patch import write_to_supabase
except ImportError:
    write_to_supabase = None

# === Конфиг регионов ===
REGIONS = {
    "perm": {"name": "Пермский край", "efrsb_region": "59", "tg_channel": "-1003759471621"},
    "kaliningrad": {"name": "Калининградская область", "efrsb_region": "39", "tg_channel": "-1003759471621"},
    "bryansk": {"name": "Брянская область", "efrsb_region": "32", "tg_channel": "-5200571061"},
}

_parser = argparse.ArgumentParser()
_parser.add_argument("--region", default="perm", choices=REGIONS.keys())
_args, _ = _parser.parse_known_args()
REGION = REGIONS[_args.region]
REGION_KEY = _args.region

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"/opt/torgi-proxy/efrsb_monitor_{REGION_KEY}.log"),
    ],
)
log = logging.getLogger("efrsb")
log.info(f"Region: {REGION['name']} (regionCode={REGION['efrsb_region']})")

SEEN_FILE   = f"/opt/torgi-proxy/efrsb_seen_{REGION_KEY}.json"
TG_BOT_TOKEN = "8650381430:AAFKGNZbjQmhAd3ogse9gOWs7_2xoypuo-A"
TG_CHAT_ID  = REGION.get("tg_channel", "-1003759471621")
SA_JSON     = "/opt/torgi-proxy/google-sa.json"
SS_LOTS     = "1Wji_7UYqIRmxbsd1Ob52NutSrKThd3m37fkXDFuBfPk"
SHEET_NAME  = "ЕФРСБ"

UA   = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BASE = "https://fedresurs.ru/backend"

REALTY_CODES = {
    "0101", "0101007", "0101015", "0101016", "0101017",
    "0103", "0108", "0108001", "0301",
}
SKIP_STATUSES = {
    "TradeCompleted", "TradeFailed", "TradeCancelled",
    "TradeAnnulled", "TradeSuspended",
}

COOKIE_FILE = "/tmp/efrsb_cookies.txt"

# ── Google Sheets ──────────────────────────────────────────────
_gc = None

def get_gc():
    global _gc
    if _gc is None:
        creds = Credentials.from_service_account_file(
            SA_JSON,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        _gc = gspread.authorize(creds)
    return _gc


def extract_cadastral(text):
    m = re.search(r'\d{2}:\d+:\d+:\d+', text or "")
    return m.group(0) if m else ""


def extract_area(text):
    m = re.search(r'[Пп]лощадь[ю:]?\s*[:\s]*([\d\s.,]+)', text or "")
    if m:
        return m.group(1).strip().split()[0].replace(",", ".")
    return ""


def fmt_date(dt_str):
    if not dt_str:
        return ""
    try:
        return datetime.fromisoformat(dt_str[:19]).strftime("%d.%m.%Y")
    except Exception:
        return dt_str[:10]


def write_to_sheets(bidding_info, lot_info, lot_order, tg_text):
    """Записать в лист ЕФРСБ.
    Колонки: lotId, dateAdded, category, name, address, area,
             price, deposit, cadastralNumber, auctionDate, applicationEnd,
             biddType, etpUrl, status, debtor, legalCase, url, telegramMessage
    """
    try:
        gc  = get_gc()
        sh  = gc.open_by_key(SS_LOTS)
        ws  = sh.worksheet(SHEET_NAME)

        desc   = lot_info.get("description", "")
        price  = lot_info.get("startPrice") or 0
        adv    = lot_info.get("advance") or 0
        adv_u  = lot_info.get("advanceStepUnit", "Percent")
        deposit = round(price * adv / 100, 2) if adv_u == "Percent" else adv

        row = [
            f"ЕФРСБ-{bidding_info['biddingGuid']}-{lot_order}",
            datetime.now().strftime("%d.%m.%Y %H:%M"),
            lot_info.get("category", ""),
            desc[:400].replace("\n", " ").strip(),
            bidding_info.get("debtorAddress", ""),
            extract_area(desc),
            price,
            deposit,
            extract_cadastral(desc),
            fmt_date(bidding_info.get("auctionDate", "")),
            fmt_date(bidding_info.get("applicationEnd", "")),
            bidding_info.get("type", ""),
            bidding_info.get("tradePlaceUrl", ""),
            bidding_info.get("status", ""),
            bidding_info.get("bankrupt", ""),
            bidding_info.get("legalCase", ""),
            f"https://fedresurs.ru/biddings/{bidding_info['biddingGuid']}",
            tg_text[:500],
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        log.info(f"  Sheets OK: {bidding_info['bankrupt']} | лот {lot_order}")
        return True
    except Exception as e:
        log.error(f"  Sheets error: {e}")
        return False


# ── curl / session ─────────────────────────────────────────────

def init_session():
    if os.path.exists(COOKIE_FILE):
        os.remove(COOKIE_FILE)
    r = subprocess.run(
        ["curl", "-s", "-c", COOKIE_FILE, "-o", "/dev/null", "-w", "%{http_code}",
         "-H", f"User-Agent: {UA}", "--max-time", "15", "https://fedresurs.ru/biddings"],
        capture_output=True, text=True, timeout=30,
    )
    status = r.stdout.strip()
    if status == "200":
        log.info("Session init OK")
        return True
    log.error(f"Session init failed: HTTP {status}")
    return False


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


def fetch_biddings(region="59", page_size=15, pages=5):
    all_items, found = [], 0
    for page in range(pages):
        url = f"{BASE}/biddings?searchByRegion=true&regionCode={region}&limit={page_size}&offset={page*page_size}"
        raw = curl_get(url)
        if not raw:
            return None if page == 0 else {"found": found, "pageData": all_items}
        try:
            data = json.loads(raw)
            found = data.get("found", 0)
            all_items.extend(data.get("pageData", []))
        except json.JSONDecodeError as e:
            log.error(f"fetch_biddings page {page}: bad JSON: {e}")
            return None if page == 0 else {"found": found, "pageData": all_items}
        time.sleep(2)
    return {"found": found, "pageData": all_items}


def fetch_detail(guid):
    raw = curl_get(f"{BASE}/biddings/{guid}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.error(f"fetch_detail: bad JSON for {guid}")
        return None


def fetch_message(msg_guid):
    raw = curl_get(
        f"{BASE}/bankruptcy-messages/{msg_guid}",
        referer=f"https://fedresurs.ru/bankruptmessages/{msg_guid}",
    )
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.error(f"fetch_message: bad JSON for {msg_guid}")
        return None


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return {}


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f)


def clean_seen(seen, days=30):
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    return {k: v for k, v in seen.items() if v > cutoff}


def map_trade_type(type_name):
    """Маппинг ЕФРСБ type.name → trade_type."""
    t = (type_name or "").lower()
    if "публичн" in t:
        return "public_offer"
    if "аукцион" in t:
        return "auction"
    if "конкурс" in t:
        return "contest"
    return "auction"  # fallback — большинство банкротных торгов это аукционы


def is_realty_lot(lot):
    classifiers = lot.get("classifierCollection", [])
    if not classifiers:
        return False
    code = classifiers[0].get("code", "")
    return any(code.startswith(rc) for rc in REALTY_CODES)


def format_telegram_message(bidding, lot):
    price = lot.get("startPrice", 0)
    price_str = f"{price:,.0f} ₽".replace(",", " ") if price else "не указана"
    category = lot.get("category", "Недвижимость")
    desc = lot.get("description", "").replace("\n", " ").strip()[:300]

    msg = f"🏠 <b>ЕФРСБ: {category}</b>\n\n"
    msg += f"💰 Цена: <b>{price_str}</b>\n"
    msg += f"📋 {bidding['type']} | {bidding['status']}\n"
    if desc:
        msg += f"\n📝 {desc}\n"
    if bidding.get("debtorAddress"):
        msg += f"\n📍 {bidding['debtorAddress']}\n"
    msg += f"\n👤 Должник: {bidding.get('bankrupt', '—')}"
    if bidding.get("legalCase"):
        msg += f"\n⚖️ Дело: {bidding['legalCase']}"
    if bidding.get("tradePlace"):
        msg += f"\n🏛 Площадка: {bidding['tradePlace']}"
    if bidding.get("tradePlaceUrl"):
        url = bidding["tradePlaceUrl"]
        if not url.startswith("http"):
            url = "https://" + url
        msg += f"\n🔗 {url}"
    msg += f'\n\n🔍 <a href="https://fedresurs.ru/biddings/{bidding["biddingGuid"]}">Открыть на ЕФРСБ</a>'
    return msg


def send_telegram(text):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10,
        )
        if r.status_code == 200:
            return True
        log.error(f"Telegram error: {r.status_code} {r.text[:200]}")
        if r.status_code == 429:
            time.sleep(r.json().get("parameters", {}).get("retry_after", 5))
        return False
    except Exception as e:
        log.error(f"Telegram exception: {e}")
        return False


def main():
    log.info("=== ЕФРСБ Monitor start ===")

    if not init_session():
        return
    time.sleep(3)

    data = fetch_biddings(REGION["efrsb_region"])
    if not data:
        log.error("Failed to fetch biddings")
        return
    items = data.get("pageData", [])
    log.info(f"Biddings: found={data.get('found', 0)}, fetched={len(items)}")

    seen = clean_seen(load_seen())
    new_count = sent_count = 0

    for bidding_raw in items:
        guid        = bidding_raw["guid"]
        status_code = bidding_raw.get("status", {}).get("code", "")

        if guid in seen:
            continue
        if status_code in SKIP_STATUSES:
            seen[guid] = datetime.now().isoformat()
            continue

        time.sleep(0.5)
        detail = fetch_detail(guid)
        if not detail:
            seen[guid] = datetime.now().isoformat()
            continue

        msg_guid = detail.get("message", {}).get("guid", "")
        if not msg_guid:
            seen[guid] = datetime.now().isoformat()
            continue

        time.sleep(0.5)
        message = fetch_message(msg_guid)
        if not message:
            seen[guid] = datetime.now().isoformat()
            continue

        mc   = message.get("content", {}).get("messageInfo", {}).get("messageContent", {})
        lots = mc.get("lotTable", [])
        realty_lots = [lot for lot in lots if is_realty_lot(lot)]

        if not realty_lots:
            seen[guid] = datetime.now().isoformat()
            continue

        type_name = detail.get("type", {}).get("name", "")
        bidding_info = {
            "biddingGuid":   guid,
            "type":          type_name,
            "trade_type":    map_trade_type(type_name),
            "status":        bidding_raw.get("status", {}).get("name", ""),
            "bankrupt":      bidding_raw.get("bankrupt", {}).get("name", ""),
            "tradePlace":    bidding_raw.get("tradePlace", {}).get("name", ""),
            "tradePlaceUrl": detail.get("tradePlace", {}).get("url", ""),
            "debtorAddress": message.get("content", {}).get("bankrupt", {}).get("address", ""),
            "legalCase":     detail.get("legalCase", {}).get("number", ""),
            "auctionDate":   detail.get("biddingPeriod", {}).get("startDate", ""),
            "applicationEnd": detail.get("applicationPeriod", {}).get("endDate", ""),
        }

        for i, lot in enumerate(realty_lots, start=1):
            classifiers = lot.get("classifierCollection", [])
            lot_info = {
                "startPrice":      lot.get("startPrice"),
                "description":     lot.get("description", ""),
                "category":        classifiers[0].get("name", "") if classifiers else "",
                "advance":         lot.get("advance"),
                "advanceStepUnit": lot.get("advanceStepUnit", "Percent"),
                "priceReduction":  lot.get("priceReduction", ""),
                "additionalText":  mc.get("additionalText", ""),
            }
            text = format_telegram_message(bidding_info, lot_info)
            if send_telegram(text):
                sent_count += 1
                log.info(f"  Sent: {bidding_info['bankrupt']} | {lot_info['category']} | {lot_info['startPrice']}")
                write_to_sheets(bidding_info, lot_info, i, text)
                if write_to_supabase:
                    write_to_supabase(bidding_info, lot_info, i)
            time.sleep(1)

        new_count += 1
        seen[guid] = datetime.now().isoformat()

    save_seen(seen)
    log.info(f"=== Done: {new_count} new biddings, {sent_count} messages sent ===")


if __name__ == "__main__":
    main()
