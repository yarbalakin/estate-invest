#!/usr/bin/env python3
"""
Читает данные из Google Sheets (Свод объекты) и генерирует index.html
с прогресс-барами по активным сборам.

Запуск: python3 update.py
Требует: /opt/estate-invest/google-sa-key.json
"""

import json
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SHEET_ID = "1dWTjYF8sEc20SKeyl-e6PomBFq3VlfX-m8K2ZRopZJ0"
SA_KEY = "/opt/estate-invest/google-sa-key.json"
OUTPUT = os.path.join(os.path.dirname(__file__), "index.html")
TEMPLATE = os.path.join(os.path.dirname(__file__), "template.html")


def parse_money(s):
    """Парсит строку вида '5 242 922,06р.' в float"""
    if not s or s.strip().lower() in ("собрали", "-", ""):
        return None
    cleaned = s.replace("\xa0", "").replace(" ", "").replace("р.", "").replace(",", ".").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def fetch_data():
    creds = Credentials.from_service_account_file(
        SA_KEY, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SHEET_ID, range="Свод объекты!A3:I200")
        .execute()
    )
    rows = result.get("values", [])

    # Row 0 = заголовки (row 3 in sheet)
    # Row 1+ = данные (row 4+ in sheet)
    objects = []
    for row in rows[1:]:
        if len(row) < 7:
            continue
        name = row[1].strip() if len(row) > 1 else ""
        if not name:
            continue

        total = parse_money(row[2])
        collected = parse_money(row[3])
        remaining_raw = row[6].strip() if len(row) > 6 else ""

        if total is None or total == 0:
            continue

        # "собрали" = полностью собрано
        if remaining_raw.lower() == "собрали":
            remaining = 0.0
            collected = total
        else:
            remaining = parse_money(remaining_raw)
            if remaining is None:
                remaining = 0.0

        if collected is None:
            collected = total - remaining

        # Только объекты с активным сбором (remaining > 0)
        if remaining <= 0:
            continue

        pct = round(collected / total * 100, 1) if total > 0 else 0

        objects.append({
            "name": name,
            "total": total,
            "collected": collected,
            "remaining": remaining,
            "pct": pct,
        })

    # Сортируем: сначала самые новые (по порядку в таблице — последние)
    objects.reverse()
    return objects


def format_money(v):
    """Форматирует число в строку вида '1 234 567'"""
    if v >= 1_000_000:
        return f"{v / 1_000_000:.2f} млн"
    if v >= 1_000:
        return f"{v / 1_000:.0f} тыс"
    return f"{v:.0f}"


def generate_html(objects):
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        template = f.read()

    cards_html = []
    for obj in objects:
        pct = obj["pct"]
        # Цвет прогресс-бара
        if pct >= 80:
            color = "#22c55e"  # зелёный
        elif pct >= 50:
            color = "#3b82f6"  # синий
        elif pct > 0:
            color = "#f59e0b"  # оранжевый
        else:
            color = "#94a3b8"  # серый

        card = f"""
    <div class="card">
      <div class="card-name">{obj['name']}</div>
      <div class="progress-bar">
        <div class="progress-fill" style="width: {pct}%; background: {color};"></div>
      </div>
      <div class="stats">
        <span class="stat-pct">{pct}%</span>
        <span class="stat-detail">{format_money(obj['collected'])} из {format_money(obj['total'])}</span>
        <span class="stat-remaining">Осталось: {format_money(obj['remaining'])}</span>
      </div>
    </div>"""
        cards_html.append(card)

    from datetime import datetime, timezone, timedelta
    kld_tz = timezone(timedelta(hours=2))
    now = datetime.now(kld_tz).strftime("%d.%m.%Y %H:%M")

    html = template.replace("{{CARDS}}", "\n".join(cards_html))
    html = html.replace("{{UPDATED}}", now)
    html = html.replace("{{COUNT}}", str(len(objects)))

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"OK: {len(objects)} объектов, записано в {OUTPUT}")


if __name__ == "__main__":
    objects = fetch_data()
    generate_html(objects)
