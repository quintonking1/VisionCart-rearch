"""One-time catalog build: caption every image, embed, add synthetic commerce fields.

Captions board pins too, so style-memory sync later hits the cache. Price, stock and sizes
do not exist in the source data; they are generated from a fixed seed per product and are
marked synthetic in the README.

    python scripts/build_catalog.py
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from visioncart import config  # noqa: E402
from visioncart.catalog.store import SIZED  # noqa: E402
from visioncart.llm import OpenAILLM  # noqa: E402
from visioncart.vision import caption_image, search_text, style_text  # noqa: E402

PRICE_RANGES = {
    "bag": (60, 450), "blazer": (90, 520), "cardigan": (45, 220), "dress": (55, 260), "pants": (40, 280),
    "sweater": (60, 420), "top": (18, 70), "vest": (30, 140), "loafer": (90, 450), "sneaker": (55, 160),
    "bed frame": (300, 1600), "chair": (150, 1400), "credenza": (400, 1900), "rug": (120, 900),
    "curtains": (40, 220), "duvet": (90, 380), "pillow": (20, 90), "lamp": (60, 380),
    "pendant light": (40, 320), "vase": (18, 140), "bowl": (16, 80), "mug": (12, 48),
    "candle holder": (14, 70), "frame": (20, 120),
}
APPAREL_SIZES = ["XS", "S", "M", "L", "XL"]
SHOE_SIZES = [str(s) for s in range(5, 12)]


def product_id(image: str) -> str:
    return "p" + hashlib.sha1(image.encode()).hexdigest()[:8]


def synthetic_fields(pid: str, category: str) -> dict:
    rng = random.Random(pid)
    lo, hi = PRICE_RANGES.get(category, (20, 300))
    sizes: list[str] = []
    if category in SIZED["apparel"]:
        sizes = [s for s in APPAREL_SIZES if rng.random() < 0.75]
    elif category in SIZED["footwear"]:
        sizes = [s for s in SHOE_SIZES if rng.random() < 0.7]
    return {"price": round(rng.uniform(lo, hi), 2), "in_stock": rng.random() < 0.85, "sizes": sizes}


async def main() -> None:
    splits = json.loads(config.SPLITS_PATH.read_text())
    llm = OpenAILLM()
    pins = [p for b in splits["boards"].values() for p in b["dev"] + b["test"]]
    items = splits["catalog"]

    print(f"captioning {len(items)} products + {len(pins)} board pins with {config.VISION_MODEL}")
    attrs = await asyncio.gather(*[caption_image(llm, it["image"], it["category"]) for it in items])
    await asyncio.gather(*[caption_image(llm, p) for p in pins])

    records = []
    for it, a in zip(items, attrs):
        pid = product_id(it["image"])
        records.append({"id": pid, "name": it["name"], "category": it["category"], "image": it["image"],
                        "link": it["link"], **synthetic_fields(pid, it["category"]),
                        "attributes": a.model_dump()})

    print(f"embedding with {config.EMBED_MODEL}")
    style = await llm.embed([style_text(a) for a in attrs])
    search = await llm.embed([search_text(r["name"], r["category"], a) for r, a in zip(records, attrs)])

    config.CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    (config.CATALOG_DIR / "catalog.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\n")
    np.savez_compressed(config.CATALOG_DIR / "embeddings.npz",
                        ids=np.array([r["id"] for r in records]), style=style, search=search)
    print(f"wrote {len(records)} products to {config.CATALOG_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
