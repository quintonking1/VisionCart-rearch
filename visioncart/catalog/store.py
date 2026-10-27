"""The static product catalog the search tool and verifier read from.

Loading refuses any record carrying a ground-truth style field (see FORBIDDEN_CATALOG_KEYS),
which is how the original eval leak is kept out.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from visioncart import config
from visioncart.vision import ImageAttributes, style_terms

SIZED = {
    "apparel": {"blazer", "cardigan", "dress", "pants", "sweater", "top", "vest"},
    "footwear": {"loafer", "sneaker"},
}


@dataclass
class Product:
    id: str
    name: str
    category: str
    image: str
    price: float
    in_stock: bool
    sizes: list[str]
    link: str | None
    attributes: ImageAttributes
    terms: list[str] = field(default_factory=list)

    @classmethod
    def from_record(cls, r: dict) -> "Product":
        leaked = config.FORBIDDEN_CATALOG_KEYS & r.keys()
        if leaked:
            raise ValueError(f"catalog record {r.get('id')} carries label fields {sorted(leaked)}")
        attrs = ImageAttributes.model_validate(r["attributes"])
        return cls(id=r["id"], name=r["name"], category=r["category"], image=r["image"],
                   price=float(r["price"]), in_stock=bool(r["in_stock"]), sizes=list(r["sizes"]),
                   link=r.get("link"), attributes=attrs, terms=style_terms(attrs))


class Catalog:
    def __init__(self, products: list[Product], style_vecs: np.ndarray, search_vecs: np.ndarray):
        self.products = products
        self.style_vecs = style_vecs
        self.search_vecs = search_vecs
        self.by_id = {p.id: p for p in products}
        self.index = {p.id: i for i, p in enumerate(products)}

    @classmethod
    def load(cls, directory: Path = config.CATALOG_DIR) -> "Catalog":
        records = [json.loads(line) for line in (directory / "catalog.jsonl").read_text().splitlines() if line]
        emb = np.load(directory / "embeddings.npz")
        order = {pid: i for i, pid in enumerate(emb["ids"].tolist())}
        rows = [order[r["id"]] for r in records]
        return cls([Product.from_record(r) for r in records], emb["style"][rows], emb["search"][rows])

    def categories(self) -> list[str]:
        return sorted({p.category for p in self.products})

    def get(self, pid: str) -> Product:
        return self.by_id[pid]

    def style_vec(self, pid: str) -> np.ndarray:
        return self.style_vecs[self.index[pid]]
