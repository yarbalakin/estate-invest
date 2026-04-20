#!/usr/bin/env python3
"""
Проверка инвесторов Estate Invest по перечню РосФинМониторинга.

Запуск:
  python3 check.py [путь_к_xml]

Инвесторы загружаются из Google Sheets "Estate Invest учет".
XML по умолчанию ищется в ~/Downloads/*.xml (последний по дате).
"""

import sys
import os
import csv
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from glob import glob

# ── Конфиг ─────────────────────────────────────────────────────
DOWNLOADS = os.path.expanduser("~/Downloads")
KEY_FILE = os.path.join(DOWNLOADS, "powerful-hall-488221-t2-b83babe8f926.json")
SPREADSHEET_ID = "1dWTjYF8sEc20SKeyl-e6PomBFq3VlfX-m8K2ZRopZJ0"
SHEET_NAME = "Инвесторы"
# Колонки (0-indexed, строка заголовка = строка 1)
COL_FIO_SHORT    = 1   # B — ФИО
COL_PHONE        = 2   # C — Телефон
COL_EMAIL        = 3   # D — Почта
COL_TG           = 4   # E — Телеграм
COL_FIO_FULL     = 15  # P — ФИО полное
COL_BIRTH        = 17  # R — Дата рождения
COL_PASSPORT     = 19  # T — Паспорт (серия номер)
COL_PASSPORT_DATE= 20  # U — Дата выдачи
COL_PASSPORT_BY  = 21  # V — Кем выдан
COL_PASSPORT_CODE= 22  # W — Код подразделения


# ── Нормализация ────────────────────────────────────────────────
def normalize_name(s):
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.strip()).upper()


def name_parts_set(s):
    return set(normalize_name(s).split())


def names_match(investor_fio, rfm_fio, rfm_parts):
    """
    Совпадение по ФИО: все три части (фамилия + имя + отчество) должны присутствовать.
    Если у инвестора только 2 слова (нет отчества) — требуем совпадение фамилии + имени,
    при условии что они оба присутствуют в rfm_parts.
    """
    inv_norm = normalize_name(investor_fio)
    if not inv_norm:
        return False
    # Точное совпадение
    if inv_norm == normalize_name(rfm_fio):
        return True
    rfm_words = normalize_name(rfm_fio).split()
    if len(rfm_words) < 2:
        return False
    inv_parts = name_parts_set(investor_fio)
    inv_words = inv_norm.split()
    if len(inv_words) >= 3:
        # У инвестора есть ФИО полностью — требуем все 3 слова РФМ
        return rfm_parts <= inv_parts  # rfm_parts — подмножество inv_parts
    else:
        # У инвестора только 2 слова — требуем фамилия + имя (первые 2 слова РФМ)
        return rfm_words[0] in inv_parts and rfm_words[1] in inv_parts


def parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    return None


def get_cell(row, idx, default=""):
    try:
        return row[idx].strip()
    except IndexError:
        return default


# ── Загрузка инвесторов из Google Sheets ────────────────────────
def load_investors_from_sheets():
    try:
        import google.oauth2.service_account as sa
        from googleapiclient.discovery import build
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install",
                        "google-auth", "google-api-python-client", "-q"])
        import google.oauth2.service_account as sa
        from googleapiclient.discovery import build

    creds = sa.Credentials.from_service_account_file(
        KEY_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:Z"
    ).execute()
    rows = result.get("values", [])

    investors = []
    # Строка 0 — служебная, строка 1 — заголовки, данные с строки 2
    for row in rows[2:]:
        fio_full  = get_cell(row, COL_FIO_FULL)
        fio_short = get_cell(row, COL_FIO_SHORT)
        fio = fio_full or fio_short
        if not fio:
            continue
        investors.append({
            "fio":             fio,
            "fio_short":       fio_short,
            "birth_str":       get_cell(row, COL_BIRTH),
            "birth_date":      parse_date(get_cell(row, COL_BIRTH)),
            "phone":           get_cell(row, COL_PHONE),
            "email":           get_cell(row, COL_EMAIL),
            "tg":              get_cell(row, COL_TG),
            "passport":        get_cell(row, COL_PASSPORT),
            "passport_date":   get_cell(row, COL_PASSPORT_DATE),
            "passport_by":     get_cell(row, COL_PASSPORT_BY),
            "passport_code":   get_cell(row, COL_PASSPORT_CODE),
        })
    return investors


