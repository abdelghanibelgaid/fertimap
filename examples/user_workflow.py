"""Typical interactive workflow for FertiMap users.

Replace coordinates with a real site before running.
"""

from fertimap import FertiMapClient

client = FertiMapClient()

# Step 1: inspect the site.
profile = client.get_site_profile(-7.616, 33.589)
print(profile)

# Expected output placeholder:
# SiteContext(longitude=-7.616, latitude=33.589, region='...', province='...', ...)

# Step 2: list all available crops and their target-yield ranges.
crops = client.list_crops(-7.616, 33.589)
print(crops[["culture_id", "culture_name_en", "rdt_min", "rdt_max", "rdt_unit"]])

# Expected output placeholder:
#    culture_id     culture_name_en  rdt_min  rdt_max rdt_unit
# 0           1   Wheat (Rainfed)     ...      ...    qx/ha

# Step 3: request recommendations for several levels at once.
recommendations = client.get_recommendations(
    longitude=-7.616,
    latitude=33.589,
    culture_name_en="Wheat (Rainfed)",
    rdt_level=["low", "medium", "high"],
)
print(
    recommendations[
        ["culture_name_en", "rdt_level", "target_yield", "N_kg_ha", "P_kg_ha", "K_kg_ha"]
    ]
)

# Expected output placeholder:
#      culture_name_en rdt_level  target_yield  N_kg_ha  P_kg_ha  K_kg_ha
# 0  Wheat (Rainfed)        low          ...      ...      ...      ...
