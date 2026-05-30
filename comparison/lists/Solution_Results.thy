theory Solution_Results
  imports Main
begin

(* PROVED *)
lemma goal_1_rev__rev_xs____xs: "rev (rev xs) = xs"
  by simp

(* PROVED *)
lemma goal_2_xs________xs: "xs @ [] = xs"
  by simp

(* PROVED *)
lemma goal_3_xs___xs: "[] @ xs = xs"
  by simp

(* PROVED *)
lemma goal_4_rev__xs___ys____rev_ys___rev_x: "rev (xs @ ys) = rev ys @ rev xs"
  by simp

(* PROVED *)
lemma goal_5_map_id_xs___xs: "map id xs = xs"
  by simp

(* PROVED *)
lemma goal_6_map_f__xs___ys____map_f_xs___m: "map f (xs @ ys) = map f xs @ map f ys"
  by simp

(* PROVED *)
lemma goal_7_map_f__rev_xs____rev__map_f_xs: "map f (rev xs) = rev (map f xs)"
  by (metis rev_map)

(* PROVED *)
lemma goal_8_length__xs___ys____length_xs: "length (xs @ ys) = length xs + length ys"
  by simp

(* PROVED *)
lemma goal_9_length__rev_xs____length_xs: "length (rev xs) = length xs"
  by simp

(* PROVED *)
lemma goal_10_take__length_xs___xs___ys____x: "take (length xs) (xs @ ys) = xs"
  by simp

(* PROVED *)
lemma goal_11_drop__length_xs___xs___ys____y: "drop (length xs) (xs @ ys) = ys"
  by simp

(* PROVED *)
lemma goal_12_take_n_xs___drop_n_xs___xs: "take n xs @ drop n xs = xs"
  by simp

(* PROVED *)
lemma goal_13_set__xs___ys____set_xs___set_y: "set (xs @ ys) = set xs \<union> set ys"
  by simp

(* PROVED *)
lemma goal_14_x___set_xs___x___set__xs___ys: "x \<in> set xs \<Longrightarrow> x \<in> set (xs @ ys)"
  by simp

(* PROVED *)
lemma goal_15_x___set_ys___x___set__xs___ys: "x \<in> set ys \<Longrightarrow> x \<in> set (xs @ ys)"
  by simp

(* PROVED *)
lemma goal_16_distinct_xs___distinct__rev_xs: "distinct xs \<Longrightarrow> distinct (rev xs)"
  by simp

(* PROVED *)
lemma goal_17_filter_p__xs___ys____filter_p: "filter p (xs @ ys) = filter p xs @ filter p ys"
  by simp

(* FAILED — no proof found *)
lemma goal_18_map_f__filter_p_xs____filter: "map f (filter p xs) = filter (\<lambda>x. p x) (map f xs)"
  sorry

end
