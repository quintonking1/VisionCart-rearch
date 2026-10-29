# Cross-split evaluation (5 folds, 2026-10-26 17:40)

Each fold re-draws boards and catalog, calibrates on its own dev boards, and is evaluated once on its own test boards. Intervals are 95% cluster-bootstrap CIs resampling whole styles (or style pairs for mixed boards), because folds share images.

## Mixed-style boards (25 boards across folds)

| Memory | nDCG@10 | AUC |
|---|---|---|
| multi-cluster | 0.906 [0.81, 0.98] | 0.926 [0.91, 0.94] |
| single averaged centroid | 0.751 [0.59, 0.89] | 0.888 [0.86, 0.92] |
| **paired Δ (multi − single)** | **+0.155 [+0.06, +0.25]** | wins/losses/ties 22/1/2, sign-test p = 5.72e-06 |

## End-to-end, contested categories (45 cases across folds)

| Ranking | nDCG@3 | MRR |
|---|---|---|
| random order | 0.414 [0.30, 0.55] | 0.538 [0.43, 0.67] |
| worker order (search only) | 0.622 [0.40, 0.78] | 0.705 [0.50, 0.85] |
| full pipeline | 0.797 [0.59, 0.93] | 0.804 [0.57, 0.94] |
| **paired Δ (pipeline − worker)** | **+0.175 [+0.08, +0.28]** | wins/losses/ties 21/2/22, sign-test p = 6.6e-05 |

## Style recognition, whole catalog

AUC 0.963 [0.95, 0.98], nDCG@10 0.828 [0.76, 0.89] (random nDCG@10 ≈ 0.10) over 50 board evaluations.

All-category end-to-end nDCG@3 0.913 [0.87, 0.95] vs random 0.824 [0.73, 0.92] (inflated by single-style categories; shown for reference).

## Per fold

| Fold | Threshold | Blend | LOSO est. | Contested n | Pipeline / worker nDCG@3 | Style AUC | Mixed multi / single | Purity | Split into 2 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.676 | 0.6 | 0.837 | 9 | 0.871 / 0.718 | 0.951 | 0.930 / 0.765 | 0.80 | 0.60 |
| 2 | 0.701 | 0.3 | 0.841 | 9 | 0.778 / 0.576 | 0.965 | 0.918 / 0.733 | 0.90 | 0.20 |
| 3 | 0.717 | 1.0 | 0.916 | 9 | 0.916 / 0.646 | 0.960 | 0.881 / 0.755 | 0.73 | 0.80 |
| 4 | 0.676 | 0.5 | 0.676 | 9 | 0.805 / 0.569 | 0.968 | 0.925 / 0.781 | 0.77 | 0.60 |
| 5 | 0.697 | 0.8 | 0.805 | 9 | 0.615 / 0.601 | 0.971 | 0.875 / 0.723 | 0.73 | 0.60 |

Commit(s): dfe7007
