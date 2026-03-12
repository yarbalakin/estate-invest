#!/usr/bin/env python3
"""
Пульс Estate Invest — Ежедневный AI-отчёт
Cron: 0 6 * * * (08:00 КЛД = 06:00 UTC)
Путь: /opt/torgi-proxy/pulse_estate.py
"""
import os
import csv
import io
import logging
import requests
from datetime import date, datetime, timedelta, timezone

import gspread
from google.oauth2.service_account import Credentials

# ── Логирование ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/opt/torgi-proxy/pulse_estate.log"),
    ],
)
log = logging.getLogger("pulse")

# ── Config ─────────────────────────────────────────────────────
SA_JSON        = "/opt/torgi-proxy/google-sa.json"
TG_TOKEN       = "8797777745:AAE6Rs7oyf-QqrXRuAXZot4RbTaXTTKTZE8"
TG_CHAT_ID     = "191260933"   # Ярослав (личка)
TG_GROUP_ID    = "-1003577129774"  # Канал "Пульс Estate Invest"
ANTHROPIC_KEY  = os.environ.get("ANTHROPIC_API_KEY", "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")

# Spreadsheet IDs
SS_LOTS    = "1Wji_7UYqIRmxbsd1Ob52NutSrKThd3m37fkXDFuBfPk"  # Монитор торгов — Лоты (VPS боты)
SS_TORGI   = "1Ulf_odOSRFcs4Ihi3waCo1Py_a0SgI3-FHlIKdCQvSU"  # Таблица торгов
SS_TORGI_GID = "1389523539"
SS_MONITOR = "1oTRqpqS5GIunhi26TO8X6quWR5wWIWoTe0LzFqEGrDs"  # Монитор объектов
SS_KASSA   = "1aRi5YLORBWDY5oU7hNo1XAWUoIvAM3ArxX7L2dbJHEc"  # Касса
SS_MAIN    = "1dWTjYF8sEc20SKeyl-e6PomBFq3VlfX-m8K2ZRopZJ0"  # Эстейт Инвест Учёт

# Bitrix24
B24_BASE = "https://estateinvest.bitrix24.ru/rest/1/qlmnwa8sza8pvx14"
B24_CATEGORY = 2  # Воронка "Регистрация"
B24_STAGES_WORK = {"C2:UC_OOYEBA", "C2:UC_TMTL7P", "C2:UC_0RH8PI",
                   "C2:UC_0BBGCA", "C2:UC_6G82ED", "C2:UC_M078EE"}
B24_STAGES_SIGN = {"C2:UC_KBB2A2", "C2:UC_6BXB4G", "C2:UC_EN4YLS",
                   "C2:UC_0GSQ0I", "C2:UC_8LYQCI"}

KLD = timezone(timedelta(hours=2))

_gc = None  # gspread client (lazy init)


# ── Helpers ────────────────────────────────────────────────────

def today_kld() -> date:
    return datetime.now(KLD).date()

def yesterday_kld() -> date:
    return today_kld() - timedelta(days=1)

def parse_date(s: str) -> date | None:
    s = str(s).strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def fmt_money(val) -> str:
    try:
        n = int(float(str(val).replace(" ", "").replace("\xa0", "").replace(",", ".")))
        return f"{n:,}".replace(",", " ") + " ₽"
    except Exception:
        return str(val)

def get_gc():
    global _gc
    if _gc is None:
        creds = Credentials.from_service_account_file(
            SA_JSON,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )
        _gc = gspread.authorize(creds)
    return _gc

def send_telegram(text: str, chat_id: str = TG_CHAT_ID):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    if len(text) > 4000:
        text = text[:3990] + "\n...[обрезано]"
    resp = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }, timeout=15)
    if not resp.ok:
        log.error("Telegram error (chat %s): %s", chat_id, resp.text)


# ── [АНАЛИТИКА] Монитор торгов — Лоты ─────────────────────────

