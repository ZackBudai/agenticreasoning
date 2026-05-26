# Planner comparison — `smoke_f11.txt` (5 goals)

Baseline CSV: `baseline/datasets/planner_results/20260526-161249-smoke_f11-mode_auto__k1__t60__repairs_on__model_ollama:qwen2.5-coder:7b__verify__strict.csv`
Solution CSV: `solution/datasets/planner_results/20260526-161859-smoke_f11-mode_auto__k1__t60__repairs_on__model_ollama:qwen2.5-coder:7b__verify__strict.csv`

| Metric | Baseline | Solution |
|---|---:|---:|
| Verified (success && verified_ok && no-sorry) | 0/5 | 0/5 |

## Per-goal
| # | Goal | Baseline | Solution |
|---:|---|:-:|:-:|
| 1 | `¬ (∀x∈A. P x) ⟷ (∃x∈A. ¬ P x)` | ✗ | ✗ |
| 2 | `(∃x. P x ∧ Q x) ⟶ (∃x. P x)` | ✗ | ✗ |
| 3 | `(∀x. P x ⟶ Q) ⟶ ((∃x. P x) ⟶ Q)` | ✗ | ✗ |
| 4 | `(∀x. P x ⟶ Q x) ∧ (∃x. P x) ⟶ (∃x. Q x)` | ✗ | ✗ |
| 5 | `(∀x. P x ⟷ Q x) ⟶ ((∀x. R x ⟶ P x) ⟷ (∀x. R x ⟶ Q x))` | ✗ | ✗ |
