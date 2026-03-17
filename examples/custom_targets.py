"""Examples with multiple custom targets and soil overrides."""

from fertimap import FertiMapClient

client = FertiMapClient()

df = client.get_recommendations(
    longitude=-7.616,
    latitude=33.589,
    culture_name_en="Wheat (Rainfed)",
    target_yield=[25, 35, 45],
    ph=7.8,
    matiere_organique_pct=1.9,
    p_assimilable_mgkg_p2o5=28,
    k_mgkg_k2o=210,
)

print(df[["culture_name_en", "rdt_level", "target_yield", "target_yield_mode", "N_kg_ha", "P_kg_ha", "K_kg_ha"]])

# Expected output placeholder:
#      culture_name_en rdt_level  target_yield target_yield_mode  N_kg_ha  P_kg_ha  K_kg_ha
# 0  Wheat (Rainfed)     custom          25.0            custom      ...      ...      ...
