#!/usr/bin/env python3
"""
Экспорт данных реализации → CSV для оценщика.
Исключает: вознаграждение агента, цену продажи мин/макс.
Запустить: python3 export_to_gsheets.py
"""
import os, sys, csv, datetime, time
sys.path.insert(0, os.path.dirname(__file__))

from generate_svodka import (
    load_monitor, load_calls, load_estate_objects,
    parse_existing_html, merge_data
)
import google.oauth2.service_account
import googleapiclient.discovery

KEY_PATH = os.path.expanduser("~/Downloads/powerful-hall-488221-t2-b83babe8f926.json")
if not os.path.exists(KEY_PATH):
    KEY_PATH = os.path.join(os.path.dirname(__file__),
                            "powerful-hall-488221-t2-b83babe8f926.json")

EXCLUDE_IPS   = {4, 7, 8, 9, 10, 11, 12, 13, 31, 70, 73, 75, 119}
FORCE_INCLUDE = {58, 65, 88, 91, 92}  # 91=Добрянка, 92=Нытва (статус "сбор средств")

HEADERS = [
    "ИП №", "Адрес", "Город", "Тип объекта", "Площадь",
    "Кадастровый номер", "Цена покупки, руб",
    "Ссылка на Авито", "Нюансы / Комментарии",
]


def build_service():
    creds = google.oauth2.service_account.Credentials.from_service_account_file(
        KEY_PATH, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    return googleapiclient.discovery.build("sheets", "v4", credentials=creds)


def fmt_buy(val):
    try:
        return f"{int(val):,}".replace(",", " ") if val else ""
    except Exception:
        return str(val) if val else ""


def main():
    print("Загружаю данные из Google Sheets...")
    for attempt in range(3):
        try:
            svc = build_service()
            monitor = load_monitor(svc)
            calls   = load_calls(svc)
            estate  = load_estate_objects(svc)
            break
        except Exception as e:
            print(f"  Попытка {attempt+1}/3 — ошибка: {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                raise

    static  = parse_existing_html("реализация-сводка.html")
    objects = merge_data(monitor, calls, estate, static)

    rieltory = sorted(
        [o for o in objects
         if ("реализация" in o.get("status", "").lower() or o["ip_num"] in FORCE_INCLUDE)
         and o["ip_num"] not in EXCLUDE_IPS],
        key=lambda x: x["ip_num"]
    )
    print(f"  → {len(rieltory)} объектов")

    rows = [HEADERS]
    for o in rieltory:
        avito = (o.get("avito_links") or [])
        rows.append([
            f"ИП {o['ip_num']}",
            o.get("address") or o.get("name", ""),
            o.get("city", ""),
            o.get("type", ""),
            o.get("area", ""),
            o.get("cadastral", ""),
            fmt_buy(o.get("buy")),
            avito[0] if avito else "",
            o.get("nyuansy") or "",
        ])

    date_str  = datetime.date.today().strftime("%Y-%m-%d")
    csv_path  = os.path.join(os.path.dirname(__file__), f"оценка-объектов-{date_str}.csv")

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(rows)

    print(f"\n✅ Файл сохранён:\n   {csv_path}")
    print(f"\nКак открыть в Google Таблицах:")
    print("  1. sheets.google.com → «+» Создать таблицу")
    print("  2. Файл → Импортировать → Загрузить файл")
    print(f"  3. Выбрать файл выше, разделитель — запятая")

    return csv_path


if __name__ == "__main__":
    main()
