"""
PropertyCard — профиль объекта недвижимости.

Архитектура: композиция. Один класс PropertyCard с опциональными
вложенными блоками по типу объекта.

Типы объектов:
  Квартира:  card.apartment + card.building + card.infra
  Земля:     card.land + card.rental (для промки)
  Дом:       card.house + card.land + card.infra
  Нежилое:   card.commercial + card.building + card.rental + card.infra
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any


# ============================================================
# Специализированные блоки
# ============================================================

@dataclass
class ApartmentInfo:
    """Блок А1: параметры квартиры."""
    rooms: int | None = None
    floor: int | None = None
    floorsTotal: int | None = None
    condition: str | None = None
    balcony: bool | None = None


@dataclass
class BuildingInfo:
    """Блок А2/Н2: данные о доме/здании."""
    year: int | None = None
    material: str | None = None         # кирпич / панель / монолит
    floors: int | None = None
    wear: float | None = None           # износ %
    buildingType: str | None = None     # МКД / таунхаус / нежилое
    apartments: int | None = None
    managementCompany: str | None = None
    isEmergency: bool | None = None
    lastCapRepairYear: int | None = None
    heatingType: str | None = None
    buildingClass: str | None = None    # A/B/C/D (для коммерции)


@dataclass
class LandInfo:
    """Блок З1+З2: участок + коммуникации."""
    landCategory: str | None = None     # ИЖС / СНТ / ЛПХ / Промка
    permittedUse: str | None = None     # ВРИ
    landShape: str | None = None
    hasElectricity: bool | None = None
    hasGas: bool | None = None
    hasWater: bool | None = None
    hasSewage: bool | None = None
    communicationsNote: str | None = None


@dataclass
class HouseInfo:
    """Блок Д1: параметры дома (ИЖС)."""
    rooms: int | None = None
    floorsTotal: int | None = None
    wallMaterial: str | None = None
    buildYear: int | None = None
    condition: str | None = None
    houseArea: float | None = None      # площадь дома м2
    landArea: float | None = None       # площадь участка сотки
    garageOnSite: bool | None = None
    bathhouse: bool | None = None


@dataclass
class CommercialInfo:
    """Блок Н1: параметры нежилого."""
    commercialType: str | None = None   # Офис / Магазин / Склад / Производство
    floor: int | None = None
    ceilingHeight: float | None = None
    entrance: str | None = None         # отдельный / общий
    parking: int | None = None


@dataclass
class RentalInfo:
    """Блок З3/Н3: арендный потенциал."""
    rentPriceMonth: float | None = None
    rentPricePerUnit: float | None = None
    avgRentDistrict: float | None = None
    annualYield: float | None = None
    paybackYears: float | None = None
    capRate: float | None = None
    occupancyRate: float | None = None


@dataclass
class InfraInfo:
    """Блок А3: инфраструктура."""
    metroDistance: float | None = None
    schoolsNearby: int | None = None
    shopsNearby: int | None = None
    transportScore: float | None = None
    infraScore: float | None = None


# ============================================================
# PropertyCard — главный класс
# ============================================================

@dataclass
class PropertyCard:
    """Профиль объекта недвижимости.

    Базовые поля всегда заполнены, специализированные блоки —
    по типу объекта (apartment, land, house, commercial).
    """

    # === Блок 1: Идентификация ===
    lotId: str = ""
    source: str = "torgi"
    propertyType: str = ""              # apartment / land / house / commercial
    dateAdded: str = ""
    name: str = ""
    category: str = ""
    cadastralNumber: str = ""
    address: str = ""
    addressStd: str | None = None
    lat: float | None = None
    lon: float | None = None
    district: str | None = None
    url: str = ""
    etpUrl: str = ""

    # === Блок 2: Торговые данные ===
    price: float = 0.0
    deposit: float = 0.0
    pricePerUnit: str = ""
    biddType: str = ""
    auctionDate: str = ""
    applicationEnd: str = ""
    status: str = ""
    area: float = 0.0
    areaUnit: str = "m2"

    # === Блок 3: Кадастр ===
    cadastralValue: float | None = None
    cadastralValueDate: str | None = None
    cadastralArea: float | None = None
    cadastralCategory: str | None = None
    cadastralPermittedUse: str | None = None
    hasEncumbrances: bool | None = None
    encumbranceType: str | None = None

    # === Блок 4: Рыночная оценка ===
    marketPrice: float | None = None
    marketPricePerUnit: float | None = None
    discount: float | None = None
    confidence: str | None = None
    analogsCount: int | None = None
    analogsMedianPrice: float | None = None
    analogsMinPrice: float | None = None
    analogsMaxPrice: float | None = None
    districtAvgPrice: float | None = None
    cadastralPriceRatio: float | None = None

    # === Блок 5: Должник ===
    debtorName: str | None = None
    debtorINN: str | None = None
    debtorType: str | None = None
    bankruptcyCase: str | None = None
    fsspDebts: float | None = None
    fsspCount: int | None = None
    courtCases: int | None = None

    # === Блок 6: История цены ===
    priceHistory: list | None = None
    originalPrice: float | None = None
    priceReduction: int | None = None
    totalDiscount: float | None = None
    daysOnMarket: int | None = None
    previousAuctions: int | None = None

    # === Блок 7: Фото ===
    photos: list | None = None
    photosCount: int | None = None
    hasPhotos: bool | None = None

    # === Блок 8: Скоринг ===
    investScore: float | None = None
    riskScore: float | None = None
    liquidityScore: float | None = None
    recommendation: str | None = None
    estimatedProfit: float | None = None
    estimatedROI: float | None = None
    estimatedSellTime: int | None = None

    # === Специализированные блоки ===
    apartment: ApartmentInfo | None = None
    building: BuildingInfo | None = None
    land: LandInfo | None = None
    house: HouseInfo | None = None
    commercial: CommercialInfo | None = None
    rental: RentalInfo | None = None
    infra: InfraInfo | None = None

    # ----------------------------------------------------------
    # Методы
    # ----------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Сериализация в dict (для Supabase upsert).

        Специализированные блоки сериализуются в dict (→ JSONB).
        None-блоки не включаются.
        """
        d = asdict(self)
        # Убираем None-блоки чтобы не писать null в JSONB
        for block_name in ("apartment", "building", "land", "house",
                           "commercial", "rental", "infra"):
            if d.get(block_name) is None:
                del d[block_name]
        return d

    def to_db_row(self) -> dict[str, Any]:
        """Конвертация в snake_case для Supabase (PostgreSQL columns)."""
        d = self.to_dict()
        return _camel_to_snake_dict(d)

    @classmethod
    def from_parsed_lot(cls, lot: dict) -> PropertyCard:
        """Создание PropertyCard из результата parse_lot() в torgi_monitor.py."""
        prop_type = _detect_property_type(
            lot.get("category", ""),
            lot.get("landType", ""),
            lot.get("commercialType", ""),
        )

        card = cls(
            lotId=lot.get("lotId", ""),
            source="torgi",
            propertyType=prop_type,
            dateAdded=lot.get("dateAdded", ""),
            name=lot.get("lotName", ""),
            category=lot.get("category", ""),
            cadastralNumber=lot.get("cadastralNumber", ""),
            address=lot.get("address", ""),
            district=lot.get("district"),
            url=lot.get("url", ""),
            etpUrl=lot.get("etpUrl", ""),
            price=lot.get("price", 0.0),
            deposit=lot.get("deposit", 0.0),
            pricePerUnit=lot.get("pricePerUnit", ""),
            biddType=lot.get("biddType", ""),
            auctionDate=lot.get("auctionDate", ""),
            applicationEnd=lot.get("applicationEnd", ""),
            status=lot.get("status", ""),
            area=lot.get("areaNum", 0.0) or 0.0,
        )

        # Определяем areaUnit
        cat = lot.get("category", "").lower()
        if "земл" in cat or "участ" in cat:
            card.areaUnit = "sotka" if card.area < 500 else "ha"
        else:
            card.areaUnit = "m2"

        # Рыночная оценка (если уже есть из torgi_monitor)
        card.marketPrice = lot.get("marketPrice")
        card.marketPricePerUnit = lot.get("marketPricePerUnit")
        card.discount = lot.get("discount")
        card.confidence = lot.get("confidence")
        card.analogsCount = lot.get("analogsCount")

        # Инициализируем блоки по типу
        _init_blocks(card, lot)

        return card


