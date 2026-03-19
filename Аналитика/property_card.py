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
    analogsList: list | None = None       # до 10 аналогов: {price, area, pricePerUnit, distance_m, address, url, lat, lon}
    analogsSource: str | None = None      # "ads-api" / "manual"
    analogsRadiusM: float | None = None   # использованный радиус фильтрации (м)
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

    # === Геометрия ===
    boundaryGeojson: dict | None = None   # GeoJSON Polygon/MultiPolygon WGS-84 (из НСПД)

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
                           "commercial", "rental", "infra", "boundaryGeojson"):
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

        # Парсим описание лота для заполнения специализированных блоков
        _parse_description(card, lot)

        return card


# ============================================================
# Вспомогательные функции
# ============================================================

def _detect_property_type(category: str, land_type: str, commercial_type: str) -> str:
    """Определяет propertyType из полей torgi_monitor."""
    cat = category.lower()

    # "нежилое" ПЕРЕД "жилое" (иначе "нежилое" матчится как "жил")
    if "нежил" in cat:
        return "commercial"
    if any(w in cat for w in ("квартир", "комнат", "жил")):
        return "apartment"
    if any(w in cat for w in ("дом",)):
        return "house"
    if any(w in cat for w in ("земл", "участ")):
        return "land"
    if any(w in cat for w in ("гараж", "здани", "помещен", "сооружен")):
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


def _parse_description(card: PropertyCard, lot: dict) -> None:
    """Парсит lotName + lotDescription и заполняет специализированные блоки."""
    name = lot.get("lotName", "") or ""
    desc = lot.get("lotDesc", "") or ""
    text = (name + " " + desc).lower()

    if card.propertyType == "apartment" and card.apartment:
        _parse_apartment(card.apartment, text)
    elif card.propertyType == "land" and card.land:
        _parse_land(card.land, text)
    elif card.propertyType == "house":
        if card.house:
            _parse_house(card.house, text)
        if card.land:
            _parse_land(card.land, text)
    elif card.propertyType == "commercial" and card.commercial:
        _parse_commercial(card.commercial, text)


def _parse_int(pattern: str, text: str) -> int | None:
    """Извлечь целое число по regex паттерну."""
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except (ValueError, IndexError):
            pass
    return None


def _parse_float(pattern: str, text: str) -> float | None:
    """Извлечь дробное число по regex паттерну."""
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except (ValueError, IndexError):
            pass
    return None


def _parse_apartment(info: ApartmentInfo, text: str) -> None:
    """Парсинг параметров квартиры из описания."""
    # Комнаты: "2-комнатная", "3-х комнатная", "комнат: 2"
    info.rooms = _parse_int(
        r"(\d)\s*-?\s*(?:х\s*)?комнатн|комнат\w*\s*:?\s*(\d)", text
    )
    if info.rooms is None:
        m = re.search(r"(\d)\s*-?\s*(?:х\s*)?комнатн", text)
        if m:
            info.rooms = int(m.group(1))
        else:
            m = re.search(r"комнат\w*\s*:?\s*(\d)", text)
            if m:
                info.rooms = int(m.group(1))

    # Этаж: "этаж 3", "3 этаж", "на 5 этаже", "3/9"
    m = re.search(r"(\d+)\s*/\s*(\d+)\s*(?:эт|этаж)", text)
    if m:
        info.floor = int(m.group(1))
        info.floorsTotal = int(m.group(2))
    else:
        info.floor = _parse_int(r"(?:этаж|на)\s+(\d+)\s*(?:этаж)?", text)
        info.floorsTotal = _parse_int(r"(\d+)\s*(?:-\s*)?этажн", text)

    # Балкон
    if "балкон" in text or "лоджи" in text:
        info.balcony = True


