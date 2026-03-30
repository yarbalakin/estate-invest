#!/usr/bin/env python3
"""
sync_sheets_to_supabase.py — Синхронизация лотов из Google Sheets → Supabase.

Читает листы "Лоты" (torgi.gov.ru) и "ЕФРСБ" из Google Sheets,
конвертирует в формат Supabase и делает upsert по lot_id.

Запуск:
  python sync_sheets_to_supabase.py
"""

import os
import re
import sys
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from supabase import create_client

load_dotenv()

# === Конфиг ===
SA_KEY = "/Users/yaroslavbalakin/Downloads/powerful-hall-488221-t2-b83babe8f926.json"
SHEET_ID = "1Wji_7UYqIRmxbsd1Ob52NutSrKThd3m37fkXDFuBfPk"
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]


def get_sheets_service():
    creds = Credentials.from_service_account_file(
        SA_KEY, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    return build("sheets", "v4", credentials=creds)


def read_sheet(service, sheet_name: str) -> list[dict]:
    """Читает лист целиком, возвращает list of dicts."""
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"{sheet_name}!A:Z"
    ).execute()
    rows = result.get("values", [])
    if len(rows) < 2:
        return []
    headers = rows[0]
    data = []
    for row in rows[1:]:
        # Дополняем пустыми значениями если строка короче заголовков
        padded = row + [""] * (len(headers) - len(row))
        data.append(dict(zip(headers, padded)))
    return data


def parse_price(val: str) -> float:
    """Парсит цену из строки: '62475' или '62 475' или '62475.50'"""
    if not val:
        return 0.0
    cleaned = re.sub(r"[^\d.,]", "", val.replace("\xa0", "").replace(" ", ""))
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_area(val: str) -> tuple[float, str]:
    """Парсит площадь: '44.2 m2' или '14.9 сот.' или '1.8 га' → (число, единица)"""
    if not val:
        return 0.0, "m2"
    val_lower = val.lower().strip()
    # Извлекаем число
    m = re.search(r"([\d.,]+)", val_lower)
    if not m:
        return 0.0, "m2"
    try:
        num = float(m.group(1).replace(",", "."))
    except ValueError:
        return 0.0, "m2"
    # Определяем единицу
    if "га" in val_lower or "ha" in val_lower:
        return num, "ha"
    elif "сот" in val_lower:
        return num, "sotka"
    else:
        return num, "m2"


def detect_property_type(category: str, name: str) -> str:
    """Определяет тип объекта."""
    cat = (category or "").lower()
    nm = (name or "").lower()
    text = cat + " " + nm

    if "нежил" in cat:
        return "commercial"
    if any(w in cat for w in ("квартир", "комнат", "жил")):
        return "apartment"
    if "дом" in cat and "домовлад" not in cat:
        return "house"
    if any(w in cat for w in ("земл", "участ")):
        return "land"
    if any(w in cat for w in ("гараж", "здани", "помещен", "сооружен")):
        return "commercial"

    # Фоллбэк по названию
    if any(w in nm for w in ("квартир", "комнат")):
        return "apartment"
    if any(w in nm for w in ("земельн", "участ")):
        return "land"
    if "дом" in nm and "домовлад" not in nm:
        return "house"

    return "commercial"


def torgi_row_to_supabase(row: dict) -> dict:
    """Конвертирует строку из листа 'Лоты' в формат Supabase."""
    area_num, area_unit = parse_area(row.get("area", ""))
    return {
        "lot_id": row.get("lotId", ""),
        "source": "torgi",
        "property_type": detect_property_type(row.get("category", ""), row.get("name", "")),
        "date_added": row.get("dateAdded", ""),
        "name": row.get("name", ""),
        "category": row.get("category", ""),
        "address": row.get("address", ""),
        "area": area_num,
        "area_unit": area_unit,
        "price": parse_price(row.get("price", "")),
        "deposit": parse_price(row.get("deposit", "")),
        "cadastral_number": row.get("cadastralNumber", ""),
        "auction_date": row.get("auctionDate", ""),
        "application_end": row.get("applicationEnd", ""),
        "bidd_type": row.get("biddType", ""),
        "price_per_unit": row.get("pricePerUnit", ""),
        "etp_url": row.get("etpUrl", ""),
        "status": row.get("status", "") or "PUBLISHED",
        "url": row.get("url", ""),
    }


