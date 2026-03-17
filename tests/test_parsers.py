from __future__ import annotations

from fertimap.parsers import parse_calcul_response, parse_culture_rules, parse_geo_and_soil


def test_parse_geo_and_soil() -> None:
    html = """
    <input id="x_coord" value="-7.1" />
    <input id="y_coord" value="33.1" />
    <input id="id_province" value="17" />
    <h3>Région : Test Region</h3>
    <h3>Province : Test Province</h3>
    <h3>Commune : Test Commune</h3>
    <table>
      <tr><th>Type de sol</th><td>Sandy</td></tr>
      <tr><th>Texture globale</th><td>Coarse</td></tr>
    </table>
    <input id="ph" value="7.2" />
    <input id="mo" value="1.1" />
    <input id="p" value="20" />
    <input id="k" value="150" />
    <input id="rdt" min="10" max="30" step="5" value="20" />
    <output id="ValueUnit">q/ha</output>
    """
    parsed = parse_geo_and_soil(html)
    assert parsed.longitude == -7.1
    assert parsed.latitude == 33.1
    assert parsed.region == "Test Region"
    assert parsed.soil_type == "Sandy"
    assert parsed.slider_rdt_unit == "q/ha"


def test_parse_culture_rules() -> None:
    html = """
    <input type="hidden" name="culture1" value="Blé tendre" />
    <input type="hidden" name="min1" value="10" />
    <input type="hidden" name="max1" value="50" />
    <input type="hidden" name="step1" value="10" />
    <input type="hidden" name="unite1" value="q/ha" />
    """
    rules = parse_culture_rules(html)
    assert rules[1].culture_name_en == "Wheat (Rainfed)"
    assert rules[1].culture_name_raw == "Blé tendre"
    assert rules[1].rdt_max == 50


def test_parse_calcul_response() -> None:
    html = """
    <tr><th>kg N/ha</th><td>100</td></tr>
    <tr><th>kg P/ha</th><td>40</td></tr>
    <tr><th>kg K/ha</th><td>20</td></tr>
    """
    parsed = parse_calcul_response(html)
    assert parsed == {"N_kg_ha": 100.0, "P_kg_ha": 40.0, "K_kg_ha": 20.0}
