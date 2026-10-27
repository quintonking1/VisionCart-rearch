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
