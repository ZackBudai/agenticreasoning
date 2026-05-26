# Planner comparison — `smoke_goal2_only.txt` (1 goals)

Baseline CSV: `baseline/datasets/planner_results/20260526-162500-smoke_goal2_only-mode_auto__k1__t60__repairs_on__model_ollama:qwen2.5-coder:7b__verify__strict.csv`
Solution CSV: `solution/datasets/planner_results/20260526-162621-smoke_goal2_only-mode_auto__k1__t60__repairs_on__model_ollama:qwen2.5-coder:7b__verify__strict.csv`

| Metric | Baseline | Solution |
|---|---:|---:|
| Verified (success && verified_ok && no-sorry) | 0/1 | 0/1 |

## Per-goal
| # | Goal | Baseline | Solution |
|---:|---|:-:|:-:|
| 1 | `(∃x. P x ∧ Q x) ⟶ (∃x. P x)` | ✗ | ✗ |
