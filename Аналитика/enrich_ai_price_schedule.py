#!/usr/bin/env python3
"""
AI-фоллбек для price_schedule: парсит priceReduction текст через Claude Haiku.
Для лотов где regex не справился.

Запуск на Aeza VPS (Нидерланды):
  cd /opt/ei-ai && python3 enrich_ai_price_schedule.py
  python3 enrich_ai_price_schedule.py --limit 30 --dry-run

Стоимость: ~$0.003/лот (Haiku), ~$0.08 на 25 лотов.
"""
import argparse
import json
import logging
import os
import subprocess
import tempfile
import time

import anthropic
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("/opt/ei-ai/.env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-haiku-4-5-20251001"
DELAY = 0.5

PRICE_INPUT = 0.80 / 1_000_000
PRICE_OUTPUT = 4.00 / 1_000_000
total_input_tokens = 0
total_output_tokens = 0

# ЕФРСБ API (через Timeweb VPS — российский IP)
TIMEWEB_SSH = "sshpass -p 'sp8hWiGY+kHsN6' ssh -o StrictHostKeyChecking=no root@5.42.102.36"
EFRSB_BASE = "https://fedresurs.ru/backend"

SYSTEM_PROMPT = """Ты — эксперт по торгам недвижимости в России. Из текста priceReduction извлеки этапы снижения цены.

Верни ТОЛЬКО JSON-массив (без markdown):
[
  {"date_start": "YYYY-MM-DD", "date_end": "YYYY-MM-DD", "price": 123456.78},
  ...
]

Правила:
- Даты в формате YYYY-MM-DD
- Цена — число (float), без пробелов и "руб."
- Если в тексте нет конкретных дат, но есть правила (%, дней) — вычисли этапы математически
- Если вообще нельзя определить этапы — верни пустой массив []
- Верни ТОЛЬКО JSON, ничего больше"""


def fetch_price_reduction_via_timeweb(cadastral):
    """Через Timeweb VPS получить priceReduction из ЕФРСБ по кадастру."""
    import urllib.parse
    q = urllib.parse.quote(cadastral)
    # Весь пайплайн одной SSH-командой
    cmd = f"""{TIMEWEB_SSH} 'cd /opt/torgi-proxy && python3 -c "
import subprocess, json, os, tempfile, time, urllib.parse
CF=\\"/tmp/efrsb_cookies.txt\\"
UA=\\"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\\"
B=\\"https://fedresurs.ru/backend\\"
def g(url,ref=\\"https://fedresurs.ru/biddings\\"):
    tmp=tempfile.mktemp(suffix=\\".json\\")
    subprocess.run([\\"curl\\",\\"-s\\",\\"-b\\",CF,\\"-c\\",CF,\\"-H\\",\\"User-Agent: \\"+UA,\\"-H\\",\\"Referer: \\"+ref,\\"-H\\",\\"Accept: application/json\\",\\"-o\\",tmp,\\"--max-time\\",\\"15\\",url],capture_output=True,text=True,timeout=30)
    r=open(tmp).read() if os.path.exists(tmp) else \\"\\"
    if os.path.exists(tmp): os.remove(tmp)
    return r
raw=g(B+\\"/biddings?limit=5&offset=0&searchString={q}\\")
items=json.loads(raw).get(\\"pageData\\",[]) if raw else []
for b in items:
    t=b.get(\\"type\\",{{}})
    tn=t.get(\\"name\\",\\"\\") if isinstance(t,dict) else str(t)
    if \\"Публичн\\" in tn:
        guid=b[\\"guid\\"]
        time.sleep(1)
        det=json.loads(g(B+\\"/biddings/\\"+guid))
        mg=det.get(\\"message\\",{{}}).get(\\"guid\\",\\"\\") if isinstance(det.get(\\"message\\"),dict) else \\"\\"
        ap=det.get(\\"applicationPeriod\\",{{}})
        sd=ap.get(\\"startDate\\",\\"\\") if isinstance(ap,dict) else \\"\\"
        time.sleep(1)
        if mg:
            msg=json.loads(g(B+\\"/bankruptcy-messages/\\"+mg))
            mc=msg.get(\\"content\\",{{}}).get(\\"messageInfo\\",{{}}).get(\\"messageContent\\",{{}})
            for lot in mc.get(\\"lotTable\\",[]):
                pr=lot.get(\\"priceReduction\\",\\"\\")
                if pr:
                    print(json.dumps({{\\"pr\\": pr, \\"start_date\\": sd[:10]}}, ensure_ascii=False))
                    exit(0)
        break
print(\\"null\\")
"'"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        out = result.stdout.strip()
        if out and out != "null":
            return json.loads(out)
    except Exception as e:
        log.error(f"SSH/EFRSB error: {e}")
    return None


def parse_with_ai(pr_text, start_date, start_price):
    """Отправить priceReduction в Haiku, получить schedule JSON."""
    user_text = f"Текст priceReduction:\n{pr_text}"
    if start_date:
        user_text += f"\n\nДата начала торгов: {start_date}"
    if start_price:
        user_text += f"\nНачальная цена: {start_price} руб."

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_text}],
        )
        global total_input_tokens, total_output_tokens
        total_input_tokens += resp.usage.input_tokens
        total_output_tokens += resp.usage.output_tokens

        text = resp.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        schedule = json.loads(text)
        if isinstance(schedule, list) and len(schedule) > 0:
            # Валидация: каждый элемент должен иметь date_start, date_end, price
            valid = all(
                isinstance(s, dict) and "date_start" in s and "date_end" in s and "price" in s
                for s in schedule
            )
            if valid:
                return schedule
        return None
    except json.JSONDecodeError as e:
        log.warning("  Невалидный JSON: %s", e)
        return None
    except Exception as e:
        log.error("  AI ошибка: %s", e)
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Лоты public_offer без price_schedule с кадастром
    resp = (
        sb.table("properties")
        .select("lot_id, cadastral_number, price, trade_type")
        .eq("trade_type", "public_offer")
        .is_("price_schedule", "null")
        .not_.is_("cadastral_number", "null")
        .limit(args.limit)
        .execute()
    )
    lots = resp.data or []
    log.info("Лотов для AI-парсинга price_schedule: %d", len(lots))

    if not lots:
        log.info("Все лоты уже обработаны!")
        return

    ok = 0
    fail = 0

    for i, lot in enumerate(lots, 1):
        lot_id = lot["lot_id"]
        cadastral = lot.get("cadastral_number", "")
        price = lot.get("price")

        log.info("[%d/%d] %s | cad=%s", i, len(lots), lot_id, cadastral)

        # Шаг 1: получить priceReduction из ЕФРСБ через Timeweb
        efrsb_data = fetch_price_reduction_via_timeweb(cadastral)
        if not efrsb_data:
            log.info("  ЕФРСБ: нет данных")
            fail += 1
            time.sleep(2)
            continue

        pr_text = efrsb_data.get("pr", "")
        start_date = efrsb_data.get("start_date", "")

        if not pr_text:
            log.info("  priceReduction пустой")
            fail += 1
            time.sleep(2)
            continue

        # Шаг 2: AI-парсинг
        schedule = parse_with_ai(pr_text, start_date, price)

        if not schedule:
            log.info("  AI не смог распарсить")
            fail += 1
            time.sleep(DELAY)
            continue

        log.info("  AI: %d этапов, первый %s %s", len(schedule), schedule[0]["date_start"], schedule[0]["price"])

        if not args.dry_run:
            sb.table("properties").update({"price_schedule": schedule}).eq("lot_id", lot_id).execute()
            log.info("  записано в Supabase")

        ok += 1
        time.sleep(DELAY)

    cost = total_input_tokens * PRICE_INPUT + total_output_tokens * PRICE_OUTPUT
    log.info("=" * 50)
    log.info("Готово! OK: %d, fail: %d, стоимость=$%.4f", ok, fail, cost)


if __name__ == "__main__":
    main()