def efrsb_row_to_supabase(row: dict) -> dict:
    """Конвертирует строку из листа 'ЕФРСБ' в формат Supabase."""
    area_num, area_unit = parse_area(row.get("area", ""))
    # Парсим дату — ЕФРСБ формат "10.03.2026 16:00" → "2026-03-10"
    date_raw = row.get("dateAdded", "")
    date_added = ""
    if date_raw:
        m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", date_raw)
        if m:
            date_added = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        else:
            date_added = date_raw[:10]

    # Парсим должника
    debtor_raw = row.get("debtor", "")

    return {
        "lot_id": row.get("lotId", ""),
        "source": "efrsb",
        "property_type": detect_property_type(row.get("category", ""), row.get("name", "")),
        "date_added": date_added,
        "name": row.get("name", ""),
        "category": row.get("category", ""),
        "address": row.get("address", ""),
        "area": area_num,
        "area_unit": area_unit,
        "price": parse_price(row.get("price", "")),
        "deposit": parse_price(row.get("deposit", "")),
        "cadastral_number": row.get("cadastralNumber", ""),
        "auction_date": row.get("auctionDate", ""),
        "application_end": row.get("applicationEnd", ""),
        "bidd_type": row.get("biddType", ""),
        "etp_url": row.get("etpUrl", ""),
        "status": row.get("status", "") or "PUBLISHED",
        "url": row.get("url", ""),
        "debtor_name": debtor_raw[:200] if debtor_raw else None,
        "bankruptcy_case": row.get("legalCase", "") or None,
    }


def upsert_batch(sb, records: list[dict], batch_size: int = 50):
    """Upsert записей в Supabase батчами."""
    total = len(records)
    ok = 0
    errors = 0
    for i in range(0, total, batch_size):
        batch = records[i:i + batch_size]
        try:
            sb.table("properties").upsert(
                batch, on_conflict="lot_id"
            ).execute()
            ok += len(batch)
            print(f"  [{ok}/{total}] upserted")
        except Exception as e:
            errors += len(batch)
            print(f"  ОШИБКА батч {i}-{i+len(batch)}: {e}")
    return ok, errors


def main():
    print("=== Синхронизация Google Sheets → Supabase ===\n")

    # 1. Читаем Google Sheets
    print("Подключаюсь к Google Sheets...")
    service = get_sheets_service()

    print("Читаю лист 'Лоты'...")
    torgi_rows = read_sheet(service, "Лоты")
    print(f"  Найдено: {len(torgi_rows)} строк")

    print("Читаю лист 'ЕФРСБ'...")
    efrsb_rows = read_sheet(service, "ЕФРСБ")
    print(f"  Найдено: {len(efrsb_rows)} строк")

    # 2. Конвертируем
    print("\nКонвертирую в формат Supabase...")
    torgi_records = []
    for row in torgi_rows:
        lot_id = row.get("lotId", "").strip()
        if not lot_id:
            continue
        torgi_records.append(torgi_row_to_supabase(row))

    efrsb_records = []
    for row in efrsb_rows:
        lot_id = row.get("lotId", "").strip()
        if not lot_id:
            continue
        efrsb_records.append(efrsb_row_to_supabase(row))

    print(f"  Торги: {len(torgi_records)} записей")
    print(f"  ЕФРСБ: {len(efrsb_records)} записей")

    # 3. Upsert в Supabase
    print("\nПодключаюсь к Supabase...")
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("\nUpsert торгов...")
    ok1, err1 = upsert_batch(sb, torgi_records)

    print("\nUpsert ЕФРСБ...")
    ok2, err2 = upsert_batch(sb, efrsb_records)

    # 4. Итог
    print("\n" + "=" * 50)
    print(f"ИТОГО:")
    print(f"  Торги:  {ok1} ok / {err1} ошибок")
    print(f"  ЕФРСБ:  {ok2} ok / {err2} ошибок")
    print(f"  Всего в базе: {ok1 + ok2} записей")

    # 5. Проверка
    count = sb.table("properties").select("lot_id", count="exact").execute()
    print(f"\nВ Supabase сейчас: {count.count} лотов")


if __name__ == "__main__":
    main()
