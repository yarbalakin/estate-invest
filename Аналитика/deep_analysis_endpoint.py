"""
Deep Analysis endpoint code — copy into VPS main.py
Replace the existing deep_analysis function.
"""

# @app.get("/api/deep-analysis")
async def deep_analysis(request, lot_id: str = "", tb_id: str = ""):
    check_key(request)
    if not lot_id or not tb_id:
        return JSONResponse({"error": "lot_id and tb_id required"}, status_code=400,
                            headers={"Access-Control-Allow-Origin": "*"})

    import re as _re
    from bs4 import BeautifulSoup
    import requests as req

    try:
        # Login to TBankrot
        s = req.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        })
        s.post("https://tbankrot.ru/script/login.php", data={
            "email": "estatetorgi@yandex.ru",
            "password": "agent2025"
        }, allow_redirects=False, timeout=10)

        resp = s.get(f"https://tbankrot.ru/item?id={tb_id}", timeout=15)
        if resp.status_code != 200:
            return JSONResponse({"error": f"TBankrot HTTP {resp.status_code}"}, status_code=502,
                                headers={"Access-Control-Allow-Origin": "*"})

        soup = BeautifulSoup(resp.text, "html.parser")
        result = {"success": True}

        # --- 1. Encumbrances ---
        enc_block = soup.select_one("div.encumbrance__apartment")
        encumbrances = None
        if enc_block:
            encumbrances = {}
            for row in enc_block.select("div.row__info"):
                label_el = row.select_one("div.flex.align-center")
                data_el = row.select_one("div.data__row")
                if not label_el or not data_el:
                    continue
                label = label_el.get_text(strip=True).lower()
                value = data_el.get_text(separator=" ", strip=True)
                if "ипотек" in label:
                    encumbrances["mortgage"] = "нет" not in value.lower()
                elif "залог" in label:
                    encumbrances["pledge"] = "нет" not in value.lower()
                elif "арест" in label:
                    encumbrances["arrest"] = "нет" not in value.lower()
                elif "обремен" in label:
                    has = "нет" not in value.lower()
                    encumbrances["has_encumbrances"] = has
                    if has:
                        items = [li.get_text(strip=True) for li in row.select("ul li")]
                        encumbrances["encumbrance_list"] = items
        result["encumbrances"] = encumbrances

        # --- 2. Property card ---
        card = {}
        for bl in soup.select("div.realEstateAnalytics"):
            card["cadastral"] = bl.get("data-kad", "")
            card["lat"] = bl.get("data-lat", "")
            card["lon"] = bl.get("data-lon", "")
            for row in bl.select("div.characteristics__apartment div.row__info"):
                lab = row.select_one("div.flex.align-center")
                val = row.select_one("div.data__row")
                if not lab or not val:
                    continue
                k = lab.get_text(strip=True).lower()
                v = val.get_text(strip=True)
                if "площадь" in k:
                    card["area"] = v
                elif "стоимость" in k:
                    card["cadastral_value"] = v
                elif "этаж" in k:
                    card["floor"] = v
                elif "собственность" in k:
                    card["ownership"] = v
                elif "использован" in k:
                    card["permitted_use"] = v
            break
        result["card"] = card if card else None

        # --- 3. Photos ---
        photo_urls = list(set(_re.findall(
            r"https://files\.tbankrot\.ru/(?:lot_photo|address_photo)/(?:origins|thumbs)/[^'\"\s]+",
            resp.text
        )))
        origins = [u.rstrip("';\")") for u in photo_urls if "/origins/" in u]
        thumbs = [u.rstrip("';\")") for u in photo_urls if "/thumbs/" in u]
        result["photos"] = origins if origins else thumbs
        result["photos_count"] = len(result["photos"])

        # --- 4. Documents ---
        docs = []
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            txt = a.get_text(strip=True)
            if not txt or len(txt) < 3:
                continue
            h_low = href.lower()
            if any(x in h_low for x in [".pdf", ".doc", ".xls", ".zip", "document", "attachment", "download"]):
                if href.startswith("/"):
                    href = "https://tbankrot.ru" + href
                docs.append({"name": txt[:100], "url": href})
        result["documents"] = docs
        result["documents_count"] = len(docs)

        # --- 5. Links ---
        links = {}
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if "bankrot.fedresurs" in href:
                links["efrsb"] = href
            elif "torgi.gov" in href:
                links["torgi_gov"] = href
            elif any(x in href for x in ["rts-tender", "lot-online", "fabrikant", "sberbank-ast", "au-pro", "etpu.ru", "utender"]):
                links["etp"] = href
        result["links"] = links

        # --- 6. Debtor ---
        debtor = {}
        for div in soup.select("div"):
            t = div.get_text(strip=True)
            if t == "ИНН:":
                nxt = div.find_next_sibling("div")
                if nxt:
                    debtor["inn"] = nxt.get_text(strip=True)
        case_el = soup.find("a", href=_re.compile(r"kad\.arbitr\.ru"))
        if case_el:
            debtor["case"] = case_el.get_text(strip=True)
            debtor["case_url"] = case_el["href"]
        result["debtor"] = debtor if debtor else None

        # --- Update Supabase ---
        import os
        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
        update = {}
        if encumbrances:
            update["encumbrances"] = encumbrances
        if result["photos"]:
            update["photos"] = result["photos"]
        if docs:
            update["documents"] = [d["name"] for d in docs]
        if card:
            update["tbankrot_card"] = card
        if links.get("etp"):
            update["etp_url"] = links["etp"]
        if debtor:
            update["debtor_info"] = debtor
        if update:
            sb.table("properties").update(update).eq("lot_id", lot_id).execute()

        return JSONResponse(result, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        import traceback
        return JSONResponse({"error": str(e), "trace": traceback.format_exc()}, status_code=500,
                            headers={"Access-Control-Allow-Origin": "*"})
