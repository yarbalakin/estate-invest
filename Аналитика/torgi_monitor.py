#!/usr/bin/env python3
"""
Монитор торгов torgi.gov.ru — недвижимость Пермский край
Cron: каждые 4 часа. Новые лоты → оценка рынка → Telegram + Google Sheets.
"""
import requests
import json
import time
import re
import os
import logging
import statistics
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/opt/torgi-proxy/torgi_monitor.log"),
    ],
)
log = logging.getLogger("torgi")

# === Config ===
PROXY_URL = "http://127.0.0.1:8080/api/torgi"
PROXY_API_KEY = "ei-torgi-2026-mvp"
CAT_CODES = "2,3,4,5,7,8,10,11,47"
DYN_SUBJ_RF = "28"  # Пермский край
SEEN_FILE = "/opt/torgi-proxy/torgi_seen.json"

# ads-api.ru (оценка рынка)
ADS_API_USER = os.environ.get("ADS_API_USER", "yabalakin@yandex.ru")
ADS_API_TOKEN = os.environ.get("ADS_API_TOKEN", "de5f6b208f2348f909fa7c3eb8793d95")
ADS_API_URL = "https://ads-api.ru/main/api"
ADS_API_DELAY = 5  # секунд между запросами

# Telegram
TG_BOT_TOKEN = "8650381430:AAFKGNZbjQmhAd3ogse9gOWs7_2xoypuo-A"
TG_CHAT_PERSONAL = "191260933"
TG_CHAT_CHANNEL = "-1003759471621"  # @topparsing

# Маппинг категорий torgi → ads-api.ru category_id
# ads-api.ru category_id (числовые)
ADS_CATEGORY_MAP = {
    "Земля": 5,       # Земельные участки
    "Нежилое": 7,     # Коммерческая недвижимость
    "Гараж": 6,       # Гаражи и машиноместа
    "Квартира": 2,    # Квартиры
    "Дом": 4,         # Дома, дачи, коттеджи
    "Прочее": 7,      # fallback → коммерческая
}

# Фильтр biddType
SKIP_BIDD_TYPES = ["Реализация имущества должников"]


# === Дедупликация ===
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return {}


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f)


def clean_seen(seen, days=30):
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    return {k: v for k, v in seen.items() if v > cutoff}


# === Запрос лотов ===
def fetch_lots():
    try:
        r = requests.get(
            PROXY_URL,
            params={
                "catCode": CAT_CODES,
                "dynSubjRF": DYN_SUBJ_RF,
                "size": "100",
                "page": "0",
                "sort": "firstVersionPublicationDate,desc",
                "lotStatus": "PUBLISHED,APPLICATIONS_SUBMISSION",
                "enrich": "true",
            },
            headers={"X-API-Key": PROXY_API_KEY},
            timeout=120,
        )
        if r.status_code != 200:
            log.error(f"Proxy error: {r.status_code}")
            return []
        data = r.json()
        lots = data.get("content", [])
        log.info(f"Fetched {len(lots)} lots from torgi.gov.ru")
        return lots
    except Exception as e:
        log.error(f"Fetch error: {e}")
        return []


