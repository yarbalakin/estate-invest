#!/usr/bin/env python3
"""
Orchestrator — запускает всю цепочку обогащения в правильном порядке.
Алерт в Telegram при >10% ошибок в любом шаге.

Порядок:
  1. archive_expired     — архивирование просроченных лотов
  2. enrich_cadastral    — кадастровые данные (lat/lon, boundary, cadastral_value)
  3. patch_land_nspd     — доп. данные НСПД для земли
  4. enrich_debtor       — парсинг должника из названия лота
  5. enrich_trade_type   — price_schedule для ЕФРСБ лотов
  6. enrich_tbankrot_from_efrsb — trade_type + price_schedule для tbankrot
  7. enrich_market       — рыночная цена через ads-api
  8. enrich_scoring      — инвест/риск/ликвидность скоринг
  9. notify_top_lots     — Telegram алерт о топ-лотах

Запуск: python3 enrich_pipeline.py [--dry-run] [--skip step1,step2]
Cron:   48 */4 * * * . /etc/environment && cd /opt/torgi-proxy && python3 enrich_pipeline.py >> /opt/torgi-proxy/enrich_pipeline.log 2>&1
"""
import argparse
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("pipeline")

TG_BOT = "8604957943:AAF37XNjilxzwZV39MMTeGvVAalr95UrSpo"
TG_CHAT = "191260933"
WORKDIR = "/opt/torgi-proxy"
PYTHON = "/usr/bin/python3"

# Aeza VPS (Нидерланды) — для AI-скриптов (Anthropic API не работает из РФ)
AEZA_SSH = "sshpass -p 'QSK0M2xVsCdb' ssh -o StrictHostKeyChecking=no root@213.108.21.37"
AEZA_AI_DIR = "/opt/ei-ai"

# Цепочка обогащения: (name, command, max_minutes, critical)
# critical=True → при падении останавливаем всю цепочку
STEPS = [
    # --- Локальные (Timeweb VPS, Москва) ---
    ("archive_expired",           f"{PYTHON} archive_expired.py",                                 5,  False),
    ("enrich_cadastral",          f"{PYTHON} enrich_cadastral.py",                               15,  False),
    ("patch_land_nspd",           f"{PYTHON} patch_land_nspd.py",                                10,  False),
    ("enrich_debtor",             f"{PYTHON} enrich_debtor.py",                                   5,  False),
    ("enrich_trade_type",         f"{PYTHON} enrich_trade_type.py",                              15,  False),
    ("enrich_tbankrot_from_efrsb", f"{PYTHON} enrich_tbankrot_from_efrsb.py --limit 50 --only-schedule", 30, False),
    ("ai_price_schedule",         f"{AEZA_SSH} 'cd {AEZA_AI_DIR} && python3 enrich_ai_price_schedule.py --limit 30'", 30, False),
    ("enrich_market",             f"{PYTHON} enrich_market.py",                                  20,  False),
    ("enrich_scoring",            f"{PYTHON} enrich_scoring.py",                                 10,  False),
    # --- AI (Aeza VPS, Нидерланды) ---
    ("ai_parse",                  f"{AEZA_SSH} 'cd {AEZA_AI_DIR} && python3 enrich_ai_parse.py --limit 100'",  30, False),
    ("ai_recommend",              f"{AEZA_SSH} 'cd {AEZA_AI_DIR} && python3 enrich_ai_recommend.py --limit 50 --model sonnet'", 30, False),
    # --- Уведомления ---
    ("notify_top_lots",           f"{PYTHON} notify_top_lots.py",                                 5,  False),
]


def send_tg(text):
    """Отправить уведомление в Telegram."""
    try:
        subprocess.run(
            ["curl", "-s", "-X", "POST",
             f"https://api.telegram.org/bot{TG_BOT}/sendMessage",
             "-d", f"chat_id={TG_CHAT}",
             "-d", f"text={text}",
             "-d", "parse_mode=HTML"],
            capture_output=True, timeout=15,
        )
    except Exception as e:
        log.error(f"TG send error: {e}")


