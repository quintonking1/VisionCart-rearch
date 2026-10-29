"""Calibrate the verifier on the DEV split only.

1. Threshold: for each dev board and each category in that style, every catalog product in
   the category is scored against the board's nearest cluster; a product is positive if its
   labelled style matches the board. The F1-maximising threshold is kept.
2. Blend: weight on the worker's retrieval score vs visual fit when ordering products that
   passed the threshold. Chosen by nDCG@3 with leave-one-style-out: for each style, the
   blend is picked on the other nine styles and scored on the held-out one, so the reported
   estimate never sees its own labels. The final blend is the best on all of dev.
   Items come from the real planner on the same request run_eval uses, so the blend is tuned
   on the queries the pipeline actually issues.

    python -m evals.calibrate
"""
from __future__ import annotations

import asyncio
import json

from sklearn.metrics import roc_auc_score

from evals import harness
from visioncart import config
from visioncart.agents import verifier
from visioncart.agents.orchestrator import plan_request
from visioncart.agents.search_worker import run_worker
from visioncart.catalog.store import Catalog
from visioncart.graph import make_deps
from visioncart.llm import OpenAILLM
from visioncart.memory.store import MemoryStore

BLEND_GRID = [round(i / 10, 1) for i in range(11)]


def calibration_pairs(catalog: Catalog, store: MemoryStore, split: str = "dev"):
    ps = harness.product_styles(catalog)
    scores, ys = [], []
    for style in harness.styles():
        mem = store.load(harness.eval_user(split, style))
        for category in harness.style_categories(catalog, style):
            for p in catalog.products:
                if p.category != category:
                    continue
                v = catalog.style_vec(p.id)
                scores.append(max(float(v @ c.centroid) for c in mem.clusters))
                ys.append(ps[p.id] == style)
    return scores, ys


async def blend_cases(llm, store: MemoryStore, catalog: Catalog, threshold: float, split: str = "dev") -> list[dict]:
    """Per (style, category): the products the verifier would order, with their scores."""
    contested = harness.contested_categories(catalog)

    async def one(style: str, category: str) -> dict:
        deps = make_deps(llm, store, harness.eval_user(split, style), catalog, threshold=threshold, blend=0.0)
        item = (await plan_request(harness.eval_request(category), deps)).items[0]
        scored = verifier.score_candidates(await run_worker(item, deps), item, deps)
        gated = [s for s in scored if not s.failures and s.score >= threshold] or verifier.fallback(scored)
        return {"style": style, "category": category, "contested": category in contested, "scored": gated,
                "rel": harness.relevant(catalog, style, category, in_stock_only=True)}

    cases = await asyncio.gather(*[one(s, c) for s in harness.styles() for c in harness.style_categories(catalog, s)])
    return [c for c in cases if c["rel"]]


def ndcg_at_blend(case: dict, blend: float) -> float:
    ranked = [s.product_id for s in verifier.blend_rank(list(case["scored"]), blend)]
    return harness.ndcg_at_k(ranked, case["rel"], 3)


def best_blend(cases: list[dict]) -> float:
    # Ties go to the blend nearest 0.5, the uninformed prior.
    return max(BLEND_GRID, key=lambda b: (harness.mean(ndcg_at_blend(c, b) for c in cases), -abs(b - 0.5)))


def leave_one_style_out(cases: list[dict]) -> dict:
    folds = []
    for style in sorted({c["style"] for c in cases}):
        train = [c for c in cases if c["style"] != style]
        held = [c for c in cases if c["style"] == style]
        b = best_blend(train)
        folds.append({"style": style, "blend": b, "held_out": [ndcg_at_blend(c, b) for c in held],
                      "held_out_contested": [ndcg_at_blend(c, b) for c in held if c["contested"]]})
    contested = [x for f in folds for x in f["held_out_contested"]]
    return {"folds": [{"style": f["style"], "blend": f["blend"]} for f in folds],
            "loso_ndcg@3_all": harness.summarize([x for f in folds for x in f["held_out"]]),
            "loso_ndcg@3_contested": harness.summarize(contested)}


async def main() -> None:
    llm, store, catalog = OpenAILLM(), MemoryStore(harness.EVAL_DB), Catalog.load()
    await harness.sync_eval_boards(llm, store, "dev")
    scores, ys = calibration_pairs(catalog, store)
    threshold, f1 = harness.best_f1_threshold(scores, ys)

    cases = await blend_cases(llm, store, catalog, threshold)
    hard = [c for c in cases if c["contested"]]
    curve = {b: round(harness.mean(ndcg_at_blend(c, b) for c in hard), 4) for b in BLEND_GRID}
    loso = leave_one_style_out(cases)

    out = {"threshold": round(threshold, 4), "dev_f1": round(f1, 4),
           "dev_auc": round(roc_auc_score(ys, scores), 4), "n_pairs": len(ys), "n_positive": sum(ys),
           "blend": best_blend(cases), "blend_curve_contested_ndcg@3": curve, "blend_loso": loso,
           "split": "dev", "embed_model": config.EMBED_MODEL}
    config.CALIBRATION_PATH.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "blend_loso"}, indent=1))
    print("LOSO folds:", loso["folds"])
    print("LOSO nDCG@3 contested:", loso["loso_ndcg@3_contested"])


if __name__ == "__main__":
    asyncio.run(main())
