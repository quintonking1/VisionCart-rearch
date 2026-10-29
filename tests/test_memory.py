import numpy as np

from evals.harness import best_f1_threshold, cohen_kappa, mrr, ndcg_at_k
from visioncart.llm import normalize
from visioncart.memory.cluster import cluster_board
from visioncart.memory.feedback import apply_feedback, feedback_bias
from visioncart.memory.store import MemoryStore


def test_cluster_splits_two_styles_and_keeps_small_boards_whole():
    rng = np.random.default_rng(0)
    a = normalize(np.eye(16)[0] + 0.05 * rng.standard_normal((4, 16)))
    b = normalize(np.eye(16)[1] + 0.05 * rng.standard_normal((4, 16)))
    labels = cluster_board(np.vstack([a, b]))
    assert len(set(labels)) == 2 and len(set(labels[:4])) == 1 and len(set(labels[4:])) == 1
    assert set(cluster_board(a[:3])) == {0}


def test_feedback_moves_terms_and_bias(memory, catalog):
    c = memory.cluster(0)
    apply_feedback(c, catalog.get("d1"), "like")
    assert c.term_weights["tweed"] > 0 and c.weight > 1
    assert feedback_bias(c, catalog.get("d2"), 0.05) > 0
    for _ in range(10):
        apply_feedback(c, catalog.get("l1"), "skip")
    assert c.term_weights["linen"] == -1.0
    assert feedback_bias(c, catalog.get("l1"), 0.05) < 0


def test_store_round_trip_and_carry_over(tmp_path, memory, catalog):
    store = MemoryStore(tmp_path / "m.sqlite")
    store.save(memory)
    c = store.load("u1").cluster(0)
    apply_feedback(c, catalog.get("d1"), "save")
    store.update_cluster("u1", c)
    # re-sync with fresh clusters; cluster 0 inherits learned weights from old cluster 0
    memory.clusters[0].term_weights, memory.clusters[0].weight = {}, 1.0
    store.save(memory, carry_over={0: 0})
    loaded = store.load("u1").cluster(0)
    assert loaded.term_weights["tweed"] > 0
    assert np.allclose(loaded.centroid, memory.clusters[0].centroid)


def test_metrics():
    assert mrr(["x", "a"], {"a"}) == 0.5
    assert ndcg_at_k(["a", "b"], {"a", "b"}, 3) == 1.0
    assert cohen_kappa([True, False, True, False], [True, False, True, False]) == 1.0
    t, f1 = best_f1_threshold([0.9, 0.8, 0.3, 0.2], [True, True, False, False])
    assert f1 == 1.0 and 0.3 < t <= 0.8