def get_lots_data() -> dict:
    """Лоты, записанные VPS-ботами за последние 2 дня (сегодня + вчера)."""
    try:
        gc = get_gc()
        sh = gc.open_by_key(SS_LOTS)
        try:
            ws = sh.worksheet("Лоты")
        except gspread.WorksheetNotFound:
            ws = sh.sheet1
        raw = ws.get_all_values()
        if not raw:
            return {"total": 0, "discounted": 0, "cats": "—"}
        header = raw[0]
        log.info("Lots sheet headers: %s", header)

        # Ищем колонки без учёта регистра и пробелов
        def find_col(names: list[str], default: int) -> int:
            for name in names:
                for i, h in enumerate(header):
                    if h.strip().lower() == name.lower():
                        return i
            return default

        i_date = find_col(["dateAdded", "date_added", "date", "Дата", "added"], 1)
        i_cat  = find_col(["category", "Категория", "cat"], 2)
        i_disc = find_col(["discount", "Скидка", "disc"], 18)

        log.info("Lots columns: date=%d, cat=%d, disc=%d", i_date, i_cat, i_disc)

        # Фильтруем за последние 2 дня (вчера + сегодня) — VPS мог писать в любой момент
        cutoff = today_kld() - timedelta(days=1)
        recent_lots = []
        for r in raw[1:]:
            if len(r) <= i_date:
                continue
            d = parse_date(r[i_date])
            if d and d >= cutoff:
                recent_lots.append(r)

        log.info("Lots found in last 2 days: %d (date col sample: %s)",
                 len(recent_lots), raw[1][i_date] if len(raw) > 1 else "—")

        discounted = 0
        cats: dict[str, int] = {}
        for r in recent_lots:
            try:
                d = float(str(r[i_disc] if len(r) > i_disc else 0).replace(",", ".").replace("%", ""))
                if d >= 30:
                    discounted += 1
            except Exception:
                pass
            cat = str(r[i_cat] if len(r) > i_cat else "Прочее")
            cats[cat] = cats.get(cat, 0) + 1

        cats_str = ", ".join(f"{k} ({v})" for k, v in cats.items()) if cats else "—"
        return {"total": len(recent_lots), "discounted": discounted, "cats": cats_str}

    except Exception as e:
        log.error("lots_data error: %s", e)
        return {"total": "н/д", "discounted": "н/д", "cats": "н/д"}


# ── [ТОРГИ] Таблица торгов (публичный лист) ────────────────────

def get_torgi_data() -> dict:
    """Читаем таблицу торгов через CSV-экспорт."""
    url = (
        f"https://docs.google.com/spreadsheets/d/{SS_TORGI}"
        f"/export?format=csv&gid={SS_TORGI_GID}"
    )
    empty = {"today": [], "tomorrow": [], "app_deadline": [], "deposit_sum": 0}
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        if len(rows) < 2:
            return empty

        now = today_kld()
        tmrw = now + timedelta(days=1)

        today_trades, tomorrow_trades, app_deadline = [], [], []
        deposit_sum = 0.0

        for row in rows[1:]:
            if not any(row):
                continue

            # Ищем "заходим" в любой ячейке строки
            status_found = any("заходим" in cell.lower() for cell in row)
            if not status_found:
                continue

            # Название объекта — первые непустые ячейки (col A или B)
            name = (row[0] or row[1] if len(row) > 1 else row[0]).strip()[:60]

            # col H (idx 7) — дата окончания подачи заявок
            app_date = parse_date(row[7]) if len(row) > 7 else None
            # col I (idx 8) — дата торгов
            trade_date = parse_date(row[8]) if len(row) > 8 else None
            # col K (idx 10) — сумма задатка
            dep_raw = row[10].strip() if len(row) > 10 else ""

            if trade_date == now:
                today_trades.append(name)
            elif trade_date == tmrw:
                tomorrow_trades.append(name)

            if app_date in (now, tmrw):
                app_deadline.append(name)

            try:
                dep = float(dep_raw.replace(" ", "").replace("\xa0", "").replace(",", "."))
                deposit_sum += dep
            except Exception:
                pass

        return {
            "today": today_trades,
            "tomorrow": tomorrow_trades,
            "app_deadline": app_deadline,
            "deposit_sum": deposit_sum,
        }

    except Exception as e:
        log.error("torgi_data error: %s", e)
        return empty


