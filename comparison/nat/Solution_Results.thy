theory Solution_Results
  imports Main
begin

(* FAILED — no proof found *)
lemma goal_1_0___n___n: "0 + n = n"
  sorry

(* FAILED — no proof found *)
lemma goal_2_n___0___n: "n + 0 = n"
  sorry

(* PROVED *)
lemma goal_3_n___Suc_m___Suc__n___m: "n + Suc m = Suc (n + m)"
  by simp

(* PROVED *)
lemma goal_4_Suc_n___0: "Suc n \<noteq> 0"
  by simp

(* FAILED — no proof found *)
lemma goal_5_n___n: "n \<le> n"
  sorry

(* PROVED *)
lemma goal_6_min_n_n___n: "min n n = n"
  by (metis min_def)

(* PROVED *)
lemma goal_7_max_n_n___n: "max n n = n"
  by (metis max_def)

(* FAILED — no proof found *)
lemma goal_8_n___m___m___n: "n + m = m + n"
  sorry

(* FAILED — no proof found *)
lemma goal_9_n____m___k_____n___m____k: "n + (m + k) = (n + m) + k"
  sorry

end
