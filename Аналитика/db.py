"""
db.py — Supabase клиент для PropertyCard.

Таблицы:
  - properties: основные данные (base columns + JSONB blocks)
  - enrichment_log: лог обогащения из внешних источников

Credentials берутся из переменных окружения:
  SUPABASE_URL — https://xxx.supabase.co
  SUPABASE_KEY — anon key
"""

import os
import logging
from datetime import datetime, timezone
from typing import Any

from supabase import create_client, Client

from property_card import PropertyCard

log = logging.getLogger(__name__)

# -----------------------------------------------------------
# Инициализация клиента
# -----------------------------------------------------------

_client: Client | None = None


def get_client() -> Client:
    """Ленивая инициализация Supabase клиента."""
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL и SUPABASE_KEY должны быть установлены. "
                "export SUPABASE_URL=https://xxx.supabase.co "
                "export SUPABASE_KEY=your-anon-key"
            )
        _client = create_client(url, key)
    return _client


# -----------------------------------------------------------
# CRUD для properties
# -----------------------------------------------------------

def upsert_property(card: PropertyCard) -> dict | None:
    """Upsert PropertyCard в таблицу properties.

    Использует lot_id как уникальный ключ (ON CONFLICT UPDATE).
    Возвращает вставленную/обновлённую запись.
    """
    row = card.to_db_row()
    row["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        result = (
            get_client()
            .table("properties")
            .upsert(row, on_conflict="lot_id")
            .execute()
        )
        if result.data:
            log.info("Upsert property %s OK", card.lotId)
            return result.data[0]
        return None
    except Exception as e:
        log.error("Upsert property %s FAIL: %s", card.lotId, e)
        return None


def get_property(lot_id: str) -> dict | None:
    """Получить PropertyCard по lot_id."""
    try:
        result = (
            get_client()
            .table("properties")
            .select("*")
            .eq("lot_id", lot_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        log.error("Get property %s FAIL: %s", lot_id, e)
        return None


def property_exists(lot_id: str) -> bool:
    """Проверить существование лота (для дедупликации)."""
    try:
        result = (
            get_client()
            .table("properties")
            .select("lot_id")
            .eq("lot_id", lot_id)
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        log.error("Check property %s FAIL: %s", lot_id, e)
        return False


def list_properties(
    property_type: str | None = None,
    district: str | None = None,
    min_discount: float | None = None,
    limit: int = 100,
) -> list[dict]:
    """Список лотов с фильтрами."""
    try:
        q = get_client().table("properties").select("*")
        if property_type:
            q = q.eq("property_type", property_type)
        if district:
            q = q.eq("district", district)
        if min_discount is not None:
            q = q.gte("discount", min_discount)
        result = q.order("date_added", desc=True).limit(limit).execute()
        return result.data or []
    except Exception as e:
        log.error("List properties FAIL: %s", e)
        return []


# -----------------------------------------------------------
# Enrichment log
# -----------------------------------------------------------

def log_enrichment(
    lot_id: str,
    source: str,
    status: str,
    data: dict | None = None,
    error: str | None = None,
) -> None:
    """Записать результат обогащения в enrichment_log."""
    row = {
        "lot_id": lot_id,
        "source": source,
        "status": status,
        "data": data,
        "error": error,
    }
    try:
        get_client().table("enrichment_log").insert(row).execute()
    except Exception as e:
        log.error("Log enrichment %s/%s FAIL: %s", lot_id, source, e)


# -----------------------------------------------------------
# SQL для создания таблиц (выполнить через Supabase SQL Editor)
# -----------------------------------------------------------

CREATE_TABLES_SQL = """
-- Таблица properties
CREATE TABLE IF NOT EXISTS properties (
  id SERIAL PRIMARY KEY,

  -- Блок 1: Идентификация
  lot_id TEXT UNIQUE NOT NULL,
  source TEXT DEFAULT 'torgi',
  property_type TEXT,
  date_added TEXT,
  name TEXT,
  category TEXT,
  cadastral_number TEXT,
  address TEXT,
  address_std TEXT,
  lat FLOAT,
  lon FLOAT,
  district TEXT,
  url TEXT,
  etp_url TEXT,

  -- Блок 2: Торговые данные
  price FLOAT,
  deposit FLOAT,
  price_per_unit TEXT,
  bidd_type TEXT,
  auction_date TEXT,
  application_end TEXT,
  status TEXT,
  area FLOAT,
  area_unit TEXT DEFAULT 'm2',

  -- Блок 3: Кадастр
  cadastral_value FLOAT,
  cadastral_value_date TEXT,
  cadastral_area FLOAT,
  cadastral_category TEXT,
  cadastral_permitted_use TEXT,
  has_encumbrances BOOLEAN,
  encumbrance_type TEXT,

  -- Блок 4: Рыночная оценка
  market_price FLOAT,
  market_price_per_unit FLOAT,
  discount FLOAT,
  confidence TEXT,
  analogs_count INT,
  analogs_median_price FLOAT,
  analogs_min_price FLOAT,
  analogs_max_price FLOAT,
  district_avg_price FLOAT,
  cadastral_price_ratio FLOAT,

  -- Блок 5: Должник
  debtor_name TEXT,
  debtor_inn TEXT,
  debtor_type TEXT,
  bankruptcy_case TEXT,
  fssp_debts FLOAT,
  fssp_count INT,
  court_cases INT,

  -- Блок 6: История цены
  price_history JSONB,
  original_price FLOAT,
  price_reduction INT,
  total_discount FLOAT,
  days_on_market INT,
  previous_auctions INT,

  -- Блок 7: Фото
  photos JSONB,
  photos_count INT,
  has_photos BOOLEAN,

  -- Блок 8: Скоринг
  invest_score FLOAT,
  risk_score FLOAT,
  liquidity_score FLOAT,
  recommendation TEXT,
  estimated_profit FLOAT,
  estimated_roi FLOAT,
  estimated_sell_time INT,

  -- Специализированные блоки (JSONB)
  apartment JSONB,
  building JSONB,
  land JSONB,
  house JSONB,
  commercial JSONB,
  rental JSONB,
  infra JSONB,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_properties_type ON properties(property_type);
CREATE INDEX IF NOT EXISTS idx_properties_district ON properties(district);
CREATE INDEX IF NOT EXISTS idx_properties_price ON properties(price);
CREATE INDEX IF NOT EXISTS idx_properties_discount ON properties(discount);
CREATE INDEX IF NOT EXISTS idx_properties_lot_id ON properties(lot_id);

-- Таблица enrichment_log
CREATE TABLE IF NOT EXISTS enrichment_log (
  id SERIAL PRIMARY KEY,
  lot_id TEXT REFERENCES properties(lot_id),
  source TEXT,
  status TEXT,
  data JSONB,
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_enrichment_lot ON enrichment_log(lot_id);
CREATE INDEX IF NOT EXISTS idx_enrichment_source ON enrichment_log(source);
"""