# === Парсинг лота ===
def parse_lot(lot):
    lot_id = str(lot.get("id", ""))
    chars = lot.get("characteristics", [])

    address = ""
    area = ""
    cadastral_number = ""

    for c in chars:
        code = c.get("code", "")
        cname = (c.get("name", "") or "").lower()
        val = c.get("characteristicValue")
        if isinstance(val, list):
            val = ", ".join(v.get("name", "") or v.get("value", "") or "" for v in val)
        elif isinstance(val, dict):
            val = val.get("name", "") or val.get("value", "") or json.dumps(val)
        val = str(val or "")

        if not address and code in ("Address", "addressFIAS") or any(
            w in cname for w in ("адрес", "местоположение", "местонахожден")
        ):
            address = val
        if not area and code in ("Square", "SquareZU", "SquareZU_project", "TotalArea") or "площадь" in cname:
            area = val
        if not cadastral_number and (code == "CadastralNumber" or "кадастровый номер" in cname):
            cadastral_number = val

    # Fallback: estateAddress
    estate_addr = lot.get("estateAddress", "")
    if estate_addr and (not address or address == "Российская Федерация" or len(address) < 10):
        address = estate_addr

    lot_name = lot.get("lotName", "") or ""
    lot_desc = lot.get("lotDescription", "") or ""
    combined = lot_name + " " + lot_desc

    # Парсинг адреса из описания
    if not address or address == "Российская Федерация" or len(address) < 10:
        patterns = [
            r"адрес\s*:\s*(.+?)(?:\s*\(|$)",
            r"(?:по адресу|расположенн?(?:ый|ая|ое|ых)\s+по\s+адресу)\s*:?\s*(.+?)(?:,\s*(?:собственник|принадлежащ|категори|общей площадью|площадью|\()|$)",
            r"(?:местоположение|местонахождение)\s*:?\s*(.+?)(?:,\s*(?:собственник|принадлежащ|категори|общей площадью|площадью)|$)",
        ]
        for pat in patterns:
            m = re.search(pat, combined, re.IGNORECASE)
            if m and len(m.group(1).strip()) > 10:
                address = m.group(1).strip()
                break

    # Парсинг кадастрового номера из описания
    if not cadastral_number:
        m = re.search(r"кад\.?\s*(?:номер|№)?\s*:?\s*(\d{2}:\d{2}:\d{6,7}:\d+)", combined, re.IGNORECASE)
        if m:
            cadastral_number = m.group(1)

    # Парсинг площади из описания
    if not area:
        m = re.search(r"(?:пл(?:ощад[ьи]ю?)?|общ\.?\s*пл)\.?\s*:?\s*([\d\s,.]+?)\s*(?:кв\.?\s*м|м2)", combined, re.IGNORECASE)
        if m:
            area = m.group(1).replace(" ", "").replace(",", ".")

    # Очистка адреса
    if address:
        address = re.sub(r"^Российская Федерация,?\s*", "", address, flags=re.IGNORECASE)
        address = re.sub(r"^край Пермский,?\s*", "Пермский край, ", address, flags=re.IGNORECASE)
        address = re.sub(r"^,\s*", "", address)
        if len(address) > 150:
            address = address[:150] + "..."

    # Цена и задаток
    price = lot.get("startPrice") or lot.get("priceMin") or 0
    deposit = lot.get("deposit") or lot.get("depositAmount") or 0

    # Даты
    bidd_end = lot.get("biddEndTime") or lot.get("auctionStartDate") or ""
    app_end = lot.get("applicationEndDate") or lot.get("biddEndTime") or ""

    def fmt_date(s):
        if not s:
            return "не указана"
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.strftime("%d.%m.%Y")
        except Exception:
            return s[:10] if len(s) >= 10 else s

    # biddType
    bidd_type_raw = lot.get("biddType")
    if isinstance(bidd_type_raw, dict):
        bidd_type = bidd_type_raw.get("name", "")
    else:
        bidd_type = str(bidd_type_raw or "")

    # Категория
    category = ""
    cat_obj = lot.get("category")
    if isinstance(cat_obj, dict) and cat_obj.get("name"):
        cn = cat_obj["name"].lower()
        if "жил" in cn:
            category = "Квартира"
        elif "зем" in cn:
            category = "Земля"
        elif "нежил" in cn:
            category = "Нежилое"
        elif "гараж" in cn:
            category = "Гараж"

    if not category:
        nl = lot_name.lower()
        if any(w in nl for w in ("квартир", "комнат")):
            category = "Квартира"
        elif any(w in nl for w in ("земельн", "участок")):
            category = "Земля"
        elif any(w in nl for w in ("гараж", "бокс")):
            category = "Гараж"
        elif any(w in nl for w in ("дом", "коттедж", "домовлад")):
            category = "Дом"
        elif any(w in nl for w in ("нежил", "здани", "помещен")):
            category = "Нежилое"
        elif "право" in nl and "аренд" in nl:
            category = "Земля"
        else:
            category = "Прочее"

    is_land = category == "Земля"

    # Площадь: числовое значение
    area_num = 0
    if area:
        try:
            area_num = float(str(area).replace(",", ".").replace(" ", ""))
        except ValueError:
            pass

    # Цена за единицу
    price_per_unit = ""
    if price > 0 and area_num > 0:
        if is_land:
            sotki = area_num / 100
            if sotki > 0:
                price_per_unit = f"{int(price / sotki):,} руб/сотка".replace(",", " ")
        else:
            price_per_unit = f"{int(price / area_num):,} руб/м2".replace(",", " ")

    # Площадь форматированная
    area_fmt = ""
    if area_num > 0:
        if is_land:
            sotki = area_num / 100
            if sotki >= 100:
                area_fmt = f"{area_num / 10000:.2f} га"
            else:
                area_fmt = f"{sotki:.1f} сот."
        else:
            area_fmt = f"{area_num:,.1f} кв.м".replace(",", " ")

    etp_url = lot.get("etpUrl", "") or ""
    torgi_url = f"https://torgi.gov.ru/new/public/lots/lot/{lot_id}"
    short_name = (lot_name[:120] + "...") if len(lot_name) > 120 else (lot_name or "Объект")

    return {
        "lotId": lot_id,
        "dateAdded": datetime.now().strftime("%Y-%m-%d"),
        "category": category,
        "name": short_name,
        "address": address,
        "area": area_fmt,
        "areaNum": area_num,
        "isLand": is_land,
        "price": price,
        "deposit": deposit,
        "cadastralNumber": cadastral_number,
        "auctionDate": fmt_date(bidd_end),
        "applicationEnd": fmt_date(app_end),
        "biddType": bidd_type,
        "pricePerUnit": price_per_unit,
        "etpUrl": etp_url,
        "status": lot.get("lotStatus", ""),
        "url": torgi_url,
    }


