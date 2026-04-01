#!/usr/bin/env python3
"""
archive_expired.py — Перенос просроченных лотов в архив.

Переносит в properties_archive лоты с истёкшим дедлайном подачи заявок
(application_end < сегодня) и без статуса (lot_status IS NULL).
Лоты со статусом watch/go/skip сохраняются.

Запуск: python3 archive_expired.py
Cron: в цепочке обогащения (перед enrich_cadastral)
"""

import logging
import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_HOST = "db.eeahxalvnvbroswzyfjx.supabase.co"


def run():
    today = date.today().isoformat()
    log.info(f"Архивация просроченных лотов (application_end < {today}, без статуса)")

    if not DB_PASSWORD:
        log.error("DB_PASSWORD не задан в .env")
        return

    import subprocess

    sql = f"""
    BEGIN;
    INSERT INTO properties_archive
    SELECT * FROM properties
    WHERE application_end IS NOT NULL
      AND application_end < '{today}'
      AND (lot_status IS NULL OR lot_status = '')
    ON CONFLICT (lot_id) DO NOTHING;
    DELETE FROM properties
    WHERE application_end IS NOT NULL
      AND application_end < '{today}'
      AND (lot_status IS NULL OR lot_status = '');
    COMMIT;
    """

    result = subprocess.run(
        [
            "psql",
            "-h", DB_HOST,
            "-U", "postgres",
            "-d", "postgres",
            "-c", sql,
        ],
        env={**os.environ, "PGPASSWORD": DB_PASSWORD},
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode == 0:
        # Парсим количество из вывода
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if "DELETE" in line:
                log.info(f"Архивировано: {line.strip()}")
    else:
        log.error(f"Ошибка: {result.stderr}")


if __name__ == "__main__":
    run()
