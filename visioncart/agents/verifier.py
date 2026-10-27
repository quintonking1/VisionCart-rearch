"""Verifier: code decides what code can decide; the LLM only writes explanations.

1. Hard checks in code: category, price, stock, size, water resistance.
2. Visual fit: cosine to the item's style cluster centroid (+ small learned-feedback nudge),
   accepted only above a threshold calibrated on the dev split.
   Products that pass are ordered by a blend of visual fit and the worker's retrieval score
   (weight calibrated leave-one-style-out on dev); visual fit alone gates, it does not rank.
3. LLM: one sentence per accepted product on why it matches. Nothing else.
"""
from __future__ import annotations

import re
from collections import Counter

from pydantic import BaseModel

from visioncart import config
from visioncart.agents.types import Deps, PlannedItem, Scored
from visioncart.catalog.store import Product
from visioncart.memory.feedback import feedback_bias


def _size(s: str) -> str:
    """'32inch' and '32 in' match '32'."""
    return re.sub(r"\s*(INCH|IN)$", "", s.strip().upper())


def hard_checks(p: Product, item: PlannedItem) -> list[str]:
    failures = []
    if p.category != item.category:
        failures.append("wrong category")
    if not p.in_stock:
        failures.append("out of stock")
    if item.max_price is not None and p.price is None:
        failures.append("price unknown")
    elif item.max_price is not None and p.price > item.max_price:
        failures.append("over budget")
    if item.size and p.sizes and _size(item.size) not in {_size(s) for s in p.sizes}:
        failures.append("size unavailable")
    if item.needs_water_resistant and not p.attributes.water_resistant:
        failures.append("not water resistant")
    return failures


def _minmax(xs: list[float]) -> list[float]:
    lo, hi = min(xs), max(xs)
    return [0.5] * len(xs) if hi - lo < 1e-9 else [(x - lo) / (hi - lo) for x in xs]


def blend_rank(scored: list[Scored], blend: float) -> list[Scored]:
    """Set `rank` = blend * retrieval + (1 - blend) * style fit, both min-max scaled within
    the batch, and return the batch ordered by it."""
    if scored:
        for s, r, v in zip(scored, _minmax([s.retrieval for s in scored]), _minmax([s.score for s in scored])):
            s.rank = blend * r + (1 - blend) * v
    return sorted(scored, key=lambda s: s.rank, reverse=True)


def score_candidates(candidates: list[tuple[str, float]], item: PlannedItem, deps: Deps) -> list[Scored]:
    cluster = deps.memory.cluster(item.cluster_id)
    out = []
    for pid, retrieval in candidates:
        p = deps.catalog.get(pid)
        out.append(Scored(pid, visual=float(deps.catalog.style_vec(pid) @ cluster.centroid),
                          bias=feedback_bias(cluster, p, config.FEEDBACK_BIAS_SCALE),
                          failures=hard_checks(p, item), retrieval=retrieval))
    return blend_rank(out, deps.blend)


def decide(scored: list[Scored], threshold: float) -> tuple[list[Scored], str | None]:
    """Accepted products (in rank order) and, if none were accepted, feedback for the worker's
    next attempt."""
    scored = sorted(scored, key=lambda s: s.rank, reverse=True)
    passing = [s for s in scored if not s.failures]
    accepted = [s for s in passing if s.score >= threshold][:config.TOP_K]
    if accepted:
        return accepted, None
    reasons = Counter(f for s in scored for f in s.failures)
    parts = [f"{n} {r}" for r, n in reasons.most_common()]
    if passing:
        parts.append(f"{len(passing)} passed checks but best style score {max(s.score for s in passing):.2f} "
                     f"< threshold {threshold:.2f}; push harder on the style persona's palette and materials")
    if not scored:
        parts.append("no products found in this category; try broader wording")
    return [], "; ".join(parts)


def fallback(scored: list[Scored]) -> list[Scored]:
    """After retries run out: best products that pass the hard checks, flagged low confidence."""
    passing = sorted((s for s in scored if not s.failures), key=lambda s: s.rank, reverse=True)
    return passing[:min(2, config.TOP_K)]


class Explanation(BaseModel):
    product_id: str
    why: str


class Explanations(BaseModel):
    items: list[Explanation]


EXPLAIN_SYSTEM = """For each product, write one sentence (max 30 words) on why it fits the user's style,
citing concrete visual attributes (colour, material, texture, shape). Do not mention prices,
brands or availability. Use the product_id exactly as given."""


async def explain(accepted: list[Scored], item: PlannedItem, deps: Deps) -> dict[str, str]:
    if not accepted:
        return {}
    c = deps.memory.cluster(item.cluster_id)
    rows = "\n".join(
        f"- product_id {s.product_id}: {deps.catalog.get(s.product_id).attributes.item_description}; "
        f"{deps.catalog.get(s.product_id).attributes.style_summary}"
        for s in accepted)
    out = await deps.llm.parse(Explanations, EXPLAIN_SYSTEM,
                               f"USER STYLE: {c.name}. {c.persona}\n\nPRODUCTS:\n{rows}")
    allowed = {s.product_id for s in accepted}
    return {e.product_id: e.why for e in out.items if e.product_id in allowed}
