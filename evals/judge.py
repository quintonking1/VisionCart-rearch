"""LLM-as-judge, gated on agreement with human labels.

    python -m evals.judge sheet --split test     # writes evals/data/label_sheet.csv for annotators
    python -m evals.judge judge                  # fills judge_relevant column
    python -m evals.judge agree                  # Cohen's kappa human vs judge

Annotators should be people who did not build the system. They fill `human_relevant` with
1/0 by looking at the board images and the product image. Until `agree` reports
kappa >= 0.6, judge scores must not be reported as a metric.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
from pathlib import Path

from pydantic import BaseModel

from evals import harness
from visioncart.catalog.store import Catalog
from visioncart.llm import OpenAILLM
from visioncart.memory.users import board_pins

SHEET = Path(__file__).parent / "data" / "label_sheet.csv"
VALIDATION = Path(__file__).parent / "data" / "judge_validation.json"
FIELDS = ["pair_id", "board", "board_images", "product_id", "product_image", "human_relevant", "annotator",
          "judge_relevant"]
MIN_KAPPA = 0.6


class Verdict(BaseModel):
    relevant: bool
    reason: str


JUDGE_SYSTEM = ("You judge whether a product fits the visual style of a mood board. The first images are "
                "the board; the LAST image is the product. Ignore product category; judge style only.")


def make_sheet(split: str, per_board: int = 12, seed: int = 0) -> None:
    catalog, rng = Catalog.load(), random.Random(seed)
    rows = []
    for style in harness.styles():
        cats = set(harness.style_categories(catalog, style))
        pool = [p for p in catalog.products if p.category in cats]
        pins = board_pins([style], split)
        # Board name is deliberately not shown to annotators; it is only an internal key.
        for p in rng.sample(pool, min(per_board, len(pool))):
            rows.append({"pair_id": f"{len(rows):04d}", "board": f"{split}-{style}", "board_images": "|".join(pins),
                         "product_id": p.id, "product_image": p.image, "human_relevant": "", "annotator": "",
                         "judge_relevant": ""})
    rng.shuffle(rows)
    with open(SHEET, "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} pairs to {SHEET}")


def _read() -> list[dict]:
    with open(SHEET) as f:
        return list(csv.DictReader(f))


async def run_judge() -> None:
    llm, rows = OpenAILLM(), _read()

    async def one(r: dict) -> None:
        v = await llm.parse(Verdict, JUDGE_SYSTEM, "Does the last image fit this board's style?",
                            images=r["board_images"].split("|") + [r["product_image"]])
        r["judge_relevant"] = str(int(v.relevant))

    await asyncio.gather(*[one(r) for r in rows])
    with open(SHEET, "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"judged {len(rows)} pairs")


def agree() -> None:
    rows = [r for r in _read() if r["human_relevant"] in ("0", "1") and r["judge_relevant"] in ("0", "1")]
    if not rows:
        print("no rows with both human and judge labels yet")
        return
    human = [r["human_relevant"] == "1" for r in rows]
    judge = [r["judge_relevant"] == "1" for r in rows]
    kappa = harness.cohen_kappa(human, judge)
    out = {"n": len(rows), "kappa": round(kappa, 4), "valid": kappa >= MIN_KAPPA,
           "agreement": round(harness.mean(h == j for h, j in zip(human, judge)), 4)}
    VALIDATION.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("--split", choices=["dev", "test"], default="test")
    sub.add_parser("judge")
    sub.add_parser("agree")
    args = ap.parse_args()
    if args.cmd == "sheet":
        make_sheet(args.split)
    elif args.cmd == "judge":
        asyncio.run(run_judge())
    else:
        agree()


if __name__ == "__main__":
    main()
