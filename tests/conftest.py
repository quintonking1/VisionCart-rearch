"""Offline fixtures: a deterministic fake LLM and a tiny two-style catalog."""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from visioncart.agents.types import Deps  # noqa: E402
from visioncart.catalog.search import CatalogSearch, tokenize  # noqa: E402
from visioncart.catalog.store import Catalog, Product  # noqa: E402
from visioncart.llm import normalize  # noqa: E402
from visioncart.memory.store import StyleCluster, StyleMemory  # noqa: E402
from visioncart.vision import ImageAttributes, search_text, style_text  # noqa: E402

DIM = 256


def bow_embed(text: str) -> np.ndarray:
    v = np.zeros(DIM, dtype=np.float32)
    for t in tokenize(text):
        v[int(hashlib.md5(t.encode()).hexdigest(), 16) % DIM] += 1
    return normalize(v)


class FakeLLM:
    """Bag-of-words embeddings, so cosine tracks word overlap; parse() dispatches on schema."""

    def __init__(self, handlers=None):
        self.handlers = handlers or {}
        self.calls: list[str] = []

    async def embed(self, texts):
        return np.stack([bow_embed(t) for t in texts])

    async def parse(self, schema, system, user, images=(), model=None):
        self.calls.append(schema.__name__)
        if schema.__name__ in self.handlers:
            return self.handlers[schema.__name__](user)
        if schema.__name__ == "Queries":
            item = re.search(r"ITEM: (.*)", user).group(1)
            terms = re.search(r"STYLE TERMS: (.*)", user).group(1)
            return schema(queries=[f"{item} {terms}", item])
        if schema.__name__ == "Explanations":
            ids = re.findall(r"product_id (\w+)", user)
            return schema(items=[{"product_id": i, "why": "Shares the board's palette."} for i in ids])
        raise AssertionError(f"no fake handler for {schema.__name__}")


DARK = dict(palette=["oxblood", "chocolate"], materials=["tweed", "wool"], textures=["herringbone"], signature_details=["elbow patches"],
            silhouette="tailored", era_influences=["edwardian"], mood=["moody", "scholarly"],
            aesthetic_tags=["dark academia"], style_summary="moody scholarly tweed")
LIGHT = dict(palette=["cream", "sky"], materials=["linen", "cotton"], textures=["gauzy"], signature_details=["rope trim"],
             silhouette="flowing", era_influences=["seventies"], mood=["airy", "sunny"],
             aesthetic_tags=["coastal"], style_summary="airy sunny linen")


def attrs(style: dict, what: str, water=False) -> ImageAttributes:
    return ImageAttributes(item_description=what, water_resistant=water, warmth="medium", **style)


def make_product(pid, name, category, style, price=100.0, in_stock=True, sizes=(), water=False) -> Product:
    a = attrs(style, f"a {category}", water)
    return Product.from_record({"id": pid, "name": name, "category": category, "image": f"img/{pid}.jpg",
                                "price": price, "in_stock": in_stock, "sizes": list(sizes), "link": None,
                                "attributes": a.model_dump()})


@pytest.fixture
def catalog() -> Catalog:
    products = [
        make_product("d1", "Tweed Blazer", "blazer", DARK, price=200, sizes=["S", "M"]),
        make_product("d2", "Wool Blazer", "blazer", DARK, price=450, sizes=["M"]),
        make_product("l1", "Linen Blazer", "blazer", LIGHT, price=120, sizes=["S", "M", "L"]),
        make_product("d3", "Leather Satchel", "bag", DARK, price=180),
        make_product("d4", "Tweed Tote", "bag", DARK, price=90, in_stock=False),
        make_product("l2", "Straw Tote", "bag", LIGHT, price=60),
    ]
    style = np.stack([bow_embed(style_text(p.attributes)) for p in products])
    search = np.stack([bow_embed(search_text(p.name, p.category, p.attributes)) for p in products])
    return Catalog(products, style, search)


@pytest.fixture
def memory() -> StyleMemory:
    dark = StyleCluster(0, "Moody scholar", "oxblood tweed, moody", ["oxblood", "tweed", "wool"], ["neon"],
                        centroid=bow_embed(style_text(attrs(DARK, "x"))))
    light = StyleCluster(1, "Airy coast", "cream linen, airy", ["cream", "linen"], ["leather"],
                         centroid=bow_embed(style_text(attrs(LIGHT, "x"))))
    return StyleMemory("u1", "hash", [dark, light])


@pytest.fixture
def make_deps(catalog, memory):
    def _make(llm, threshold=0.5, blend=0.0) -> Deps:
        return Deps(llm=llm, catalog=catalog, search=CatalogSearch(catalog), memory=memory, threshold=threshold,
                    blend=blend)
    return _make
