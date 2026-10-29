import asyncio

from visioncart.agents import presenter, verifier
from visioncart.agents.orchestrator import validate_plan
from visioncart.agents.search_worker import run_worker
from visioncart.agents.types import ItemResult, Plan, PlannedItem, Scored
from tests.conftest import FakeLLM


def item(category="blazer", cluster=0, **kw) -> PlannedItem:
    base = dict(requested_as=category, category=category, description="", cluster_id=cluster,
                max_price=None, size=None, needs_water_resistant=False)
    return PlannedItem(**{**base, **kw})


def test_hard_checks(catalog):
    assert verifier.hard_checks(catalog.get("d1"), item()) == []
    assert "over budget" in verifier.hard_checks(catalog.get("d2"), item(max_price=300))
    assert "out of stock" in verifier.hard_checks(catalog.get("d4"), item("bag"))
    assert "size unavailable" in verifier.hard_checks(catalog.get("d2"), item(size="s"))
    assert "wrong category" in verifier.hard_checks(catalog.get("d3"), item("blazer"))
    assert "not water resistant" in verifier.hard_checks(catalog.get("d1"), item(needs_water_resistant=True))


def test_visual_score_prefers_matching_cluster(make_deps):
    deps = make_deps(FakeLLM())
    dark = verifier.score_candidates([("d1", 0.5), ("l1", 0.5)], item(cluster=0), deps)
    light = verifier.score_candidates([("d1", 0.5), ("l1", 0.5)], item(cluster=1), deps)
    assert dark[0].product_id == "d1" and light[0].product_id == "l1"


def test_decide_threshold_and_feedback():
    scored = [Scored("a", 0.8, 0.0), Scored("b", 0.4, 0.0), Scored("c", 0.9, 0.0, ["out of stock"])]
    accepted, fb = verifier.decide(scored, 0.5)
    assert [s.product_id for s in accepted] == ["a"] and fb is None
    accepted, fb = verifier.decide(scored, 0.85)
    assert accepted == [] and "out of stock" in fb and "threshold" in fb
    assert [s.product_id for s in verifier.fallback(scored)] == ["a", "b"]


def test_validate_plan(make_deps):
    deps = make_deps(FakeLLM())
    plan = Plan(items=[item("Blazer", cluster=9), item("rain boots"), item("bag", max_price=500)],
                total_budget=300, occasion=None)
    plan = validate_plan(plan, deps)
    assert plan.items[0].category == "blazer" and plan.items[0].cluster_id in (0, 1)
    assert plan.items[1].category == "unavailable"
    assert plan.items[0].max_price == 150 and plan.items[2].max_price == 150


def test_worker_returns_only_in_category_ids(make_deps):
    deps = make_deps(FakeLLM())
    hits = asyncio.run(run_worker(item("bag"), deps))
    assert {pid for pid, _ in hits} == {"d3", "d4", "l2"}
    assert [s for _, s in hits] == sorted((s for _, s in hits), reverse=True)


def test_blend_rank_moves_between_visual_and_retrieval_order():
    a, b = Scored("a", visual=0.9, bias=0.0, retrieval=0.1), Scored("b", visual=0.6, bias=0.0, retrieval=0.8)
    assert [s.product_id for s in verifier.blend_rank([a, b], 0.0)] == ["a", "b"]
    assert [s.product_id for s in verifier.blend_rank([a, b], 1.0)] == ["b", "a"]


def test_threshold_gates_but_rank_orders():
    hi_style = Scored("v", visual=0.95, bias=0.0, rank=0.2)
    hi_rank = Scored("r", visual=0.75, bias=0.0, rank=0.9)
    below = Scored("x", visual=0.5, bias=0.0, rank=1.0)
    accepted, _ = verifier.decide([hi_style, hi_rank, below], threshold=0.7)
    assert [s.product_id for s in accepted] == ["r", "v"]


def test_presenter_drops_explanations_with_prices(make_deps):
    deps = make_deps(FakeLLM())
    r = ItemResult(0, item(), [Scored("d1", 0.9, 0.0)], {"d1": "Only $20, a steal"}, 1, False)
    card = presenter.build_sections([r], deps)[0].cards[0]
    assert "$" not in card.why and card.price == deps.catalog.get("d1").price


def test_plan_drops_sizes_that_are_not_sizes(make_deps):
    deps = make_deps(FakeLLM())
    items = [PlannedItem(requested_as="blazer", category="blazer", description="", cluster_id=0, max_price=None,
                         size=s, needs_water_resistant=False) for s in ("Quinn's size", "m", "32x30", "10.5")]
    plan = validate_plan(Plan(items=items, total_budget=None, occasion=None), deps)
    assert [i.size for i in plan.items] == [None, "m", "32x30", "10.5"]


def test_size_check_accepts_inch_suffix():
    assert verifier._size("32inch") == verifier._size("32") == "32" and verifier._size(" m ") == "M"
