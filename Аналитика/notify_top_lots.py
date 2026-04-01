#!/usr/bin/env python3
"""Дайджест топовых лотов в Telegram (cron: после enrichment цепочки)."""

import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from supabase import create_client
import requests

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
TG_TOKEN = "8604957943:AAF37XNjilxzwZV39MMTeGvVAalr95UrSpo"
TG_CHAT = "191260933"

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Top-5 lots ---
top = (
    sb.table("properties")
    .select("name,price,market_price,invest_score,url")
    .gte("invest_score", 50)
    .is_("lot_status", "null")
    .neq("is_remote", "true")
    .in_("confidence", ["высокая", "средняя"])
    .order("invest_score", desc=True)
    .range(0, 4)
    .execute()
).data

# --- Counters: new lots since yesterday ---
yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
new_all = (
    sb.table("properties")
    .select("id", count="exact")
    .gte("created_at", yesterday)
    .range(0, 0)
    .execute()
)
new_priced = (
    sb.table("properties")
    .select("id", count="exact")
    .gte("created_at", yesterday)
    .not_.is_("market_price", "null")
    .range(0, 0)
    .execute()
)
cnt_all = new_all.count or 0
cnt_priced = new_priced.count or 0

# --- Format message ---
lines = [f"📊 Дайджест лотов\n\nНовых за сутки: {cnt_all} (с оценкой: {cnt_priced})"]

if top:
    lines.append("\n🏆 ТОП-5 (score >= 50, без статуса):\n")
    for i, lot in enumerate(top, 1):
        score = lot.get("invest_score", 0)
        price = lot.get("price") or 0
        market = lot.get("market_price")
        title = (lot.get("name") or "—")[:50]
        url = lot.get("url") or ""
        if market and price:
            disc = round((1 - price / market) * 100)
            price_line = f"{price/1e6:.1f}М → {market/1e6:.1f}М (скидка {disc}%)"
        else:
            price_line = f"{price/1e6:.1f}М (нет рыночной)"
        lines.append(f"{i}. [{score}] | {price_line}\n   {title}\n   {url}")
else:
    lines.append("\nЛотов с score >= 50 нет.")

text = "\n".join(lines)

# --- Send to Telegram ---
resp = requests.post(
    f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
    data={"chat_id": TG_CHAT, "text": text, "disable_web_page_preview": True},
    timeout=10,
)
print(f"[{datetime.now():%Y-%m-%d %H:%M}] TG status={resp.status_code}, lots={len(top)}, new={cnt_all}")
