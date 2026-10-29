"""Chat-style demo UI over the same pipeline the CLI runs.

    python -m visioncart.web            # http://localhost:8000

Two kinds of profile:
- demo users (maya, jordan, sam): boards from the dev split, the static 120-product catalog.
- live users (quinn): a real Pinterest board, products from Uniqlo US's live search.

POST /api/ask streams NDJSON: the concierge's reply, then (for shopping requests) the plan,
live progress, each item as its worker/verifier loop finishes, the presenter's sections, and
the concierge's wrap-up. Product facts on screen come only from the sections.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from visioncart import config
from visioncart.agents import concierge
from visioncart.catalog.store import Catalog
from visioncart.graph import GRAPH, make_deps
from visioncart.live.board import board_pins, fetch_board
from visioncart.live.profiles import LIVE_USERS, make_live_deps
from visioncart.live.web_catalog import LiveCatalog
from visioncart.memory import feedback
from visioncart.memory.store import MemoryStore, StyleMemory
from visioncart.memory.sync import sync_user
from visioncart.memory.users import DEMO_USERS, user_pins

STATIC = Path(__file__).parent / "static"

for d in (config.BOARDS_DIR, config.LIVE_DIR / "images"):
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="VisionCart demo")
app.mount("/dataset/images", StaticFiles(directory=config.ROOT / "dataset" / "images"), name="images")
app.mount("/data/boards", StaticFiles(directory=config.BOARDS_DIR), name="boards")
app.mount("/data/live/images", StaticFiles(directory=config.LIVE_DIR / "images"), name="live")

# All endpoints are async: the sqlite connection lives on the event-loop thread.
_state: dict = {}


def _llm():
    if "llm" not in _state:
        from visioncart.llm import OpenAILLM
        _state["llm"] = OpenAILLM()
    return _state["llm"]


def _store() -> MemoryStore:
    if "store" not in _state:
        _state["store"] = MemoryStore()
    return _state["store"]


def _catalog() -> Catalog:
    if "catalog" not in _state:
        _state["catalog"] = Catalog.load()
    return _state["catalog"]


def _live_catalog(user_id: str) -> LiveCatalog:
    return _state.setdefault("live", {}).setdefault(user_id, LiveCatalog())


def _check_user(user_id: str) -> None:
    if user_id not in DEMO_USERS and user_id not in LIVE_USERS:
        raise HTTPException(404, f"unknown user {user_id!r}")


def _catalog_for(user_id: str):
    return _live_catalog(user_id) if user_id in LIVE_USERS else _catalog()


def _store_label(user_id: str) -> str:
    return "Uniqlo US" if user_id in LIVE_USERS else "the VisionCart demo catalog (home decor and fashion)"


def _first_name(user_id: str) -> str:
    return LIVE_USERS.get(user_id, {}).get("name", user_id).split()[0].title()


async def _sync(user_id: str) -> StyleMemory:
    if user_id in LIVE_USERS:
        pins = board_pins(user_id) or await fetch_board(user_id, LIVE_USERS[user_id]["board_url"])
    else:
        pins = user_pins(user_id)
    return await sync_user(_llm(), _store(), user_id, pins)  # no-op unless the board changed


def _memory_json(mem: StyleMemory) -> list[dict]:
    out = []
    for c in mem.clusters:
        liked, disliked = c.learned_terms()
        out.append({"id": c.id, "name": c.name, "persona": c.persona, "weight": round(c.weight, 3),
                    "pins": c.pins, "search_terms": c.search_terms, "liked": liked, "disliked": disliked})
    return out


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/users")
async def users():
    live = [{"id": uid, "name": u["name"], "about": u["about"], "boards": [u["about"]], "live": True,
             "store": "Uniqlo", "board_url": u["board_url"]} for uid, u in LIVE_USERS.items()]
    demo = [{"id": uid, "name": uid.title(), "about": u["about"], "boards": u["boards"], "live": False,
             "store": "Demo catalog"} for uid, u in DEMO_USERS.items()]
    return live + demo


@app.get("/api/users/{user_id}/memory")
async def memory(user_id: str):
    _check_user(user_id)
    mem = await _sync(user_id)
    return {"user": user_id, "clusters": _memory_json(mem)}


@app.post("/api/users/{user_id}/refresh")
async def refresh_board(user_id: str):
    """Re-pull a live board; style memory re-syncs only if the pins changed."""
    if user_id not in LIVE_USERS:
        raise HTTPException(400, "only live profiles have a remote board")
    await fetch_board(user_id, LIVE_USERS[user_id]["board_url"])
    return {"user": user_id, "clusters": _memory_json(await _sync(user_id))}


class Ask(BaseModel):
    user: str
    message: str
    history: list[dict] = []


def _line(event: dict) -> str:
    return json.dumps(event) + "\n"


@app.post("/api/ask")
async def ask(body: Ask):
    _check_user(body.user)
    message = body.message.strip()
    if not message:
        raise HTTPException(400, "empty message")
    user, name, store = body.user, _first_name(body.user), _store_label(body.user)

    async def events():
        try:
            mem = await _sync(user)
            desk = await concierge.front_desk(_llm(), message, body.history, name, store, mem)
            yield _line({"type": "reply", "text": desk.reply})
            if desk.intent != "shop":
                return

            queue: asyncio.Queue = asyncio.Queue()

            def progress(stage: str, item, info: dict) -> None:
                queue.put_nowait({"type": "progress", "stage": stage, "requested_as": item.requested_as, **info})

            if user in LIVE_USERS:
                deps = make_live_deps(_llm(), _store(), user, _live_catalog(user), progress)
            else:
                deps = make_deps(_llm(), _store(), user, _catalog())
            clusters = {c.id: c.name for c in deps.memory.clusters}

            async def drive():
                try:
                    async for update in GRAPH.astream({"request": desk.request, "results": []},
                                                      {"configurable": {"deps": deps}}, stream_mode="updates"):
                        await queue.put({"type": "_update", "update": update})
                except Exception as e:
                    await queue.put({"type": "error", "text": f"{type(e).__name__}: {e}"})
                finally:
                    await queue.put(None)

            task = asyncio.create_task(drive())
            sections = []
            while (ev := await queue.get()) is not None:
                if ev["type"] != "_update":
                    yield _line(ev)
                    continue
                for node, out in ev["update"].items():
                    if node == "plan":
                        yield _line({"type": "plan", "request": desk.request, "items": [
                            {**i.model_dump(), "cluster_name": clusters.get(i.cluster_id)} for i in out["plan"].items],
                            "total_budget": out["plan"].total_budget})
                    elif node in ("item_pipeline", "skip_item"):
                        for r in out["results"]:
                            yield _line({"type": "item", "index": r.index, "requested_as": r.item.requested_as,
                                         "attempts": r.attempts, "accepted": len(r.accepted),
                                         "low_confidence": r.low_confidence, "skipped": node == "skip_item"})
                    elif node == "present":
                        sections = out["sections"]
                        yield _line({"type": "result", "sections": [asdict(s) for s in sections]})
            await task
            if sections:
                text = await concierge.closing(_llm(), desk.request, sections, name, store, deps.memory)
                yield _line({"type": "closing", "text": text})
        except Exception as e:  # surface to the chat instead of a dead stream
            yield _line({"type": "error", "text": f"{type(e).__name__}: {e}"})

    return StreamingResponse(events(), media_type="application/x-ndjson")


class Feedback(BaseModel):
    user: str
    product_id: str
    cluster: int
    action: str


@app.post("/api/feedback")
async def give_feedback(body: Feedback):
    _check_user(body.user)
    if body.action not in feedback.TERM_STEP:
        raise HTTPException(400, f"action must be one of {sorted(feedback.TERM_STEP)}")
    try:
        product = _catalog_for(body.user).get(body.product_id)
    except KeyError:
        raise HTTPException(404, "unknown product")
    c = feedback.record(_store(), body.user, body.cluster, product, body.action)
    liked, disliked = c.learned_terms()
    return {"cluster": c.id, "name": c.name, "weight": round(c.weight, 3), "liked": liked, "disliked": disliked}
