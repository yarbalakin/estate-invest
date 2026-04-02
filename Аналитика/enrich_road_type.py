#!/usr/bin/env python3
"""
enrich_road_type.py — Обогащение земельных лотов типом дороги из OpenStreetMap.

Запуск на VPS:
  cd /opt/torgi-proxy && source venv/bin/activate
  python enrich_road_type.py          # все без road_type
  python enrich_road_type.py --limit 30  # тестовый прогон

Что делает:
  1. Берёт land-лоты с координатами, но без road_type
  2. Запрашивает Overpass API (OSM) — дороги в радиусе 500м
  3. Определяет лучшую дорогу и покрытие → road_access_score (0-10)
  4. Пишет в Supabase: road_type, road_surface, road_access_score
"""

import argparse
import json
import logging
import os
import time

import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
_mirror_idx = 0  # round-robin индекс
RADIUS = 500  # метров
DELAY = 3  # секунд между запросами

# Ранг типа дороги (чем выше — тем лучше доступность)
ROAD_RANK = {
    "motorway": 7, "trunk": 6, "primary": 5, "secondary": 4, "tertiary": 3,
    "residential": 2, "living_street": 2, "unclassified": 1,
    "service": 1, "track": 0, "path": 0, "footway": 0,
}

# Ранг покрытия
SURFACE_RANK = {
    "asphalt": 3, "paved": 3, "concrete": 3, "concrete:plates": 3,
    "compacted": 2, "gravel": 1, "unpaved": 1,
    "ground": 0, "dirt": 0, "mud": 0, "sand": 0,
}

# Человекочитаемый тип дороги
ROAD_LABEL = {
    "motorway": "магистраль", "trunk": "шоссе", "primary": "главная",
    "secondary": "второстепенная", "tertiary": "местная",
    "residential": "жилая", "living_street": "жилая",
    "unclassified": "без категории", "service": "служебная",
    "track": "грунтовка", "path": "тропа", "footway": "пешеходная",
}

SURFACE_LABEL = {
    "asphalt": "асфальт", "paved": "асфальт", "concrete": "бетон",
    "concrete:plates": "бетонные плиты", "compacted": "уплотнённый грунт",
    "gravel": "гравий", "unpaved": "без покрытия",
    "ground": "грунт", "dirt": "грунт", "mud": "грязь", "sand": "песок",
}


def fetch_roads(lat: float, lon: float) -> list[dict]:
    """Запрос дорог из OSM Overpass в радиусе RADIUS метров."""
    query = f"""
[out:json][timeout:10];
way(around:{RADIUS},{lat},{lon})[highway];
out tags center 5;
"""
    global _mirror_idx
    for attempt in range(len(OVERPASS_MIRRORS) * 2):
        url = OVERPASS_MIRRORS[_mirror_idx % len(OVERPASS_MIRRORS)]
        _mirror_idx += 1
        try:
            resp = requests.post(url, data={"data": query}, timeout=15)
            if resp.status_code in (429, 504):
                log.warning("  %d от %s — следующее зеркало", resp.status_code, url.split("//")[1].split("/")[0])
                time.sleep(2)
                continue
            resp.raise_for_status()
            return resp.json().get("elements", [])
        except Exception as e:
            log.warning("  Ошибка %s: %s — следующее зеркало", url.split("//")[1].split("/")[0], e)
            time.sleep(2)
    log.error("  Все зеркала недоступны после %d попыток", len(OVERPASS_MIRRORS) * 2)
    return None


def classify_roads(roads: list[dict]) -> dict:
    """Классифицировать дороги → road_type, road_surface, road_access_score."""
    if not roads:
        return {
            "road_type": "нет дорог",
            "road_surface": None,
            "road_access_score": 0,
        }

    best_road_rank = -1
    best_road_hw = None
    best_surface_rank = -1
    best_surface_val = None

    for road in roads:
        tags = road.get("tags", {})
        hw = tags.get("highway", "")
        sf = tags.get("surface", "")

        rr = ROAD_RANK.get(hw, 0)
        if rr > best_road_rank:
            best_road_rank = rr
            best_road_hw = hw

        sr = SURFACE_RANK.get(sf, -1)
        if sr > best_surface_rank:
            best_surface_rank = sr
            best_surface_val = sf

    # Скор 0-10: road_rank (0-7) масштабируем + бонус за покрытие (0-3)
    road_score = min(10, round(best_road_rank * 1.2 + max(best_surface_rank, 0)))

    road_label = ROAD_LABEL.get(best_road_hw, best_road_hw or "?")
    surface_label = SURFACE_LABEL.get(best_surface_val, best_surface_val) if best_surface_val else None

    return {
        "road_type": road_label,
        "road_surface": surface_label,
        "road_access_score": road_score,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Лимит лотов (0=все)")
    args = parser.parse_args()

    log.info("Загрузка land-лотов с координатами без road_type...")
    q = (
        sb.table("properties")
        .select("lot_id, lat, lon")
        .eq("property_type", "land")
        .not_.is_("lat", "null")
        .is_("road_type", "null")
        .order("created_at", desc=True)
    )
    if args.limit:
        q = q.limit(args.limit)
    else:
        # Пагинация для всех
        q = q.limit(1000)

    resp = q.execute()
    lots = resp.data
    log.info("Найдено %d лотов для обогащения", len(lots))

    if not lots:
        log.info("Все лоты уже обогащены!")
        return

    ok = 0
    fail = 0
    no_roads = 0

    for i, lot in enumerate(lots, 1):
        lot_id = lot["lot_id"]
        lat, lon = lot["lat"], lot["lon"]
        log.info("[%d/%d] %s (%.4f, %.4f)", i, len(lots), lot_id, lat, lon)

        roads = fetch_roads(lat, lon)
        if roads is None:
            log.warning("  API недоступен после 3 попыток — пропуск")
            fail += 1
            time.sleep(DELAY)
            continue

        result = classify_roads(roads)

        log.info("  %d дорог → %s / %s / score=%d",
                 len(roads), result["road_type"], result["road_surface"] or "?",
                 result["road_access_score"])

        if result["road_access_score"] == 0:
            no_roads += 1

        try:
            update = {"road_type": result["road_type"], "road_access_score": result["road_access_score"]}
            if result["road_surface"]:
                update["road_surface"] = result["road_surface"]
            sb.table("properties").update(update).eq("lot_id", lot_id).execute()
            ok += 1
        except Exception as e:
            log.error("  Ошибка записи: %s", e)
            fail += 1

        time.sleep(DELAY)

    log.info("=" * 50)
    log.info("Готово! OK: %d, ошибок: %d, без дорог: %d", ok, fail, no_roads)


if __name__ == "__main__":
    main()
