"""Search worker: one per planned item. Writes queries, calls the catalog search tool,
and returns (product id, retrieval score) pairs only. It never sees or emits prices,
names or links."""
from __future__ import annotations

from pydantic import BaseModel, Field

from visioncart import config
from visioncart.agents.types import Deps, PlannedItem

SYSTEM = """You write catalog search queries for one item in a shopper's style.
Each query is 4-10 words: the item plus concrete visual descriptors (colour, material, texture,
silhouette, mood) drawn from the style persona. Make the queries take different angles.
If verifier feedback is given, change approach to address it."""


class Queries(BaseModel):
    queries: list[str] = Field(description="2-3 distinct search queries.")


def _prompt(item: PlannedItem, deps: Deps, feedback: str | None) -> str:
    c = deps.memory.cluster(item.cluster_id)
    liked, disliked = c.learned_terms()
    lines = [
        f"ITEM: {item.requested_as} (category: {item.category})",
        f"WHAT A GOOD MATCH LOOKS LIKE: {item.description}",
        f"STYLE PERSONA: {c.name}. {c.persona}",
        f"STYLE TERMS: {', '.join(c.search_terms + liked)}",
        f"AVOID: {', '.join(c.avoid_terms + disliked)}",
    ]
    if feedback:
        lines.append(f"VERIFIER FEEDBACK FROM LAST ATTEMPT: {feedback}")
    return "\n".join(lines)


async def run_worker(item: PlannedItem, deps: Deps, feedback: str | None = None,
                     exclude: set[str] = frozenset()) -> list[tuple[str, float]]:
    queries = (await deps.llm.parse(Queries, SYSTEM, _prompt(item, deps, feedback))).queries[:3]
    if not queries:
        queries = [f"{item.requested_as} {item.description}"]
    vecs = await deps.llm.embed(queries)
    best: dict[str, float] = {}
    for q, v in zip(queries, vecs):
        for pid, score in deps.search.search(q, v, item.category, k=config.CANDIDATES_PER_WORKER, exclude=exclude):
            best[pid] = max(best.get(pid, float("-inf")), score)
    ranked = sorted(best, key=best.get, reverse=True)[:config.CANDIDATES_PER_WORKER]
    return [(pid, best[pid]) for pid in ranked]
