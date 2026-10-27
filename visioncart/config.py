"""Paths, model names, and pipeline knobs. Everything model-related is env-overridable."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
SPLITS_PATH = DATA_DIR / "splits.json"
CATALOG_DIR = DATA_DIR / "catalog"
CACHE_DIR = DATA_DIR / "cache"
MEMORY_DB = DATA_DIR / "memory.sqlite"
CALIBRATION_PATH = DATA_DIR / "calibration.json"

CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", CHAT_MODEL)
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
MAX_CONCURRENCY = int(os.getenv("OPENAI_MAX_CONCURRENCY", "8"))

# Verifier
MAX_RETRIES = 2            # worker re-runs after the first attempt
TOP_K = 3                  # products shown per requested item
CANDIDATES_PER_WORKER = 12
DEFAULT_THRESHOLD = 0.5    # used only until evals/calibrate.py writes CALIBRATION_PATH
DEFAULT_BLEND = 0.5        # retrieval vs visual weight for ordering; calibrated alongside the threshold
FEEDBACK_BIAS_SCALE = 0.05 # max score nudge from learned term weights

# Fields that carry ground-truth style labels. They must never reach the pipeline.
FORBIDDEN_CATALOG_KEYS = {"style", "style_label", "style_terms", "query", "query_terms", "ground_truth"}


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p