def _parse_land(info: LandInfo, text: str) -> None:
    """Парсинг параметров земельного участка из описания."""
    # ВРИ (вид разрешённого использования)
    m = re.search(
        r"(?:разрешённое|разрешенное)\s+использование\s*[–—:-]\s*(.+?)(?:\.|,\s*(?:общ|площ|кад)|\n|$)",
        text,
    )
    if m:
        info.permittedUse = m.group(1).strip()[:120]

    # landCategory уже может быть заполнен из extract_land_type()
    # Дополнительно проверяем ВРИ
    if not info.landCategory:
        if any(w in text for w in ("ижс", "индивидуальное жилищное", "жилая застройка")):
            info.landCategory = "ИЖС"
        elif any(w in text for w in ("снт", "днп", "садовод", "дачн")):
            info.landCategory = "СНТ"
        elif any(w in text for w in ("лпх", "личное подсобное")):
            info.landCategory = "ЛПХ"
        elif any(w in text for w in ("промышлен", "промназначени")):
            info.landCategory = "Промка"
        elif any(w in text for w in ("сельхоз", "сельскохоз")):
            info.landCategory = "Сельхоз"

    # Коммуникации
    info.hasElectricity = _has_communication(text, ("электр", "электроснабж", "э/снабж"))
    info.hasGas = _has_communication(text, ("газ", "газоснабж", "газифиц"))
    info.hasWater = _has_communication(text, ("водоснабж", "водопровод", "водоподач", "скважин"))
    info.hasSewage = _has_communication(text, ("канализац", "водоотвед", "септик"))

    # Примечание о коммуникациях
    comms = []
    if info.hasElectricity:
        comms.append("электричество")
    if info.hasGas:
        comms.append("газ")
    if info.hasWater:
        comms.append("вода")
    if info.hasSewage:
        comms.append("канализация")
    if comms:
        info.communicationsNote = ", ".join(comms)


def _has_communication(text: str, keywords: tuple) -> bool | None:
    """Проверяет наличие коммуникации в тексте. None если не упоминается."""
    for kw in keywords:
        if kw in text:
            idx = text.index(kw)
            # Контекст до и после ключевого слова
            before = text[max(0, idx - 20):idx]
            after = text[idx:idx + len(kw) + 30]
            if any(neg in before or neg in after for neg in ("нет ", "без ", "отсутств")):
                return False
            return True
    return None


def _parse_house(info: HouseInfo, text: str) -> None:
    """Парсинг параметров дома из описания."""
    # Комнаты
    m = re.search(r"(\d)\s*-?\s*(?:х\s*)?комнатн", text)
    if m:
        info.rooms = int(m.group(1))

    # Этажность дома
    info.floorsTotal = _parse_int(r"(\d+)\s*(?:-\s*)?этажн", text)

    # Год постройки
    info.buildYear = _parse_int(r"(?:год\w*\s+постройки|построен\w*\s+в)\s*:?\s*(\d{4})", text)
    if not info.buildYear:
        info.buildYear = _parse_int(r"(\d{4})\s*г\.?\s*(?:постройки|строительства)", text)

    # Материал стен
    if any(w in text for w in ("кирпич", "кирп.")):
        info.wallMaterial = "кирпич"
    elif any(w in text for w in ("бревн", "бруc", "деревян")):
        info.wallMaterial = "дерево"
    elif "блок" in text and "блокир" not in text:
        info.wallMaterial = "блок"
    elif "панел" in text:
        info.wallMaterial = "панель"
    elif "каркас" in text:
        info.wallMaterial = "каркас"

    # Площадь дома (м2)
    m = re.search(r"(?:площад\w*\s+(?:дома|жилого|строения))\s*:?\s*([\d,.]+)\s*(?:кв\.?\s*м|м2)", text)
    if m:
        try:
            info.houseArea = float(m.group(1).replace(",", "."))
        except ValueError:
            pass

    # Площадь участка (сотки)
    m = re.search(r"(?:площад\w*\s+(?:участка|земельного))\s*:?\s*([\d,.]+)\s*(?:сот|кв\.?\s*м|м2)", text)
    if m:
        try:
            val = float(m.group(1).replace(",", "."))
            # Если > 100, скорее всего м2
            info.landArea = val / 100 if val > 100 else val
        except ValueError:
            pass

    # Гараж / баня
    info.garageOnSite = "гараж" in text or None
    info.bathhouse = "баня" in text or "бани" in text or None


def _parse_commercial(info: CommercialInfo, text: str) -> None:
    """Парсинг параметров нежилого помещения из описания."""
    # commercialType уже может быть заполнен из extract_commercial_type()
    if not info.commercialType:
        if any(w in text for w in ("офис",)):
            info.commercialType = "Офис"
        elif any(w in text for w in ("торгов", "магазин")):
            info.commercialType = "Торговое"
        elif "склад" in text:
            info.commercialType = "Склад"
        elif any(w in text for w in ("производств", "цех")):
            info.commercialType = "Производство"

    # Этаж
    info.floor = _parse_int(r"(?:этаж|на)\s+(\d+)", text)

    # Высота потолков
    info.ceilingHeight = _parse_float(r"высот\w*\s+(?:потолк\w*|помещен\w*)\s*:?\s*([\d,.]+)\s*м", text)

    # Отдельный вход
    if "отдельн" in text and "вход" in text:
        info.entrance = "отдельный"


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