# ── [ОБЪЕКТЫ] Монитор объектов + Монитор аренды ───────────────

def get_objects_data() -> dict:
    try:
        gc = get_gc()
        sh = gc.open_by_key(SS_MONITOR)

        # Лист "Монитор объектов" (gid=0) — статус в col C (idx 2)
        ws_obj = sh.get_worksheet(0)
        obj_data = ws_obj.get_all_values()

        realization = sale = done = 0
        for row in obj_data[2:]:  # пропускаем строки 1-2 (заголовки)
            if not any(row):
                continue
            status = row[2].strip().lower() if len(row) > 2 else ""
            if "реализац" in status:
                realization += 1
            elif "сбор" in status:
                sale += 1
            elif "завершен" in status or "продан" in status:
                done += 1

        # Лист "Монитор аренды":
        # idx0 — заголовки групп, idx1 — подзаголовки (Текущий АП, Загрузка...)
        # idx2 — итоговая строка со значениями, idx3+ — объекты
        ws_rent = sh.worksheet("Монитор аренды")
        rent_data = ws_rent.get_all_values()

        summary = rent_data[2] if len(rent_data) > 2 else []
        rent_ap   = summary[2].strip().replace("\xa0", " ") if len(summary) > 2  else "н/д"   # col C
        rent_load = summary[12].strip()                     if len(summary) > 12 else "н/д"   # col M

        # Объектов в аренде: строки с idx 3+, непустые
        rent_count = sum(1 for row in rent_data[3:] if any(c.strip() for c in row))

        return {
            "realization": realization,
            "sale": sale,
            "done": done,
            "rent_count": rent_count,
            "rent_ap": rent_ap,
            "rent_load": rent_load,
        }

    except Exception as e:
        log.error("objects_data error: %s", e)
        return {"realization": "н/д", "sale": "н/д", "done": "н/д",
                "rent_count": "н/д", "rent_ap": "н/д", "rent_load": "н/д"}


# ── [ИНВЕСТОРЫ] Битрикс24 ──────────────────────────────────────

def get_investors_data() -> dict:
    try:
        deals = _b24_all_deals()
        yest = yesterday_kld()

        new_yest = sum(
            1 for d in deals
            if d.get("STAGE_ID") == "C2:NEW"
            and _b24_date(d.get("DATE_CREATE", "")) == yest
        )
        in_work  = sum(1 for d in deals if d.get("STAGE_ID") in B24_STAGES_WORK)
        signing  = sum(1 for d in deals if d.get("STAGE_ID") in B24_STAGES_SIGN)
        won_all  = sum(1 for d in deals if d.get("STAGE_ID") == "C2:WON")
        won_week = sum(
            1 for d in deals
            if d.get("STAGE_ID") == "C2:WON"
            and _within_days(_b24_date(d.get("DATE_MODIFY", "")), 7)
        )

        return {"new_yest": new_yest, "in_work": in_work,
                "signing": signing, "won_all": won_all, "won_week": won_week}

    except Exception as e:
        log.error("investors_data error: %s", e)
        return {"new_yest": "н/д", "in_work": "н/д",
                "signing": "н/д", "won_all": "н/д", "won_week": "н/д"}

def _b24_all_deals() -> list:
    deals, start = [], 0
    while True:
        resp = requests.get(f"{B24_BASE}/crm.deal.list.json", params={
            "FILTER[CATEGORY_ID]": B24_CATEGORY,
            "SELECT[]": ["ID", "STAGE_ID", "DATE_CREATE", "DATE_MODIFY"],
            "start": start,
        }, timeout=20)
        data = resp.json()
        deals.extend(data.get("result", []))
        if data.get("next") is None:
            break
        start = data["next"]
    return deals

