"""Repeated board/catalog splits, pooled.

Each fold re-draws which images are dev pins, test pins and catalog products, then runs the
whole procedure in its own data directory: build catalog -> calibrate on that fold's dev
boards -> evaluate once on that fold's test boards. Pooling the folds gives ~5x the cases.

Folds reuse the same 180 images, so cases are not independent. Pooled intervals therefore
resample whole styles (cluster bootstrap), not individual cases.

    python -m evals.cross_split run --folds 5     # resumable; skips finished steps
    python -m evals.cross_split pool              # writes results/cross_split.{md,json}
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

from evals import harness
from visioncart import config

FOLDS_DIR = config.ROOT / "data" / "folds"
SEED_BASE = 100


def fold_dir(k: int) -> Path:
    return FOLDS_DIR / str(k)


def run_fold(k: int) -> None:
    d = fold_dir(k)
    env = {**os.environ, "VISIONCART_DATA_DIR": str(d), "VISIONCART_RESULTS_DIR": str(d / "results")}
    steps = [
        (d / "splits.json", ["scripts/make_splits.py", "--seed", str(SEED_BASE + k)]),
        (d / "catalog" / "embeddings.npz", ["scripts/build_catalog.py"]),
        (d / "calibration.json", ["-m", "evals.calibrate"]),
        (None, ["-m", "evals.run_eval", "--split", "test"]),
    ]
    for done_marker, args in steps:
        if done_marker is None and glob.glob(str(d / "results" / "eval_test_*.json")):
            continue
        if done_marker is not None and done_marker.exists():
            continue
        print(f"[fold {k}] {' '.join(args)}", flush=True)
        subprocess.run([sys.executable, *args], cwd=config.ROOT, env=env, check=True,
                       stdout=subprocess.DEVNULL)


# ---------- pooling ----------

def cluster_bootstrap(rows: list[dict], cluster: str, value, n: int = 2000, seed: int = 0) -> dict:
    """Mean of value(row) with a CI from resampling whole clusters (e.g. styles)."""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r[cluster], []).append(r)
    keys = sorted(groups)
    rng = random.Random(seed)
    means = []
    for _ in range(n):
        sample = [r for k in rng.choices(keys, k=len(keys)) for r in groups[k]]
        means.append(harness.mean(value(r) for r in sample))
    means.sort()
    return {"mean": harness.mean(value(r) for r in rows), "ci95": [means[int(0.025 * n)], means[int(0.975 * n) - 1]],
            "n": len(rows), "clusters": len(keys)}


def load_folds() -> list[dict]:
    folds = []
    for d in sorted(FOLDS_DIR.glob("*"), key=lambda p: int(p.name)):
        runs = sorted(glob.glob(str(d / "results" / "eval_test_*.json")))
        if runs:
            folds.append({"fold": int(d.name), "eval": json.loads(Path(runs[-1]).read_text()),
                          "calibration": json.loads((d / "calibration.json").read_text())})
    return folds


def pool(folds: list[dict]) -> dict:
    contested, all_cases, boards, mixed = [], [], [], []
    for f in folds:
        ev = f["eval"]
        for c in ev["retrieval"]["cases"]:
            row = {"fold": f["fold"], "style": c["style"], "category": c["category"],
                   **{f"{v}_{m}": c[v][m] for v in ("random", "worker_order", "pipeline") for m in ("ndcg@3", "mrr")}}
            all_cases.append(row)
            if c["contested"]:
                contested.append(row)
        boards += [{"fold": f["fold"], "style": b["board"], **b} for b in ev["style_ranking"]["boards"]]
        mixed += [{"fold": f["fold"], "pair": b["board"], **b} for b in ev["style_ranking"]["mixed_boards"]]

    def cb(rows, cluster, key):
        return cluster_bootstrap(rows, cluster, lambda r: r[key])

    delta = [r["pipeline_ndcg@3"] - r["worker_order_ndcg@3"] for r in contested]
    for r, d in zip(contested, delta):
        r["delta"] = d
    mixed_delta = [r["multi_ndcg@10"] - r["single_ndcg@10"] for r in mixed]
    for r, d in zip(mixed, mixed_delta):
        r["delta"] = d
    wins, losses = sum(d > 1e-9 for d in delta), sum(d < -1e-9 for d in delta)
    mwins, mlosses = sum(d > 1e-9 for d in mixed_delta), sum(d < -1e-9 for d in mixed_delta)

    return {
        "folds": [f["fold"] for f in folds],
        "contested": {
            **{f"{v}_{m}": cb(contested, "style", f"{v}_{m}")
               for v in ("random", "worker_order", "pipeline") for m in ("ndcg@3", "mrr")},
            "delta_pipeline_minus_worker": {**cb(contested, "style", "delta"), "wins": wins, "losses": losses,
                                            "ties": len(delta) - wins - losses,
                                            "sign_p": harness.sign_test(wins, losses)},
        },
        "all_pipeline_ndcg@3": cb(all_cases, "style", "pipeline_ndcg@3"),
        "all_random_ndcg@3": cb(all_cases, "style", "random_ndcg@3"),
        "style_ranking": {"auc": cb(boards, "style", "auc"), "ndcg@10": cb(boards, "style", "ndcg@10")},
        "mixed": {"multi_ndcg@10": cb(mixed, "pair", "multi_ndcg@10"), "single_ndcg@10": cb(mixed, "pair", "single_ndcg@10"),
                  "multi_auc": cb(mixed, "pair", "multi_auc"), "single_auc": cb(mixed, "pair", "single_auc"),
                  "delta_ndcg@10": {**cb(mixed, "pair", "delta"), "wins": mwins, "losses": mlosses,
                                    "ties": len(mixed_delta) - mwins - mlosses,
                                    "sign_p": harness.sign_test(mwins, mlosses)}},
        "per_fold": [{
            "fold": f["fold"], "commit": f["eval"].get("commit"),
            "threshold": f["calibration"]["threshold"], "blend": f["calibration"]["blend"],
            "loso_contested_ndcg@3": f["calibration"]["blend_loso"]["loso_ndcg@3_contested"]["mean"],
            "contested_cases": f["eval"]["retrieval"]["contested"]["n"],
            "pipeline_ndcg@3": f["eval"]["retrieval"]["contested"]["pipeline"]["ndcg@3"]["mean"],
            "worker_ndcg@3": f["eval"]["retrieval"]["contested"]["worker_order"]["ndcg@3"]["mean"],
            "style_auc": f["eval"]["style_ranking"]["single_style"]["auc"]["mean"],
            "mixed_multi": f["eval"]["style_ranking"]["mixed"]["multi_ndcg@10"]["mean"],
            "mixed_single": f["eval"]["style_ranking"]["mixed"]["single_ndcg@10"]["mean"],
            "cluster_purity": f["eval"]["clustering"]["mean_purity"],
            "split_into_2": f["eval"]["clustering"]["found_2_clusters"],
        } for f in folds],
    }


def _f(s: dict, signed: bool = False) -> str:
    lo, hi = s["ci95"]
    return f"{s['mean']:+.3f} [{lo:+.2f}, {hi:+.2f}]" if signed else f"{s['mean']:.3f} [{lo:.2f}, {hi:.2f}]"


def to_markdown(p: dict) -> str:
    c, m = p["contested"], p["mixed"]
    d, md = c["delta_pipeline_minus_worker"], m["delta_ndcg@10"]
    L = [f"# Cross-split evaluation ({len(p['folds'])} folds, {time.strftime('%Y-%m-%d %H:%M')})", "",
         "Each fold re-draws boards and catalog, calibrates on its own dev boards, and is evaluated once on "
         "its own test boards. Intervals are 95% cluster-bootstrap CIs resampling whole styles "
         "(or style pairs for mixed boards), because folds share images.", "",
         f"## Mixed-style boards ({md['n']} boards across folds)", "",
         "| Memory | nDCG@10 | AUC |", "|---|---|---|",
         f"| multi-cluster | {_f(m['multi_ndcg@10'])} | {_f(m['multi_auc'])} |",
         f"| single averaged centroid | {_f(m['single_ndcg@10'])} | {_f(m['single_auc'])} |",
         f"| **paired Δ (multi − single)** | **{_f(md, True)}** | wins/losses/ties {md['wins']}/{md['losses']}/{md['ties']}, "
         f"sign-test p = {md['sign_p']:.3g} |", "",
         f"## End-to-end, contested categories ({d['n']} cases across folds)", "",
         "| Ranking | nDCG@3 | MRR |", "|---|---|---|"]
    for name, v in [("random order", "random"), ("worker order (search only)", "worker_order"), ("full pipeline", "pipeline")]:
        L.append(f"| {name} | {_f(c[f'{v}_ndcg@3'])} | {_f(c[f'{v}_mrr'])} |")
    L += [f"| **paired Δ (pipeline − worker)** | **{_f(d, True)}** | wins/losses/ties {d['wins']}/{d['losses']}/{d['ties']}, "
          f"sign-test p = {d['sign_p']:.3g} |", "",
          "## Style recognition, whole catalog", "",
          f"AUC {_f(p['style_ranking']['auc'])}, nDCG@10 {_f(p['style_ranking']['ndcg@10'])} "
          f"(random nDCG@10 ≈ 0.10) over {p['style_ranking']['auc']['n']} board evaluations.", "",
          f"All-category end-to-end nDCG@3 {_f(p['all_pipeline_ndcg@3'])} vs random {_f(p['all_random_ndcg@3'])} "
          "(inflated by single-style categories; shown for reference).", "",
          "## Per fold", "",
          "| Fold | Threshold | Blend | LOSO est. | Contested n | Pipeline / worker nDCG@3 | Style AUC | Mixed multi / single | Purity | Split into 2 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in p["per_fold"]:
        L.append(f"| {r['fold']} | {r['threshold']:.3f} | {r['blend']:.1f} | {r['loso_contested_ndcg@3']:.3f} | "
                 f"{r['contested_cases']} | {r['pipeline_ndcg@3']:.3f} / {r['worker_ndcg@3']:.3f} | {r['style_auc']:.3f} | "
                 f"{r['mixed_multi']:.3f} / {r['mixed_single']:.3f} | {r['cluster_purity']:.2f} | {r['split_into_2']:.2f} |")
    commits = sorted({r["commit"] for r in p["per_fold"]})
    L += ["", f"Commit(s): {', '.join(str(c) for c in commits)}"]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--folds", type=int, default=5)
    sub.add_parser("pool")
    args = ap.parse_args()
    if args.cmd == "run":
        for k in range(1, args.folds + 1):
            run_fold(k)
        print("all folds done")
        return
    pooled = pool(load_folds())
    out = config.ROOT / "results"
    (out / "cross_split.json").write_text(json.dumps(pooled, indent=1))
    md = to_markdown(pooled)
    (out / "cross_split.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
