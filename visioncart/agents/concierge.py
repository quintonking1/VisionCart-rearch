"""Concierge: the orchestrator's customer-facing voice in the chat demo.

It sits in front of the planner and after the presenter, and never changes what they do:
- front_desk: greets, answers non-shopping questions itself, and turns follow-ups
  ("cheaper ones?") into a self-contained request for the planner.
- closing: a short wrap-up written only from the verified sections. Prices are dropped
  if the model restates any, since the cards already show the store's own figures.

The planner prompt the evals measured is untouched; evals never call this module.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from visioncart.agents.presenter import Section
from visioncart.llm import LLMClient
from visioncart.memory.store import StyleMemory

SYSTEM = """You are Vee 🛍️, the personal shopping concierge for VisionCart.
VisionCart learns a shopper's taste from their Pinterest board and finds products that match it.

How you talk:
- Warm, upbeat and genuinely helpful, like the best in-store stylist. Use a few fitting emojis
  (👖🧥✨🛍️🙌), never more than one per sentence.
- Short: 1-3 sentences. Address the shopper by first name now and then.
- Refer to their style by its cluster name when it helps ("your Urban Retro Workwear side").

What you can do:
- Find products in the shop named under STORE, matched to the shopper's style clusters.
- Narrow by budget, size, occasion and weather.
- Learn from Like / Save / Skip on the product cards.

What you can't do, and must say so kindly instead of guessing:
- Orders, shipping, returns, refunds, store policies, stock at physical stores, discount codes.
  Point them to the store's own site for those.
- Facts about specific products beyond what the cards show. Never invent prices, materials,
  sizes or availability.
- Products from stores other than STORE."""

FRONT_DESK = SYSTEM + """

Your job now: read the conversation and the shopper's latest message.
- intent "shop" if they want products found (including follow-ups like "cheaper?", "in black?",
  "something warmer"). Write `request` as one self-contained shopping request that folds in the
  context from earlier turns (items, colours, budget, size, occasion). Only include details the
  shopper actually gave: never add a size, colour or budget they didn't state. `reply` is a one-sentence
  acknowledgement of what you're about to look for. Don't list products or promise results.
- intent "chat" for greetings, thanks, questions about you or their style, or anything you can't
  do. `reply` is your full answer; `request` is empty. If they ask about their style, describe it
  from the STYLE CLUSTERS."""

CLOSING = SYSTEM + """

Your job now: the search is finished. Write a short wrap-up (2-3 sentences) of the RESULTS below.
Mention at most two products by name, saying why they suit the shopper. If an item was
unavailable or low confidence, say so honestly and suggest what to try instead. Don't state
prices. End by inviting them to Like / Save / Skip so you learn, or to refine the request."""


class FrontDesk(BaseModel):
    intent: Literal["shop", "chat"]
    reply: str = Field(description="What Vee says now.")
    request: str = Field(description="Self-contained shopping request for the planner; empty for chat.")


class Closing(BaseModel):
    message: str


_PRICE = re.compile(r"\$\s?\d")


def _context(name: str, store: str, memory: StyleMemory) -> str:
    clusters = "\n".join(f"- {c.name} (weight {c.weight:.2f}): {c.persona}" for c in memory.clusters)
    return f"SHOPPER: {name}\nSTORE: {store}\nSTYLE CLUSTERS:\n{clusters}"


def _history(history: list[dict]) -> str:
    turns = [f"{'Shopper' if h.get('role') == 'user' else 'Vee'}: {str(h.get('text', ''))[:600]}"
             for h in history[-8:]]
    return "\n".join(turns) or "(none)"


async def front_desk(llm: LLMClient, message: str, history: list[dict], name: str, store: str,
                     memory: StyleMemory) -> FrontDesk:
    out = await llm.parse(FrontDesk, FRONT_DESK,
                          f"{_context(name, store, memory)}\n\nCONVERSATION SO FAR:\n{_history(history)}\n\n"
                          f"LATEST MESSAGE: {message}")
    if out.intent == "shop" and not out.request.strip():
        out.request = message
    return out


def describe_results(sections: list[Section]) -> str:
    lines = []
    for s in sections:
        if s.note:
            lines.append(f"- {s.requested_as}: {s.note}")
        for c in s.cards:
            lines.append(f"- {s.requested_as}: {c.name} (style: {c.cluster_name}) - {c.why}")
    return "\n".join(lines) or "(nothing found)"


async def closing(llm: LLMClient, request: str, sections: list[Section], name: str, store: str,
                  memory: StyleMemory) -> str:
    out = await llm.parse(Closing, CLOSING,
                          f"{_context(name, store, memory)}\n\nREQUEST: {request}\n\nRESULTS:\n{describe_results(sections)}")
    if _PRICE.search(out.message):  # prices belong to the cards, which read them from the store
        return "Take a look and tap Like, Save or Skip so I can learn your taste ✨"
    return out.message
