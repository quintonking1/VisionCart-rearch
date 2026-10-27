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
