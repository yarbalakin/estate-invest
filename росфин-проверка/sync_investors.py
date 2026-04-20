#!/usr/bin/env python3
"""
Синхронизация списка инвесторов на VPS.
Запуск с Mac: python3 sync_investors.py

Читает инвесторов из Google Sheets и заливает JSON на сервер.
"""

import json, os, sys, subprocess
from datetime import datetime

KEY_FILE       = os.path.expanduser("~/Downloads/powerful-hall-488221-t2-b83babe8f926.json")
SPREADSHEET_ID = "1dWTjYF8sEc20SKeyl-e6PomBFq3VlfX-m8K2ZRopZJ0"
SHEET_NAME     = "Инвесторы"
VPS            = "root@213.108.21.37"
REMOTE_PATH    = "/opt/fedsfm/investors.json"
LOCAL_TMP      = "/tmp/investors_sync.json"

COL_FIO_SHORT    = 1
COL_PHONE        = 2
COL_EMAIL        = 3
COL_TG           = 4
COL_FIO_FULL     = 15
COL_BIRTH        = 17
COL_PASSPORT     = 19
COL_PASSPORT_DATE= 20
COL_PASSPORT_BY  = 21
COL_PASSPORT_CODE= 22

def get_cell(row, idx):
    try: return row[idx].strip()
    except: return ""

def fetch_investors():
    import google.oauth2.service_account as sa
    from googleapiclient.discovery import build
    creds = sa.Credentials.from_service_account_file(
        KEY_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    svc = build("sheets", "v4", credentials=creds)
    result = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"{SHEET_NAME}!A:Z").execute()
    rows = result.get("values", [])
    investors = []
    for row in rows[2:]:
        fio = get_cell(row, COL_FIO_FULL) or get_cell(row, COL_FIO_SHORT)
        if not fio: continue
        investors.append({
            "fio":          fio,
            "birth_str":    get_cell(row, COL_BIRTH),
            "phone":        get_cell(row, COL_PHONE),
            "email":        get_cell(row, COL_EMAIL),
            "tg":           get_cell(row, COL_TG),
            "passport":     get_cell(row, COL_PASSPORT),
            "passport_date":get_cell(row, COL_PASSPORT_DATE),
            "passport_by":  get_cell(row, COL_PASSPORT_BY),
            "passport_code":get_cell(row, COL_PASSPORT_CODE),
        })
    return investors

def main():
    print("Загружаем инвесторов из Google Sheets...")
    investors = fetch_investors()
    print(f"  Получено: {len(investors)} инвесторов")

    payload = {"updated": datetime.now().isoformat(), "investors": investors}
    with open(LOCAL_TMP, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    print(f"Загружаем на сервер {VPS}:{REMOTE_PATH}...")
    r = subprocess.run(["scp", LOCAL_TMP, f"{VPS}:{REMOTE_PATH}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("Ошибка SCP:", r.stderr)
        sys.exit(1)

    print(f"Готово. {len(investors)} инвесторов залито на сервер.")

if __name__ == "__main__":
    main()