def parse_stats_from_output(output):
    """
    Пытается извлечь статистику из вывода скрипта.
    Ищет паттерны: ok=N, err=N, not_found=N, Готово: {...}
    Возвращает (total, errors) или (None, None).
    """
    # Pattern: {'ok': 42, 'trade_type_only': 10, 'err': 0} (из 181)
    m = re.search(r"\(из\s+(\d+)\)", output)
    total = int(m.group(1)) if m else None

    err_m = re.search(r"'err':\s*(\d+)", output)
    errors = int(err_m.group(1)) if err_m else 0

    nf_m = re.search(r"'not_found':\s*(\d+)", output)
    not_found = int(nf_m.group(1)) if nf_m else 0

    # Также ищем: "Supabase error" или "ошибка" в логе
    log_errors = len(re.findall(r"\[ERROR\]", output))
    errors = max(errors, log_errors)

    return total, errors + not_found


def run_step(name, command, max_minutes, dry_run=False):
    """Запускает один шаг цепочки. Возвращает (success, output, duration, error_rate)."""
    log.info(f"▶ {name}")
    if dry_run:
        log.info(f"  [dry-run] {command}")
        return True, "", 0.0, 0.0

    start = time.time()
    logfile = os.path.join(WORKDIR, f"{name}.log")

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=max_minutes * 60,
            env={**os.environ},
        )
        duration = time.time() - start
        output = (result.stdout or "") + "\n" + (result.stderr or "")

        # Записываем в отдельный лог
        with open(logfile, "a") as f:
            f.write(f"\n{'='*60}\n{datetime.now().isoformat()} | pipeline run\n{'='*60}\n")
            f.write(output)

        if result.returncode != 0:
            log.warning(f"  {name}: exit code {result.returncode} ({duration:.0f}s)")
            return False, output, duration, 1.0

        # Парсим статистику
        total, errors = parse_stats_from_output(output)
        error_rate = errors / total if total and total > 0 else 0.0

        log.info(f"  {name}: OK ({duration:.0f}s, total={total}, errors={errors}, rate={error_rate:.0%})")
        return True, output, duration, error_rate

    except subprocess.TimeoutExpired:
        duration = time.time() - start
        log.error(f"  {name}: TIMEOUT after {max_minutes}min")
        return False, f"TIMEOUT after {max_minutes}min", duration, 1.0
    except Exception as e:
        duration = time.time() - start
        log.error(f"  {name}: EXCEPTION {e}")
        return False, str(e), duration, 1.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Не запускать, только показать план")
    parser.add_argument("--skip", type=str, default="", help="Пропустить шаги (через запятую)")
    args = parser.parse_args()

    skip = set(args.skip.split(",")) if args.skip else set()

    log.info(f"=== Pipeline start ({len(STEPS)} steps, skip={skip or 'none'}) ===")
    pipeline_start = time.time()

    results = []
    alerts = []

    for name, command, max_min, critical in STEPS:
        if name in skip:
            log.info(f"  {name}: SKIPPED")
            results.append((name, "skipped", 0, 0))
            continue

        success, output, duration, error_rate = run_step(name, command, max_min, args.dry_run)

        results.append((name, "ok" if success else "FAIL", duration, error_rate))

        # Алерт при >10% ошибок
        if error_rate > 0.10:
            msg = f"⚠ {name}: {error_rate:.0%} ошибок"
            alerts.append(msg)
            log.warning(msg)

        # Критический шаг упал — стоп
        if not success and critical:
            msg = f"🛑 Pipeline остановлен: {name} упал (critical)"
            alerts.append(msg)
            log.error(msg)
            break

    total_duration = time.time() - pipeline_start

    # Сводка
    ok_count = sum(1 for _, s, _, _ in results if s == "ok")
    fail_count = sum(1 for _, s, _, _ in results if s == "FAIL")
    skip_count = sum(1 for _, s, _, _ in results if s == "skipped")

    summary = f"Pipeline: {ok_count} ok, {fail_count} fail, {skip_count} skip ({total_duration:.0f}s)"
    log.info(f"=== {summary} ===")

    # Telegram: отправляем если есть алерты ИЛИ всё ок (краткая сводка)
    if alerts:
        tg_text = f"🔴 <b>Pipeline Alert</b>\n{chr(10).join(alerts)}\n\n{summary}"
        send_tg(tg_text)
    elif not args.dry_run:
        # Краткая сводка без алертов — только если были обработки
        if ok_count > 0:
            details = []
            for name, status, dur, rate in results:
                if status == "ok" and dur > 0:
                    details.append(f"  {name}: {dur:.0f}s")
            tg_text = f"✅ <b>Pipeline OK</b> ({total_duration:.0f}s)\n" + "\n".join(details[:5])
            send_tg(tg_text)

    if args.dry_run:
        log.info("(--dry-run: ничего не запущено)")


if __name__ == "__main__":
    main()
