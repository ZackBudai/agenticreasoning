theory Solution_Results
  imports Main
begin

(* PROVED *)
lemma goal_1_x____A___insert_x_A: "{x} \<union> A = insert x A"
  by simp

(* PROVED *)
lemma goal_2_x___insert_y_A____x___y___x: "x \<in> insert y A \<longleftrightarrow> (x = y \<or> x \<in> A)"
  by simp

(* PROVED *)
lemma goal_3_A____B___C_____A___B_____A___C: "A \<inter> (B \<union> C) = (A \<inter> B) \<union> (A \<inter> C)"
  by auto

(* PROVED *)
lemma goal_4_A___A___B: "A \<subseteq> A \<union> B"
  by simp

(* PROVED *)
lemma goal_5_A___B___A: "A \<inter> B \<subseteq> A"
  by simp

(* PROVED *)
lemma goal_6_A___B___B___C____A___C: "(A \<subseteq> B \<and> B \<subseteq> C) \<Longrightarrow> A \<subseteq> C"
  by auto

(* PROVED *)
lemma goal_7_A___B___B___A____A___B: "(A \<subseteq> B \<and> B \<subseteq> A) \<Longrightarrow> A = B"
  by auto

(* PROVED *)
lemma goal_8_set__xs___ys____set_xs___set_y: "set (xs @ ys) = set xs \<union> set ys"
  by simp

end