# === Извлечение города из адреса ===
def extract_city(address):
    if not address:
        return "Пермь"
    addr_lower = address.lower()
    # "г. Город" или "г.Город" или "город Город"
    m = re.search(r"(?:г\.\s*|город\s+)([А-ЯЁа-яё\-]+)", address)
    if m:
        return m.group(1)
    # Известные города Пермского края
    cities = [
        "Пермь", "Краснокамск", "Березники", "Соликамск", "Чайковский",
        "Лысьва", "Кунгур", "Чусовой", "Добрянка", "Чернушка",
        "Оса", "Верещагино", "Нытва", "Губаха", "Кизел",
        "Александровск", "Горнозаводск", "Очёр", "Суксун",
    ]
    for city in cities:
        if city.lower() in addr_lower:
            return city
    # Район → ищем на уровне района
    m = re.search(r"(\w+)\s+(?:район|р-н|муниципальн)", address, re.IGNORECASE)
    if m:
        district = m.group(1)
        # Для сельских районов ищем по названию района
        return district
    return "Пермь"


# === Поиск аналогов (ads-api.ru) ===
def fetch_analogs(parsed_lot):
    if not ADS_API_USER or not ADS_API_TOKEN:
        log.debug("ads-api.ru credentials not set, skipping market evaluation")
        return None

    category = parsed_lot["category"]
    ads_category = ADS_CATEGORY_MAP.get(category)
    if not ads_category:
        log.info(f"  ads-api: нет маппинга для категории '{category}', пропуск")
        return None

    area_num = parsed_lot["areaNum"]
    city = extract_city(parsed_lot["address"])
    log.info(f"  ads-api: ищу аналоги — {category}, г.{city}, площадь={area_num}")

    params = {
        "user": ADS_API_USER,
        "token": ADS_API_TOKEN,
        "category_id": ads_category,
        "city": city,
        "nedvigimost_type": "1",  # продажа
        "limit": "50",
        "sort": "desc",
    }

    # Фильтр по площади — на стороне клиента (API не поддерживает для всех категорий)
    # Передаём nedvigimost_type=1 (продажа) и person_type=1 (частные лица — чище данные)

    try:
        time.sleep(ADS_API_DELAY)
        r = requests.get(ADS_API_URL, params=params, timeout=30)
        if r.status_code != 200:
            log.error(f"ads-api.ru error: {r.status_code}")
            return None
        data = r.json()
        items = []
        if isinstance(data, dict) and "data" in data:
            items = data["data"]
        elif isinstance(data, list):
            items = data
        log.info(f"  ads-api: получено {len(items)} объявлений")
        return items if items else None
    except Exception as e:
        log.error(f"ads-api.ru exception: {e}")
        return None


