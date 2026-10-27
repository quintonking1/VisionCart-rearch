"""Eval harness. The only code allowed to read ground-truth labels.

Separation rules (enforced by tests/test_leakage.py):
  * visioncart/ never imports evals/.
  * The pipeline only ever receives a request string and board pin paths.
  * Labels are joined to pipeline output here, after the pipeline has run.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

from visioncart import config
from visioncart.catalog.store import Catalog
from visioncart.memory.store import MemoryStore
from visioncart.memory.sync import sync_user
from visioncart.memory.users import board_pins

LABELS_PATH = Path(__file__).parent / "data" / "labels.json"
EVAL_DB = config.DATA_DIR / "eval_memory.sqlite"  # kept apart from demo users' memory
RESULTS_DIR = config.ROOT / "results"

# Fixed two-style boards for checking that clustering separates mixed taste.
MIXED_PAIRS = [("dark_academia", "cottagecore"), ("japandi", "maximalist_eclectic"),
               ("y2k_streetwear", "quiet_luxury"), ("coastal_mediterranean", "dark_moody_organic"),
               ("mid_century_modern", "vintage_bohemian")]


def labels() -> dict[str, dict[str, str]]:
    return json.loads(LABELS_PATH.read_text())


def styles() -> list[str]:
    return sorted(json.loads(config.SPLITS_PATH.read_text())["boards"])


def product_styles(catalog: Catalog) -> dict[str, str]:
    lab = labels()
    return {p.id: lab[p.image]["style"] for p in catalog.products}


def style_categories(catalog: Catalog, style: str) -> list[str]:
    ps = product_styles(catalog)
    return sorted({p.category for p in catalog.products if ps[p.id] == style})


def contested_categories(catalog: Catalog) -> set[str]:
    """Categories sold by more than one style. Only these test style matching end to end;
    in the rest every in-category candidate is relevant."""
    ps = product_styles(catalog)
    styles_per_cat: dict[str, set[str]] = {}
    for p in catalog.products:
        styles_per_cat.setdefault(p.category, set()).add(ps[p.id])
    return {c for c, s in styles_per_cat.items() if len(s) > 1}


def relevant(catalog: Catalog, style: str, category: str, in_stock_only: bool = False) -> set[str]:
    ps = product_styles(catalog)
    return {p.id for p in catalog.products
            if ps[p.id] == style and p.category == category and (p.in_stock or not in_stock_only)}


def eval_request(category: str) -> str:
    return f"I'm looking for a {category}."


def eval_user(split: str, style: str) -> str:
    return f"eval-{split}-{style}"


async def sync_eval_boards(llm, store: MemoryStore, split: str) -> None:
    for style in styles():
        await sync_user(llm, store, eval_user(split, style), board_pins([style], split))
    for a, b in MIXED_PAIRS:
        await sync_user(llm, store, eval_user(split, f"{a}+{b}"), board_pins([a, b], split))


# ---------- metrics ----------

def precision_at_k(ranked: list[str], rel: set[str], k: int) -> float:
    return sum(r in rel for r in ranked[:k]) / k


def mrr(ranked: list[str], rel: set[str]) -> float:
    return next((1 / (i + 1) for i, r in enumerate(ranked) if r in rel), 0.0)


def ndcg_at_k(ranked: list[str], rel: set[str], k: int) -> float:
    dcg = sum(1 / math.log2(i + 2) for i, r in enumerate(ranked[:k]) if r in rel)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(len(rel), k)))
    return dcg / ideal if ideal else 0.0


def precision_shown(ranked: list[str], rel: set[str]) -> float | None:
    """Precision of what was shown, not penalised for slots that had no relevant item to fill."""
    if not ranked:
        return None
    return sum(r in rel for r in ranked) / min(len(ranked), len(rel)) if rel else 0.0


def random_baseline(pool: list[str], rel: set[str], k: int = 3, trials: int = 500, seed: int = 0) -> dict:
    """Expected metrics if the pool were shown in random order."""
    rng = random.Random(seed)
    acc = {"p@1": 0.0, "mrr": 0.0, f"ndcg@{k}": 0.0}
    for _ in range(trials):
        order = rng.sample(pool, len(pool))
        acc["p@1"] += precision_at_k(order, rel, 1)
        acc["mrr"] += mrr(order, rel)
        acc[f"ndcg@{k}"] += ndcg_at_k(order, rel, k)
    return {m: v / trials for m, v in acc.items()}


def bootstrap_ci(values: list[float], n: int = 2000, alpha: float = 0.05, seed: int = 0) -> tuple[float, float]:
    """Percentile bootstrap CI of the mean, resampling cases."""
    vals = [v for v in values if v == v]  # drop NaN
    if not vals:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(vals, k=len(vals))) / len(vals) for _ in range(n))
    return means[int(alpha / 2 * n)], means[int((1 - alpha / 2) * n) - 1]


def summarize(values: list[float]) -> dict:
    lo, hi = bootstrap_ci(values)
    return {"mean": mean(v for v in values if v == v), "ci95": [lo, hi], "n": len(values)}


def best_f1_threshold(scores: list[float], ys: list[bool]) -> tuple[float, float]:
    best = (config.DEFAULT_THRESHOLD, 0.0)
    for t in sorted(set(scores)):
        tp = sum(s >= t and y for s, y in zip(scores, ys))
        fp = sum(s >= t and not y for s, y in zip(scores, ys))
        fn = sum(s < t and y for s, y in zip(scores, ys))
        f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
        if f1 > best[1]:
            best = (t, f1)
    return best


def cohen_kappa(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def mean(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")
