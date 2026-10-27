# VisionCart 🎨🛍️🛒

**Group Members:** Kurumi Kaneko, Quinton King, Raras Pramudita, Lance Santana

## Overview

Modern e-commerce remains anchored to keyword-based retrieval, a modality that often fails to capture the aesthetic preferences of individual users. Consumers already curate rich visual data on platforms like Pinterest, Instagram, and TikTok, yet these vision boards are disconnected from the point of purchase. This forces users to manually translate visual inspiration into text-based search queries, creating avoidable gaps between what they envision and what they can actually find. By leveraging multimodal models and agentic reasoning, VisionCart builds a personalized, intent-driven retail agent that reduces search friction and filters out products misaligned with a user's established taste profile.

---

## Rearchitecture (this branch)

A multi-agent rebuild that runs entirely on a **static local catalog** (no web requests) and **OpenAI models only** (no local models, no GPU). The original pipeline lives in [`legacy/`](legacy/).

```
request ─▶ Orchestrator ──reads──▶ Style memory (SQLite, per user)
              │ Send, one per item (parallel)
              ▼
         Search worker ─▶ Verifier ─┬─▶ explain ─▶ Presenter (renders from verified ids only)
              ▲                     │
              └── retry w/ feedback ┘  max 2 retries, then LOW MATCH CONFIDENCE fallback
user feedback (like / save / skip) ─▶ style memory term + cluster weights
```

| Agent | Model vs code |
|---|---|
| **Style memory** | Vision model describes each pin (fixed schema), `text-embedding-3-small` embeds it, k-means + silhouette splits the board into 1–4 clusters, LLM writes a persona + search terms per cluster. Re-syncs only when the board's content hash changes. |
| **Orchestrator** | LLM drafts a typed `Plan` (items, category, cluster, budget, size, weather); code validates categories/clusters and splits budgets. |
| **Search worker** | LLM writes 2–3 queries; code runs hybrid BM25 + embedding search inside the category. Returns ids only. |
| **Verifier** | Code: category, price, stock, size, water resistance. Visual fit: cosine to the cluster centroid with a threshold calibrated on the dev split. LLM: one-sentence explanation per accepted id, nothing else. |
| **Presenter** | Pure code. Names, prices, images and links come from catalog records by id. |

**Image "embeddings":** OpenAI has no image-embedding endpoint, so each image is described once by a vision model and that description is embedded. Captions and embeddings are cached under `data/cache/`.

### Data

- `scripts/make_splits.py` fixes the split: per style, one pin per product type goes to a **dev board** and one to a **test board** (3 pins each); the other 120 images form the catalog.
- Ground-truth style labels exist only in `evals/data/labels.json`. Catalog records have no style fields, product ids are opaque hashes, and `Catalog.load()` refuses any record carrying a label field.
- **Price, stock and sizes are synthetic** (seeded per product). The source data has none of them.
- The catalog covers 24 categories, 2–3 per style. Requests outside them (e.g. boots, umbrellas) come back as "the catalog has no …" rather than a forced match.

### Demo users (hardcoded, built from dev-board pins)

| User | Boards |
|---|---|
| `maya` | dark_academia |
| `jordan` | japandi + coastal_mediterranean |
| `sam` | cottagecore + y2k_streetwear + quiet_luxury |

### Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY
python scripts/make_splits.py        # already committed; rerun only to change the split
python scripts/build_catalog.py      # one-time: captions + embeds ~180 images
python -m evals.calibrate            # dev split -> data/calibration.json
```

### Run

```bash
python -m visioncart.cli users
python -m visioncart.cli ask jordan "a vase and a pendant light for my sunroom, under $250 total"
python -m visioncart.cli feedback jordan <product_id> like --cluster 0
```

### Evals

```bash
python -m evals.run_eval --split dev
python -m evals.run_eval --split test         # once, after calibration
python -m evals.judge sheet --split test      # CSV for annotators who did not build the system
python -m evals.judge judge && python -m evals.judge agree   # judge counts only if kappa >= 0.6
pytest                                        # offline, fake LLM; includes leak guards
```

Reported per component (clustering purity on mixed boards, planner category extraction, worker recall, verifier precision) and end-to-end (P@1, MRR, nDCG@3 against the worker's raw order as a baseline). `tests/test_leakage.py` fails if pipeline code imports `evals/`, references the labels file, or if any board pin appears in the catalog.
