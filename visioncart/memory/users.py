"""Hardcoded demo users. Each board is built from dev-split pins in data/splits.json, so no
board image is ever in the catalog and test-split pins stay reserved for evals."""
from __future__ import annotations

import json

from visioncart import config

DEMO_USERS = {
    "maya": {"about": "one clear style", "boards": ["dark_academia"]},
    "jordan": {"about": "home decor, two styles", "boards": ["japandi", "coastal_mediterranean"]},
    "sam": {"about": "mixed wardrobe", "boards": ["cottagecore", "y2k_streetwear", "quiet_luxury"]},
}


def board_pins(board_names: list[str], split: str = "dev") -> list[str]:
    boards = json.loads(config.SPLITS_PATH.read_text())["boards"]
    return [p for name in board_names for p in boards[name][split]]


def user_pins(user_id: str) -> list[str]:
    if user_id not in DEMO_USERS:
        raise KeyError(f"unknown demo user {user_id!r}; choose from {sorted(DEMO_USERS)}")
    return board_pins(DEMO_USERS[user_id]["boards"])