# === Расчёт рыночной оценки ===
def calculate_market_price(analogs, parsed_lot):
    if not analogs or len(analogs) == 0:
        return None

    area_num = parsed_lot["areaNum"]
    is_land = parsed_lot["isLand"]
    lot_price = parsed_lot["price"]

    if area_num <= 0 or lot_price <= 0:
        log.info(f"  оценка: пропуск (площадь={area_num}, цена={lot_price})")
        return None

    # Площадь лота для фильтрации аналогов
    if is_land:
        lot_area_sotki = area_num / 100  # torgi.gov.ru хранит в м2, переводим в сотки
    else:
        lot_area_sotki = area_num  # для нежилого площадь в м2

    # Собираем цены за единицу (фильтруем по площади ±50%)
    unit_prices = []
    for a in analogs:
        a_price = a.get("price", 0)
        if not a_price or a_price <= 0:
            continue

        # Площадь аналога (ads-api: для земли в сотках, для остального в м2)
        a_area = 0
        a_params = a.get("params", {})
        if isinstance(a_params, dict):
            for key, val in a_params.items():
                if "площадь" in key.lower():
                    try:
                        a_area = float(str(val).replace(",", ".").replace(" ", ""))
                    except (ValueError, TypeError):
                        pass
                    if a_area > 0:
                        break

        if a_area <= 0:
            continue

        # Фильтр по площади ±50% (клиентская сторона)
        if lot_area_sotki > 0:
            if a_area < lot_area_sotki * 0.5 or a_area > lot_area_sotki * 1.5:
                continue

        if is_land:
            # ads-api возвращает площадь земли в сотках
            if a_area > 0:
                unit_prices.append(a_price / a_area)  # руб/сотка
        else:
            unit_prices.append(a_price / a_area)  # руб/м2

    if len(unit_prices) < 2:
        log.info(f"  оценка: мало аналогов с площадью ({len(unit_prices)} из {len(analogs)})")
        return None

    log.info(f"  оценка: {len(unit_prices)} аналогов с площадью из {len(analogs)} всего")

    # Убрать выбросы (IQR)
    unit_prices.sort()
    n = len(unit_prices)
    q1 = unit_prices[n // 4] if n >= 4 else unit_prices[0]
    q3 = unit_prices[(3 * n) // 4] if n >= 4 else unit_prices[-1]
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    filtered = [p for p in unit_prices if lower <= p <= upper]

    if len(filtered) < 2:
        filtered = unit_prices  # fallback

    median_unit = statistics.median(filtered)

    # Рыночная оценка
    if is_land:
        sotki = area_num / 100
        market_price = median_unit * sotki
        market_per_unit = f"{int(median_unit):,} руб/сотка".replace(",", " ")
    else:
        market_price = median_unit * area_num
        market_per_unit = f"{int(median_unit):,} руб/м2".replace(",", " ")

    # Скидка
    discount = ((market_price - lot_price) / market_price * 100) if market_price > 0 else 0

    # Confidence
    count = len(filtered)
    if count < 3:
        confidence = "низкая"
    elif count <= 5:
        confidence = "средняя"
    else:
        confidence = "высокая"

    result = {
        "marketPrice": int(market_price),
        "marketPricePerUnit": market_per_unit,
        "discount": round(discount, 1),
        "confidence": confidence,
        "analogsCount": count,
    }
    mp_fmt = f"{int(market_price):,}".replace(",", " ")
    log.info(f"  оценка: рынок ~{mp_fmt} руб, скидка {result['discount']}%, аналогов {count} ({confidence})")
    return result


# === Форматирование Telegram ===
def format_telegram(parsed, market=None):
    cat = parsed["category"].upper()
    bidd_type = parsed["biddType"]
    name = parsed["name"]
    price = parsed["price"]
    deposit = parsed["deposit"]
    address = parsed["address"]
    area = parsed["area"]
    cadastral = parsed["cadastralNumber"]
    price_per_unit = parsed["pricePerUnit"]
    app_end = parsed["applicationEnd"]
    auction_date = parsed["auctionDate"]
    torgi_url = parsed["url"]
    etp_url = parsed["etpUrl"]

    price_fmt = f"{int(price):,}".replace(",", " ") if price else "0"
    deposit_fmt = f"{int(deposit):,}".replace(",", " ") if deposit else "0"

    msg = f"<b>{cat}</b>"
    if bidd_type:
        msg += f" | {bidd_type}"
    msg += f"\n\n{name}\n\n"

    if price > 0:
        msg += f"Цена: <b>{price_fmt} руб</b>"
        if price_per_unit:
            msg += f" ({price_per_unit})"
        msg += "\n"
    else:
        msg += "Цена: <b>по результатам торгов</b>\n"

    if area:
        msg += f"Площадь: {area}\n"
    if address:
        msg += f"Адрес: {address}\n"
    if cadastral:
        msg += f"Кадастр: {cadastral}\n"

    # Блок оценки рынка
    if market:
        mp = f"{market['marketPrice']:,}".replace(",", " ")
        disc = market["discount"]

        if disc > 40:
            label = "Отличная скидка"
        elif disc > 20:
            label = "Хорошая скидка"
        elif disc > 10:
            label = "Средняя скидка"
        elif disc > 0:
            label = "Слабая скидка"
        else:
            label = "Выше рынка"

        msg += f"\n<b>--- ОЦЕНКА РЫНКА ---</b>\n"
        msg += f"Рыночная: ~{mp} руб ({market['marketPricePerUnit']})\n"
        msg += f"Скидка: <b>{disc}%</b> — {label}\n"
        msg += f"Аналогов: {market['analogsCount']} ({market['confidence']} точность)\n"

    msg += f"\nПодача заявок до: {app_end}\n"
    msg += f"Торги: {auction_date}\n"
    msg += f"\n<b>Задаток: {deposit_fmt + ' руб' if deposit > 0 else 'не указан'}</b>\n"
    msg += f'\n<a href="{torgi_url}">Карточка на torgi.gov.ru</a>'
    if etp_url:
        msg += f'\n<a href="{etp_url}">Перейти на ЭТП</a>'

    return msg


# === Telegram ===
def send_telegram(text, chat_id):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if r.status_code == 200:
            return True
        log.error(f"Telegram error: {r.status_code} {r.text[:200]}")
        if r.status_code == 429:
            retry_after = r.json().get("parameters", {}).get("retry_after", 5)
            time.sleep(retry_after)
        return False
    except Exception as e:
        log.error(f"Telegram exception: {e}")
        return False


# === Google Sheets (через Sheets API v4) ===
# TODO: добавить после решения с авторизацией (service account или OAuth)
def append_google_sheets(row):
    pass


# === Main ===
def main():
    log.info("=== Torgi Monitor start ===")

    lots = fetch_lots()
    if not lots:
        log.info("No lots fetched, exiting")
        return

    seen = load_seen()
    seen = clean_seen(seen)

    new_count = 0
    sent_count = 0
    first_run = len(seen) == 0

    for lot in lots:
        lot_id = str(lot.get("id", ""))
        if not lot_id:
            continue

        # Дедупликация
        if lot_id in seen:
            continue

        # Парсинг
        parsed = parse_lot(lot)

        # Фильтр: пропускаем арестованное имущество
        if any(skip in parsed["biddType"] for skip in SKIP_BIDD_TYPES):
            seen[lot_id] = datetime.now().isoformat()
            continue

        new_count += 1
        price_fmt = f"{int(parsed['price']):,}".replace(",", " ") if parsed["price"] else "0"
        log.info(f"[{new_count}] {parsed['category']} | {parsed['name'][:60]} | {price_fmt} руб")

        # Лимит на первый запуск (не спамить)
        if first_run and new_count > 10:
            seen[lot_id] = datetime.now().isoformat()
            continue

        # Оценка рынка (ads-api.ru)
        market = None
        analogs = fetch_analogs(parsed)
        if analogs:
            market = calculate_market_price(analogs, parsed)

        # Telegram
        msg = format_telegram(parsed, market)

        # Отправляем в личный чат и канал
        if send_telegram(msg, TG_CHAT_PERSONAL):
            sent_count += 1
        time.sleep(1)
        send_telegram(msg, TG_CHAT_CHANNEL)
        time.sleep(1)

        # Google Sheets
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

    save_seen(seen)

    log.info(f"=== Done: {new_count} new lots, {sent_count} messages sent ===")

    # Heartbeat если ничего нового
    if new_count == 0:
        send_telegram("Монитор торгов: проверка завершена, новых лотов нет.", TG_CHAT_PERSONAL)


if __name__ == "__main__":
    main()
