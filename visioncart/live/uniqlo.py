"""Uniqlo US product search (the public JSON API behind uniqlo.com's own search box).

Every fact on a card (name, price, sizes, photo, link) comes from this response, never from a
model. Uniqlo's search matches keywords literally, so the worker searches by category word
("sweater", "jeans") and lets the style verifier do the selecting.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx

SEARCH_URL = "https://www.uniqlo.com/us/api/commerce/v5/en/products"
PRODUCT_URL = "https://www.uniqlo.com/us/en/products/{product_id}/{price_group}"
MENS = {"MEN", "UNISEX"}

# Planner categories -> the word Uniqlo's search understands.
KEYWORDS = {"t-shirt": "t-shirt", "hoodie": "hoodie", "sweatshirt": "sweatshirt", "pants": "pants",
            "jeans": "jeans", "shorts": "shorts", "shirt": "shirt", "polo": "polo", "sweater": "sweater",
            "cardigan": "cardigan", "jacket": "jacket", "coat": "coat", "fleece": "fleece", "vest": "vest",
            "hat": "cap", "bag": "bag", "belt": "belt", "socks": "socks"}


@dataclass
class UniqloItem:
    product_id: str
    name: str
    price: float
    image_url: str
    url: str
    color: str
    sizes: list[str] = field(default_factory=list)


def parse_item(it: dict) -> UniqloItem | None:
    if it.get("genderName") not in MENS:
        return None
    prices = it.get("prices") or {}
    price = ((prices.get("promo") or {}).get("value")) or ((prices.get("base") or {}).get("value"))
    main = (it.get("images") or {}).get("main") or {}
    rep = ((it.get("representative") or {}).get("color") or {}).get("displayCode")
    image = (main.get(rep) or next(iter(main.values()), {})).get("image")
    if not (it.get("productId") and it.get("name") and price and image):
        return None
    color = ((it.get("representative") or {}).get("color") or {}).get("name", "")
    return UniqloItem(product_id=it["productId"], name=it["name"], price=float(price), image_url=image,
                      url=PRODUCT_URL.format(product_id=it["productId"], price_group=it.get("priceGroup", "00")),
                      color=color.title(), sizes=[s["name"] for s in it.get("sizes") or [] if s.get("name")])


async def search(client: httpx.AsyncClient, category: str, limit: int = 100) -> list[UniqloItem]:
    """Men's and unisex items for a category, in Uniqlo's own relevance order."""
    r = await client.get(SEARCH_URL, params={"q": KEYWORDS.get(category, category), "limit": limit})
    r.raise_for_status()
    items = [parse_item(it) for it in r.json()["result"]["items"]]
    seen, out = set(), []
    for item in items:
        if item and item.product_id not in seen:
            seen.add(item.product_id)
            out.append(item)
    return out
