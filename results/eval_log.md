## 2026-10-26 16:43 | split: dev | threshold 0.723 | gpt-4.1-mini / text-embedding-3-small

| Component | Metric | Value |
|---|---|---|
| clustering | mixed boards split into 2 | 0.80 |
| clustering | mean pin purity | 0.70 |
| planner | precision / recall / exact | 1.00 / 1.00 / 1.00 |
| worker | recall of relevant | 1.00 |
| verifier | accepted precision | 0.92 |
| verifier | empty / low-confidence rate | 0.00 / 0.03 |

| End-to-end | P@1 | MRR | nDCG@3 |
|---|---|---|---|
| worker order (no verifier) | 0.900 | 0.932 | 0.868 |
| full pipeline | 0.933 | 0.967 | 0.931 |

---
## 2026-10-26 16:51 | split: dev | threshold 0.723 | gpt-4.1-mini / text-embedding-3-small

Values are mean [bootstrap 95% CI] over boards or cases.

### Style ranking, whole catalog (10 boards, ~12 relevant of 120)

| Board type | AUC | nDCG@10 |
|---|---|---|
| single-style | 0.931 [0.87, 0.97] | 0.731 [0.53, 0.89] |
| random order | 0.500 | 0.102 [0.10, 0.11] |
| mixed, multi-cluster memory | 0.913 [0.85, 0.96] | 0.825 [0.58, 0.99] |
| mixed, single averaged centroid | 0.862 [0.81, 0.90] | 0.775 [0.62, 0.93] |

### End-to-end, contested categories (headline) — 9 cases

| Ranking | nDCG@3 | MRR | P@1 |
|---|---|---|---|
| random order | 0.417 [0.31, 0.56] | 0.544 [0.44, 0.67] | 0.333 [0.20, 0.50] |
| worker order (no verifier) | 0.625 [0.38, 0.84] | 0.772 [0.55, 0.94] | 0.667 [0.33, 0.89] |
| full pipeline | 0.839 [0.68, 0.96] | 0.889 [0.72, 1.00] | 0.778 [0.44, 1.00] |

### End-to-end, all categories (inflated by single-style categories) — 30 cases

| Ranking | nDCG@3 | MRR | P@1 |
|---|---|---|---|
| random order | 0.825 [0.72, 0.92] | 0.863 [0.78, 0.94] | 0.800 [0.68, 0.91] |
| worker order (no verifier) | 0.868 [0.77, 0.95] | 0.932 [0.85, 1.00] | 0.900 [0.77, 1.00] |
| full pipeline | 0.931 [0.87, 0.98] | 0.967 [0.92, 1.00] | 0.933 [0.83, 1.00] |

### Components

| Component | Metric | Value |
|---|---|---|
| clustering | mixed boards split into 2 | 0.80 |
| clustering | mean pin purity | 0.70 |
| planner | precision / recall / exact (n=12) | 1.00 / 1.00 / 1.00 |
| worker | recall of relevant | 1.00 |
| verifier | shown precision, contested / all | 0.89 / 0.97 |
| verifier | empty / low-confidence rate | 0.00 / 0.03 |

---
## 2026-10-26 16:55 | split: dev | threshold 0.684 | gpt-4.1-mini / text-embedding-3-small

Values are mean [bootstrap 95% CI] over boards or cases.

### Style ranking, whole catalog (10 boards, ~12 relevant of 120)

| Board type | AUC | nDCG@10 |
|---|---|---|
| single-style | 0.961 [0.93, 0.99] | 0.830 [0.68, 0.95] |
| random order | 0.500 | 0.102 [0.10, 0.11] |
| mixed, multi-cluster memory | 0.936 [0.91, 0.96] | 0.861 [0.64, 1.00] |
| mixed, single averaged centroid | 0.906 [0.89, 0.92] | 0.793 [0.61, 0.92] |

### End-to-end, contested categories (headline) — 9 cases

| Ranking | nDCG@3 | MRR | P@1 |
|---|---|---|---|
| random order | 0.417 [0.31, 0.56] | 0.544 [0.44, 0.67] | 0.333 [0.20, 0.50] |
| worker order (no verifier) | 0.567 [0.38, 0.76] | 0.750 [0.56, 0.94] | 0.556 [0.22, 0.89] |
| full pipeline | 0.790 [0.56, 1.00] | 0.815 [0.56, 1.00] | 0.778 [0.44, 1.00] |

### End-to-end, all categories (inflated by single-style categories) — 30 cases

