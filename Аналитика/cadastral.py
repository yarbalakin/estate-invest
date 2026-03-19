"""
cadastral.py — Кадастровые данные из НСПД (Росреестр).

Что делает:
  - Кадастровый номер → кадастровая стоимость, площадь, назначение
  - Кадастровый номер → вид разрешённого использования (ВРИ)
  - Кадастровый номер → тип собственности, этаж, дата регистрации
  - Кадастровый номер → координаты (центроид полигона из geometry)

API: НСПД (nspd.gov.ru) — бесплатный, без ключа.
Требует заголовки sec-fetch-* для обхода WAF.
Geometry возвращается в EPSG:3857, конвертируем в WGS-84.
"""

import logging
import math
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
    Дополнительно включает _geometry (GeoJSON Polygon в EPSG:3857).
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

        # Структура ответа: {data: {features: [{geometry: {...}, properties: {options: {...}}}]}}
        features = data.get("data", {}).get("features", [])
        if not features:
            return None

        feature = features[0]
        props = feature.get("properties", {})
        result = props.get("options", {})
        # Добавляем categoryName из верхнего уровня
        result["_categoryName"] = props.get("categoryName", "")
        # Добавляем geometry для извлечения координат
        result["_geometry"] = feature.get("geometry")
        return result

    except requests.RequestException as e:
        log.error("NSPD fetch %s FAIL: %s", cadastral_number, e)
        return None


def _epsg3857_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """Конвертация EPSG:3857 (Web Mercator) → WGS-84 (lat, lon)."""
    lon = x * 180.0 / 20037508.34
    lat = math.atan(math.exp(y * math.pi / 20037508.34)) * 360.0 / math.pi - 90.0
    return lat, lon


def _extract_ring(geom: dict) -> list | None:
    """Извлечь внешнее кольцо координат из GeoJSON geometry (Polygon/MultiPolygon/Point)."""
    gtype = geom.get("type", "")
    coords = geom.get("coordinates", [])
    if not coords:
        return None

    if gtype == "Point":
        # Одна точка [x, y] → обернуть в кольцо
        if len(coords) >= 2 and isinstance(coords[0], (int, float)):
            return [coords]
        return None

    if gtype == "MultiPolygon":
        # [[[ring]]] → первый полигон, внешнее кольцо
        try:
            ring = coords[0][0]
        except (IndexError, TypeError):
            return None
    else:
        # Polygon: [[ring]]
        try:
            ring = coords[0]
        except (IndexError, TypeError):
            return None

    # Проверяем что ring — список точек [x, y], а не вложенный ещё глубже
    if not ring:
        return None
    first = ring[0]
    if isinstance(first, (int, float)):
        # ring = [x, y, x, y, ...] — плоский, нужно парсить парами
        pairs = []
        for j in range(0, len(ring) - 1, 2):
            pairs.append([ring[j], ring[j + 1]])
        return pairs if pairs else None
    if isinstance(first, list) and len(first) >= 2 and isinstance(first[0], (int, float)):
        return ring  # нормальный формат [[x, y], ...]
    # Ещё один уровень вложенности
    if isinstance(first, list) and isinstance(first[0], list):
        return first
    return None


def _extract_polygon_wgs84(geom: dict) -> dict | None:
    """Конвертировать geometry НСПД (EPSG:3857) → GeoJSON Polygon WGS-84.

    Возвращает {"type": "Polygon", "coordinates": [[[lon, lat], ...]]}
    или None если геометрия некорректна / является точкой.
    """
    if not geom:
        return None
    # Точка — не граница участка, пропускаем
    if geom.get("type") == "Point":
        return None
    ring = _extract_ring(geom)
    if not ring or len(ring) < 3:
        return None
    coords = [[round(lon, 6), round(lat, 6)]
              for p in ring
              for lat, lon in [_epsg3857_to_wgs84(p[0], p[1])]]
    if not coords:
        return None
    # Замкнуть кольцо если не замкнуто
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    return {"type": "Polygon", "coordinates": [coords]}


