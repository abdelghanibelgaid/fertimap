"""Minimal example for the public API."""

from fertimap import FertimapClient

client = FertimapClient()
recommendations = client.recommend_site(
    longitude=-7.616,
    latitude=33.589,
    crop_name="Wheat (Rainfed)",
)
print(recommendations)