| Ranking | nDCG@3 | MRR | P@1 |
|---|---|---|---|
| random order | 0.825 [0.72, 0.92] | 0.863 [0.78, 0.94] | 0.800 [0.68, 0.91] |
| worker order (no verifier) | 0.825 [0.72, 0.91] | 0.908 [0.82, 0.97] | 0.833 [0.70, 0.93] |
| full pipeline | 0.937 [0.85, 1.00] | 0.944 [0.86, 1.00] | 0.933 [0.83, 1.00] |

### Components

| Component | Metric | Value |
|---|---|---|
| clustering | mixed boards split into 2 | 0.60 |
| clustering | mean pin purity | 0.77 |
| planner | precision / recall / exact (n=12) | 1.00 / 1.00 / 1.00 |
| worker | recall of relevant | 1.00 |
| verifier | shown precision, contested / all | 0.83 / 0.95 |
| verifier | empty / low-confidence rate | 0.00 / 0.03 |

---
## 2026-10-26 16:59 | split: dev | threshold 0.690 | gpt-4.1-mini / text-embedding-3-small

Values are mean [bootstrap 95% CI] over boards or cases.

### Style ranking, whole catalog (10 boards, ~12 relevant of 120)

| Board type | AUC | nDCG@10 |
|---|---|---|
| single-style | 0.944 [0.89, 0.98] | 0.832 [0.71, 0.93] |
| random order | 0.500 | 0.102 [0.10, 0.11] |
| mixed, multi-cluster memory | 0.930 [0.90, 0.96] | 0.920 [0.82, 1.00] |
| mixed, single averaged centroid | 0.889 [0.85, 0.93] | 0.834 [0.76, 0.92] |

### End-to-end, contested categories (headline) — 9 cases

| Ranking | nDCG@3 | MRR | P@1 |
|---|---|---|---|
| random order | 0.417 [0.31, 0.56] | 0.544 [0.44, 0.67] | 0.333 [0.20, 0.50] |
| worker order (no verifier) | 0.855 [0.74, 0.96] | 0.944 [0.83, 1.00] | 0.889 [0.67, 1.00] |
| full pipeline | 0.778 [0.53, 0.96] | 0.833 [0.61, 1.00] | 0.778 [0.44, 1.00] |

### End-to-end, all categories (inflated by single-style categories) — 30 cases

| Ranking | nDCG@3 | MRR | P@1 |
|---|---|---|---|
| random order | 0.825 [0.72, 0.92] | 0.863 [0.78, 0.94] | 0.800 [0.68, 0.91] |
| worker order (no verifier) | 0.937 [0.89, 0.98] | 0.983 [0.95, 1.00] | 0.967 [0.90, 1.00] |
| full pipeline | 0.882 [0.79, 0.95] | 0.950 [0.87, 1.00] | 0.933 [0.83, 1.00] |

### Components

| Component | Metric | Value |
|---|---|---|
| clustering | mixed boards split into 2 | 0.20 |
| clustering | mean pin purity | 0.83 |
| planner | precision / recall / exact (n=12) | 1.00 / 1.00 / 1.00 |
| worker | recall of relevant | 1.00 |
| verifier | shown precision, contested / all | 0.78 / 0.93 |
| verifier | empty / low-confidence rate | 0.00 / 0.03 |

---
## 2026-10-26 17:03 | split: dev | threshold 0.690 | blend 0.7 | gpt-4.1-mini / text-embedding-3-small

Values are mean [bootstrap 95% CI] over boards or cases.

### Style ranking, whole catalog (10 boards, ~12 relevant of 120)

| Board type | AUC | nDCG@10 |
|---|---|---|
| single-style | 0.944 [0.89, 0.98] | 0.832 [0.71, 0.93] |
| random order | 0.500 | 0.102 [0.10, 0.11] |
| mixed, multi-cluster memory | 0.930 [0.90, 0.96] | 0.920 [0.82, 1.00] |
| mixed, single averaged centroid | 0.889 [0.85, 0.93] | 0.834 [0.76, 0.92] |

### End-to-end, contested categories (headline) — 9 cases

| Ranking | nDCG@3 | MRR | P@1 |
|---|---|---|---|
| random order | 0.417 [0.31, 0.56] | 0.544 [0.44, 0.67] | 0.333 [0.20, 0.50] |
| worker order (no verifier) | 0.855 [0.74, 0.96] | 0.944 [0.83, 1.00] | 0.889 [0.67, 1.00] |
| full pipeline | 0.823 [0.65, 0.96] | 0.833 [0.67, 0.94] | 0.667 [0.33, 0.89] |