def _split_cadastral(cadastral_number: str) -> list[str]:
    """Разделить составной кадастровый номер на отдельные."""
    import re
    parts = re.split(r'\s*[|,;]\s*', cadastral_number.strip())
    result = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if re.match(r'^\d{2}:\d{2}:\d{5,7}:\d+$', p):
            result.append(p)
        elif re.match(r'^\d{17,}$', p):
            # ЕФРСБ формат без двоеточий — пробуем разные разбивки
            # Формат: RR KK QQQQQQQ NNNN... (2:2:7:rest или 2:3:7:rest)
            for split in [(2, 4, 11), (2, 5, 12)]:
                try:
                    cn = f"{p[:split[0]]}:{p[split[0]:split[1]]}:{p[split[1]:split[2]]}:{p[split[2]:]}"
                    if re.match(r'^\d{2}:\d{2,3}:\d{5,7}:\d+$', cn):
                        result.append(cn)
                        break
                except Exception:
                    pass
        else:
            result.append(p)
    return result if result else [cadastral_number.strip()]


def geocode_by_cadastral(cadastral_number: str) -> tuple[float | None, float | None]:
    """Получить координаты (lat, lon) по кадастровому номеру через НСПД.

    Поддерживает составные номера (через | или ,) — пробует каждый.
    Возвращает (lat, lon) или (None, None).
    """
    candidates = _split_cadastral(cadastral_number)

    for cn in candidates:
        data = fetch_nspd(cn)
        if not data:
            continue
        geom = data.get("_geometry")
        if not geom:
            continue
        ring = _extract_ring(geom)
        if not ring:
            continue
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        lat, lon = _epsg3857_to_wgs84(sum(xs) / len(xs), sum(ys) / len(ys))
        return round(lat, 6), round(lon, 6)

    return None, None


def enrich_card(card: PropertyCard) -> bool:
    """Обогащает PropertyCard кадастровыми данными из НСПД.

    Заполняет:
      - cadastralValue — кадастровая стоимость
      - cadastralArea — площадь по кадастру
      - cadastralCategory — категория/назначение
      - cadastralPermittedUse — ВРИ / тип помещения
      - cadastralPriceRatio — цена лота / кадастровая стоимость
      - hasEncumbrances — наличие обременений (по ownership_type)
      - lat, lon — координаты из geometry (если ещё не заполнены)

    Возвращает True если обогащение успешно.
    """
    if not card.cadastralNumber:
        return False

    data = fetch_nspd(card.cadastralNumber)
    if not data:
        return False

    _parse_nspd(card, data)

    # Извлекаем координаты и границы из geometry
    geom = data.get("_geometry")
    if geom:
        ring = _extract_ring(geom)
        if ring:
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            # Координаты центроида (если ещё не заполнены)
            if not card.lat or not card.lon:
                lat, lon = _epsg3857_to_wgs84(sum(xs) / len(xs), sum(ys) / len(ys))
                card.lat = round(lat, 6)
                card.lon = round(lon, 6)
                log.info("NSPD geocode %s → (%.6f, %.6f)", card.cadastralNumber, lat, lon)
        # Полный полигон границ (всегда обновляем)
        boundary = _extract_polygon_wgs84(geom)
        if boundary:
            card.boundaryGeojson = boundary
            log.info("NSPD boundary %s → %d points", card.cadastralNumber, len(boundary["coordinates"][0]))

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

    # Координаты и полигон из geometry (EPSG:3857 → WGS-84)
    geom = raw.get("_geometry")
    if geom:
        ring = _extract_ring(geom)
        if ring:
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            lat, lon = _epsg3857_to_wgs84(sum(xs) / len(xs), sum(ys) / len(ys))
            result["lat"] = round(lat, 6)
            result["lon"] = round(lon, 6)
        boundary = _extract_polygon_wgs84(geom)
        if boundary:
            result["boundary_geojson"] = boundary

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
