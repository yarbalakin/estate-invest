"""
cadastral.py — Кадастровые данные из НСПД (Росреестр).

Что делает:
  - Кадастровый номер → кадастровая стоимость, площадь, назначение
  - Кадастровый номер → вид разрешённого использования (ВРИ)
  - Кадастровый номер → тип собственности, этаж, дата регистрации

API: НСПД (nspd.gov.ru) — бесплатный, без ключа.
Требует заголовки sec-fetch-* для обхода WAF.
"""

import logging
import time
from typing import Any

import requests

from property_card import PropertyCard

log = logging.getLogger(__name__)

NSPD_SEARCH_URL = "https://nspd.gov.ru/api/geoportal/v2/search/geoportal"

_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.verify = False
        _session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://nspd.gov.ru",
            "Referer": "https://nspd.gov.ru/map",
            "sec-ch-ua": '"Chromium";"v="120"',
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        })
    return _session


def fetch_nspd(cadastral_number: str) -> dict[str, Any] | None:
    """Запрос кадастровых данных через НСПД API.

    Возвращает dict с полями options из первого найденного объекта,
    или None если не найден / ошибка.
    """
    if not cadastral_number:
        return None

    try:
        sess = _get_session()
        # Обновляем Referer с конкретным кад. номером
        sess.headers["Referer"] = (
            f"https://nspd.gov.ru/map?search={cadastral_number}"
        )
        resp = sess.get(
            NSPD_SEARCH_URL,
            params={"query": cadastral_number, "limit": 1},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        # Структура ответа: {data: {features: [{properties: {options: {...}}}]}}
        features = data.get("data", {}).get("features", [])
        if not features:
            return None

        props = features[0].get("properties", {})
        result = props.get("options", {})
        # Добавляем categoryName из верхнего уровня
        result["_categoryName"] = props.get("categoryName", "")
        return result

    except requests.RequestException as e:
        log.error("NSPD fetch %s FAIL: %s", cadastral_number, e)
        return None


def enrich_card(card: PropertyCard) -> bool:
    """Обогащает PropertyCard кадастровыми данными из НСПД.

    Заполняет:
      - cadastralValue — кадастровая стоимость
      - cadastralArea — площадь по кадастру
      - cadastralCategory — категория/назначение
      - cadastralPermittedUse — ВРИ / тип помещения
      - cadastralPriceRatio — цена лота / кадастровая стоимость
      - hasEncumbrances — наличие обременений (по ownership_type)

    Возвращает True если обогащение успешно.
    """
    if not card.cadastralNumber:
        return False

    data = fetch_nspd(card.cadastralNumber)
    if not data:
        return False

    _parse_nspd(card, data)

    # Рассчитываем отношение цены к кадастровой стоимости
    if card.cadastralValue and card.cadastralValue > 0 and card.price > 0:
        card.cadastralPriceRatio = round(card.price / card.cadastralValue, 2)

    return True


def enrich_from_raw(raw: dict[str, Any]) -> dict[str, Any]:
    """Обогащение из сырого ответа НСПД — возвращает dict полей для UPDATE.

    Используется в скрипте массового обогащения (без PropertyCard).
    """
    result = {}

    # Кадастровая стоимость
    cv = raw.get("cost_value")
    if cv is not None:
        try:
            result["cadastral_value"] = float(cv)
        except (ValueError, TypeError):
            pass

    # Площадь
    area = raw.get("area")
    if area is not None:
        try:
            result["cadastral_area"] = float(area)
        except (ValueError, TypeError):
            pass

    # Категория / назначение
    purpose = raw.get("purpose")  # "Жилое", "Нежилое", "Земли населённых пунктов"
    cat_name = raw.get("_categoryName", "")  # "Помещения", "Земельные участки"
    params_type = raw.get("params_type")  # "Квартира", "Здание", "Участок"

    if purpose:
        result["cadastral_category"] = purpose
    elif cat_name:
        result["cadastral_category"] = cat_name

    # ВРИ / тип
    if params_type:
        result["cadastral_permitted_use"] = params_type

    # Обременения — если собственность "Долевая" или есть encumbrances
    # НСПД не отдаёт обременения напрямую, но мы можем отметить тип собственности
    ownership = raw.get("ownership_type")
    if ownership:
        result["encumbrance_type"] = ownership

    # Дата кадастровой оценки
    cost_index = raw.get("cost_index")
    if cost_index is not None:
        try:
            result["cadastral_value_date"] = str(round(float(cost_index), 2))
        except (ValueError, TypeError):
            pass

    # Этаж (для квартир) — обогащаем apartment блок
    floor_info = raw.get("floor")
    if floor_info and isinstance(floor_info, list):
        # Формат: ["4/Этаж"]
        for f in floor_info:
            if "/" in str(f):
                parts = str(f).split("/")
                try:
                    result["_floor"] = int(parts[0])
                except ValueError:
                    pass

    return result


def _parse_nspd(card: PropertyCard, data: dict) -> None:
    """Парсинг ответа НСПД в PropertyCard."""
    # Кадастровая стоимость
    cv = data.get("cost_value")
    if cv is not None:
        try:
            card.cadastralValue = float(cv)
        except (ValueError, TypeError):
            pass

    # Площадь
    area = data.get("area")
    if area is not None:
        try:
            card.cadastralArea = float(area)
        except (ValueError, TypeError):
            pass

    # Категория / назначение
    purpose = data.get("purpose")
    if purpose:
        card.cadastralCategory = purpose
    elif data.get("_categoryName"):
        card.cadastralCategory = data["_categoryName"]

    # Тип
    params_type = data.get("params_type")
    if params_type:
        card.cadastralPermittedUse = params_type

    # Этаж (для квартир)
    floor_info = data.get("floor")
    if floor_info and isinstance(floor_info, list) and card.apartment:
        for f in floor_info:
            if "/" in str(f):
                parts = str(f).split("/")
                try:
                    card.apartment.floor = int(parts[0])
                except ValueError:
                    pass