### End-to-end, all categories (inflated by single-style categories) — 30 cases

| Ranking | nDCG@3 | MRR | P@1 |
|---|---|---|---|
| random order | 0.825 [0.72, 0.92] | 0.863 [0.78, 0.94] | 0.800 [0.68, 0.91] |
| worker order (no verifier) | 0.937 [0.89, 0.98] | 0.983 [0.95, 1.00] | 0.967 [0.90, 1.00] |
| full pipeline | 0.895 [0.82, 0.96] | 0.950 [0.88, 1.00] | 0.900 [0.77, 1.00] |

### Components

| Component | Metric | Value |
|---|---|---|
| clustering | mixed boards split into 2 | 0.20 |
| clustering | mean pin purity | 0.83 |
| planner | precision / recall / exact (n=12) | 1.00 / 1.00 / 1.00 |
| worker | recall of relevant | 1.00 |
| verifier | shown precision, contested / all | 0.89 / 0.97 |
| verifier | empty / low-confidence rate | 0.00 / 0.03 |

---
## 2026-10-26 17:04 | split: dev | threshold 0.690 | blend 0.9 | gpt-4.1-mini / text-embedding-3-small

Values are mean [bootstrap 95% CI] over boards or cases.

### Style ranking, whole catalog (10 boards, ~12 relevant of 120)

| Board type | AUC | nDCG@10 |
|---|---|---|
| single-style | 0.944 [0.89, 0.98] | 0.832 [0.71, 0.93] |
| random order | 0.500 | 0.102 [0.10, 0.11] |
| mixed, multi-cluster memory | 0.930 [0.90, 0.96] | 0.920 [0.82, 1.00] |
| mixed, single averaged centroid | 0.889 [0.85, 0.93] | 0.834 [0.76, 0.92] |

### End-to-end, contested categories (headline) — 9 cases

| Ranking | nDCG@3 | MRR | P@1 |
|---|---|---|---|
| random order | 0.417 [0.31, 0.56] | 0.544 [0.44, 0.67] | 0.333 [0.20, 0.50] |
| worker order (no verifier) | 0.688 [0.50, 0.88] | 0.741 [0.54, 0.93] | 0.556 [0.22, 0.89] |
| full pipeline | 0.882 [0.76, 0.97] | 0.889 [0.72, 1.00] | 0.778 [0.44, 1.00] |

### End-to-end, all categories (inflated by single-style categories) — 30 cases

| Ranking | nDCG@3 | MRR | P@1 |
|---|---|---|---|
| random order | 0.825 [0.72, 0.92] | 0.863 [0.78, 0.94] | 0.800 [0.68, 0.91] |
| worker order (no verifier) | 0.860 [0.76, 0.94] | 0.889 [0.80, 0.96] | 0.800 [0.63, 0.93] |
| full pipeline | 0.913 [0.85, 0.96] | 0.967 [0.92, 1.00] | 0.933 [0.83, 1.00] |

### Components

| Component | Metric | Value |
|---|---|---|
| clustering | mixed boards split into 2 | 0.20 |
| clustering | mean pin purity | 0.83 |
| planner | precision / recall / exact (n=12) | 1.00 / 1.00 / 1.00 |
| worker | recall of relevant | 1.00 |
| verifier | shown precision, contested / all | 0.94 / 0.98 |
| verifier | empty / low-confidence rate | 0.00 / 0.03 |

---
## 2026-10-26 17:11 | split: test | threshold 0.690 | blend 0.9 | commit a346140 | gpt-4.1-mini / text-embedding-3-small

Values are mean [bootstrap 95% CI] over boards or cases.

### Style ranking, whole catalog (10 boards, ~12 relevant of 120)

| Board type | AUC | nDCG@10 |
|---|---|---|
| single-style | 0.962 [0.93, 0.98] | 0.843 [0.76, 0.92] |
| random order | 0.500 | 0.102 [0.10, 0.11] |
| mixed, multi-cluster memory | 0.929 [0.89, 0.97] | 0.905 [0.85, 0.96] |
| mixed, single averaged centroid | 0.879 [0.84, 0.92] | 0.651 [0.47, 0.85] |

### End-to-end, contested categories (headline) — 9 cases

