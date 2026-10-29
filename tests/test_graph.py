import asyncio

from visioncart import config
from visioncart.agents.types import Plan, PlannedItem
from visioncart.graph import run
from tests.conftest import FakeLLM


def planner(*items):
    def handler(_user):
        return Plan(items=[PlannedItem(requested_as=c, category=c, description=f"{c} in my style", cluster_id=k,
                                       max_price=None, size=None, needs_water_resistant=False)
                           for c, k in items], total_budget=None, occasion=None)
    return handler


def test_multi_item_request_renders_only_verified_catalog_products(make_deps):
    llm = FakeLLM({"Plan": planner(("blazer", 0), ("bag", 1), ("umbrella", 0))})
    deps = make_deps(llm, threshold=0.6)
    out = asyncio.run(run("blazer, bag and an umbrella", deps))
    secs = out["sections"]
    assert [s.category for s in secs] == ["blazer", "bag", "unavailable"]
    assert {c.product_id for c in secs[0].cards} == {"d1", "d2"}  # dark cluster only
    assert secs[1].cards[0].product_id == "l2"                    # light cluster
    assert "d4" not in [c.product_id for c in secs[1].cards]  # out of stock never shown
    assert secs[2].cards == [] and "no umbrella" in secs[2].note
    for s in secs:
        for c in s.cards:
            assert c.name == deps.catalog.get(c.product_id).name


def test_retries_are_capped_and_fall_back_to_low_confidence(make_deps):
    llm = FakeLLM({"Plan": planner(("blazer", 0))})
    out = asyncio.run(run("a blazer", make_deps(llm, threshold=1.5)))  # unreachable
    sec = out["sections"][0]
    assert llm.calls.count("Queries") <= 1 + config.MAX_RETRIES
    assert sec.cards and all(c.low_confidence for c in sec.cards)
    assert "LOW MATCH CONFIDENCE" in sec.note


def test_empty_plan(make_deps):
    out = asyncio.run(run("hi", make_deps(FakeLLM({"Plan": planner()}))))
    assert out["sections"] == []
