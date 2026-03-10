"""
geocoder.py — Геокодирование через DaData API.

Что делает:
  - Адрес → координаты (lat, lon)
  - Адрес → стандартизированный адрес (ФИАС)
  - Адрес → кадастровый номер (если есть в DaData)

DaData: 10 000 бесплатных запросов в день.
API docs: https://dadata.ru/api/clean/address/

Credentials:
  DADATA_TOKEN — API-ключ
  DADATA_SECRET — секретный ключ (для стандартизации)
"""

import os
import logging
from typing import Any

import requests

from property_card import PropertyCard

log = logging.getLogger(__name__)

DADATA_TOKEN = os.environ.get("DADATA_TOKEN", "")
DADATA_SECRET = os.environ.get("DADATA_SECRET", "")

CLEAN_URL = "https://cleaner.dadata.ru/api/v1/clean/address"
SUGGEST_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address"

_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Token {DADATA_TOKEN}",
            "X-Secret": DADATA_SECRET,
        })
    return _session


def clean_address(address: str) -> dict[str, Any] | None:
    """Стандартизация адреса через DaData Clean API.

    Возвращает полный ответ DaData или None при ошибке.
    Заполняет: lat, lon, address_std, cadastral_number (если есть).
    """
    if not DADATA_TOKEN or not DADATA_SECRET:
        log.warning("DADATA_TOKEN/DADATA_SECRET не установлены, пропускаю геокодирование")
        return None

    if not address or len(address.strip()) < 5:
        return None

    try:
        resp = _get_session().post(
            CLEAN_URL,
            json=[address],
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
        return None

    except requests.RequestException as e:
        log.error("DaData clean_address FAIL: %s", e)
        return None


def enrich_card(card: PropertyCard) -> bool:
    """Обогащает PropertyCard данными из DaData.

    Заполняет:
      - card.lat, card.lon — координаты
      - card.addressStd — стандартизированный адрес
      - card.cadastralNumber — кадастровый номер (если пустой и DaData знает)

    Возвращает True если обогащение успешно.
    """
    result = clean_address(card.address)
    if not result:
        return False

    # Координаты
    geo_lat = result.get("geo_lat")
    geo_lon = result.get("geo_lon")
    if geo_lat and geo_lon:
        try:
            card.lat = float(geo_lat)
            card.lon = float(geo_lon)
        except (ValueError, TypeError):
            pass

    # Стандартизированный адрес
    card.addressStd = result.get("result")

    # Кадастровый номер (если не заполнен из torgi)
    if not card.cadastralNumber:
        fias_code = result.get("fias_code")
        if fias_code:
            card.cadastralNumber = fias_code

    # Район (если не заполнен)
    if not card.district:
        # DaData: city_district, city_district_with_type
        district = result.get("city_district")
        if district:
            card.district = district

    return True
