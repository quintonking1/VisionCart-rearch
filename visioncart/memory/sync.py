"""Board -> style memory. Runs once per board change, not once per request."""
from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field

from visioncart.llm import LLMClient, file_sha
from visioncart.memory.cluster import centroids, cluster_board
from visioncart.memory.store import MemoryStore, StyleCluster, StyleMemory
from visioncart.vision import CAPTION_VERSION, STYLE_TEXT_VERSION, ImageAttributes, caption_image, style_text


class ClusterPersona(BaseModel):
    name: str = Field(description="2-4 word name for this style, e.g. 'Moody scholarly tailoring'.")
    persona: str = Field(description="2-3 sentences describing the taste: palette, materials, mood, what to avoid.")
    search_terms: list[str] = Field(description="6-10 short descriptive terms a shopper would search with.")
    avoid_terms: list[str] = Field(description="3-6 terms describing things this taste would reject.")


PERSONA_SYSTEM = (
    "You summarise one cluster of a user's inspiration board into a style persona that "
    "search agents will use. Ground every claim in the pin descriptions you are given."
)


def board_hash(pins: list[str]) -> str:
    # Includes caption + style-text versions so a captioner or embedding change re-syncs every board.
    return hashlib.sha256((CAPTION_VERSION + STYLE_TEXT_VERSION + "".join(sorted(file_sha(p) for p in pins))).encode()).hexdigest()


async def sync_user(llm: LLMClient, store: MemoryStore, user_id: str, pins: list[str | Path],
                    force: bool = False) -> StyleMemory:
    pins = [str(p) for p in pins]
    h = board_hash(pins)
    if not force and store.board_hash(user_id) == h:
        return store.load(user_id)

    attrs: list[ImageAttributes] = await asyncio.gather(*[caption_image(llm, p) for p in pins])
    vecs = await llm.embed([style_text(a) for a in attrs])
    labels = cluster_board(vecs)
    cents = centroids(vecs, labels)

    async def persona(cid: int) -> ClusterPersona:
        members = [attrs[i] for i in np.flatnonzero(labels == cid)]
        body = "\n".join(f"- {a.item_description}: {style_text(a)}" for a in members)
        return await llm.parse(ClusterPersona, PERSONA_SYSTEM, f"Pins in this cluster:\n{body}")

    cluster_ids = sorted(set(labels.tolist()))
    personas = await asyncio.gather(*[persona(c) for c in cluster_ids])
    clusters = [
        StyleCluster(id=c, name=p.name, persona=p.persona, search_terms=p.search_terms, avoid_terms=p.avoid_terms,
                     centroid=cent, pins=[pins[i] for i in np.flatnonzero(labels == c)])
        for c, p, cent in zip(cluster_ids, personas, cents)
    ]
    mem = StyleMemory(user_id, h, clusters)

    # Keep learned feedback for clusters that still exist after the board changed.
    carry = {}
    try:
        old = store.load(user_id)
        for c in clusters:
            carry[c.id] = max(old.clusters, key=lambda o: float(o.centroid @ c.centroid)).id
    except KeyError:
        pass
    store.save(mem, carry_over=carry)
    return store.load(user_id)
