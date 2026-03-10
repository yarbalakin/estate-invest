"""
torgi_monitor_patch.py — Патч для интеграции PropertyCard в torgi_monitor.py

Этот файл содержит изменения для torgi_monitor.py на VPS.
После проверки — применить через SSH.

Что добавляется:
1. Импорт property_card, db, geocoder, cadastral
2. Функция enrich_card() — обогащение карточки из всех источников
3. Обновлённый main() — создаёт PropertyCard и сохраняет в Supabase
"""

# ============================================================
# 1. ДОБАВИТЬ В НАЧАЛО ФАЙЛА (после существующих импортов)
# ============================================================

IMPORTS_PATCH = """
# === PropertyCard integration ===
from property_card import PropertyCard
import db as supabase_db
import geocoder as geo
import cadastral as cad
"""

# ============================================================
# 2. ДОБАВИТЬ НОВУЮ ФУНКЦИЮ (после calculate_market_price)
# ============================================================

ENRICH_FUNCTION = """
# === Обогащение PropertyCard ===
def enrich_card(card):
    \"\"\"Обогащает PropertyCard из внешних источников.

    Порядок:
      1. DaData (геокодирование) — заполняет lat, lon, addressStd, district
      2. НСПД/PKK (кадастр) — заполняет cadastralValue, cadastralArea, ВРИ
    \"\"\"
    # 1. Геокодирование (DaData)
    try:
        if geo.enrich_card(card):
            log.info(f"  DaData: координаты ({card.lat}, {card.lon}), район: {card.district}")
            supabase_db.log_enrichment(card.lotId, "dadata", "success")
        else:
            log.info(f"  DaData: не удалось геокодировать")
            supabase_db.log_enrichment(card.lotId, "dadata", "skipped")
    except Exception as e:
        log.error(f"  DaData error: {e}")
        supabase_db.log_enrichment(card.lotId, "dadata", "error", error=str(e))

    # 2. Кадастр (НСПД/PKK)
    try:
        if cad.enrich_card(card):
            cv = f"{int(card.cadastralValue):,}".replace(",", " ") if card.cadastralValue else "нет"
            log.info(f"  Кадастр: стоимость {cv} руб, ВРИ: {card.cadastralPermittedUse or 'нет'}")
            supabase_db.log_enrichment(card.lotId, "nspd", "success")
        else:
            log.info(f"  Кадастр: нет данных")
            supabase_db.log_enrichment(card.lotId, "nspd", "skipped")
    except Exception as e:
        log.error(f"  Кадастр error: {e}")
        supabase_db.log_enrichment(card.lotId, "nspd", "error", error=str(e))
"""

# ============================================================
# 3. ОБНОВЛЁННЫЙ ЦИКЛ В main() — заменить участок после parse_lot()
# ============================================================

MAIN_LOOP_PATCH = """
        # --- PropertyCard ---
        card = PropertyCard.from_parsed_lot(parsed)

        # Оценка рынка (ads-api.ru)
        market = None
        analogs = fetch_analogs(parsed)
        if analogs:
            market = calculate_market_price(analogs, parsed)

        # Записать оценку в карточку
        if market:
            card.marketPrice = market["marketPrice"]
            card.marketPricePerUnit = market.get("marketPricePerUnit")
            card.discount = market["discount"]
            card.confidence = market["confidence"]
            card.analogsCount = market["analogsCount"]

        # Обогащение из внешних источников
        enrich_card(card)

        # Сохранить в Supabase
        try:
            supabase_db.upsert_property(card)
        except Exception as e:
            log.error(f"  Supabase upsert error: {e}")

        # Telegram (без изменений)
        msg = format_telegram(parsed, market)

        if send_telegram(msg, TG_CHAT_PERSONAL):
            sent_count += 1
        time.sleep(1)
        send_telegram(msg, TG_CHAT_CHANNEL)
        time.sleep(1)

        # Google Sheets (оставляем как было)
        row = {
            "lotId": parsed["lotId"],
            "dateAdded": parsed["dateAdded"],
            "category": parsed["category"],
            "name": parsed["name"],
            "address": parsed["address"],
            "area": parsed["area"],
            "price": str(parsed["price"]),
            "deposit": str(parsed["deposit"]),
            "cadastralNumber": parsed["cadastralNumber"],
            "auctionDate": parsed["auctionDate"],
            "applicationEnd": parsed["applicationEnd"],
            "biddType": parsed["biddType"],
            "pricePerUnit": parsed["pricePerUnit"],
            "etpUrl": parsed["etpUrl"],
            "status": parsed["status"],
            "url": parsed["url"],
        }
        if market:
            row["marketPrice"] = str(market["marketPrice"])
            row["marketPricePerUnit"] = market["marketPricePerUnit"]
            row["discount"] = str(market["discount"])
            row["confidence"] = market["confidence"]
            row["analogsCount"] = str(market["analogsCount"])

        append_google_sheets(row)

        seen[lot_id] = datetime.now().isoformat()
"""

# ============================================================
# Инструкции по применению
# ============================================================

print("""
=== Инструкция по применению патча ===

1. Скопировать на VPS файлы:
   - property_card.py
   - db.py
   - geocoder.py
   - cadastral.py

2. Установить зависимости на VPS:
   pip install supabase

3. Установить переменные окружения на VPS:
   export SUPABASE_URL="https://eeahxalvnvbroswzyfjx.supabase.co"
   export SUPABASE_KEY="<anon key>"
   export DADATA_TOKEN="<token>"
   export DADATA_SECRET="<secret>"

4. В torgi_monitor.py:
   a) Добавить импорты (после строки 16)
   b) Добавить функцию enrich_card() (после строки 601)
   c) Заменить участок main() (строки 783-827) на обновлённый

5. Создать таблицы в Supabase SQL Editor:
   - Скопировать CREATE_TABLES_SQL из db.py
   - Вставить в SQL Editor → Run

6. Тестировать:
   python3 torgi_monitor.py
""")
