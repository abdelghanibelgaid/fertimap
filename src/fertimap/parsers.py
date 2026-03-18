"""HTML parsers for Fertimap endpoints."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from fertimap.constants import CROP_ID
from fertimap.models import CultureRule, SiteContext
from fertimap.utils import maybe_fix_mojibake, to_float


def parse_geo_and_soil(html: str) -> SiteContext:
    """Parse one ``detail.inc.php`` HTML response."""
    soup = BeautifulSoup(maybe_fix_mojibake(html), "html.parser")

    x_input = soup.find("input", {"id": "x_coord"})
    y_input = soup.find("input", {"id": "y_coord"})
    lon = to_float(x_input.get("value")) if x_input else None
    lat = to_float(y_input.get("value")) if y_input else None

    region = province = commune = None
    id_province_input = soup.find("input", {"id": "id_province"})
    id_province = id_province_input.get("value") if id_province_input else None

    for heading in soup.find_all("h3"):
        text = maybe_fix_mojibake(heading.get_text(" ", strip=True).replace(" ", " "))
        if "Région" in text or "Region" in text:
            region = text.split(":", 1)[-1].strip()
        elif "Préfecture" in text or "Province" in text:
            province = text.split(":", 1)[-1].strip()
        elif "Commune" in text:
            commune = text.split(":", 1)[-1].strip()

    fert_table = None
    for table in soup.find_all("table"):
        th = table.find("th", string=lambda t: t and "Type de sol" in t)
        if th:
            fert_table = table
            break

    soil_type = texture_globale = None
    if fert_table:
        soil_th = fert_table.find("th", string=lambda t: t and "Type de sol" in t)
        if soil_th:
            soil_td = soil_th.find_next("td")
            soil_type = maybe_fix_mojibake(soil_td.get_text(" ", strip=True)) if soil_td else None

        texture_th = fert_table.find("th", string=lambda t: t and "Texture globale" in t)
        if texture_th:
            texture_td = texture_th.find_next("td")
            texture_globale = maybe_fix_mojibake(texture_td.get_text(" ", strip=True)) if texture_td else None

    ph_input = soup.find("input", {"id": "ph"})
    mo_input = soup.find("input", {"id": "mo"})
    p_input = soup.find("input", {"id": "p"})
    k_input = soup.find("input", {"id": "k"})

    rdt_input = soup.find("input", {"id": "rdt"})
    rdt_unit_output = soup.find("output", {"id": "ValueUnit"})

    return SiteContext(
        longitude=lon,
        latitude=lat,
        region=region,
        province=province,
        id_province=id_province,
        commune=commune,
        soil_type=soil_type,
        texture_globale=texture_globale,
        ph=to_float(ph_input.get("value") if ph_input else None),
        matiere_organique_pct=to_float(mo_input.get("value") if mo_input else None),
        p_assimilable_mgkg_p2o5=to_float(p_input.get("value") if p_input else None),
        k_mgkg_k2o=to_float(k_input.get("value") if k_input else None),
        slider_target_yield_min=to_float(rdt_input.get("min") if rdt_input else None),
        slider_target_yield_max=to_float(rdt_input.get("max") if rdt_input else None),
        slider_target_yield_step=to_float(rdt_input.get("step") if rdt_input else None),
        slider_target_yield_default=to_float(rdt_input.get("value") if rdt_input else None),
        slider_target_yield_unit=(rdt_unit_output.get_text(strip=True) if rdt_unit_output else None),
    )


def parse_culture_rules(html: str) -> dict[int, CultureRule]:
    """Parse all crop slider rules available for the current site."""
    soup = BeautifulSoup(maybe_fix_mojibake(html), "html.parser")
    culture_rules: dict[int, CultureRule] = {}

    for inp in soup.find_all("input", {"type": "hidden"}):
        name = (inp.get("name") or "").strip()
        value = maybe_fix_mojibake(inp.get("value", "").strip())
        match = re.match(r"(culture|min|max|step|unite)(\d+)$", name)
        if not match:
            continue

        key, cid_str = match.groups()
        cid = int(cid_str)
        meta = culture_rules.setdefault(cid, CultureRule(culture_id=cid))

        if key == "culture":
            meta.culture_name_raw = value
        elif key == "min":
            meta.target_yield_min = to_float(value)
        elif key == "max":
            meta.target_yield_max = to_float(value)
        elif key == "step":
            meta.target_yield_step = to_float(value)
        elif key == "unite":
            meta.target_yield_unit = value

    for cid, meta in culture_rules.items():
        meta.crop_name = CROP_ID.get(cid, meta.culture_name_raw)

    return culture_rules


def parse_calcul_response(html: str) -> dict[str, float | None]:
    """Parse calculator HTML and return only N, P, K recommendation values."""
    soup = BeautifulSoup(maybe_fix_mojibake(html), "html.parser")

    n_kg_ha = p_kg_ha = k_kg_ha = None

    for row in soup.find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        if not th or not td:
            continue
        label = " ".join(th.stripped_strings).lower()
        value = to_float(td.get_text(strip=True))

        if "kg n/ha" in label:
            n_kg_ha = value
        elif "kg p/ha" in label:
            p_kg_ha = value
        elif "kg k/ha" in label:
            k_kg_ha = value

    return {"N_kg_ha": n_kg_ha, "P_kg_ha": p_kg_ha, "K_kg_ha": k_kg_ha}
