"""
detail_parser.py — Парсинг детальных страниц лотов для обогащения данных.

Источники:
  - tbankrot.ru — банкротные торги (HTML)
  - fedresurs.ru — ЕФРСБ (JSON API)
  - torgi.gov.ru — госторги (JSON API)

Извлекает: area, address, cadastral_number
"""

import re
import subprocess
import tempfile
import json
import logging
import requests

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# --- Regex patterns ---

AREA_PATTERNS = [
    r"(?:площадь[юи]?|S|общ\.?\s*пл\.?)[:\s=]*([\d\s,.]+)\s*(?:кв\.?\s*м|м[²2]|сот|га)",
    r"(\d+[.,]\d+)\s*(?:кв\.?\s*м|м[²2]|сот|га)",
    r"(\d+)\s*(?:кв\.?\s*м|м[²2])\b",
    r"(\d+)\s*сот(?:ок|ки|ка)?",
]

CADASTRAL_PATTERN = r"\b(\d{2}:\d{2}:\d{5,7}:\d{1,6})\b"

ADDRESS_KEYWORDS = re.compile(
    r"(край|область|округ|город|г\.|ул\.|улица|пер\.|переулок|пр\.|проспект|"
    r"д\.|дом\b|кв\.|квартира|район|р-н|село|деревня|пос\.|поселок|посёлок|"
    r"республика|обл\.|мкр|микрорайон)",
    re.IGNORECASE
)


def _clean_area(raw: str) -> float | None:
    """Очистка строки площади -> float."""
    s = raw.replace(" ", "").replace(",", ".")
    try:
        val = float(s)
        return val if val > 0 else None
    except ValueError:
        return None


def _extract_area(text: str) -> float | None:
    """Извлечь площадь из текста, пробуя все паттерны."""
    for pat in AREA_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = _clean_area(m.group(1))
            if val and val < 100000:  # sanity check
                return val
    return None


def _extract_cadastral(text: str) -> str | None:
    """Извлечь кадастровый номер."""
    m = re.search(CADASTRAL_PATTERN, text)
    return m.group(1) if m else None


def _extract_address(text: str) -> str | None:
    """Извлечь адрес из текста."""
    # Clean HTML for text search
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean)

    # Try structured patterns first (priority order)
    patterns = [
        r"[Мм]естонахождени[ея][^:]*:\s*(.{10,250}?)(?:\s*Категория|\s*Форма|\s*$)",
        r"адрес:\s*(.{10,200}?)(?:\s*\(|\s*Сведения|\s*Категория|\s*$)",
        r"[Аа]дрес[:\s]+(.{10,200})",
    ]
    for pat in patterns:
        m = re.search(pat, clean)
        if m:
            addr = m.group(1).strip().rstrip(".,;(")
            if ADDRESS_KEYWORDS.search(addr) and len(addr) > 10:
                return addr[:250]

    # Fallback: find lines with address keywords
    for line in text.split("\n"):
        line = line.strip()
        if 20 < len(line) < 300 and ADDRESS_KEYWORDS.search(line):
            line_clean = re.sub(r"<[^>]+>", " ", line).strip()
            if len(line_clean) > 15:
                return line_clean[:250]

    return None


# --- Source parsers ---

def parse_tbankrot_detail(lot_id: str) -> dict:
    """Parse tbankrot.ru detail page."""
    tb_id = lot_id.replace("TB-", "")
    url = f"https://tbankrot.ru/item?id={tb_id}"
    result = {"area": None, "address": None, "cadastral_number": None}

    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        resp.raise_for_status()
        text = resp.text

        # Extract from page text (strip HTML for regex)
        clean_text = re.sub(r"<[^>]+>", " ", text)
        clean_text = re.sub(r"\s+", " ", clean_text)

        result["area"] = _extract_area(clean_text)
        result["cadastral_number"] = _extract_cadastral(clean_text)
        result["address"] = _extract_address(text)

        log.info("tbankrot %s parsed: %s", lot_id, {k: v for k, v in result.items() if v})
    except Exception as e:
        log.error("tbankrot %s error: %s", lot_id, e)

    return result


