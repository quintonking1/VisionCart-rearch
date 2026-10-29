"""Live search worker: same contract as agents.search_worker.run_worker (returns
(product id, retrieval score) pairs), but candidates come from Uniqlo's live product search.

1. Code searches Uniqlo by category and takes the next batch it hasn't scored yet.
2. Each product photo is captioned and embedded, so the verifier scores it exactly like a
   catalog product against the user's style cluster.
3. Retrieval score = similarity between the planner's description of a good match and the
   product's description.
"""
from __future__ import annotations

import asyncio

from visioncart import config
from visioncart.agents.types import Deps, PlannedItem
from visioncart.catalog.store import Product
from visioncart.live import uniqlo
from visioncart.live.web_catalog import LiveCatalog, download_image, http_client
from visioncart.vision import caption_image, search_text, style_terms, style_text


def product_id(item: uniqlo.UniqloItem) -> str:
    return "uq" + item.product_id


async def run_live_worker(item: PlannedItem, deps: Deps, feedback: str | None = None,
                          exclude: set[str] = frozenset()) -> list[tuple[str, float]]:
    catalog: LiveCatalog = deps.catalog
    say = deps.progress or (lambda *_: None)
    say("searching", item, {"store": "Uniqlo", "query": uniqlo.KEYWORDS.get(item.category, item.category)})

    async with http_client() as client:
        found = await uniqlo.search(client, item.category)
        batch = [u for u in found if product_id(u) not in exclude][:config.LIVE_BATCH]
        say("reading", item, {"found": len(found), "checking": len(batch)})

        async def one(u: uniqlo.UniqloItem) -> Product | None:
            pid = product_id(u)
            if pid in catalog:
                return catalog.get(pid)
            image = await download_image(client, u.image_url)
            if not image:
                return None
            attrs = await caption_image(deps.llm, image, product_hint=item.category)
            name = f"{u.name} · {u.color}" if u.color else u.name
            return Product(id=pid, name=name, category=item.category, image=image, price=u.price,
                           in_stock=True, sizes=u.sizes, link=u.url, attributes=attrs, terms=style_terms(attrs))

        products = [p for p in await asyncio.gather(*[one(u) for u in batch]) if p]

    new = [p for p in products if p.id not in catalog]
    if new:
        vecs = await deps.llm.embed([style_text(p.attributes) for p in new] +
                                    [search_text(p.name, p.category, p.attributes) for p in new])
        for p, sv, qv in zip(new, vecs[:len(new)], vecs[len(new):]):
            catalog.add(p, sv, qv)
    say("verifying", item, {"products": len(products)})
    if not products:
        return []
    want = (await deps.llm.embed([f"{item.requested_as}. {item.description}"]))[0]
    scores = {p.id: float(catalog.search_vec(p.id) @ want) for p in products}
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
