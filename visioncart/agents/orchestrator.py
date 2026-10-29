"""Orchestrator: turns a free-text request into a typed plan of items to search for."""
from __future__ import annotations

import re

from visioncart.agents.types import UNAVAILABLE, Deps, Plan

# Letter sizes, numeric sizes (32, 10.5) and waist x inseam (32x30). Anything else ("my size") is dropped.
_SIZE = re.compile(r"^(XXS|XS|S|M|L|XL|XXL|XXXL|\d{1,2}(\.5)?|\d{2}\s*[X/]\s*\d{2})$")

SYSTEM = """You plan shopping requests for a style-matching assistant.
Break the request into the individual items to find (one item for single-item requests).
For each item pick:
- category: exactly one name from CATALOG CATEGORIES. If nothing fits, use "unavailable".
- cluster_id: the user's style cluster that best fits that item and the occasion.
Only set max_price, size or total_budget if the user stated them. Set needs_water_resistant only
when the user mentions rain, snow or wet conditions and the item is worn outdoors."""


def _prompt(request: str, deps: Deps) -> str:
    clusters = "\n".join(
        f"- id {c.id} (weight {c.weight:.2f}): {c.name}. {c.persona}" for c in deps.memory.clusters)
    return (f"CATALOG CATEGORIES: {', '.join(deps.catalog.categories())}\n\n"
            f"USER STYLE CLUSTERS:\n{clusters}\n\nREQUEST: {request}")


def validate_plan(plan: Plan, deps: Deps) -> Plan:
    """The model proposes; code decides what is legal."""
    categories = set(deps.catalog.categories())
    cluster_ids = {c.id for c in deps.memory.clusters}
    default_cluster = max(deps.memory.clusters, key=lambda c: c.weight).id
    for item in plan.items:
        item.category = item.category.strip().lower()
        if item.category not in categories:
            item.category = UNAVAILABLE
        if item.size and not _SIZE.match(item.size.strip().upper()):
            item.size = None
        if item.cluster_id not in cluster_ids:
            item.cluster_id = default_cluster
    searchable = [i for i in plan.items if i.category != UNAVAILABLE]
    if plan.total_budget and searchable:
        share = plan.total_budget / len(searchable)
        for item in searchable:
            item.max_price = min(item.max_price, share) if item.max_price else share
    return plan


async def plan_request(request: str, deps: Deps) -> Plan:
    plan = await deps.llm.parse(Plan, SYSTEM, _prompt(request, deps))
    return validate_plan(plan, deps)
