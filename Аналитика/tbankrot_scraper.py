#!/usr/bin/env python3
"""
Скрапер tbankrot.ru — Пермский край, недвижимость.
Сравнение с нашими данными из Google Sheets.

Пагинация через ?page=N (HTML), фильтры в URL.
~193 страницы x 4 лота = ~772 лота, ~16 мин.

Использование:
    python tbankrot_scraper.py                      # листинг + сравнение
    python tbankrot_scraper.py --detail             # + карточки (долго)
    python tbankrot_scraper.py --detail --limit 50  # первые 50 карточек
    python tbankrot_scraper.py --no-compare         # без сравнения
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import signal
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

BASE_URL = "https://tbankrot.ru"

TBANKROT_REGIONS = {
    "perm": {"name": "Пермский край", "region_id": "51", "tg_channel": "-1003759471621"},
    "kaliningrad": {"name": "Калининградская область", "region_id": "21", "tg_channel": "-1003759471621"},
    "bryansk": {"name": "Брянская область", "region_id": "9", "tg_channel": "-5200571061"},
}

# По умолчанию Пермь, переопределяется через --region
_REGION_KEY = "perm"
LISTING_URL = BASE_URL + "/?page={page}&region[]={region_id}&apId=2&parent_cat[]=2"

GSHEETS_ID = "1Wji_7UYqIRmxbsd1Ob52NutSrKThd3m37fkXDFuBfPk"
GOOGLE_SA_JSON = "/opt/torgi-proxy/google-sa.json"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHANNEL_ID = os.environ.get("TG_CHANNEL_ID", "")
TG_NOTIFY_TOKEN = os.environ.get("TG_NOTIFY_TOKEN", "")
TG_NOTIFY_CHAT = os.environ.get("TG_NOTIFY_CHAT", "")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) "
    "Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]

DELAY_PAGE = (3, 7)           # между страницами листинга
DELAY_DETAIL = (3, 7)         # между карточками
BATCH_SIZE = 50               # пауза каждые N карточек
BATCH_PAUSE = 300             # 5 минут
MAX_RETRIES = 3
MAX_EMPTY_PAGES = 3           # стоп после N пустых страниц подряд

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tbankrot")

_interrupted = False


def _handle_sigint(sig, frame):
    global _interrupted
    _interrupted = True
    log.warning("Ctrl+C — сохраняю собранные данные...")


signal.signal(signal.SIGINT, _handle_sigint)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

class SafeClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Referer": BASE_URL + "/",
        })
        self._rotate_ua()
        try:
            self.session.get(BASE_URL, timeout=15)
            time.sleep(2)
        except Exception:
            pass

    def _rotate_ua(self):
        self.session.headers["User-Agent"] = random.choice(USER_AGENTS)

    def get(self, url, delay_range=None):
        for attempt in range(MAX_RETRIES):
            self._rotate_ua()
            try:
                resp = self.session.get(url, timeout=30)
                if resp.status_code in (429, 503):
                    wait = (2 ** attempt) * 10
                    log.warning(f"HTTP {resp.status_code}, жду {wait}с...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                if delay_range:
                    time.sleep(random.uniform(*delay_range))
                return resp
            except requests.RequestException as e:
                wait = (2 ** attempt) * 5
                log.warning(f"Ошибка (попытка {attempt + 1}): {e}")
                time.sleep(wait)
        return None


# ---------------------------------------------------------------------------
# Парсинг
# ---------------------------------------------------------------------------

def parse_price(text):
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.]", "", text.strip()).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_lots_html(html):
    """Парсинг div.lot из HTML страницы."""
    soup = BeautifulSoup(html, "html.parser")
    lots = []

    for lot_div in soup.find_all("div", class_="lot"):
        lot_id = lot_div.get("data-id", "")
        if not lot_id:
            link = lot_div.find("a", class_="lot_num")
            if link:
                m = re.search(r"id=(\d+)", link.get("href", ""))
                lot_id = m.group(1) if m else ""
        if not lot_id:
            continue

        lot = {
            "id": lot_id,
            "url": f"{BASE_URL}/item?id={lot_id}",
            "name": "",
            "price": None,
            "price_str": "",
            "section": "",
            "area": "",
            "cadastral": "",
            "address": "",
            "auction_date": "",
            "deadline": "",
            "debtor": "",
            "etp_url": "",
            "discount": "",
            "date_posted": "",
        }

        # Название
        title_link = (
            lot_div.select_one("div.lot_description p.lot_title a")
            or lot_div.select_one("p.lot_title a")
        )
        if title_link:
            lot["name"] = title_link.get_text(strip=True)[:200]

        # Описание
        desc_div = lot_div.select_one("div.lot_description div.text")
        desc_text = desc_div.get_text(strip=True) if desc_div else ""

        # Кадастровый номер
        cad = re.search(r"\d{2}:\d{2}:\d{5,7}:\d+", desc_text)
        if cad:
            lot["cadastral"] = cad.group(0)

        # Площадь
        area_m = re.search(r"Площадь[:\s]*([\d\s,.+/-]+)", desc_text, re.I)
        if area_m:
            lot["area"] = area_m.group(0).strip()[:50]

        # Цена
        price_el = lot_div.select_one("div.current_price > span")
        if price_el:
            lot["price_str"] = price_el.get_text(strip=True)
            lot["price"] = parse_price(lot["price_str"])

        # Даты — ищем все div с class содержащим "date" внутри inline_dates
        dates_container = lot_div.select_one("div.inline_dates")
        if dates_container:
            for dd in dates_container.find_all("div", class_=lambda c: c and "date" in c):
                title = dd.get("title", "")
                span = dd.find("span")
                text = span.get_text(strip=True) if span else ""
                tl = title.lower()
                if "заявок" in tl or "окончание этапа" in tl or "окончание приема" in tl:
                    m = re.search(r"(\d{2}\.\d{2}\.\d{2,4})", title)
                    if m:
                        lot["deadline"] = m.group(1)
                elif "торгов" in tl or "начало" in tl:
                    lot["auction_date"] = text

        # Секция
        full_text = lot_div.get_text(separator=" ", strip=True).lower()
        if "торгигов" in full_text or "torgi.gov" in full_text:
            lot["section"] = "TorgiGov"
        elif "залог" in full_text:
            lot["section"] = "Залог"
        elif "коммерч" in full_text:
            lot["section"] = "Коммерческое"
        else:
            lot["section"] = "Банкротство"

        # Должник
        debtor_el = lot_div.select_one("div.lot_debtor")
        if debtor_el:
            lot["debtor"] = debtor_el.get_text(strip=True)[:150]

        # Дата размещения
        created_el = lot_div.select_one("div.lot_created")
        if created_el:
            lot["date_posted"] = created_el.get_text(strip=True)

        lots.append(lot)

    return lots


def scrape_listing(client):
    """Собрать все лоты через HTML-пагинацию."""
    log.info("Начинаю сбор лотов (HTML-пагинация)...")

    all_lots = []
    empty_streak = 0
    page = 0

    while not _interrupted:
        page += 1
        url = LISTING_URL.format(page=page)
        resp = client.get(url, delay_range=DELAY_PAGE)

        if not resp:
            empty_streak += 1
            if empty_streak >= MAX_EMPTY_PAGES:
                log.info(f"{MAX_EMPTY_PAGES} ошибок подряд, завершаю")
                break
            continue

        page_lots = parse_lots_html(resp.text)

        if not page_lots:
            empty_streak += 1
            if empty_streak >= MAX_EMPTY_PAGES:
                log.info(f"Пустые страницы, последняя: {page}. Завершаю.")
                break
            continue

        empty_streak = 0
        existing_ids = {l["id"] for l in all_lots}
        new = [l for l in page_lots if l["id"] not in existing_ids]
        all_lots.extend(new)

        if page % 10 == 0 or page <= 3:
            log.info(f"Стр. {page}: +{len(new)}, всего {len(all_lots)}")

    log.info(f"Сбор завершён: {len(all_lots)} лотов за {page - 1} стр.")
    return all_lots


# ---------------------------------------------------------------------------
# Детализация карточек
# ---------------------------------------------------------------------------

def parse_detail_page(html, lot):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n", strip=True)

    cad = re.search(r"\d{2}:\d{2}:\d{5,7}:\d+", text)
    if cad:
        lot["cadastral"] = cad.group(0)

    addr_m = re.search(r"(?:Адрес|Местоположение)[:\s]*([^\n]{10,200})", text, re.I)
    if addr_m:
        lot["address"] = addr_m.group(1).strip().rstrip(",.")

    if not lot["address"]:
        for line in text.split("\n"):
            if re.search(r"(край|область|округ|район|город|улица|ул\.)", line, re.I):
                if 15 < len(line) < 250:
                    lot["address"] = line.strip()
                    break

    if not lot["area"]:
        area_m = re.search(
            r"(?:Площадь)[:\s]*([\d\s,.+/-]+)\s*(м²|кв\.?\s*м|сот|га)",
            text, re.I,
        )
        if area_m:
            lot["area"] = area_m.group(0).strip()

    trade_m = re.search(
        r"\((Открытый аукцион|Публичное предложение|Конкурс|Закрытый аукцион)\)",
        text, re.I,
    )
    if trade_m:
        lot["trade_type"] = trade_m.group(1)

    debtor_m = re.search(r"(?:Должник|Банкрот)[:\s]*([^\n]{5,150})", text, re.I)
    if debtor_m:
        d = debtor_m.group(1).strip()
        if "\u2592" not in d:
            lot["debtor"] = d

    for a_tag in soup.find_all("a", href=re.compile(r"https?://", re.I)):
        href = a_tag["href"]
        if any(kw in href.lower() for kw in [
            "etp", "lot-online", "fabrikant", "sberbank-ast", "rts-tender",
        ]):
            lot["etp_url"] = href
            break

    case_m = re.search(r"А\d{2}-\d{3,6}/\d{4}", text)
    if case_m:
        lot["legal_case"] = case_m.group(0)

    return lot


def enrich_details(client, lots, limit=None):
    target = lots[:limit] if limit else lots
    total = len(target)
    log.info(f"Загружаю карточки: {total} лотов")

    for i, lot in enumerate(target):
        if _interrupted:
            break
        if i > 0 and i % BATCH_SIZE == 0:
            log.info(f"Пауза {BATCH_PAUSE}с после {i} карточек...")
            time.sleep(BATCH_PAUSE)

        resp = client.get(f"{BASE_URL}/item?id={lot['id']}", delay_range=DELAY_DETAIL)
        if not resp:
            continue
        parse_detail_page(resp.text, lot)

        if (i + 1) % 20 == 0:
            log.info(f"Карточка {i + 1}/{total}")

    log.info(f"Карточки: {min(total, i + 1)}/{total}")


# ---------------------------------------------------------------------------
# Google Sheets
# ---------------------------------------------------------------------------

def load_our_data():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        log.error("gspread не установлен")
        return []

    try:
        creds = Credentials.from_service_account_file(
            GOOGLE_SA_JSON,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(GSHEETS_ID)
    except Exception as e:
        log.error(f"Google Sheets: {e}")
        return []

    all_rows = []
    for sheet_name in ["Лоты", "ЕФРСБ"]:
        log.info(f"Загружаю '{sheet_name}'...")
        try:
            ws = sh.worksheet(sheet_name)
            values = ws.get_all_values()
            if len(values) < 2:
                continue
            header = values[0]
            for row_vals in values[1:]:
                row = dict(zip(header, row_vals))
                row["_source_sheet"] = sheet_name
                all_rows.append(row)
            log.info(f"  {sheet_name}: {len(values) - 1} строк")
        except Exception as e:
            log.warning(f"  Ошибка: {e}")

    return all_rows


# ---------------------------------------------------------------------------
# Сравнение
# ---------------------------------------------------------------------------

def normalize_cadastral(val):
    if not val:
        return ""
    parts = val.strip().split(":")
    if len(parts) == 4:
        try:
            return ":".join(str(int(p)) for p in parts)
        except ValueError:
            pass
    return val.strip()


def normalize_address_words(addr):
    if not addr:
        return []
    stop = {
        "ул", "ул.", "г", "г.", "д", "д.", "пос", "с", "р-н", "обл", "край",
        "пермский", "пермская", "российская", "федерация", "россия", "область",
        "район", "округ", "городской", "муниципальный", "поселок", "село",
        "деревня", "улица", "дом", "кв", "корп", "стр",
    }
    words = re.findall(r"[а-яёa-z0-9]+", addr.lower())
    return [w for w in words if w not in stop and len(w) > 2][:3]


def compare_lots(tb_lots, our_lots):
    our_by_cad = {}
    our_by_price = {}

    for lot in our_lots:
        cad = normalize_cadastral(lot.get("cadastralNumber", ""))
        if cad:
            our_by_cad[cad] = lot
        price = parse_price(str(lot.get("price", "")))
        if price:
            bucket = round(price, -3)
            our_by_price.setdefault(bucket, []).append(lot)

    matched = []
    only_tb = []

    for tb in tb_lots:
        found = False

        cad = normalize_cadastral(tb.get("cadastral", ""))
        if cad and cad in our_by_cad:
            matched.append({"tb": tb, "ours": our_by_cad[cad], "type": "cadastral"})
            found = True
            continue

        tb_price = tb.get("price")
        tb_words = normalize_address_words(tb.get("address") or tb.get("name", ""))

        if tb_price and tb_words:
            for delta in range(-10, 11):
                bucket = round(tb_price * (1 + delta / 100), -3)
                for our in our_by_price.get(bucket, []):
                    our_price = parse_price(str(our.get("price", "")))
                    if not our_price or abs(tb_price - our_price) / max(our_price, 1) > 0.05:
                        continue
                    our_words = normalize_address_words(our.get("address", "") or our.get("name", ""))
                    if len(set(tb_words) & set(our_words)) >= 2:
                        matched.append({"tb": tb, "ours": our, "type": "fuzzy"})
                        found = True
                        break
                if found:
                    break

        if not found:
            only_tb.append(tb)

    matched_our_ids = {m["ours"].get("lotId", "") for m in matched}
    only_ours = [l for l in our_lots if l.get("lotId", "") not in matched_our_ids]

    return {"matched": matched, "only_tb": only_tb, "only_ours": only_ours}


# ---------------------------------------------------------------------------
# Вывод
# ---------------------------------------------------------------------------

def save_csv(lots, filename):
    if not lots:
        return
    keys = []
    for lot in lots:
        for k in lot:
            if k not in keys:
                keys.append(k)
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(lots)
    log.info(f"CSV: {filename} ({len(lots)} строк)")


def print_summary(result, tb_lots, our_lots):
    m = result["matched"]
    otb = result["only_tb"]
    oo = result["only_ours"]
    zalog = [l for l in otb if l.get("section") == "Залог"]

    print("\n" + "=" * 60)
    print("СВОДКА СРАВНЕНИЯ")
    print("=" * 60)
    print(f"TBankrot (Пермь, недвижимость): {len(tb_lots):>6}")
    print(f"Наши (Лоты + ЕФРСБ):           {len(our_lots):>6}")
    print("-" * 60)
    print(f"Совпадений:                     {len(m):>6}")
    print(f"  по кадастру:                  {sum(1 for x in m if x['type'] == 'cadastral'):>6}")
    print(f"  по цене+адресу:               {sum(1 for x in m if x['type'] == 'fuzzy'):>6}")
    print(f"Только в TBankrot:              {len(otb):>6}  <-- пробелы")
    print(f"  ЗАЛОГОВЫЕ:                    {len(zalog):>6}  <-- новое")
    print(f"Только у нас:                   {len(oo):>6}")
    print("=" * 60)

    sections = {}
    for l in otb:
        s = l.get("section", "?")
        sections[s] = sections.get(s, 0) + 1
    if sections:
        print("\nПо секциям (только TBankrot):")
        for s, cnt in sorted(sections.items(), key=lambda x: -x[1]):
            print(f"  {s:25s} {cnt:>5}")
    print()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

_sb_client = None


def _get_supabase():
    global _sb_client
    if _sb_client is None:
        try:
            from supabase import create_client
            _sb_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            log.warning(f"Supabase init: {e}")
    return _sb_client


def parse_area_num(area_str):
    if not area_str:
        return None
    m = re.search(r"([\d\s,.]+)", area_str)
    if m:
        try:
            return float(m.group(1).replace(" ", "").replace(",", "."))
        except ValueError:
            pass
    return None


CATEGORY_TO_TYPE = {
    "Квартиры и комнаты": "apartment",
    "Земельные участки": "land",
    "Жилые дома": "house",
    "Нежилые помещения": "commercial",
    "Гаражи": "garage",
    "Здания": "commercial",
    "Прочее": "commercial",
}


def write_to_supabase(lot, category):
    try:
        sb = _get_supabase()
        if not sb:
            return False

        lot_id = f"TB-{lot['id']}"
        raw_price = lot.get("price") or 0
        try:
            price = float(raw_price)
        except (ValueError, TypeError):
            price = 0
        area = parse_area_num(lot.get("area", ""))
        is_land = "участ" in (lot.get("name", "") or "").lower()

        # Определяем тип: название важнее категории (tbankrot часто ошибается)
        name_lower = (lot.get("name") or "").lower()
        if "земельн" in name_lower or "участ" in name_lower or "з/у" in name_lower:
            ptype = "land"
        elif "жилой дом" in name_lower or "коттедж" in name_lower or "дача" in name_lower:
            ptype = "house"
        elif "гараж" in name_lower or "бокс" in name_lower:
            ptype = "garage"
        elif "нежил" in name_lower or "здани" in name_lower or "помещен" in name_lower or "склад" in name_lower or "офис" in name_lower:
            ptype = "commercial"
        elif "квартир" in name_lower or "комнат" in name_lower:
            ptype = "apartment"
        else:
            ptype = CATEGORY_TO_TYPE.get(category, "commercial")

        row = {
            "lot_id": lot_id,
            "source": "tbankrot",
            "date_added": datetime.now().strftime("%Y-%m-%d"),
            "name": (lot.get("name") or "")[:400],
            "category": category,
            "property_type": ptype,
            "address": (lot.get("address") or "")[:200],
            "cadastral_number": lot.get("cadastral") or None,
            "price": price if price else None,
            "deposit": round(price * 0.1, 2) if price else None,
            "area": area,
            "area_unit": "sotka" if is_land else "m2",
            "bidd_type": "Банкротство (TBankrot)",
            "auction_date": lot.get("auction_date", ""),
            "application_end": lot.get("deadline", ""),
            "status": "PUBLISHED",
            "url": lot.get("url", ""),
            "etp_url": lot.get("etp_url") or None,
            "district": "Пермский край",
        }

        row = {k: v for k, v in row.items() if v is not None and v != ""}
        sb.table("properties").upsert(row, on_conflict="lot_id").execute()
        return True
    except Exception as e:
        log.warning(f"Supabase error {lot.get('id')}: {e}")
        return False


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def send_telegram_lot(lot, category):
    """Отправить уведомление о новом лоте в канал."""
    price = lot.get("price") or 0
    price_str = f"{price:,.0f}".replace(",", " ") + " руб." if price else "Цена не указана"
    name = (lot.get("name") or "Без названия")[:150]
    cad = lot.get("cadastral", "")
    addr = lot.get("address", "")

    text = f"🏠 <b>Новый лот (TBankrot)</b>\n\n"
    text += f"<b>{name}</b>\n"
    text += f"💰 {price_str}\n"
    if cad:
        text += f"📋 Кадастр: {cad}\n"
    if addr:
        text += f"📍 {addr}\n"
    text += f"📂 {category} | {lot.get('section', 'Банкротство')}\n"
    text += f"\n🔗 <a href=\"{lot.get('url', '')}\">Открыть на TBankrot</a>"

    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            data={
                "chat_id": TG_CHANNEL_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            },
            timeout=10,
        )
        time.sleep(1)
        return True
    except Exception as e:
        log.warning(f"TG error: {e}")
        return False


def send_notify(text):
    """Техническое уведомление Ярославу."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_NOTIFY_TOKEN}/sendMessage",
            data={"chat_id": TG_NOTIFY_CHAT, "text": text},
            timeout=10,
        )
    except Exception:
        pass