def parse_efrsb_detail(lot_id: str) -> dict:
    """Parse EFRSB detail. lot_id: EFRSB-{guid}-{N} or ЕФРСБ-{guid}-{N}"""
    result = {"area": None, "address": None, "cadastral_number": None}

    # Extract guid
    parts = lot_id.split("-")
    if len(parts) >= 2:
        # EFRSB-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx-N
        # or ЕФРСБ-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx-N
        # GUID is parts 1..5 joined
        try:
            guid = "-".join(parts[1:6])  # UUID has 5 segments
        except IndexError:
            log.error("efrsb: cannot extract guid from %s", lot_id)
            return result
    else:
        log.error("efrsb: bad lot_id format %s", lot_id)
        return result

    # Use curl (Qrator blocks Python requests)
    api_url = f"https://fedresurs.ru/backend/bankruptcy-messages/{guid}"
    try:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        cmd = [
            "curl", "-s", "-o", tmp_path,
            "-H", f"User-Agent: {UA}",
            "-H", "Accept: application/json",
            "--max-time", "15",
            api_url,
        ]
        subprocess.run(cmd, capture_output=True, timeout=20)

        with open(tmp_path, "r") as f:
            data = json.load(f)

        # Combine all text fields for parsing
        texts = []
        if "content" in data:
            texts.append(str(data["content"]))
        if "lotTable" in data:
            for lot_row in data.get("lotTable", []):
                texts.append(json.dumps(lot_row, ensure_ascii=False))
        if "additionalInfo" in data:
            texts.append(str(data["additionalInfo"]))

        combined = " ".join(texts)
        clean = re.sub(r"<[^>]+>", " ", combined)
        clean = re.sub(r"\s+", " ", clean)

        result["area"] = _extract_area(clean)
        result["cadastral_number"] = _extract_cadastral(clean)
        result["address"] = _extract_address(combined)

        log.info("efrsb %s parsed: %s", lot_id, {k: v for k, v in result.items() if v})
    except Exception as e:
        log.error("efrsb %s error: %s", lot_id, e)
    finally:
        import os
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    return result


def parse_torgi_detail(lot_id: str) -> dict:
    """Parse torgi.gov.ru detail."""
    result = {"area": None, "address": None, "cadastral_number": None}
    api_url = f"https://torgi.gov.ru/new/api/public/lotcards/{lot_id}"

    try:
        resp = requests.get(api_url, headers={"User-Agent": UA}, timeout=15, verify=False)
        resp.raise_for_status()
        data = resp.json()

        # Parse characteristics
        for char in data.get("characteristics", []):
            code = char.get("code", "")
            val = char.get("characteristicValue", "")
            if not val:
                continue
            if code in ("Address", "estateAddress") or "адрес" in char.get("name", "").lower():
                if val and val != "Российская Федерация" and len(val) > 5:
                    result["address"] = val
            elif code in ("Square", "area") or "площадь" in char.get("name", "").lower():
                result["area"] = _clean_area(str(val))
            elif code in ("CadastralNumber", "cadastralNumber"):
                result["cadastral_number"] = val

        # Fallbacks from top-level fields
        if not result["address"] and data.get("estateAddress"):
            addr = data["estateAddress"]
            if addr != "Российская Федерация" and len(addr) > 5:
                result["address"] = addr

        # Try lotDescription for missing data
        desc = data.get("lotDescription", "") or ""
        if not result["area"]:
            result["area"] = _extract_area(desc)
        if not result["cadastral_number"]:
            result["cadastral_number"] = _extract_cadastral(desc)
        if not result["address"]:
            result["address"] = _extract_address(desc)

        log.info("torgi %s parsed: %s", lot_id, {k: v for k, v in result.items() if v})
    except Exception as e:
        log.error("torgi %s error: %s", lot_id, e)

    return result
