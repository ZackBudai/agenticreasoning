# Planner comparison — `hard_25.txt` (25 goals)

Baseline CSV: `baseline/datasets/planner_results/20260525-210000-hard_25-mode_auto__k3__t120__repairs_on__model_ollama:qwen2.5-coder:32b__verify__strict.csv`
Solution CSV: `solution/datasets/planner_results/20260525-220023-hard_25-mode_auto__k3__t120__repairs_on__model_ollama:qwen2.5-coder:32b__verify__strict.csv`

| Metric | Baseline | Solution |
|---|---:|---:|
| Verified (success && verified_ok && no-sorry) | 0/25 | 0/25 |

## Per-goal
| # | Goal | Baseline | Solution |
|---:|---|:-:|:-:|
| 1 | `(∀x. P x ⟶ Q x) ∧ (∃x. P x) ⟶ (∃x. Q x)` | ✗ | ✗ |
| 2 | `(∀x. P x ⟷ Q x) ⟶ ((∀x. R x ⟶ P x) ⟷ (∀x. R x ⟶ Q x))` | ✗ | ✗ |
| 3 | `(∀x. P x) ⟶ ((∀x. Q x ⟶ R x) ⟶ (∀x. P x ∧ Q x ⟶ R x))` | ✗ | ✗ |
| 4 | `(∃x. P x ∧ (Q x ⟶ R x)) ⟶ ((∃x. P x ∧ Q x) ⟶ (∃x. R x))` | ✗ | ✗ |
| 5 | `(if A then f x else f y) = f (if A then x else y)` | ✗ | ✗ |
| 6 | `(if A then (B ⟶ C) else True) ⟷ (¬ A ∨ (B ⟶ C))` | ✗ | ✗ |
| 7 | `(∀x. f x = g x) ⟶ (∃!x. f x = a) ⟶ (∃!x. g x = a)` | ✗ | ✗ |
| 8 | `(∃!x. P x) ⟶ (∀x y. P x ∧ P y ⟶ x = y)` | ✗ | ✗ |
| 9 | `finite A ⟹ card (A ∪ B) = card A + card (B - A)` | ✗ | ✗ |
| 10 | `finite A ⟹ card (A ∩ B) + card (A - B) = card A - card (A ∩ (B - A))` | ✗ | ✗ |
| 11 | `finite A ⟹ finite B ⟹ A ∩ B = {} ⟹ card (A ∪ B) = card A + card B` | ✗ | ✗ |
| 12 | `finite A ⟹ card {x∈A. P x ∧ Q x} + card {x∈A. P x ∧ ¬ Q x} = card {x∈A. P x}` | ✗ | ✗ |
| 13 | `finite A ⟹ card {x∈A. P x} + card {x∈A. ¬ P x} = card A` | ✗ | ✗ |
| 14 | `finite A ⟹ inj_on f A ⟹ card (f ` A) = card A` | ✗ | ✗ |
| 15 | `finite A ⟹ card ((A × B) ∩ (C × D)) = card (A ∩ C) * card (B ∩ D)` | ✗ | ✗ |
| 16 | `finite A ⟹ finite B ⟹ card (A × B - C) = card (A × B) - card (C ∩ (A × B))` | ✗ | ✗ |
| 17 | `finite A ⟹ sum (λx. (if x∈B then (1::nat) else 0)) A = card (A ∩ B)` | ✗ | ✗ |
| 18 | `finite A ⟹ sum (λx. (if P x then (1::nat) else 0)) A = card {x∈A. P x}` | ✗ | ✗ |
| 19 | `finite A ⟹ sum (λx. (if x∈A then (0::int) else 0)) A = 0` | ✗ | ✗ |
| 20 | `finite A ⟹ sum (λx. c::int) A = c * int (card A)` | ✗ | ✗ |
| 21 | `finite A ⟹ sum (λx. f x + g x::int) A = sum f A + sum g A` | ✗ | ✗ |
| 22 | `finite A ⟹ (∀x∈A. f x = g x) ⟶ sum f A = (sum g A::int)` | ✗ | ✗ |
| 23 | `finite A ⟹ card (A - {x}) = (if x∈A then card A - 1 else card A)` | ✗ | ✗ |
| 24 | `finite A ⟹ card (insert x A) = (if x∈A then card A else Suc (card A))` | ✗ | ✗ |
| 25 | `finite A ⟹ finite B ⟹ card { (x,y)∈A×B. P x ∧ Q y } ≤ card A * card B` | ✗ | ✗ |