def _b24_date(s: str) -> date | None:
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return None

def _within_days(d: date | None, n: int) -> bool:
    return d is not None and (today_kld() - d).days <= n


# ── [ИНВЕСТОРЫ] Свободные средства на балансе ─────────────────

def get_svod_investors() -> dict:
    """Из 'Свод инвесторы': реальные инвесторы (взнос > 0) + свободные средства."""
    try:
        gc = get_gc()
        sh = gc.open_by_key(SS_MAIN)
        ws = sh.worksheet("Свод инвесторы")
        rows = ws.get_all_values()

        # Строка 0 (row 1 в gspread) — итоги, кол 20 = "ИТОГО остаток инвестора в рублях"
        row0 = rows[0] if rows else []
        free_funds = row0[20].strip().replace("\xa0", " ") if len(row0) > 20 else "н/д"

        # Строки с 3-й (0-indexed) — данные инвесторов, заголовки на строке 2
        # Взносы в колонках 2 ($), 3 (€), 4 (USDT), 5 (руб)
        def parse_num(s):
            try:
                return float(str(s).replace("\xa0", "").replace(" ", "").replace(",", "."))
            except Exception:
                return 0.0

        invested = 0
        for r in rows[3:]:
            name = r[1].strip() if len(r) > 1 else ""
            if not name:
                continue
            if any(parse_num(r[i]) > 0 for i in [2, 3, 4, 5] if len(r) > i):
                invested += 1

        log.info("Свод инвесторы: реальных %d, свободные средства: %s", invested, free_funds)
        return {"count": invested, "free_funds": free_funds or "н/д"}

    except Exception as e:
        log.error("svod_investors error: %s", e)
        return {"count": "н/д", "free_funds": "н/д"}


# ── [ИНВЕСТОРЫ] Движение средств из "Общая база" ─────────────

def _parse_money(s: str) -> float:
    """Парсинг денежной суммы из строки."""
    try:
        clean = str(s).replace(" ", "").replace("\xa0", "").replace(",", ".")
        clean = clean.replace("₽", "").replace("р.", "").replace("р", "").strip()
        return float(clean) if clean else 0.0
    except Exception:
        return 0.0

def get_investor_flows() -> dict:
    """Из 'Общая база': внесено/выведено за вчера и за текущий месяц.

    Структура листа (СТРУКТУРА_ДАННЫХ.md):
      col 0: №, 1: Инвестор, 2: Проверка, 3: Вид взноса, 4: Дата,
      5: Сумма, 6: Валюта взноса, 7: Сумма в рублях,
      ...
      17: Вид выплаты, 18: Дата выплаты, 19: Сумма выплаты,
      20: Валюта выплаты, 21: Сумма выплаты в руб.
    """
    empty = {"y_in": 0, "y_out": 0, "m_in": 0, "m_out": 0}
    try:
        gc = get_gc()
        sh = gc.open_by_key(SS_MAIN)
        ws = sh.worksheet("Общая база")
        data = ws.get_all_values()

        if not data:
            return empty

        # Логируем первую строку для верификации колонок
        log.info("Общая база headers: %s", [c[:20] for c in data[0][:22]])
        log.info("Общая база rows: %d", len(data) - 1)

        yest = yesterday_kld()
        now = today_kld()
        month_start = now.replace(day=1)

        y_in = y_out = m_in = m_out = 0.0

        for row in data[1:]:
            if len(row) < 8:
                continue

            # --- Внесение: дата в col 4, сумма в рублях в col 7 ---
            deposit_date = parse_date(row[4]) if row[4].strip() else None
            deposit_rub = _parse_money(row[7]) if len(row) > 7 else 0.0

            if deposit_date and deposit_rub > 0:
                if deposit_date == yest:
                    y_in += deposit_rub
                if deposit_date >= month_start:
                    m_in += deposit_rub

            # --- Выплата: дата в col 18, сумма в руб. в col 21 ---
            if len(row) > 21:
                payout_date = parse_date(row[18]) if row[18].strip() else None
                payout_rub = _parse_money(row[21])

                if payout_date and payout_rub > 0:
                    if payout_date == yest:
                        y_out += payout_rub
                    if payout_date >= month_start:
                        m_out += payout_rub

        log.info("Investor flows: y_in=%.0f y_out=%.0f m_in=%.0f m_out=%.0f",
                 y_in, y_out, m_in, m_out)
        return {"y_in": y_in, "y_out": y_out, "m_in": m_in, "m_out": m_out}

    except Exception as e:
        log.error("investor_flows error: %s", e)
        return empty


