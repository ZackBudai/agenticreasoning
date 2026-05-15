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

end