| Ranking | nDCG@3 | MRR | P@1 |
|---|---|---|---|
| random order | 0.417 [0.31, 0.56] | 0.544 [0.44, 0.67] | 0.333 [0.20, 0.50] |
| worker order (no verifier) | 0.719 [0.48, 0.92] | 0.787 [0.57, 0.94] | 0.667 [0.33, 0.89] |
| full pipeline | 0.882 [0.76, 1.00] | 0.889 [0.72, 1.00] | 0.778 [0.44, 1.00] |

### End-to-end, all categories (inflated by single-style categories) — 30 cases

| Ranking | nDCG@3 | MRR | P@1 |
|---|---|---|---|
| random order | 0.825 [0.72, 0.92] | 0.863 [0.78, 0.94] | 0.800 [0.68, 0.91] |
| worker order (no verifier) | 0.890 [0.80, 0.96] | 0.919 [0.84, 0.98] | 0.867 [0.73, 0.97] |
| full pipeline | 0.939 [0.89, 0.98] | 0.967 [0.92, 1.00] | 0.933 [0.83, 1.00] |

### Components

| Component | Metric | Value |
|---|---|---|
| clustering | mixed boards split into 2 | 0.80 |
| clustering | mean pin purity | 0.93 |
| planner | precision / recall / exact (n=12) | 1.00 / 1.00 / 1.00 |
| worker | recall of relevant | 1.00 |
| verifier | shown precision, contested / all | 0.94 / 0.98 |
| verifier | empty / low-confidence rate | 0.00 / 0.07 |

---

## Cross-split evaluation (5 folds, 2026-10-26 17:40)

Each fold re-draws boards and catalog, calibrates on its own dev boards, and is evaluated once on its own test boards. Intervals are 95% cluster-bootstrap CIs resampling whole styles (or style pairs for mixed boards), because folds share images.

### Mixed-style boards (25 boards across folds)

| Memory | nDCG@10 | AUC |
|---|---|---|
| multi-cluster | 0.906 [0.81, 0.98] | 0.926 [0.91, 0.94] |
| single averaged centroid | 0.751 [0.59, 0.89] | 0.888 [0.86, 0.92] |
| **paired Δ (multi − single)** | **+0.155 [+0.06, +0.25]** | wins/losses/ties 22/1/2, sign-test p = 5.72e-06 |

### End-to-end, contested categories (45 cases across folds)

| Ranking | nDCG@3 | MRR |
|---|---|---|
| random order | 0.414 [0.30, 0.55] | 0.538 [0.43, 0.67] |
| worker order (search only) | 0.622 [0.40, 0.78] | 0.705 [0.50, 0.85] |
| full pipeline | 0.797 [0.59, 0.93] | 0.804 [0.57, 0.94] |
| **paired Δ (pipeline − worker)** | **+0.175 [+0.08, +0.28]** | wins/losses/ties 21/2/22, sign-test p = 6.6e-05 |

### Style recognition, whole catalog

AUC 0.963 [0.95, 0.98], nDCG@10 0.828 [0.76, 0.89] (random nDCG@10 ≈ 0.10) over 50 board evaluations.

All-category end-to-end nDCG@3 0.913 [0.87, 0.95] vs random 0.824 [0.73, 0.92] (inflated by single-style categories; shown for reference).

### Per fold

| Fold | Threshold | Blend | LOSO est. | Contested n | Pipeline / worker nDCG@3 | Style AUC | Mixed multi / single | Purity | Split into 2 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.676 | 0.6 | 0.837 | 9 | 0.871 / 0.718 | 0.951 | 0.930 / 0.765 | 0.80 | 0.60 |
| 2 | 0.701 | 0.3 | 0.841 | 9 | 0.778 / 0.576 | 0.965 | 0.918 / 0.733 | 0.90 | 0.20 |
| 3 | 0.717 | 1.0 | 0.916 | 9 | 0.916 / 0.646 | 0.960 | 0.881 / 0.755 | 0.73 | 0.80 |
| 4 | 0.676 | 0.5 | 0.676 | 9 | 0.805 / 0.569 | 0.968 | 0.925 / 0.781 | 0.77 | 0.60 |
| 5 | 0.697 | 0.8 | 0.805 | 9 | 0.615 / 0.601 | 0.971 | 0.875 / 0.723 | 0.73 | 0.60 |

Commit(s): dfe7007

Per-fold full reports: data/folds/<k>/results/eval_log.md (gitignored). Pooled JSON: results/cross_split.json.

---
