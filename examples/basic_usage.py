"""Minimal example for the public API."""

from fertimap import FertiMapClient

client = FertiMapClient()
recommendations = client.recommend_site(
    longitude=-7.616,
    latitude=33.589,
    culture_name_en="Wheat (Rainfed)",
)
print(recommendations)
