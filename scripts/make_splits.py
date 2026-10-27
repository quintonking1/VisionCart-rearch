"""Fix the board / catalog split once, before any pipeline code runs.

For each style, one pin per product type goes to a dev board and one to a test board
(3 pins each). Every other image becomes a catalog product. Ground-truth style labels
are written ONLY to evals/data/labels.json; data/splits.json's catalog list has none.

    python scripts/make_splits.py                 # canonical split (seed 7) into data/
    VISIONCART_DATA_DIR=data/folds/1 python scripts/make_splits.py --seed 101
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from visioncart import config  # noqa: E402

SEED = 7
CATEGORY_ALIASES = {"tote": "bag", "trousers": "pants"}


def name_from_filename(fname: str) -> str:
    stem = re.sub(r"^\d+_", "", Path(fname).stem)
    return stem.replace("_", " ").strip().title()


def main(seed: int = SEED) -> None:
    rows = json.loads((config.ROOT / "dataset" / "dataset.json").read_text())
    known = {Path(r["image_local"]).name: r for r in rows}

    # style -> category -> [image entries]; dataset order defines the "first" type.
    by_style: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    first_type: dict[str, str] = {}
    for r in rows:
        first_type.setdefault(r["style_label"], r["product_type"])

    for img in sorted((config.ROOT / "dataset" / "images").glob("*/*.jpg")):
        style = img.parent.name
        rel = str(img.relative_to(config.ROOT))
        r = known.get(img.name)
        # Images outside dataset.json are extra instances (05-10) of the style's first type.
        raw_type = r["product_type"] if r else first_type[style]
        by_style[style][CATEGORY_ALIASES.get(raw_type, raw_type)].append({
            "image": rel,
            "name": r["product_name"] if r else name_from_filename(img.name),
            "link": r["link"] if r else None,
        })

    rng = random.Random(seed)
    boards: dict[str, dict[str, list[str]]] = {}
    catalog, labels = [], {}
    for style in sorted(by_style):
        boards[style] = {"dev": [], "test": []}
        for category in sorted(by_style[style]):
            items = by_style[style][category]
            dev, test = rng.sample(range(len(items)), 2)
            for i, item in enumerate(items):
                labels[item["image"]] = {"style": style, "category": category}
                if i == dev:
                    boards[style]["dev"].append(item["image"])
                elif i == test:
                    boards[style]["test"].append(item["image"])
                else:
                    catalog.append({**item, "category": category})

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.SPLITS_PATH.write_text(json.dumps({"seed": seed, "boards": boards, "catalog": catalog}, indent=1))
    labels_path = config.ROOT / "evals" / "data" / "labels.json"
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    labels_path.write_text(json.dumps(labels, indent=1, sort_keys=True))
    print(f"boards: {len(boards)} styles x (3 dev + 3 test) pins | catalog: {len(catalog)} products")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=SEED)
    main(ap.parse_args().seed)
