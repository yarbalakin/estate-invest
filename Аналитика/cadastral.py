"""
cadastral.py — Кадастровые данные из НСПД (Росреестр).

Что делает:
  - Кадастровый номер → кадастровая стоимость, площадь, назначение
  - Кадастровый номер → вид разрешённого использования (ВРИ)
  - Кадастровый номер → обременения

API: НСПД (nspd.gov.ru) — бесплатный, без ключа.
Фаллбек: PKK (pkk.rosreestr.ru) — бесплатный, без ключа.
"""

import logging
from typing import Any

import requests

from property_card import PropertyCard

log = logging.getLogger(__name__)

# НСПД API (новый портал Росреестра)
NSPD_SEARCH_URL = "https://nspd.gov.ru/api/geoportal/v2/search/geoportal"
# PKK API (старый портал, фаллбек)
PKK_URL = "https://pkk.rosreestr.ru/api/features/1"  # 1 = участки, 5 = ОКС

_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })
    return _session


def fetch_nspd(cadastral_number: str) -> dict[str, Any] | None:
    """Запрос кадастровых данных через НСПД API."""
    if not cadastral_number:
        return None

    try:
        resp = _get_session().get(
            NSPD_SEARCH_URL,
            params={"query": cadastral_number, "limit": 1},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        features = data.get("features", [])
        if features:
            return features[0].get("properties", {})
        return None

    except requests.RequestException as e:
        log.error("NSPD fetch %s FAIL: %s", cadastral_number, e)
        return None


def fetch_pkk(cadastral_number: str) -> dict[str, Any] | None:
    """Фаллбек: запрос через PKK API."""
    if not cadastral_number:
        return None

    try:
        resp = _get_session().get(
            f"{PKK_URL}/{cadastral_number}",
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        feature = data.get("feature")
        if feature:
            return feature.get("attrs", {})
        return None

    except requests.RequestException as e:
        log.error("PKK fetch %s FAIL: %s", cadastral_number, e)
        return None


def enrich_card(card: PropertyCard) -> bool:
    """Обогащает PropertyCard кадастровыми данными.

    Заполняет:
      - card.cadastralValue — кадастровая стоимость
      - card.cadastralArea — площадь по кадастру
      - card.cadastralCategory — категория земли
      - card.cadastralPermittedUse — ВРИ
      - card.cadastralPriceRatio — цена лота / кадастровая стоимость

    Пробует НСПД, при неудаче — PKK.
    Возвращает True если обогащение успешно.
    """
    if not card.cadastralNumber:
        return False

    # Попытка 1: НСПД
    data = fetch_nspd(card.cadastralNumber)
    source = "nspd"

    # Попытка 2: PKK
    if not data:
        data = fetch_pkk(card.cadastralNumber)
        source = "pkk"

    if not data:
        return False

    if source == "nspd":
        _parse_nspd(card, data)
    else:
        _parse_pkk(card, data)

    # Рассчитываем отношение цены к кадастровой стоимости
    if card.cadastralValue and card.cadastralValue > 0 and card.price > 0:
        card.cadastralPriceRatio = round(card.price / card.cadastralValue, 2)

    return True


def _parse_nspd(card: PropertyCard, data: dict) -> None:
    """Парсинг ответа НСПД."""
    # Кадастровая стоимость
    cad_value = data.get("cadastral_cost") or data.get("cad_cost")
    if cad_value:
        try:
            card.cadastralValue = float(cad_value)
        except (ValueError, TypeError):
            pass

    # Площадь
    area = data.get("area_value") or data.get("area")
    if area:
        try:
            card.cadastralArea = float(area)
        except (ValueError, TypeError):
            pass

    # Категория
    card.cadastralCategory = data.get("category_type") or data.get("category")

    # ВРИ
    card.cadastralPermittedUse = data.get("permitted_use") or data.get("util_by_doc")

    # Обременения
    encumbrances = data.get("encumbrances")
    if encumbrances:
        card.hasEncumbrances = True
        if isinstance(encumbrances, list) and encumbrances:
            card.encumbranceType = encumbrances[0].get("type", "")
    else:
        card.hasEncumbrances = False

    # Дата кадастровой оценки
    card.cadastralValueDate = data.get("cad_cost_date")


def _parse_pkk(card: PropertyCard, data: dict) -> None:
    """Парсинг ответа PKK."""
    # Кадастровая стоимость
    cad_value = data.get("cad_cost")
    if cad_value:
        try:
            card.cadastralValue = float(cad_value)
        except (ValueError, TypeError):
            pass

    # Площадь
    area = data.get("area_value")
    if area:
        try:
            card.cadastralArea = float(area)
        except (ValueError, TypeError):
            pass

    # Категория
    card.cadastralCategory = data.get("category_type")

    # ВРИ
    card.cadastralPermittedUse = data.get("util_by_doc") or data.get("fp")
