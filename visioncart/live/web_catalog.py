"""A catalog that grows as the live worker pulls products from a store.

Same read interface the verifier, presenter and feedback use on the static Catalog, so the rest
of the pipeline doesn't know whether a product came from the dataset or the web.
"""
from __future__ import annotations

import hashlib

import httpx
import numpy as np

from visioncart import config
from visioncart.catalog.store import Product

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
           "Accept-Language": "en-US,en;q=0.9"}
IMAGES_DIR = config.LIVE_DIR / "images"


def http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15)


async def download_image(client: httpx.AsyncClient, image_url: str) -> str | None:
    """Local copy (path relative to ROOT) so the captioner and the UI read the same bytes."""
    path = IMAGES_DIR / f"{hashlib.sha1(image_url.encode()).hexdigest()[:16]}.jpg"
    if path.exists():
        return str(path.relative_to(config.ROOT))
    try:
        r = await client.get(image_url)
    except httpx.HTTPError:
        return None
    if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image/"):
        return None
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    return str(path.relative_to(config.ROOT))


class LiveCatalog:
    def __init__(self):
        self.products: list[Product] = []
        self.by_id: dict[str, Product] = {}
        self._style: dict[str, np.ndarray] = {}
        self._search: dict[str, np.ndarray] = {}

    def add(self, product: Product, style_vec: np.ndarray, search_vec: np.ndarray) -> None:
        if product.id not in self.by_id:
            self.products.append(product)
        self.by_id[product.id] = product
        self._style[product.id] = style_vec
        self._search[product.id] = search_vec

    def categories(self) -> list[str]:
        return list(config.LIVE_CATEGORIES)

    def get(self, pid: str) -> Product:
        return self.by_id[pid]

    def style_vec(self, pid: str) -> np.ndarray:
        return self._style[pid]

    def search_vec(self, pid: str) -> np.ndarray:
        return self._search[pid]

    def __contains__(self, pid: str) -> bool:
        return pid in self.by_id
