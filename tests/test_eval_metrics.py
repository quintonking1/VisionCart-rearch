from evals.harness import bootstrap_ci, precision_shown, random_baseline, summarize


def test_precision_shown_not_penalised_for_unfillable_slots():
    assert precision_shown(["a", "b", "x"], {"a", "b"}) == 1.0
    assert precision_shown(["a", "x", "y"], {"a", "b"}) == 0.5
    assert precision_shown([], {"a"}) is None


def test_random_baseline_matches_expectation():
    r = random_baseline(["a", "b", "c", "d"], {"a"}, trials=4000)
    assert abs(r["p@1"] - 0.25) < 0.03
    assert abs(r["mrr"] - (1 + 1 / 2 + 1 / 3 + 1 / 4) / 4) < 0.03
    assert random_baseline(["a", "b"], {"a", "b"})["ndcg@3"] == 1.0


def test_bootstrap_ci_brackets_mean_and_narrows_with_n():
    small = [0.0, 1.0] * 5
    big = [0.0, 1.0] * 100
    lo_s, hi_s = bootstrap_ci(small)
    lo_b, hi_b = bootstrap_ci(big)
    assert lo_s <= 0.5 <= hi_s and lo_b <= 0.5 <= hi_b
    assert (hi_b - lo_b) < (hi_s - lo_s)
    assert summarize([1.0, 1.0])["ci95"] == [1.0, 1.0]


def test_paired_and_sign_test():
    from evals.harness import paired, sign_test
    p = paired([1.0, 0.5, 0.8, 0.8], [0.5, 0.5, 0.6, 0.9])
    assert (p["wins"], p["losses"], p["ties"]) == (2, 1, 1)
    assert abs(p["mean"] - 0.15) < 1e-9
    assert sign_test(4, 0) == 0.125 and sign_test(0, 0) == 1.0


def test_cluster_bootstrap_resamples_whole_clusters():
    from evals.cross_split import cluster_bootstrap
    rows = [{"style": "a", "v": 1.0}] * 5 + [{"style": "b", "v": 0.0}]
    out = cluster_bootstrap(rows, "style", lambda r: r["v"])
    assert abs(out["mean"] - 5 / 6) < 1e-9 and out["clusters"] == 2
    assert out["ci95"][0] == 0.0 and out["ci95"][1] == 1.0  # two clusters: any mix is possible
