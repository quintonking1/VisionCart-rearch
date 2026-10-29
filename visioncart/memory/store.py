"""Persistent per-user style memory (SQLite)."""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from visioncart import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, board_hash TEXT, synced_at REAL);
CREATE TABLE IF NOT EXISTS pins (user_id TEXT, path TEXT, cluster_id INTEGER, PRIMARY KEY (user_id, path));
CREATE TABLE IF NOT EXISTS clusters (
    user_id TEXT, cluster_id INTEGER, name TEXT, persona TEXT, search_terms TEXT, avoid_terms TEXT,
    centroid BLOB, weight REAL, term_weights TEXT, PRIMARY KEY (user_id, cluster_id));
CREATE TABLE IF NOT EXISTS feedback (user_id TEXT, product_id TEXT, cluster_id INTEGER, action TEXT, ts REAL);
"""


@dataclass
class StyleCluster:
    id: int
    name: str
    persona: str
    search_terms: list[str]
    avoid_terms: list[str]
    centroid: np.ndarray
    weight: float = 1.0
    term_weights: dict[str, float] = field(default_factory=dict)
    pins: list[str] = field(default_factory=list)

    def learned_terms(self, n: int = 6) -> tuple[list[str], list[str]]:
        ranked = sorted(self.term_weights.items(), key=lambda kv: kv[1])
        liked = [t for t, w in reversed(ranked) if w > 0][:n]
        disliked = [t for t, w in ranked if w < 0][:n]
        return liked, disliked


@dataclass
class StyleMemory:
    user_id: str
    board_hash: str
    clusters: list[StyleCluster]

    def cluster(self, cid: int) -> StyleCluster:
        return next(c for c in self.clusters if c.id == cid)


class MemoryStore:
    def __init__(self, path: Path = config.MEMORY_DB):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)

    def board_hash(self, user_id: str) -> str | None:
        row = self.db.execute("SELECT board_hash FROM users WHERE user_id=?", (user_id,)).fetchone()
        return row[0] if row else None

    def save(self, mem: StyleMemory, carry_over: dict[int, int] | None = None) -> None:
        """Replace a user's clusters. `carry_over` maps new cluster id -> old id whose learned
        weights should survive a re-sync."""
        old = {c.id: c for c in self.load(mem.user_id).clusters} if self.board_hash(mem.user_id) else {}
        for c in mem.clusters:
            prev = old.get((carry_over or {}).get(c.id, -1))
            if prev is not None:
                c.weight, c.term_weights = prev.weight, dict(prev.term_weights)
        with self.db:
            self.db.execute("DELETE FROM clusters WHERE user_id=?", (mem.user_id,))
            self.db.execute("DELETE FROM pins WHERE user_id=?", (mem.user_id,))
            self.db.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (mem.user_id, mem.board_hash, time.time()))
            for c in mem.clusters:
                self._write_cluster(mem.user_id, c)
                self.db.executemany("INSERT INTO pins VALUES (?,?,?)", [(mem.user_id, p, c.id) for p in c.pins])

    def update_cluster(self, user_id: str, c: StyleCluster) -> None:
        with self.db:
            self._write_cluster(user_id, c)

    def _write_cluster(self, user_id: str, c: StyleCluster) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO clusters VALUES (?,?,?,?,?,?,?,?,?)",
            (user_id, c.id, c.name, c.persona, json.dumps(c.search_terms), json.dumps(c.avoid_terms),
             c.centroid.astype(np.float32).tobytes(), c.weight, json.dumps(c.term_weights)))

    def load(self, user_id: str) -> StyleMemory:
        board_hash = self.board_hash(user_id)
        if board_hash is None:
            raise KeyError(f"no style memory for {user_id!r}; sync their board first")
        pins: dict[int, list[str]] = {}
        for path, cid in self.db.execute("SELECT path, cluster_id FROM pins WHERE user_id=?", (user_id,)):
            pins.setdefault(cid, []).append(path)
        clusters = [
            StyleCluster(id=cid, name=name, persona=persona, search_terms=json.loads(st), avoid_terms=json.loads(at),
                         centroid=np.frombuffer(blob, dtype=np.float32).copy(), weight=w,
                         term_weights=json.loads(tw), pins=sorted(pins.get(cid, [])))
            for cid, name, persona, st, at, blob, w, tw in self.db.execute(
                "SELECT cluster_id, name, persona, search_terms, avoid_terms, centroid, weight, term_weights "
                "FROM clusters WHERE user_id=? ORDER BY cluster_id", (user_id,))
        ]
        return StyleMemory(user_id, board_hash, clusters)

    def log_feedback(self, user_id: str, product_id: str, cluster_id: int, action: str) -> None:
        with self.db:
            self.db.execute("INSERT INTO feedback VALUES (?,?,?,?,?)",
                            (user_id, product_id, cluster_id, action, time.time()))