# ── [ФИНАНСЫ] Касса ────────────────────────────────────────────

def get_finance_data() -> dict:
    try:
        gc = get_gc()
        sh = gc.open_by_key(SS_KASSA)
        ws = sh.worksheet("Общ. касса")
        data = ws.get_all_values()

        # Иван: дата в col C (idx 2), остаток в col F (idx 5)
        ivan = _last_balance(data, date_col=2, balance_col=5)
        return {"ivan": ivan}

    except Exception as e:
        log.error("finance_data error: %s", e)
        return {"ivan": "н/д"}

def _last_balance(data: list, date_col: int, balance_col: int) -> str:
    """Последняя строка с датой → значение balance_col."""
    last = None
    for row in data:
        if max(date_col, balance_col) >= len(row):
            continue
        if parse_date(row[date_col]):
            val = row[balance_col].strip()
            if val:
                last = val
    return last or "н/д"


# ── [AI-СВОДКА] Anthropic Claude Haiku ────────────────────────

def get_ai_summary(report_text: str) -> str:
    if not ANTHROPIC_KEY:
        return "(нет ключа ANTHROPIC_API_KEY — установите env-переменную)"
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 600,
                "messages": [{
                    "role": "user",
                    "content": (
                        "Ты аналитик инвестиционной компании Estate Invest (Пермь/Калининград). "
                        "Компания выкупает недвижимость на торгах ниже рынка и реализует с прибылью. "
                        "На основе ежедневного отчёта дай 3–4 конкретные рекомендации: "
                        "что требует внимания сегодня, какие цифры отклоняются от нормы. "
                        "Будь краток. Формат: пронумерованный список без вступления.\n\n"
                        f"ОТЧЁТ:\n{report_text}"
                    )
                }]
            },
            timeout=30,
        )
        data = resp.json()
        if "content" not in data:
            log.error("AI summary bad response: %s", data)
            return f"AI-сводка недоступна: {data.get('error', {}).get('message', str(data))}"
        return data["content"][0]["text"]
    except Exception as e:
        log.error("AI summary error: %s", e)
        return "AI-сводка временно недоступна"


# ── Сборка отчёта ──────────────────────────────────────────────

