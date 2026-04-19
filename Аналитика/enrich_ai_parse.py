#!/usr/bin/env python3
"""
enrich_ai_parse.py — AI-парсинг описаний лотов через Claude Code (Max подписка).
Модель: Sonnet. Батчинг: 30 лотов за вызов.

Запуск на Aeza VPS:
  cd /opt/ei-ai && python3 enrich_ai_parse.py
  python3 enrich_ai_parse.py --limit 100
  python3 enrich_ai_parse.py --batch-size 20  # меньше батч
"""
import argparse
import json
import logging
import os
import subprocess
import time

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

TG_BOT = "8604957943:AAF37XNjilxzwZV39MMTeGvVAalr95UrSpo"
TG_CHAT = "191260933"

def notify_tg(text):
    try:
        import requests as _r
        _r.post(f"https://api.telegram.org/bot{TG_BOT}/sendMessage",
                data={"chat_id": TG_CHAT, "text": text}, timeout=10)
    except Exception:
        pass

PARSE_PROMPT = """Ты — эксперт по анализу объявлений о продаже недвижимости на торгах.

Для КАЖДОГО лота из списка ниже извлеки факты в JSON. Если информации нет — ставь null.

Формат ответа — JSON-объект где ключ = lot_id, значение = данные:
{
  "LOT-123": {
    "property_type_refined": "apartment|land|house|commercial|garage|other",
    "rooms": null, "floor": null, "floors_total": null,
    "area_m2": null, "land_area_m2": null,
    "condition": null,
    "wall_material": null, "build_year": null,
    "has_gas": null, "has_water": null, "has_electricity": null,
    "has_sewage": null, "has_heating": null,
    "land_category": null, "permitted_use": null,
    "is_share": false, "share_fraction": null,
    "has_encumbrances": null, "encumbrance_details": null,
    "address_details": null,
    "notable_features": null
  },
  "LOT-456": { ... }
}

Верни ТОЛЬКО JSON. Без markdown, без пояснений."""


def call_claude(prompt, model="sonnet"):
    """Вызвать Claude Code CLI через stdin (Max подписка)."""
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    try:
        result = subprocess.run(
            ["claude", "-p", "-", "--model", model, "--max-turns", "1"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
        text = (result.stdout or "").strip()
        if not text and result.stderr:
            log.error("  Claude stderr: %s", result.stderr[:200])
            return None
        # Убираем markdown обёртку ```json ... ```
        import re
        m = re.search(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
        if m:
            text = m.group(1).strip()
        return text
    except subprocess.TimeoutExpired:
        log.error("Claude Code таймаут (5 мин)")
        return None
    except Exception as e:
        log.error(f"Claude Code ошибка: {e}")
        return None


def apply_ai_fields(lot, parsed):
    """Из AI-парсинга обновить конкретные поля в Supabase."""
    update = {"ai_parsed": parsed}
    ptype = lot.get("property_type", "")

    if ptype == "apartment":
        apt = lot.get("apartment") or {}
        for k in ["rooms", "floor", "floors_total", "condition"]:
            if parsed.get(k) and not apt.get(k):
                apt[k] = parsed[k]
        if any(apt.get(k) for k in ["rooms", "floor", "floors_total", "condition"]):
            update["apartment"] = apt

    elif ptype == "land":
        land = lot.get("land") or {}
        for k in ["has_gas", "has_water", "has_electricity", "has_sewage", "land_category"]:
            if parsed.get(k) is not None and land.get(k) is None:
                land[k] = parsed[k]
        if any(land.get(k) is not None for k in ["has_gas", "has_water", "has_electricity"]):
            update["land"] = land

    elif ptype == "house":
        house = lot.get("house") or {}
        for k in ["wall_material", "build_year", "condition", "rooms"]:
            if parsed.get(k) and not house.get(k):
                house[k] = parsed[k]
        if any(house.get(k) for k in ["wall_material", "build_year", "condition"]):
            update["house"] = house

    elif ptype == "commercial":
        comm = lot.get("commercial") or {}
        for k in ["floor", "condition"]:
            if parsed.get(k) and not comm.get(k):
                comm[k] = parsed[k]
        if any(comm.get(k) for k in ["floor", "condition"]):
            update["commercial"] = comm

    if parsed.get("area_m2") and not lot.get("area"):
        update["area"] = parsed["area_m2"]

    return update


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Лимит лотов (0=все до 1000)")
    parser.add_argument("--batch-size", type=int, default=30, help="Лотов в одном вызове Claude")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    log.info("Загрузка лотов...")
    q = (
        sb.table("properties")
        .select("lot_id, property_type, name, address, address_std, apartment, land, house, commercial, area, ai_parsed")
        .neq("name", "")
        .not_.is_("name", "null")
    )
    if not args.force:
        q = q.is_("ai_parsed", "null")

    limit = args.limit if args.limit else 1000
    resp = q.order("created_at", desc=True).limit(limit).execute()
    lots = resp.data

    log.info("Найдено %d лотов для AI-парсинга", len(lots))
    if not lots:
        return

    # Разбиваем на батчи
    ok = 0
    fail = 0
    batches = [lots[i:i+args.batch_size] for i in range(0, len(lots), args.batch_size)]

    for bi, batch in enumerate(batches, 1):
        log.info("[Батч %d/%d] %d лотов", bi, len(batches), len(batch))

        # Формируем промпт с описаниями лотов
        lot_texts = []
        for lot in batch:
            name = lot.get("name") or ""
            if len(name) < 10:
                continue
            addr = lot.get("address_std") or lot.get("address") or ""
            lot_texts.append(f'{lot["lot_id"]}: {name}' + (f' | Адрес: {addr}' if addr else ''))

        if not lot_texts:
            continue

        prompt = PARSE_PROMPT + "\n\nЛоты:\n" + "\n".join(lot_texts)

        raw = call_claude(prompt, model="sonnet")
        if not raw:
            fail += len(batch)
            continue

        try:
            results = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("  Невалидный JSON от Claude")
            fail += len(batch)
            continue

        # Записываем результаты
        for lot in batch:
            lot_id = lot["lot_id"]
            parsed = results.get(lot_id)
            if not parsed:
                fail += 1
                continue

            update = apply_ai_fields(lot, parsed)
            try:
                sb.table("properties").update(update).eq("lot_id", lot_id).execute()
                ok += 1
            except Exception as e:
                log.error("  %s: ошибка записи: %s", lot_id, e)
                fail += 1

        log.info("  Батч %d: %d записано", bi, sum(1 for l in batch if results.get(l["lot_id"])))
        time.sleep(2)  # пауза между батчами

    log.info("=" * 50)
    log.info("Готово! OK: %d, ошибок: %d (из %d)", ok, fail, len(lots))
    notify_tg(f"AI Parse (Sonnet/Max): {ok} лотов, {fail} ошибок")


if __name__ == "__main__":
    main()