# ============================================================
# Вспомогательные функции
# ============================================================

def _detect_property_type(category: str, land_type: str, commercial_type: str) -> str:
    """Определяет propertyType из полей torgi_monitor."""
    cat = category.lower()

    if any(w in cat for w in ("квартир", "комнат", "жил")):
        return "apartment"
    if any(w in cat for w in ("дом",)):
        return "house"
    if any(w in cat for w in ("земл", "участ")):
        return "land"
    if any(w in cat for w in ("нежил", "гараж", "здани", "помещен", "сооружен")):
        return "commercial"

    # Фаллбек по вторичным признакам
    if land_type:
        return "land"
    if commercial_type:
        return "commercial"

    return "commercial"  # default для неопределённых


def _init_blocks(card: PropertyCard, lot: dict) -> None:
    """Инициализирует специализированные блоки по типу объекта."""
    if card.propertyType == "apartment":
        card.apartment = ApartmentInfo()
        card.building = BuildingInfo()
        card.infra = InfraInfo()

    elif card.propertyType == "land":
        card.land = LandInfo(
            landCategory=lot.get("landType"),
        )
        # Для промышленной земли — арендный блок
        lt = (lot.get("landType") or "").lower()
        if "пром" in lt:
            card.rental = RentalInfo()

    elif card.propertyType == "house":
        card.house = HouseInfo()
        card.land = LandInfo(
            landCategory=lot.get("landType"),
        )
        card.infra = InfraInfo()

    elif card.propertyType == "commercial":
        card.commercial = CommercialInfo(
            commercialType=lot.get("commercialType"),
        )
        card.building = BuildingInfo()
        card.rental = RentalInfo()
        card.infra = InfraInfo()


_CAMEL_RE = re.compile(r"(?<=[a-z0-9])([A-Z])")


def _camel_to_snake(name: str) -> str:
    return _CAMEL_RE.sub(r"_\1", name).lower()


def _camel_to_snake_dict(d: dict) -> dict:
    """Рекурсивно конвертирует ключи dict из camelCase в snake_case."""
    out = {}
    for k, v in d.items():
        new_key = _camel_to_snake(k)
        if isinstance(v, dict):
            out[new_key] = _camel_to_snake_dict(v)
        else:
            out[new_key] = v
    return out