# ── Загрузка перечня РосФинМониторинга ─────────────────────────
def load_rfm(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    list_date = root.findtext("ДатаПеречня") or ""
    persons = []

    for subj in root.iter("Субъект"):
        subj_id   = subj.findtext("ИдСубъекта") or ""
        t = subj.find("ТипСубъекта")
        subj_type = t.findtext("Наименование") if t is not None else ""

        fl = subj.find("ФЛ")
        if fl is None:
            continue

        fio   = fl.findtext("ФИО") or ""
        birth = fl.findtext("ДатаРождения") or ""
        inn   = fl.findtext("ИНН") or ""
        snils = fl.findtext("СНИЛС") or ""

        passports = []
        for doc in fl.iter("Документ"):
            dtype = doc.find("ТипДокумента")
            if dtype is not None and "ПАСПОРТ" in (dtype.findtext("Наименование") or "").upper():
                ser = doc.findtext("Серия") or ""
                num = doc.findtext("Номер") or ""
                passports.append(f"{ser} {num}".strip())

        persons.append({
            "id":         subj_id,
            "type":       subj_type or "",
            "fio":        fio,
            "birth_date": parse_date(birth),
            "birth_str":  birth,
            "inn":        inn,
            "snils":      snils,
            "passport":   "; ".join(passports),
            "parts":      name_parts_set(fio),
            "list_date":  list_date,
        })
    return persons


def normalize_passport(s):
    """Серия+номер без пробелов и спецсимволов для сравнения."""
    return re.sub(r"[\s\-]", "", s or "").upper()


def passport_match(inv_passport, rfm_passport_str):
    """
    True если паспорт инвестора совпадает хотя бы с одним паспортом из перечня.
    rfm_passport_str — строка вида "1234 567890" или "1234 567890; 9876 543210".
    """
    inv_norm = normalize_passport(inv_passport)
    if not inv_norm:
        return None  # нет данных
    for part in rfm_passport_str.split(";"):
        if normalize_passport(part) and normalize_passport(part) == inv_norm:
            return True
    return False


# ── Индекс паспортов РФМ для быстрого поиска ────────────────────
def build_passport_index(rfm_persons):
    """Словарь normalized_passport → список субъектов РФМ."""
    idx = {}
    for rfm in rfm_persons:
        for part in rfm["passport"].split(";"):
            key = normalize_passport(part)
            if key:
                idx.setdefault(key, []).append(rfm)
    return idx


# ── Сравнение ────────────────────────────────────────────────────
def compare(investors, rfm_persons):
    """
    Два прохода:
      1. По ФИО (фамилия+имя+отчество) — основной фильтр.
         ВЫСОКИЙ: ФИО + (ДР совпала ИЛИ паспорт совпал)
         СРЕДНИЙ:  ФИО совпало, нечем подтвердить (нет ДР/паспорта)
         НИЗКИЙ:   ФИО совпало, ДР и паспорт — другие (однофамилец)

      2. По паспорту (серия+номер) — страховочный проход.
         Если паспорт инвестора найден в РФМ даже при несовпадении ФИО →
         ВЫСОКИЙ (смена фамилии / опечатка в имени).
    """
    seen = set()  # (inv_fio+phone, rfm_id) — дедупликация
    matches = []

    # — Проход 1: по ФИО —
    for inv in investors:
        for rfm in rfm_persons:
            if not names_match(inv["fio"], rfm["fio"], rfm["parts"]):
                continue

            key = (inv["fio"] + "|" + inv["phone"], rfm["id"])
            seen.add(key)

            if inv["birth_date"] and rfm["birth_date"]:
                dob_match = (inv["birth_date"] == rfm["birth_date"])
            else:
                dob_match = None

            p_match = passport_match(inv["passport"], rfm["passport"])

            if dob_match is True or p_match is True:
                level = "ВЫСОКИЙ"
            elif dob_match is None and p_match is None:
                level = "СРЕДНИЙ"
            elif dob_match is None and p_match is False:
                level = "СРЕДНИЙ"
            else:
                level = "НИЗКИЙ"

            matches.append(_make_match(level, inv, rfm, "ФИО"))

    # — Проход 2: по паспорту (только инвесторы с паспортом) —
    passport_idx = build_passport_index(rfm_persons)
    for inv in investors:
        inv_norm = normalize_passport(inv["passport"])
        if not inv_norm:
            continue
        for rfm in passport_idx.get(inv_norm, []):
            key = (inv["fio"] + "|" + inv["phone"], rfm["id"])
            if key in seen:
                continue  # уже найдено через ФИО
            seen.add(key)
            matches.append(_make_match("ВЫСОКИЙ", inv, rfm, "Паспорт"))

    return matches


def _make_match(level, inv, rfm, method):
    return {
        "level":        level,
        "method":       method,
        "inv_fio":      inv["fio"],
        "inv_birth":    inv["birth_str"],
        "inv_phone":    inv["phone"],
        "inv_email":    inv["email"],
        "inv_tg":       inv["tg"],
        "inv_passport": inv["passport"],
        "inv_passport_date": inv["passport_date"],
        "inv_passport_by":   inv["passport_by"],
        "inv_passport_code": inv["passport_code"],
        "rfm_id":        rfm["id"],
        "rfm_fio":       rfm["fio"],
        "rfm_birth":     rfm["birth_str"],
        "rfm_inn":       rfm["inn"],
        "rfm_snils":     rfm["snils"],
        "rfm_passport":  rfm["passport"],
        "rfm_type":      rfm["type"],
        "rfm_list_date": rfm["list_date"],
    }


# ── Отчёт ────────────────────────────────────────────────────────
REPORT_FIELDS = [
    "level", "inv_fio", "inv_birth", "inv_passport", "inv_phone", "inv_email", "inv_tg",
    "rfm_fio", "rfm_birth", "rfm_inn", "rfm_passport", "rfm_type", "rfm_list_date", "rfm_id",
]


def write_report(matches, out_path):
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_FIELDS, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        for m in matches:
            writer.writerow(m)


def print_summary(matches, n_investors, n_rfm):
    high   = [m for m in matches if m["level"] == "ВЫСОКИЙ"]
    medium = [m for m in matches if m["level"] == "СРЕДНИЙ"]
    low    = [m for m in matches if m["level"] == "НИЗКИЙ"]

    print(f"\n{'='*60}")
    print(f"  Перечень РФМ:  {n_rfm:,} субъектов")
    print(f"  Инвесторы:     {n_investors:,} записей")
    print(f"{'='*60}")
    print(f"  ВЫСОКИЙ (имя + дата рождения):  {len(high)}")
    print(f"  СРЕДНИЙ  (имя, дата не задана): {len(medium)}")
    print(f"  НИЗКИЙ   (имя совпало, даты ≠): {len(low)}")
    print(f"{'='*60}\n")

    if high:
        print("!!! ВЫСОКИЙ — немедленная проверка !!!")
        for m in high:
            print(f"  Инвестор: {m['inv_fio']}  ДР: {m['inv_birth']}  Паспорт: {m['inv_passport']}")
            print(f"  В перечне: {m['rfm_fio']}  ДР: {m['rfm_birth']}  ИНН: {m['rfm_inn']}")
            print()

    if medium:
        print("--- СРЕДНИЙ — требует ручной проверки ---")
        for m in medium:
            print(f"  Инвестор: {m['inv_fio']}  ДР: {m['inv_birth']}  Тел: {m['inv_phone']}")
            print(f"  В перечне: {m['rfm_fio']}  ДР: {m['rfm_birth']}  ИНН: {m['rfm_inn']}")
            print()


# ── Main ─────────────────────────────────────────────────────────
def main():
    if len(sys.argv) > 1:
        xml_path = sys.argv[1]
    else:
        files = sorted(glob(os.path.join(DOWNLOADS, "*.xml")), key=os.path.getmtime, reverse=True)
        xml_path = files[0] if files else None
        if not xml_path:
            print("XML файл не найден в ~/Downloads/")
            sys.exit(1)

    print(f"XML: {os.path.basename(xml_path)}")
    print(f"Инвесторы: Google Sheets ({SPREADSHEET_ID}), лист '{SHEET_NAME}'")
    print("Загружаем данные...")

    rfm_persons = load_rfm(xml_path)
    investors   = load_investors_from_sheets()

    print(f"  Субъектов в перечне: {len(rfm_persons):,}")
    print(f"  Инвесторов в базе:   {len(investors):,}")
    print("Сравниваем...")

    matches = compare(investors, rfm_persons)

    level_order = {"ВЫСОКИЙ": 0, "СРЕДНИЙ": 1, "НИЗКИЙ": 2}
    matches.sort(key=lambda m: level_order[m["level"]])

    print_summary(matches, len(investors), len(rfm_persons))

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, f"report_{ts}.csv")
    write_report(matches, out_path)
    print(f"Отчёт: {out_path}")

    if not matches:
        print("Совпадений не найдено.")


if __name__ == "__main__":
    main()
