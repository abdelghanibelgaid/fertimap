"""Batch example where the user CSV headers differ from the library schema."""

import pandas as pd

from fertimap import FertiMapClient

client = FertiMapClient()

raw = pd.DataFrame(
    [
        {"lon": -7.616, "lat": 33.589, "crop": "Wheat (Rainfed)", "targets": "low|high"},
        {"lon": -6.832, "lat": 33.972, "crop": "Barley (Rainfed)", "yield_values": "20|30"},
    ]
)

results = client.get_recommendations_batch(
    raw,
    column_map={
        "longitude": "lon",
        "latitude": "lat",
        "culture_name_en": "crop",
        "rdt_level": "targets",
        # Or use target_yield instead when your CSV contains numeric custom targets.
        # "target_yield": "yield_values",
    },
)

print(results.head())

# Expected output placeholder:
#    input_row_index  longitude  latitude     culture_name_en rdt_level  ...
# 0                0     -7.616    33.589  Wheat (Rainfed)        low  ...
