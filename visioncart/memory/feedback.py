"""Likes, saves and skips adjust a cluster's term weights and overall weight.

This is where the "learning" lives: a bounded running update over the product's style
terms, not model retraining.
"""
from __future__ import annotations

from visioncart.catalog.store import Product
from visioncart.memory.store import MemoryStore, StyleCluster

TERM_STEP = {"save": 0.3, "like": 0.2, "skip": -0.2}
WEIGHT_STEP = {"save": 1.08, "like": 1.05, "skip": 0.97}


def apply_feedback(cluster: StyleCluster, product: Product, action: str) -> StyleCluster:
    if action not in TERM_STEP:
        raise ValueError(f"action must be one of {sorted(TERM_STEP)}")
    step = TERM_STEP[action]
    for t in product.terms:
        cluster.term_weights[t] = max(-1.0, min(1.0, cluster.term_weights.get(t, 0.0) + step))
    cluster.weight = max(0.2, min(5.0, cluster.weight * WEIGHT_STEP[action]))
    return cluster


def feedback_bias(cluster: StyleCluster, product: Product, scale: float) -> float:
    """Small score nudge from learned weights, in [-scale, scale]."""
    hits = [cluster.term_weights[t] for t in product.terms if t in cluster.term_weights]
    return scale * sum(hits) / len(hits) if hits else 0.0


def record(store: MemoryStore, user_id: str, cluster_id: int, product: Product, action: str) -> StyleCluster:
    cluster = store.load(user_id).cluster(cluster_id)
    apply_feedback(cluster, product, action)
    store.update_cluster(user_id, cluster)
    store.log_feedback(user_id, product.id, cluster_id, action)
    return cluster
