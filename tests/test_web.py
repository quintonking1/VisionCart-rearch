import json

import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeLLM
from tests.test_graph import planner
from visioncart.agents.concierge import Closing, FrontDesk
from visioncart.memory.store import MemoryStore
from visioncart.web import app as web


@pytest.fixture
def client(monkeypatch, tmp_path, catalog, memory, make_deps):
    memory.user_id = "maya"

    def desk(prompt):
        if "LATEST MESSAGE: hi" in prompt:
            return FrontDesk(intent="chat", reply="Hey Maya 👋", request="")
        return FrontDesk(intent="shop", reply="On it ✨", request="a blazer and an umbrella")

    llm = FakeLLM({"Plan": planner(("blazer", 0), ("umbrella", 0)), "FrontDesk": desk,
                   "Closing": lambda _p: Closing(message="Costs $5, enjoy!")})

    def make_store():  # built lazily on the app's thread, as in production (sqlite is thread-bound)
        store = MemoryStore(tmp_path / "memory.sqlite")
        store.save(memory)
        return store

    async def fake_sync(_llm, _store, user_id, _pins, force=False):
        return _store.load(user_id)

    monkeypatch.setattr(web, "_state", {"llm": llm, "catalog": catalog})
    monkeypatch.setattr(web, "MemoryStore", make_store)
    monkeypatch.setattr(web, "sync_user", fake_sync)
    monkeypatch.setattr(web, "make_deps", lambda *a, **k: make_deps(llm, threshold=0.6))
    return TestClient(web.app)


def test_ask_streams_plan_items_then_verified_sections(client, catalog):
    r = client.post("/api/ask", json={"user": "maya", "message": "a blazer and an umbrella"})
    events = [json.loads(line) for line in r.text.splitlines() if line]
    types = [e["type"] for e in events]
    assert types[:2] == ["reply", "plan"] and types[-2:] == ["result", "closing"]
    assert sorted(e["requested_as"] for e in events if e["type"] == "item") == ["blazer", "umbrella"]
    blazer, umbrella = events[-2]["sections"]
    assert {c["product_id"] for c in blazer["cards"]} == {"d1", "d2"}
    for c in blazer["cards"]:
        assert c["name"] == catalog.get(c["product_id"]).name  # names come from the catalog
    assert umbrella["cards"] == [] and "no umbrella" in umbrella["note"]
    assert "$" not in events[-1]["text"]  # concierge never restates prices


def test_small_talk_is_answered_without_searching(client):
    r = client.post("/api/ask", json={"user": "maya", "message": "hi", "history": []})
    events = [json.loads(line) for line in r.text.splitlines() if line]
    assert [e["type"] for e in events] == ["reply"] and "Maya" in events[0]["text"]


def test_feedback_updates_memory_and_validates_input(client):
    r = client.post("/api/feedback", json={"user": "maya", "product_id": "d1", "cluster": 0, "action": "like"})
    assert r.status_code == 200 and r.json()["weight"] > 1.0 and r.json()["liked"]
    assert client.post("/api/feedback", json={"user": "maya", "product_id": "d1", "cluster": 0,
                                              "action": "buy"}).status_code == 400
    assert client.post("/api/feedback", json={"user": "maya", "product_id": "nope", "cluster": 0,
                                              "action": "like"}).status_code == 404
    assert client.post("/api/ask", json={"user": "nobody", "message": "x"}).status_code == 404
