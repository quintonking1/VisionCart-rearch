# VisionCart 🎨🛍️🛒

**Original team:** Kurumi Kaneko, Quinton King, Raras Pramudita, Lance Santana

People curate their taste visually, on Pinterest boards and saved posts, but shopping still runs on keyword search. VisionCart turns a mood board into a shopping agent: it learns a user's styles from their pins, then finds and verifies products that match a request like *"a vase and a pendant light for my sunroom, under $250"*.

This branch is a ground-up **multi-agent rebuild**. It runs on a **static local catalog** (no web requests) and **OpenAI models only** (no local models, no GPU). The original pipeline is preserved in [`legacy/`](legacy/).

---

## Results (held-out test split, run once on a frozen config)

| What | Result |
|---|---|
| Contested categories, nDCG@3: random → search only → full pipeline | 0.42 → 0.72 → **0.88** [0.76, 1.00] |
| Style recognition across the whole catalog, AUC (random = 0.5) | **0.96** [0.93, 0.98] |
| Mixed two-style boards, nDCG@10: multi-cluster memory vs one averaged centroid | **0.91** vs 0.65 |

Brackets are bootstrap 95% confidence intervals. The full tables are in [`results/eval_log.md`](results/eval_log.md). [How to read the metrics](#evaluation) is below.

**Known limits:** the end-to-end headline rests on 9 contested cases, so the intervals are wide. Relevance labels come from the source dataset, not yet from independent annotators. The catalog has 120 products.

---

## Architecture

```
request ─▶ Orchestrator ──reads──▶ Style memory (SQLite, per user)
              │ one Send per item (parallel)
              ▼
         Search worker ─▶ Verifier ─┬─▶ explain ─▶ Presenter (renders verified ids only)
              ▲                     │
              └── retry w/ feedback ┘  max 2 retries, then LOW MATCH CONFIDENCE fallback
user feedback (like / save / skip) ─▶ style memory term + cluster weights
```

**Design rule: code decides what code can decide.** The model handles judgment and language. Prices, stock, sizes and links never pass through model output.

| Agent | Model | Code |
|---|---|---|
| **Style memory** | Describes each pin (fixed schema); writes a persona + search terms per cluster | Embeds, clusters (k-means, k = 1–4 by silhouette), persists, re-syncs only when the board changes, applies feedback |
| **Orchestrator** | Drafts a typed plan: items, category, style cluster, budget, size, weather | Validates categories and clusters; splits the budget |
| **Search worker** | Writes 2–3 queries per item | Hybrid BM25 + embedding search within the category; returns ids + scores |
| **Verifier** | One-sentence "why it matches" per product, nothing else | Hard checks (category, price, stock, size, water resistance); **style gate** (calibrated threshold); **ranking** (calibrated blend) |
| **Presenter** | — | Renders names, prices, images and links from catalog records by id |

**Style gates, retrieval ranks.** A product must clear a style-fit threshold to be shown. Products that clear it are ordered mostly by search relevance (blend weight 0.9, chosen with leave-one-style-out on dev). Ranking by style score alone made results worse.

**Image "embeddings":** OpenAI has no image-embedding endpoint, so each image is described once by a vision model and that description is embedded with `text-embedding-3-small`.
- **Catalog products** are described as the single product for sale. The category is given as a hint, so a lamp in a room photo isn't described as the sofa.
- **Board pins** are described by the overall style of the scene, because on a mood board the whole image is the inspiration.
- The style embedding uses palette, materials, textures, era, mood and aesthetic only. Shape fields are left out so chairs don't match chairs regardless of style.

---

## Data

- **Split:** `scripts/make_splits.py` fixes it once. For each of 10 styles, one image per product type goes to a **dev board** and one to a **test board** (3 pins each). The other 120 images form the catalog.
- **No label leakage:** style labels exist only in `evals/data/labels.json`. Catalog records have no style fields, product ids are opaque hashes, and `Catalog.load()` refuses any record that carries a label. `tests/test_leakage.py` fails if pipeline code imports `evals/`, references the labels file, or if a board pin appears in the catalog.
- **Synthetic fields:** price, stock and sizes don't exist in the source data. They're generated from a fixed seed per product.
- **Coverage:** 24 categories, 2–3 per style. Requests outside them (e.g. rain boots) return "the catalog has no …" rather than a forced match.

**Demo users** (hardcoded, built from dev-board pins):

| User | Boards |
|---|---|
| `maya` | dark_academia |
| `jordan` | japandi + coastal_mediterranean |
| `sam` | cottagecore + y2k_streetwear + quiet_luxury |

---

## Setup and run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                  # add OPENAI_API_KEY; model names are overridable here
python scripts/build_catalog.py       # only if data/catalog is missing; captions + embeds ~180 images
python -m evals.calibrate             # dev split -> data/calibration.json (threshold + blend)
```

```bash
python -m visioncart.cli users
python -m visioncart.cli ask jordan "a vase and a pendant light for my sunroom, under $250 total"
python -m visioncart.cli feedback jordan <product_id> like --cluster 0
pytest                                # offline with a fake LLM; includes the leak guards
```

---

## Evaluation

```bash
python -m evals.run_eval --split dev
python -m evals.run_eval --split test          # once, on a frozen config; records the git commit
python -m evals.judge sheet --split test       # label sheet for annotators who didn't build the system
python -m evals.judge judge && python -m evals.judge agree   # LLM judge counts only if kappa >= 0.6
```

**Style ranking (whole catalog).** For each board, score all 120 products by style fit, ignoring category. About 12 are correct and the rest are distractors. This tests style recognition on its own.
- **AUC:** chance that a correct product outranks a wrong one (0.5 = random).
- **nDCG@10:** quality of the top 10.
- **Single-style boards:** one style per board.
- **Mixed boards:** two styles per board. Compares multi-cluster memory with a single averaged centroid.

**End-to-end.** Send "I'm looking for a {category}" for each board and each category its style sells, then grade the 3 products shown.
- **nDCG@3** is the headline. **MRR** measures how far down the first correct product is.
- **Three orderings:**
  - **random order:** the floor;
  - **worker order:** search only, no verifier;
  - **full pipeline:** what the user sees.
- **Contested categories** (sold by several styles) are the headline. The all-category numbers are inflated, because when only one style sells a category every candidate is correct, and even random order scores about 0.83.

**Components:** clustering purity on mixed boards, planner category extraction (12 cases), worker recall, shown precision, and empty / low-confidence rates.

**Discipline:**
- The threshold and blend are calibrated on dev only, and the blend uses leave-one-style-out.
- The test split was run once, at commit `a346140`.
- Further tuning needs new data to evaluate honestly.

---

## Layout

```
visioncart/      pipeline: agents/, catalog/, memory/, graph.py (LangGraph), cli.py
evals/           harness, calibration, eval runner, LLM judge; the only code that reads labels
scripts/         make_splits.py, build_catalog.py
data/            splits, built catalog + embeddings, calibration (cache/ and *.sqlite are gitignored)
results/         eval_log.md + per-run JSON
tests/           offline tests with a fake LLM
legacy/          original pipeline (Qwen-VL, Ollama, SerpAPI, Chainlit)
```
