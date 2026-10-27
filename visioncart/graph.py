"""LangGraph wiring.

    plan ──Send per item──▶ item pipeline (parallel) ──▶ present
                             worker ─▶ verify ─┬─▶ explain ─▶ END
                                ▲              │
                                └── retry ─────┘  (capped at MAX_RETRIES, then low-confidence fallback)
"""
from __future__ import annotations

import json
import operator
from typing import Annotated, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from visioncart import config as settings
from visioncart.agents import presenter, verifier
from visioncart.agents.orchestrator import plan_request
from visioncart.agents.search_worker import run_worker
from visioncart.agents.types import UNAVAILABLE, Deps, ItemResult, Plan, PlannedItem, Scored
from visioncart.catalog.search import CatalogSearch
from visioncart.catalog.store import Catalog
from visioncart.llm import LLMClient
from visioncart.memory.store import MemoryStore


def _deps(config: RunnableConfig) -> Deps:
    return config["configurable"]["deps"]


# ---------- per-item subgraph ----------

class ItemState(TypedDict, total=False):
    index: int
    item: PlannedItem
    attempt: int
    scored: dict[str, Scored]
    accepted: list[Scored]
    feedback: str | None
    exhausted: bool
    low_confidence: bool
    explanations: dict[str, str]


async def worker_node(s: ItemState, config: RunnableConfig) -> ItemState:
    seen = s.get("scored", {})
    ids = await run_worker(s["item"], _deps(config), s.get("feedback"), exclude=set(seen))
    new = {x.product_id: x for x in verifier.score_candidates(ids, s["item"], _deps(config))}
    return {"scored": {**seen, **new}, "attempt": s.get("attempt", 0) + 1, "exhausted": not new}


def verify_node(s: ItemState, config: RunnableConfig) -> ItemState:
    ranked = list(s["scored"].values())
    accepted, feedback = verifier.decide(ranked, _deps(config).threshold)
    out_of_tries = s["attempt"] > settings.MAX_RETRIES or s["exhausted"]
    if not accepted and out_of_tries:
        return {"accepted": verifier.fallback(ranked), "low_confidence": True, "feedback": feedback}
    return {"accepted": accepted, "feedback": feedback, "low_confidence": False}


def route_after_verify(s: ItemState) -> str:
    if s["accepted"] or s.get("low_confidence"):
        return "explain"
    return "worker"


async def explain_node(s: ItemState, config: RunnableConfig) -> ItemState:
    return {"explanations": await verifier.explain(s["accepted"], s["item"], _deps(config))}


def build_item_graph():
    g = StateGraph(ItemState)
    g.add_node("worker", worker_node)
    g.add_node("verify", verify_node)
    g.add_node("explain", explain_node)
    g.add_edge(START, "worker")
    g.add_edge("worker", "verify")
    g.add_conditional_edges("verify", route_after_verify, ["worker", "explain"])
    g.add_edge("explain", END)
    return g.compile()


ITEM_GRAPH = build_item_graph()


# ---------- top-level graph ----------

class PipelineState(TypedDict, total=False):
    request: str
    plan: Plan
    results: Annotated[list[ItemResult], operator.add]
    sections: list[presenter.Section]


async def plan_node(s: PipelineState, config: RunnableConfig) -> PipelineState:
    return {"plan": await plan_request(s["request"], _deps(config))}


def fan_out(s: PipelineState):
    sends = []
    for i, item in enumerate(s["plan"].items):
        if item.category == UNAVAILABLE:
            sends.append(Send("skip_item", {"index": i, "item": item}))
        else:
            sends.append(Send("item_pipeline", {"index": i, "item": item}))
    return sends or [Send("present", {})]


async def item_pipeline_node(s: ItemState, config: RunnableConfig) -> PipelineState:
    out = await ITEM_GRAPH.ainvoke(s, config)
    return {"results": [ItemResult(index=s["index"], item=s["item"], accepted=out["accepted"],
                                   explanations=out.get("explanations", {}), attempts=out["attempt"],
                                   low_confidence=out.get("low_confidence", False))]}


def skip_item_node(s: ItemState) -> PipelineState:
    return {"results": [ItemResult(index=s["index"], item=s["item"], accepted=[], explanations={},
                                   attempts=0, low_confidence=False)]}


def present_node(s: PipelineState, config: RunnableConfig) -> PipelineState:
    return {"sections": presenter.build_sections(s.get("results", []), _deps(config))}


def build_graph():
    g = StateGraph(PipelineState)
    g.add_node("plan", plan_node)
    g.add_node("item_pipeline", item_pipeline_node)
    g.add_node("skip_item", skip_item_node)
    g.add_node("present", present_node)
    g.add_edge(START, "plan")
    g.add_conditional_edges("plan", fan_out, ["item_pipeline", "skip_item", "present"])
    g.add_edge("item_pipeline", "present")
    g.add_edge("skip_item", "present")
    g.add_edge("present", END)
    return g.compile()


GRAPH = build_graph()


def _calibration() -> dict:
    if settings.CALIBRATION_PATH.exists():
        return json.loads(settings.CALIBRATION_PATH.read_text())
    return {}


def load_threshold() -> float:
    return float(_calibration().get("threshold", settings.DEFAULT_THRESHOLD))


def load_blend() -> float:
    return float(_calibration().get("blend", settings.DEFAULT_BLEND))


def make_deps(llm: LLMClient, store: MemoryStore, user_id: str, catalog: Catalog | None = None,
              threshold: float | None = None, blend: float | None = None) -> Deps:
    catalog = catalog or Catalog.load()
    return Deps(llm=llm, catalog=catalog, search=CatalogSearch(catalog), memory=store.load(user_id),
                threshold=load_threshold() if threshold is None else threshold,
                blend=load_blend() if blend is None else blend)


async def run(request: str, deps: Deps) -> PipelineState:
    return await GRAPH.ainvoke({"request": request, "results": []}, {"configurable": {"deps": deps}})
