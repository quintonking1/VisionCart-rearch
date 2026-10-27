"""Guards against the original eval leak: labels must never reach the pipeline."""
import ast
import json
from pathlib import Path

import pytest

from visioncart import config
from visioncart.catalog.store import Product

PKG = config.ROOT / "visioncart"


def test_pipeline_never_imports_evals():
    for path in PKG.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            assert not any(n == "evals" or n.startswith("evals.") for n in names), f"{path} imports evals"


def test_pipeline_never_reads_labels_file():
    for path in PKG.rglob("*.py"):
        assert "labels.json" not in path.read_text(), f"{path} references the eval labels file"


@pytest.mark.parametrize("key", sorted(config.FORBIDDEN_CATALOG_KEYS))
def test_catalog_rejects_label_fields(key):
    rec = {"id": "x", "name": "n", "category": "bag", "image": "i", "price": 1, "in_stock": True,
           "sizes": [], "attributes": {}, key: "dark_academia"}
    with pytest.raises(ValueError, match="label fields"):
        Product.from_record(rec)


@pytest.mark.skipif(not config.SPLITS_PATH.exists(), reason="run scripts/make_splits.py first")
def test_splits_keep_boards_out_of_catalog():
    splits = json.loads(config.SPLITS_PATH.read_text())
    catalog_imgs = {c["image"] for c in splits["catalog"]}
    pins = [p for b in splits["boards"].values() for p in b["dev"] + b["test"]]
    assert not catalog_imgs & set(pins)
    dev = {p for b in splits["boards"].values() for p in b["dev"]}
    test = {p for b in splits["boards"].values() for p in b["test"]}
    assert not dev & test
    for c in splits["catalog"]:
        assert not config.FORBIDDEN_CATALOG_KEYS & c.keys()


@pytest.mark.skipif(not (config.CATALOG_DIR / "catalog.jsonl").exists(), reason="catalog not built")
def test_built_catalog_has_no_labels_and_opaque_ids():
    from visioncart.catalog.store import Catalog
    cat = Catalog.load()  # raises on label fields
    labels = json.loads((config.ROOT / "evals" / "data" / "labels.json").read_text())
    styles = {v["style"] for v in labels.values()}
    for p in cat.products:
        assert not any(s in p.id for s in styles)
