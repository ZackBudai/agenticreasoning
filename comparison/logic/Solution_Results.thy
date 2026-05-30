theory Solution_Results
  imports Main
begin

(* PROVED *)
lemma goal_1_True___P____P: "(True \<and> P) \<longleftrightarrow> P"
  by simp

(* PROVED *)
lemma goal_2_P___True____P: "(P \<and> True) \<longleftrightarrow> P"
  by simp

(* PROVED *)
lemma goal_3_P___False____P: "(P \<or> False) \<longleftrightarrow> P"
  by simp

(* PROVED *)
lemma goal_4_P____P: "(\<not> \<not> P) \<longleftrightarrow> P"
  by simp

(* PROVED *)
lemma goal_5_P___Q_______P___Q: "(P \<longrightarrow> Q) \<longleftrightarrow> (\<not> P \<or> Q)"
  by simp

end
