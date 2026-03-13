#!/usr/bin/env python3
"""
enrich_debtor.py — Парсинг данных о должнике из описания лота.

Запуск на VPS:
  cd /opt/torgi-proxy && source venv/bin/activate
  python enrich_debtor.py

Паттерны:
  "соб-к: Лавров И. С."
  "соб-к: ООО Тайм ОФ Инвест ИНН 7751068439"
  "соб-ки по решению суда: Кандакова О.В., Дозморов Д.А."
  "Д-к, с-к: Сулоев Д.О."
"""

import logging
import os
import re

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)


# Паттерны имён должников
DEBTOR_PATTERNS = [
    # "соб-к: Лавров И. С., адрес:"  или  "соб-к: ООО Тайм ОФ Инвест ИНН 123"
    re.compile(
        r"соб-к\s*(?:по\s+\w+)?\s*:\s*(.+?)(?:,\s*(?:адрес|местоположен|г\.|ул\.|Пермский|расположен))",
        re.IGNORECASE,
    ),
    # "соб-ки по решению суда: Кандакова О.В., Дозморов Д.А., адрес:"
    re.compile(
        r"соб-ки?\s+по\s+\w+\s+\w+:\s*(.+?)(?:,\s*адрес|$)",
        re.IGNORECASE,
    ),
    # "Д-к, с-к: Сулоев Д.О. Лот:"
    re.compile(
        r"[дД]-к,?\s*с-к:\s*(.+?)(?:\.\s*[лЛ]от|$)",
        re.IGNORECASE,
    ),
    # "собственник: ФИО"
    re.compile(
        r"собственник\s*:\s*(.+?)(?:,\s*адрес|$)",
        re.IGNORECASE,
    ),
]

# ИНН в тексте
INN_PATTERN = re.compile(r"ИНН\s*(\d{10,12})")

# Определяем тип должника
ORG_PREFIXES = ("ооо", "оао", "зао", "пао", "ип ", "ао ", "гуп", "муп", "нко", "тсж")


def parse_debtor(name: str) -> dict:
    """Парсит имя должника и ИНН из описания лота."""
    result = {}

    if not name:
        return result

    # Ищем имя должника
    debtor_name = None
    for pat in DEBTOR_PATTERNS:
        m = pat.search(name)
        if m:
            debtor_name = m.group(1).strip().rstrip(",. ")
            break

    if not debtor_name:
        return result

    result["debtor_name"] = debtor_name[:200]  # ограничиваем длину

    # Ищем ИНН
    inn_match = INN_PATTERN.search(name)
    if inn_match:
        result["debtor_inn"] = inn_match.group(1)

    # Определяем тип: физлицо или юрлицо
    dn_lower = debtor_name.lower()
    if any(dn_lower.startswith(p) for p in ORG_PREFIXES) or "инн" in dn_lower:
        result["debtor_type"] = "юрлицо"
    else:
        result["debtor_type"] = "физлицо"

    return result


def main():
    log.info("Загрузка лотов из Supabase...")

    # Берём лоты с типом "Реализация имущества должников" и без debtor_name
    resp = (
        sb.table("properties")
        .select("lot_id, name, bidd_type, debtor_name")
        .is_("debtor_name", "null")
        .execute()
    )
    lots = resp.data
    log.info("Найдено %d лотов без данных о должнике", len(lots))

    ok = 0
    skip = 0

    for i, lot in enumerate(lots, 1):
        name = lot.get("name", "")
        lot_id = lot["lot_id"]

        debtor = parse_debtor(name)
        if not debtor:
            skip += 1
            continue

        # Записываем в Supabase
        try:
            sb.table("properties").update(debtor).eq("lot_id", lot_id).execute()
            log.info(
                "[%d] %s — %s (%s)",
                ok + 1,
                lot_id,
                debtor.get("debtor_name", "?"),
                debtor.get("debtor_type", "?"),
            )
            ok += 1
        except Exception as e:
            log.error("Ошибка записи %s: %s", lot_id, e)

    log.info("=" * 50)
    log.info("Готово! Обогащено: %d, пропущено (нет паттерна): %d", ok, skip)


if __name__ == "__main__":
    main()
