"""Блок 1: DATA LOADER — загрузка данных из Google Sheets."""

import io
import re

import pandas as pd
import requests

from config import BASE_URL, SHEETS, TRANSACTION_COLUMNS, REQUEST_TIMEOUT


# ---------------------------------------------------------------------------
# Утилиты парсинга
# ---------------------------------------------------------------------------

def parse_number(value):
    """Парсинг русского числового формата.

    '5 228 170,99р.' -> 5228170.99
    '0,93%'          -> 0.93
    '-20 523,90'     -> -20523.90
    """
    if pd.isna(value):
        return None
    s = str(value).strip()
    if s in ("", "-", "формула", "ошибка", "собрали"):
        return None

    # Убираем суффиксы валют и процентов
    for suffix in ("р.", "₽", "€", "$", "%"):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
            break

    # Пробелы и неразрывные пробелы — разделители тысяч
    s = s.replace("\xa0", "").replace(" ", "")
    # Запятая — десятичный разделитель
    s = s.replace(",", ".")

    try:
        return float(s)
    except ValueError:
        return None


def parse_date(value):
    """Парсинг даты в формате ДД.ММ.ГГГГ."""
    if pd.isna(value):
        return None
    s = str(value).strip()
    if not s or s == "-":
        return None
    try:
        return pd.to_datetime(s, format="%d.%m.%Y")
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Загрузка CSV из Google Sheets
# ---------------------------------------------------------------------------

def fetch_csv(gid, range_str=None):
    """Скачать CSV лист из Google Sheets по публичному URL.

    Используем gviz endpoint — не требует API-ключей,
    работает для таблиц с доступом «Все, у кого есть ссылка».
    """
    url = f"{BASE_URL}?tqx=out:csv&gid={gid}"
    if range_str:
        url += f"&range={range_str}"

    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.text


# ---------------------------------------------------------------------------
# Загрузка и очистка отдельных листов
# ---------------------------------------------------------------------------

def _assign_column_names(df, sheet_key, header_row):
    """Назначить колонкам осмысленные имена."""
    if sheet_key == "transactions":
        # У «Общей базы» много безымянных колонок — используем свой список
        names = list(TRANSACTION_COLUMNS)
        if len(df.columns) > len(names):
            names += [f"col_{i}" for i in range(len(names), len(df.columns))]
        df.columns = names[: len(df.columns)]
    else:
        # Для остальных листов берём имена из строки заголовков
        raw_names = list(df.iloc[0]) if header_row >= 0 else list(df.columns)
        clean = []
        seen = {}
        for i, name in enumerate(raw_names):
            n = str(name).strip() if pd.notna(name) else ""
            if not n:
                n = f"col_{i}"
            # Дедупликация
            if n in seen:
                seen[n] += 1
                n = f"{n}_{seen[n]}"
            else:
                seen[n] = 0
            clean.append(n)
        df.columns = clean
    return df


def load_sheet(sheet_key):
    """Загрузить и очистить один лист таблицы.

    Возвращает DataFrame со строковыми значениями.
    Числовой парсинг — ответственность Блока 2 (Analytics Engine).
    """
    config = SHEETS[sheet_key]
    csv_text = fetch_csv(config["gid"])
    header_row = config["header_row"]

    # Читаем весь CSV как строки
    df = pd.read_csv(
        io.StringIO(csv_text),
        header=None,
        dtype=str,
        keep_default_na=False,
    )

    if sheet_key == "transactions":
        # Для транзакций: пропускаем метаданные, назначаем свои имена колонок
        df = df.iloc[header_row + 1 :].reset_index(drop=True)
        _assign_column_names(df, sheet_key, header_row)
    else:
        # Для остальных: строка header_row — заголовки, данные — ниже
        header_values = df.iloc[header_row]
        df = df.iloc[header_row + 1 :].reset_index(drop=True)
        # Назначаем имена из заголовков
        clean_names = []
        seen = {}
        for i, val in enumerate(header_values):
            name = str(val).strip() if pd.notna(val) else ""
            if not name:
                name = f"col_{i}"
            if name in seen:
                seen[name] += 1
                name = f"{name}_{seen[name]}"
            else:
                seen[name] = 0
            clean_names.append(name)
        df.columns = clean_names[: len(df.columns)]

    # Убираем полностью пустые строки
    mask = df.astype(str).apply(lambda x: x.str.strip()).ne("").any(axis=1)
    df = df[mask].reset_index(drop=True)

    # Для транзакций: убираем строки без инвестора (мусор / заглушки)
    if sheet_key == "transactions" and "Инвестор" in df.columns:
        df = df[df["Инвестор"].str.strip() != ""].reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# Курсы валют
# ---------------------------------------------------------------------------

def load_currency_rates():
    """Загрузить курсы валют из первых строк «Общей базы».

    Строки 2-4 в таблице (CSV индексы 1-3):
      $    | 58,66
      €    | 64,46
      USDT | 56,33
    """
    csv_text = fetch_csv(SHEETS["transactions"]["gid"], range_str="A2:B4")
    # Используем pandas для корректного разбора CSV
    # (ручной split по запятой ломает числа вроде "58,66")
    df = pd.read_csv(
        io.StringIO(csv_text), header=None, dtype=str, keep_default_na=False
    )
    rates = {}
    for _, row in df.iterrows():
        currency = str(row.iloc[0]).strip()
        rate = parse_number(row.iloc[1])
        if currency and rate:
            rates[currency] = rate
    return rates


# ---------------------------------------------------------------------------
# Загрузка всех данных
# ---------------------------------------------------------------------------

def load_all_data():
    """Загрузить все листы + курсы валют.

    Возвращает dict:
        {
            "transactions": DataFrame,
            "investors": DataFrame,
            "objects": DataFrame,
            "summary_investors": DataFrame,
            "summary_objects": DataFrame,
            "summary_combined": DataFrame,
            "rates": {"$": 58.66, "€": 64.46, "USDT": 56.33},
        }
    """
    data = {}
    for key in SHEETS:
        data[key] = load_sheet(key)
    data["rates"] = load_currency_rates()
    return data
