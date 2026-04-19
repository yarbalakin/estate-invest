#!/usr/bin/env python3
"""
enrich_ai_recommend.py — AI-рекомендации через Claude Code (Max подписка).
Модель: Opus. Батчинг: 10 лотов за вызов.

Запуск на Aeza VPS:
  cd /opt/ei-ai && python3 enrich_ai_recommend.py
  python3 enrich_ai_recommend.py --limit 50
  python3 enrich_ai_recommend.py --min-score 60 --batch-size 5
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

SYSTEM_PROMPT = """Ты — старший инвестиционный аналитик компании Estate Invest (Пермь).
Компания выкупает недвижимость ниже рынка на торгах по банкротству и арестованному имуществу,
создаёт ценность и продаёт с прибылью (50/50 с инвесторами).

Для КАЖДОГО лота дай конкретную рекомендацию партнёру Ивану.

Формат — JSON-объект где ключ = lot_id:
{
  "LOT-123": "ПОКУПАТЬ. Дисконт 45% к рынку, квартира в хорошем районе. Вложить 200К в ремонт, продать за 2.8М через 3 мес. Риск: обременение залогом.",
  "LOT-456": "ПРОПУСТИТЬ. Земля ИЖС без коммуникаций, дисконт всего 15%. Не окупится."
}

Правила:
- Вердикт: ПОКУПАТЬ / РАССМОТРЕТЬ / ПРОПУСТИТЬ
- Конкретные суммы, сроки, проценты
- Главный риск
- 3-5 предложений на каждый лот, НЕ обрезай
- Без markdown разметки, только простой текст
- Верни ТОЛЬКО JSON"""


def format_lot(lot):
    """Краткая сводка лота для AI."""
    parts = [f"Тип: {lot.get('property_type', '?')}"]
    parts.append(f"Описание: {(lot.get('name') or '?')[:200]}")
    parts.append(f"Адрес: {lot.get('address_std') or lot.get('address') or '?'}")

    if lot.get("price"):
        parts.append(f"Цена: {lot['price']:,.0f}р")
    if lot.get("market_price"):
        parts.append(f"Рынок: {lot['market_price']:,.0f}р")
    if lot.get("discount"):
        parts.append(f"Дисконт: {lot['discount']:.0f}%")
    if lot.get("area"):
        parts.append(f"Площадь: {lot['area']}м²")
    if lot.get("invest_score"):
        parts.append(f"Скор: invest={lot['invest_score']}, risk={lot.get('risk_score')}, liq={lot.get('liquidity_score')}")
    if lot.get("cadastral_value"):
        parts.append(f"Кадастр.стоим: {lot['cadastral_value']:,.0f}р")
    if lot.get("analogs_count"):
        parts.append(f"Аналогов: {lot['analogs_count']}")

    # AI-парсинг
    ai = lot.get("ai_parsed")
    if ai and isinstance(ai, dict):
        filled = {k: v for k, v in ai.items() if v is not None}
        if filled:
            parts.append(f"AI: {json.dumps(filled, ensure_ascii=False)[:200]}")

    if lot.get("encumbrance_type"):
        parts.append(f"Обременения: {lot['encumbrance_type']}")

    return " | ".join(parts)


def call_claude(prompt, model="opus"):
    """Вызвать Claude Code CLI через stdin (Max подписка)."""
    # Убираем ANTHROPIC_API_KEY чтобы Claude использовал Max подписку, а не API
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    try:
        result = subprocess.run(
            ["claude", "-p", "-", "--model", model, "--max-turns", "1"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=600,
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
        log.error("Claude Code таймаут (10 мин)")
        return None
    except Exception as e:
        log.error("Claude Code ошибка: %s", e)
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--min-score", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    log.info("Загрузка лотов (min_score=%d)...", args.min_score)
    cols = (
        "lot_id,property_type,name,address,address_std,district,price,market_price,"
        "discount,area,area_unit,cadastral_number,cadastral_value,cadastral_price_ratio,"
        "invest_score,risk_score,liquidity_score,"
        "analogs_count,analogs_median_price,confidence,"
        "ai_parsed,encumbrance_type,ai_recommendation"
    )
    q = (
        sb.table("properties")
        .select(cols)
        .gte("invest_score", args.min_score)
        .order("invest_score", desc=True)
    )
    if not args.force:
        q = q.is_("ai_recommendation", "null")

    limit = args.limit if args.limit else 500
    resp = q.limit(limit).execute()
    lots = resp.data

    log.info("Найдено %d лотов для рекомендаций", len(lots))
    if not lots:
        return

    ok = 0
    fail = 0
    batches = [lots[i:i+args.batch_size] for i in range(0, len(lots), args.batch_size)]

    for bi, batch in enumerate(batches, 1):
        log.info("[Батч %d/%d] %d лотов", bi, len(batches), len(batch))

        lot_texts = []
        for lot in batch:
            lot_texts.append(f'{lot["lot_id"]}:\n{format_lot(lot)}')

        prompt = SYSTEM_PROMPT + "\n\nЛоты:\n\n" + "\n\n".join(lot_texts)

        # Retry с ожиданием при rate limit
        raw = None
        for attempt in range(5):
            raw = call_claude(prompt, model="opus")
            if raw and "Credit balance" not in raw and "rate" not in raw.lower():
                break
            wait = 120 * (attempt + 1)
            log.warning("  Rate limit (попытка %d/5) — жду %d сек...", attempt + 1, wait)
            time.sleep(wait)
            raw = None

        if not raw:
            log.error("  Все 5 попыток неуспешны, пропуск батча")
            fail += len(batch)
            continue

        try:
            results = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("  Невалидный JSON от Claude, raw[:300]: %s", raw[:300] if raw else 'EMPTY')
            fail += len(batch)
            continue

        for lot in batch:
            lot_id = lot["lot_id"]
            rec = results.get(lot_id)
            if not rec:
                fail += 1
                continue

            try:
                sb.table("properties").update({"ai_recommendation": rec}).eq("lot_id", lot_id).execute()
                ok += 1
                log.info("  %s: %s", lot_id, rec[:60])
            except Exception as e:
                log.error("  %s: ошибка записи: %s", lot_id, e)
                fail += 1

        log.info("  Батч %d: %d записано", bi, sum(1 for l in batch if results.get(l["lot_id"])))
        import random
        pause = random.randint(30, 180)  # 30 сек — 3 мин рандомная пауза
        log.info("  Пауза %d сек...", pause)
        time.sleep(pause)

    log.info("=" * 50)
    log.info("Готово! OK: %d, ошибок: %d (из %d)", ok, fail, len(lots))
    notify_tg(f"AI Recommend (Opus/Max): {ok} лотов, {fail} ошибок")


if __name__ == "__main__":
    main()