def build_report(lots, torgi, objects, investors, finance, svod=None, flows=None) -> str:
    if svod is None:
        svod = {"count": "н/д", "free_funds": "н/д"}
    if flows is None:
        flows = {"y_in": 0, "y_out": 0, "m_in": 0, "m_out": 0}
    now_dt = datetime.now(KLD)
    d = now_dt.strftime("%d.%m.%Y")
    day = now_dt.strftime("%A")
    day_ru = {"Monday":"Понедельник","Tuesday":"Вторник","Wednesday":"Среда",
              "Thursday":"Четверг","Friday":"Пятница","Saturday":"Суббота","Sunday":"Воскресенье"}.get(day, day)
    months_ru = {1:"Январь",2:"Февраль",3:"Март",4:"Апрель",5:"Май",6:"Июнь",
                 7:"Июль",8:"Август",9:"Сентябрь",10:"Октябрь",11:"Ноябрь",12:"Декабрь"}
    now_month = months_ru.get(now_dt.month, str(now_dt.month))
    lines = [f"🏢 <b>ПУЛЬС ESTATE INVEST</b>", f"📅 {day_ru}, {d}", ""]

    # [АНАЛИТИКА]
    lines += [
        "🔍 <b>Мониторинг торгов</b>",
        f"├ Лотов найдено: <b>{lots['total']}</b>",
        f"├ Со скидкой ≥30%: <b>{lots['discounted']}</b>",
        f"└ Категории: {lots['cats']}",
        "",
    ]

    # [ТОРГИ]
    def fmt_list(lst): return ", ".join(lst) if lst else "—"
    lines += [
        "⚖️ <b>Торги</b>",
        f"├ Сегодня: <b>{len(torgi['today'])}</b> — {fmt_list(torgi['today'])}",
        f"├ Завтра: <b>{len(torgi['tomorrow'])}</b> — {fmt_list(torgi['tomorrow'])}",
        f"└ Заявки истекают: {fmt_list(torgi['app_deadline'])}",
    ]
    if torgi["deposit_sum"] > 0:
        lines.append(f"💰 Нужно задатков: <b>{fmt_money(torgi['deposit_sum'])}</b>")
    lines.append("")

    # [ОБЪЕКТЫ]
    lines += [
        "🏗️ <b>Объекты</b>",
        f"├ В реализации: <b>{objects['realization']}</b>",
        f"├ Сбор средств: <b>{objects['sale']}</b>",
        f"├ Завершено: <b>{objects['done']}</b>",
        f"├ В аренде: <b>{objects['rent_count']}</b> объектов",
        f"├ Арендный поток: <b>{objects['rent_ap']}</b> руб/мес",
        f"└ Загрузка: <b>{objects['rent_load']}</b>",
        "",
    ]

    # [ИНВЕСТОРЫ]
    lines += [
        "👥 <b>Инвесторы</b>",
        f"├ Новых анкет (вчера): <b>{investors['new_yest']}</b>",
        f"├ В работе: <b>{investors['in_work']}</b>",
        f"├ На подписании: <b>{investors['signing']}</b>",
        f"├ Новых за 7 дней: <b>{investors['won_week']}</b>",
        f"├ Всего инвесторов: <b>{svod['count']}</b>",
        f"├ Свободные средства: <b>{svod['free_funds']} ₽</b>",
    ]
    # Движение средств инвесторов
    if flows["y_in"] > 0 or flows["y_out"] > 0:
        lines.append(f"├ Вчера: внесено <b>{fmt_money(flows['y_in'])}</b>, выведено <b>{fmt_money(flows['y_out'])}</b>")
    else:
        lines.append("├ Вчера: движений не было")
    lines.append(f"└ {now_month}: внесено <b>{fmt_money(flows['m_in'])}</b>, выведено <b>{fmt_money(flows['m_out'])}</b>")
    lines.append("")

    # [ФИНАНСЫ]
    lines += [
        "💼 <b>Касса</b>",
        f"└ Остаток: <b>{finance['ivan']}</b>",
        "",
    ]

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────

def main():
    log.info("=== Пульс Estate Invest START ===")

    lots    = get_lots_data()
    torgi   = get_torgi_data()
    objects = get_objects_data()
    investors = get_investors_data()
    finance = get_finance_data()
    svod    = get_svod_investors()
    flows   = get_investor_flows()

    report = build_report(lots, torgi, objects, investors, finance, svod, flows)
    log.info("Отчёт собран:\n%s", report)

    ai = get_ai_summary(report)
    full = report + f"🤖 <b>AI-сводка</b>\n{ai}"

    send_telegram(full)
    if TG_GROUP_ID:
        send_telegram(full, chat_id=TG_GROUP_ID)
    log.info("=== Пульс Estate Invest DONE ===")


if __name__ == "__main__":
    main()
