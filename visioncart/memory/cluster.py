"""Split a board into style clusters instead of averaging it into one centroid."""
from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from visioncart.llm import normalize

MAX_K = 4
MIN_SILHOUETTE = 0.1  # below this, extra clusters are noise and k stays at 1


def cluster_board(vecs: np.ndarray, seed: int = 0) -> np.ndarray:
    """Return a cluster label per pin. k is picked by silhouette; tiny boards stay one cluster."""
    n = len(vecs)
    if n < 4:
        return np.zeros(n, dtype=int)
    best_labels, best_score = np.zeros(n, dtype=int), MIN_SILHOUETTE
    for k in range(2, min(MAX_K, n - 1) + 1):
        labels = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(vecs)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(vecs, labels, metric="cosine")
        if score > best_score:
            best_labels, best_score = labels, score
    return best_labels


def centroids(vecs: np.ndarray, labels: np.ndarray) -> list[np.ndarray]:
    return [normalize(vecs[labels == c].mean(axis=0)) for c in sorted(set(labels.tolist()))]
