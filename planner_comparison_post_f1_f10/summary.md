# Planner comparison — `mid_25.txt` (25 goals)

Baseline CSV: `baseline/datasets/planner_results/20260526-062524-mid_25-mode_auto__k3__t180__repairs_on__model_ollama:qwen2.5-coder:7b__verify__strict.csv`
Solution CSV: `solution/datasets/planner_results/20260526-092528-mid_25-mode_auto__k3__t180__repairs_on__model_ollama:qwen2.5-coder:7b__verify__strict.csv`

| Metric | Baseline | Solution |
|---|---:|---:|
| Verified (success && verified_ok && no-sorry) | 0/25 | 0/25 |

## Per-goal
| # | Goal | Baseline | Solution |
|---:|---|:-:|:-:|
| 1 | `¬ (∀x∈A. P x) ⟷ (∃x∈A. ¬ P x)` | ✗ | ✗ |
| 2 | `(∃x. P x ∧ Q x) ⟶ (∃x. P x)` | ✗ | ✗ |
| 3 | `(∀x. P x ⟶ Q) ⟶ ((∃x. P x) ⟶ Q)` | ✗ | ✗ |
| 4 | `(∀x∈A. P x ∧ Q x) ⟷ ((∀x∈A. P x) ∧ (∀x∈A. Q x))` | ✗ | ✗ |
| 5 | `(∃x. P x ∨ Q x) ⟷ ((∃x. P x) ∨ (∃x. Q x))` | ✗ | ✗ |
| 6 | `(¬ ∃x. P x) ⟷ (∀x. ¬ P x)` | ✗ | ✗ |
| 7 | `(∀x. P x ⟶ R) ⟶ ((∃x. P x) ⟶ R)` | ✗ | ✗ |
| 8 | `(∃x. P x) ⟶ (∀y. P y ⟶ ∃z. P z)` | ✗ | ✗ |
| 9 | `(∃x. P x) ⟶ (∃y. P y ∧ ∃z. P z)` | ✗ | ✗ |
| 10 | `((P ⟶ Q) ∧ (Q ⟶ R)) ⟶ (P ⟶ R)` | ✗ | ✗ |
| 11 | `(P ∧ (Q ∨ R)) ⟶ ((P ∧ Q) ∨ (P ∧ R))` | ✗ | ✗ |
| 12 | `(P ⟶ Q) ⟷ (¬ P ∨ Q)` | ✗ | ✗ |
| 13 | `(P ∧ False) ⟶ Q` | ✗ | ✗ |
| 14 | `(P ⟶ (Q ⟶ R)) ⟷ ((P ∧ Q) ⟶ R)` | ✗ | ✗ |
| 15 | `(∀x. P x) ⟶ (∀y. P y)` | ✗ | ✗ |
| 16 | `(A ∩ (B ∪ C)) = (A ∩ B) ∪ (A ∩ C)` | ✗ | ✗ |
| 17 | `A ∪ (B ∩ C) = (A ∪ B) ∩ (A ∪ C)` | ✗ | ✗ |
| 18 | `(A - B) ∪ (A ∩ B) = A` | ✗ | ✗ |
| 19 | `(A ∩ B) ∪ (A - B) = A` | ✗ | ✗ |
| 20 | `A ⊆ B ⟶ (A ∩ B = A)` | ✗ | ✗ |
| 21 | `A ⊆ B ⟶ (A ∪ B = B)` | ✗ | ✗ |
| 22 | `(A ⊆ B ∧ B ⊆ C) ⟶ (A ⊆ C)` | ✗ | ✗ |
| 23 | `inj f ⟹ finite A ⟹ card (f ` A) = card A` | ✗ | ✗ |
| 24 | `finite A ⟹ card (A ∪ B) + card (A ∩ B) = card A + card B` | ✗ | ✗ |
| 25 | `finite A ⟹ finite B ⟹ card (A × B) = card A * card B` | ✗ | ✗ |
