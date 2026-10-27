"""Component + end-to-end evaluation.

    python -m evals.run_eval --split dev
    python -m evals.run_eval --split test      # run once, after calibrating on dev

Headline metrics (hard enough to be informative):
  style ranking   every board ranks ALL catalog products by visual fit (no category filter):
                  ~12 relevant vs ~108 distractors. AUC and nDCG@10, plus multi-cluster vs a
                  single averaged centroid on mixed two-style boards.
  contested e2e   full pipeline on categories sold by more than one style. nDCG@3 / MRR with
                  bootstrap 95% CIs, vs. the worker's raw order and a random order.

Diagnostics:
  all-category e2e  includes single-style categories where any order scores ~1 (inflated)
  clustering        mixed boards: clusters found and pin purity
  planner           category extraction on evals/data/planner_cases.json
  worker / verifier recall of candidates; precision of shown items; empty / low-confidence rate
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

from evals import harness
from visioncart import config
from visioncart.agents.orchestrator import plan_request
from visioncart.agents.search_worker import run_worker
from visioncart.catalog.store import Catalog
from visioncart.graph import make_deps, run
from visioncart.llm import OpenAILLM, normalize
from visioncart.memory.store import MemoryStore

PLANNER_CASES = Path(__file__).parent / "data" / "planner_cases.json"
E2E_METRICS = ("ndcg@3", "mrr", "p@1")


def eval_clustering(store: MemoryStore, split: str) -> dict:
    lab = harness.labels()
    rows = []
    for a, b in harness.MIXED_PAIRS:
        mem = store.load(harness.eval_user(split, f"{a}+{b}"))
        majority = sum(Counter(lab[p]["style"] for p in c.pins).most_common(1)[0][1] for c in mem.clusters)
        total = sum(len(c.pins) for c in mem.clusters)
        rows.append({"board": f"{a}+{b}", "k": len(mem.clusters), "purity": majority / total})
    return {"found_2_clusters": sum(r["k"] == 2 for r in rows) / len(rows),
            "mean_purity": harness.mean(r["purity"] for r in rows), "boards": rows}


def _rank_metrics(scores: np.ndarray, ids: list[str], rel: set[str]) -> dict:
    ranked = [ids[i] for i in np.argsort(-scores)]
    ys = [i in rel for i in ids]
    return {"auc": float(roc_auc_score(ys, scores)), "ndcg@10": harness.ndcg_at_k(ranked, rel, 10)}


def eval_style_ranking(store: MemoryStore, catalog: Catalog, split: str) -> dict:
    """Visual fit alone, across the whole catalog. Tests captions + embeddings + clusters."""
    ps = harness.product_styles(catalog)
    ids = [p.id for p in catalog.products]
    V = catalog.style_vecs
    rng = random.Random(0)

    def board_scores(user: str) -> tuple[np.ndarray, np.ndarray]:
        mem = store.load(user)
        C = np.stack([c.centroid for c in mem.clusters])
        w = np.array([len(c.pins) for c in mem.clusters], dtype=np.float32)
        single = normalize((C * w[:, None]).sum(axis=0))  # what one averaged centroid would give
        return (V @ C.T).max(axis=1), V @ single

    single_rows = []
    for style in harness.styles():
        multi, _ = board_scores(harness.eval_user(split, style))
        rel = {i for i in ids if ps[i] == style}
        rand = harness.mean(harness.ndcg_at_k(rng.sample(ids, len(ids)), rel, 10) for _ in range(200))
        single_rows.append({"board": style, **_rank_metrics(multi, ids, rel), "random_ndcg@10": rand})

    mixed_rows = []
    for a, b in harness.MIXED_PAIRS:
        multi, single = board_scores(harness.eval_user(split, f"{a}+{b}"))
        rel = {i for i in ids if ps[i] in (a, b)}
        m, s = _rank_metrics(multi, ids, rel), _rank_metrics(single, ids, rel)
        mixed_rows.append({"board": f"{a}+{b}", "multi_auc": m["auc"], "single_auc": s["auc"],
                           "multi_ndcg@10": m["ndcg@10"], "single_ndcg@10": s["ndcg@10"]})

    return {
        "single_style": {k: harness.summarize([r[k] for r in single_rows]) for k in ("auc", "ndcg@10", "random_ndcg@10")},
        "mixed": {k: harness.summarize([r[k] for r in mixed_rows])
                  for k in ("multi_auc", "single_auc", "multi_ndcg@10", "single_ndcg@10")},
        "boards": single_rows, "mixed_boards": mixed_rows,
    }


async def eval_planner(llm, store, catalog, split: str) -> dict:
    cases = json.loads(PLANNER_CASES.read_text())
    deps = make_deps(llm, store, harness.eval_user(split, harness.styles()[0]), catalog)
    plans = await asyncio.gather(*[plan_request(c["request"], deps) for c in cases])
    p_list, r_list, exact = [], [], 0
    rows = []
    for c, plan in zip(cases, plans):
        got = {i.category for i in plan.items if i.category != "unavailable"}
        want = set(c["expected"])
        p_list.append(len(got & want) / len(got) if got else float(not want))
        r_list.append(len(got & want) / len(want) if want else float(not got))
        exact += got == want
        rows.append({"request": c["request"], "expected": sorted(want), "got": sorted(got)})
    return {"precision": harness.mean(p_list), "recall": harness.mean(r_list),
            "exact": exact / len(cases), "n": len(cases), "cases": rows}


def _e2e(rows: list[dict]) -> dict:
    return {variant: {m: harness.summarize([r[variant][m] for r in rows]) for m in E2E_METRICS}
            for variant in ("random", "worker_order", "pipeline")}


async def eval_retrieval(llm, store, catalog, split: str) -> dict:
    cases = [(s, cat) for s in harness.styles() for cat in harness.style_categories(catalog, s)]
    contested = harness.contested_categories(catalog)

    async def one(style: str, category: str) -> dict:
        deps = make_deps(llm, store, harness.eval_user(split, style), catalog)
        rel = harness.relevant(catalog, style, category, in_stock_only=True)
        pool = [p.id for p in catalog.products if p.category == category and p.in_stock]
        # Baseline = the pipeline's own first worker call (same planner item, cached queries).
        item = (await plan_request(harness.eval_request(category), deps)).items[0]
        worker_ranked = [pid for pid, _ in await run_worker(item, deps)]
        out = await run(harness.eval_request(category), deps)
        sec = out["sections"][0] if out["sections"] else None
        ranked = [c.product_id for c in sec.cards] if sec else []

        def metrics(order):
            return {"p@1": harness.precision_at_k(order, rel, 1), "mrr": harness.mrr(order, rel),
                    "ndcg@3": harness.ndcg_at_k(order, rel, 3)}

        return {
            "style": style, "category": category, "contested": category in contested,
            "n_relevant": len(rel), "pool": len(pool), "planned_category": sec.category if sec else None,
            "worker_recall": len(set(worker_ranked) & rel) / len(rel) if rel else float("nan"),
            "random": harness.random_baseline(pool, rel), "worker_order": metrics(worker_ranked),
            "pipeline": metrics(ranked), "shown": ranked,
            "shown_precision": harness.precision_shown(ranked, rel),
            "low_confidence": bool(sec and sec.cards and sec.cards[0].low_confidence),
        }

    rows = [r for r in await asyncio.gather(*[one(s, c) for s, c in cases]) if r["n_relevant"]]
    hard = [r for r in rows if r["contested"]]
    return {
        "contested": {"n": len(hard), **_e2e(hard)},
        "all": {"n": len(rows), **_e2e(rows)},
        "worker_recall": harness.mean(r["worker_recall"] for r in rows),
        "shown_precision_contested": harness.mean(r["shown_precision"] for r in hard if r["shown_precision"] is not None),
        "shown_precision_all": harness.mean(r["shown_precision"] for r in rows if r["shown_precision"] is not None),
        "empty_rate": harness.mean(not r["shown"] for r in rows),
        "low_confidence_rate": harness.mean(r["low_confidence"] for r in rows),
        "planner_category_match": harness.mean(r["planned_category"] == r["category"] for r in rows),
        "cases": rows,
    }


def _fmt(s: dict) -> str:
    lo, hi = s["ci95"]
    return f"{s['mean']:.3f} [{lo:.2f}, {hi:.2f}]"


def to_markdown(split: str, res: dict) -> str:
    sr, e2e = res["style_ranking"], res["retrieval"]
    L = [f"## {time.strftime('%Y-%m-%d %H:%M')} | split: {split} | threshold {res['threshold']:.3f} "
         f"| blend {res['blend']:.1f} "
         f"| {config.CHAT_MODEL} / {config.EMBED_MODEL}", "",
         "Values are mean [bootstrap 95% CI] over boards or cases.", "",
         f"### Style ranking, whole catalog ({sr['single_style']['auc']['n']} boards, "
         f"~{len(res['catalog_ids']) // 10} relevant of {len(res['catalog_ids'])})", "",
         "| Board type | AUC | nDCG@10 |", "|---|---|---|",
         f"| single-style | {_fmt(sr['single_style']['auc'])} | {_fmt(sr['single_style']['ndcg@10'])} |",
         f"| random order | 0.500 | {_fmt(sr['single_style']['random_ndcg@10'])} |",
         f"| mixed, multi-cluster memory | {_fmt(sr['mixed']['multi_auc'])} | {_fmt(sr['mixed']['multi_ndcg@10'])} |",
         f"| mixed, single averaged centroid | {_fmt(sr['mixed']['single_auc'])} | {_fmt(sr['mixed']['single_ndcg@10'])} |",
         ""]
    for title, key in [("End-to-end, contested categories (headline)", "contested"),
                       ("End-to-end, all categories (inflated by single-style categories)", "all")]:
        g = e2e[key]
        L += [f"### {title} — {g['n']} cases", "", "| Ranking | nDCG@3 | MRR | P@1 |", "|---|---|---|---|"]
        for name, v in [("random order", "random"), ("worker order (no verifier)", "worker_order"),
                        ("full pipeline", "pipeline")]:
            L.append(f"| {name} | " + " | ".join(_fmt(g[v][m]) for m in E2E_METRICS) + " |")
        L.append("")
    L += ["### Components", "", "| Component | Metric | Value |", "|---|---|---|",
          f"| clustering | mixed boards split into 2 | {res['clustering']['found_2_clusters']:.2f} |",
          f"| clustering | mean pin purity | {res['clustering']['mean_purity']:.2f} |",
          f"| planner | precision / recall / exact (n={res['planner']['n']}) | {res['planner']['precision']:.2f} / "
          f"{res['planner']['recall']:.2f} / {res['planner']['exact']:.2f} |",
          f"| worker | recall of relevant | {e2e['worker_recall']:.2f} |",
          f"| verifier | shown precision, contested / all | {e2e['shown_precision_contested']:.2f} / {e2e['shown_precision_all']:.2f} |",
          f"| verifier | empty / low-confidence rate | {e2e['empty_rate']:.2f} / {e2e['low_confidence_rate']:.2f} |"]
    return "\n".join(L) + "\n\n---\n"


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], default="dev")
    args = ap.parse_args()

    llm, store, catalog = OpenAILLM(), MemoryStore(harness.EVAL_DB), Catalog.load()
    await harness.sync_eval_boards(llm, store, args.split)
    from visioncart.graph import load_blend, load_threshold
    res = {"split": args.split, "threshold": load_threshold(), "blend": load_blend(), "catalog_ids": [p.id for p in catalog.products],
           "style_ranking": eval_style_ranking(store, catalog, args.split),
           "clustering": eval_clustering(store, args.split),
           "planner": await eval_planner(llm, store, catalog, args.split),
           "retrieval": await eval_retrieval(llm, store, catalog, args.split)}

    harness.RESULTS_DIR.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (harness.RESULTS_DIR / f"eval_{args.split}_{stamp}.json").write_text(json.dumps(res, indent=1))
    md = to_markdown(args.split, res)
    with open(harness.RESULTS_DIR / "eval_log.md", "a") as f:
        f.write(md)
    print(md)


if __name__ == "__main__":
    asyncio.run(main())
