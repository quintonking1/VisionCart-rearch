"""Presenter: renders only from verified state. Names, prices, images and links come from
catalog records looked up by id; the only model-written text is the verifier's explanation."""
from __future__ import annotations

import re
from dataclasses import dataclass

from visioncart.agents.types import UNAVAILABLE, Deps, ItemResult

_PRICE = re.compile(r"\$\s?\d")


@dataclass
class Card:
    product_id: str
    name: str
    category: str
    price: float | None
    image: str
    link: str | None
    match_score: float
    why: str
    cluster_id: int
    cluster_name: str
    low_confidence: bool


@dataclass
class Section:
    requested_as: str
    category: str
    cards: list[Card]
    note: str | None


def build_sections(results: list[ItemResult], deps: Deps) -> list[Section]:
    sections = []
    for r in sorted(results, key=lambda r: r.index):
        cluster = deps.memory.cluster(r.item.cluster_id)
        cards = []
        for s in r.accepted:
            p = deps.catalog.get(s.product_id)  # KeyError here means an unverified id slipped through
            why = r.explanations.get(p.id, "")
            if _PRICE.search(why) or p.name.lower() in why.lower():
                why = ""  # explanation strayed into facts the presenter owns
            cards.append(Card(p.id, p.name, p.category, p.price, p.image, p.link, round(s.score, 3),
                              why or f"Matches your {cluster.name.lower()} style.",
                              cluster.id, cluster.name, r.low_confidence))
        note = r.note
        if r.item.category == UNAVAILABLE:
            note = f"The catalog has no {r.item.requested_as}."
        elif not cards and not note:
            note = f"No {r.item.requested_as} passed verification."
        elif r.low_confidence:
            note = "LOW MATCH CONFIDENCE: nothing cleared the style threshold; showing the closest verified items."
        sections.append(Section(r.item.requested_as, r.item.category, cards, note))
    return sections


def render_text(sections: list[Section]) -> str:
    lines = []
    for sec in sections:
        lines.append(f"\n## {sec.requested_as}  [{sec.category}]")
        if sec.note:
            lines.append(f"   {sec.note}")
        for i, c in enumerate(sec.cards, 1):
            price = f"${c.price:,.2f}" if c.price is not None else "price at store"
            lines.append(f"   {i}. {c.name} - {price}  (match {c.match_score:.2f}, style: {c.cluster_name})")
            lines.append(f"      {c.why}")
            lines.append(f"      id={c.product_id} cluster={c.cluster_id}  image={c.image}")
    return "\n".join(lines)