def categorize(name):
    n = name.lower()
    if any(w in n for w in ["квартир", "комнат", "доля"]):
        return "Квартиры и комнаты"
    elif any(w in n for w in ["участ", "земел"]):
        return "Земельные участки"
    elif any(w in n for w in ["дом", "жилой дом", "коттедж"]):
        return "Жилые дома"
    elif any(w in n for w in ["нежил", "помещен", "офис", "магазин", "склад"]):
        return "Нежилые помещения"
    elif any(w in n for w in ["гараж", "бокс", "машино"]):
        return "Гаражи"
    elif any(w in n for w in ["здани"]):
        return "Здания"
    return "Прочее"


def sync_new_lots_to_sheets(new_lots):
    """Записать новые банкротные лоты в лист ЕФРСБ + Supabase + Telegram."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        log.error("gspread не установлен, sync невозможен")
        return 0

    creds = Credentials.from_service_account_file(
        GOOGLE_SA_JSON,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(GSHEETS_ID)
    ws = sh.worksheet("ЕФРСБ")

    existing_ids = set(ws.col_values(1)[1:])
    today = datetime.now().strftime("%d.%m.%Y")

    batch = []
    for lot in new_lots:
        if lot.get("section") != "Банкротство":
            continue
        lot_id = f"TB-{lot['id']}"
        if lot_id in existing_ids:
            continue

        price = lot.get("price") or 0
        deposit = round(price * 0.1, 2) if price else ""

        row = [
            lot_id,
            today,
            categorize(lot.get("name", "")),
            lot.get("name", "")[:400],
            lot.get("address", ""),
            lot.get("area", ""),
            str(price) if price else "",
            str(deposit) if deposit else "",
            lot.get("cadastral", ""),
            lot.get("auction_date", ""),
            lot.get("deadline", ""),
            "Банкротство (TBankrot)",
            lot.get("etp_url", ""),
            "PUBLISHED",
            lot.get("debtor", ""),
            "",
            lot.get("url", ""),
            "",
        ]
        batch.append(row)

    if not batch:
        log.info("Нет новых лотов для записи в Sheets")
        return 0

    CHUNK = 50
    added = 0
    for i in range(0, len(batch), CHUNK):
        chunk = batch[i:i + CHUNK]
        try:
            ws.append_rows(chunk, value_input_option="USER_ENTERED")
            added += len(chunk)
            log.info(f"Sheets: записано {added}/{len(batch)}")
            time.sleep(2)
        except Exception as e:
            log.error(f"Sheets ошибка: {e}")
            time.sleep(10)

    # Supabase + Telegram для новых лотов
    sb_ok = 0
    tg_ok = 0
    for lot in new_lots:
        cat = categorize(lot.get("name", ""))
        if write_to_supabase(lot, cat):
            sb_ok += 1
        if send_telegram_lot(lot, cat):
            tg_ok += 1

    log.info(f"Supabase: {sb_ok}/{len(new_lots)}, Telegram: {tg_ok}/{len(new_lots)}")
    return added


def main():
    ap = argparse.ArgumentParser(description="TBankrot scraper")
    ap.add_argument("--region", default="perm", choices=TBANKROT_REGIONS.keys())
    ap.add_argument("--detail", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-compare", action="store_true")
    ap.add_argument("--sync", action="store_true",
                    help="Автоматически добавлять новые лоты в Sheets (для cron)")
    ap.add_argument("--output-dir", type=str, default=".")
    args = ap.parse_args()

    global _REGION_KEY, LISTING_URL, TG_CHANNEL_ID
    _REGION_KEY = args.region
    region_cfg = TBANKROT_REGIONS[_REGION_KEY]
    LISTING_URL = BASE_URL + f"/?page={{page}}&region[]={region_cfg['region_id']}&apId=2&parent_cat[]=2"
    TG_CHANNEL_ID = region_cfg.get("tg_channel", TG_CHANNEL_ID)
    log.info(f"Region: {region_cfg['name']} (tbankrot region_id={region_cfg['region_id']})")

    today = datetime.now().strftime("%Y-%m-%d")
    log.info(f"=== TBankrot Scraper — {today} ===")

    client = SafeClient()
    lots = scrape_listing(client)

    if not lots:
        log.error("Нет лотов. Выход.")
        sys.exit(1)

    if args.detail and not _interrupted:
        enrich_details(client, lots, limit=args.limit)

    raw_file = os.path.join(args.output_dir, f"tbankrot_raw_{today}.csv")
    save_csv(lots, raw_file)

    if args.sync and not _interrupted:
        # Режим cron: сравниваем и автодобавляем новые
        our_lots = load_our_data()
        if our_lots:
            result = compare_lots(lots, our_lots)
            new_bankrot = [l for l in result["only_tb"] if l.get("section") == "Банкротство"]
            if new_bankrot:
                added = sync_new_lots_to_sheets(new_bankrot)
                msg = f"TBankrot sync: +{added} новых лотов в Sheets+Supabase+TG (всего {len(lots)} на сайте)"
                log.info(msg)
                send_notify(msg)
            else:
                log.info("Sync: новых банкротных лотов нет")
                send_notify(f"TBankrot sync: новых лотов нет (всего {len(lots)} на сайте)")
        else:
            log.warning("Не удалось загрузить наши данные для sync")

    elif not args.no_compare and not _interrupted:
        our_lots = load_our_data()
        if our_lots:
            result = compare_lots(lots, our_lots)
            print_summary(result, lots, our_lots)

            matched_ids = {x["tb"]["id"] for x in result["matched"]}
            for lot in lots:
                lot["_match"] = "matched" if lot["id"] in matched_ids else "only_tb"
            save_csv(lots, os.path.join(args.output_dir, f"tbankrot_comparison_{today}.csv"))

            zalog = [l for l in result["only_tb"] if l.get("section") == "Залог"]
            if zalog:
                save_csv(zalog, os.path.join(args.output_dir, f"tbankrot_zalog_{today}.csv"))
        else:
            log.warning("Нет наших данных, сравнение пропущено")

    log.info("Готово.")


if __name__ == "__main__":
    main()
