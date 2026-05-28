# Report-metric sweep — 2026-05-27 20:42 UTC

All numbers are **solution-only**. Baseline can be re-run later if there's time.

| Set | Goals | Strict pass | % |
|---|---:|---:|---:|
| `hol_main_easy` | 100 | 75 | 75% |
| `hol_main_hard` | 100 | 67 | 67% |
| `hol_main_mid` | 100 | 83 | 83% |
| **total** | **300** | **225** | **75%** |

## `hol_main_easy` — 75/100
| # | Goal | Strict | Wall (s) |
|---:|---|:-:|---:|
| 1 | `!!k:: 'a::linorder. -lessThan k = atLeast k` | ✓ |  |
| 2 | `(1 - x) * (\<Sum>i=m..n. x^i) = x^m - x^Suc n` | ✗ |  |
| 3 | `(A \<union> B) - C = (A - C) \<union> (B - C)` | ✓ |  |
| 4 | `(\<And>x::unit. PROP P x) \<equiv> PROP P ()` | ✓ |  |
| 5 | `(\<exists>x y. P x y) = (\<exists>y x. P x y)` | ✓ |  |
| 6 | `(\<lambda>h::'a::mult_zero. 0) = (*) 0` | ✓ |  |
| 7 | `(a::'a::group_add) - (b + c) = a - c - b` | ✓ |  |
| 8 | `(a::'a::idom_divide) div - b = - (a div b)` | ✗ |  |
| 9 | `(equivclp r)\<^sup>*\<^sup>* = equivclp r` | ✓ |  |
| 10 | `(if True then x else y) = x` | ✓ |  |
| 11 | `(if x = y then y else x) = x` | ✓ |  |
| 12 | `(map_option f opt = None) = (opt = None)` | ✓ |  |
| 13 | `(n + m) - n = m` | ✗ |  |
| 14 | `(take n xs = []) = (n = 0 \<or> xs = [])` | ✓ |  |
| 15 | `(x, x) \<in> R ^^ 0` | ✓ |  |
| 16 | `(xs @ ys = []) = (xs = [] \<and> ys = [])` | ✓ |  |
| 17 | `(xs @ ys = xs @ zs) = (ys = zs)` | ✓ |  |
| 18 | `0 - (a::'a::group_add) = - a` | ✓ |  |
| 19 | `0 \<notin> Suc ` A` | ✓ |  |
| 20 | `0 gchoose (Suc k) = 0` | ✓ |  |
| 21 | `1 + a + a \<noteq> 0` | ✓ |  |
| 22 | `A = B \<Longrightarrow> A \<subseteq> B` | ✓ |  |
| 23 | `A \<union> B = fold insert B A` | ✗ |  |
| 24 | `Ball (f ` A) g = Ball A (g \<circ> f)` | ✓ |  |
| 25 | `Ball A P = (A \<subseteq> (Collect P))` | ✓ |  |
| 26 | `Ball UNIV P \<longleftrightarrow> All P` | ✓ |  |
| 27 | `CARD('a bit1) = Suc (2 * CARD('a::finite))` | ✗ |  |
| 28 | `HOL.equal k k \<longleftrightarrow> True` | ✗ |  |
| 29 | `Neg m + Neg n = Neg (m + n)` | ✗ |  |
| 30 | `Range (r\<inverse>) = Domain r` | ✓ |  |
| 31 | `UNIV = List.coset []` | ✓ |  |
| 32 | `UNIV \<inter> B = B` | ✓ |  |
| 33 | `X = Y \<longleftrightarrow> (x, y) \<in> r` | ✗ |  |
| 34 | `\<Sum> {0..<card S} \<le> \<Sum> S` | ✗ |  |
| 35 | `\<exists>!x. t = x` | ✓ |  |
| 36 | `\<exists>a. b = f a` | ✗ |  |
| 37 | `\<exists>n. k = int n` | ✗ |  |
| 38 | `\<exists>x y. p = (x, y)` | ✓ |  |
| 39 | `\<forall>X \<in> A//r. univ f X \<in> B` | ✗ |  |
| 40 | `\<forall>x y. P x y \<Longrightarrow> P x y` | ✓ |  |
| 41 | `\<lambda>x. x \<in> A` | ✗ |  |
| 42 | `\<nexists>f. f ` A = Pow A` | ✓ |  |
| 43 | `\<not> [] \<parallel> x` | ✗ |  |
| 44 | `\<not> finite (UNIV :: num0 set)` | ✗ |  |
| 45 | `\<top> = (\<lambda>x. x \<in> UNIV)` | ✗ |  |
| 46 | `a \<ge> 0 \<Longrightarrow> mono ((*) a)` | ✗ |  |
| 47 | `a \<in> {} \<Longrightarrow> P` | ✓ |  |
| 48 | `apfst f (apfst g x) = apfst (f \<circ> g) x` | ✓ |  |
| 49 | `apsnd f (apfst g x) = (g (fst x), f (snd x))` | ✓ |  |
| 50 | `asymp_on A r \<Longrightarrow> irreflp_on A r` | ✓ |  |
| 51 | `butlast (rev xs) = rev (tl xs)` | ✓ |  |
| 52 | `card (A <+> B) = card A + card B` | ✗ |  |
| 53 | `card {l<..<u} = u - Suc l` | ✓ |  |
| 54 | `dom (m ++ n) = dom n \<union> dom m` | ✓ |  |
| 55 | `drop n (map f xs) = map f (drop n xs)` | ✓ |  |
| 56 | `equivclp (conversep r) = equivclp r` | ✓ |  |
| 57 | `equivp R \<Longrightarrow> R x x` | ✓ |  |
| 58 | `f(x := f x) = f` | ✓ |  |
| 59 | `finite (r\<^sup>+) = finite r` | ✓ |  |
| 60 | `finite F \<Longrightarrow> finite (h ` F)` | ✓ |  |
| 61 | `finite {i :: int. a < i \<and> i \<le> b}` | ✓ |  |
| 62 | `fst (apfst f x) = f (fst x)` | ✓ |  |
| 63 | `fst bc = (fst \<circ> fstOp P Q) bc` | ✗ |  |
| 64 | `i \<le> j \<Longrightarrow> k * i \<le> k * j` | ✓ |  |
| 65 | `insert a B = {x. x = a} \<union> B` | ✓ |  |
| 66 | `insert x UNIV = UNIV` | ✓ |  |
| 67 | `inv (\<lambda>a. a) = (\<lambda>a. a)` | ✓ |  |
| 68 | `irrefl R \<Longrightarrow> irrefl (lexord R)` | ✓ |  |
| 69 | `last (xs @ [x]) = x` | ✓ |  |
| 70 | `length (rev xs) = length xs` | ✓ |  |
| 71 | `length (suffixes xs) = Suc (length xs)` | ✗ |  |
| 72 | `length (x # xs) = Suc (length xs)` | ✓ |  |
| 73 | `lfp f = (f ^^ k) bot` | ✗ |  |
| 74 | `listsp (inf A B) = inf (listsp A) (listsp B)` | ✓ |  |
| 75 | `m < nat z \<longleftrightarrow> int m < z` | ✓ |  |
| 76 | `m \<le> n \<Longrightarrow> m - n = 0` | ✓ |  |
| 77 | `map_of xs = map_of ys` | ✗ |  |
| 78 | `map_option f \<circ> empty = empty` | ✗ |  |
| 79 | `min top (x::'a::order_top) = x` | ✓ |  |
| 80 | `mono f \<Longrightarrow> mono_on A f` | ✓ |  |
| 81 | `m|`A|`B = m|`(A\<inter>B)` | ✓ |  |
| 82 | `n > 0 \<Longrightarrow> Suc (n - Suc 0) = n` | ✓ |  |
| 83 | `nat (Int.Pos k) = nat_of_num k` | ✓ |  |
| 84 | `prefix xs ys \<Longrightarrow> sublist xs ys` | ✗ |  |
| 85 | `r\<^sup>+ = r \<union> r\<^sup>+ O r` | ✓ |  |
| 86 | `r``{a} = {b. (a, b) \<in> r}` | ✓ |  |
| 87 | `s = t \<Longrightarrow> t = s` | ✓ |  |
| 88 | `set(minus_list_set xs ys) = set xs - set ys` | ✓ |  |
| 89 | `snd (prod.swap x) = fst x` | ✓ |  |
| 90 | `sort [m..<n] = [m..<n]` | ✓ |  |
| 91 | `sum f (A - B) = sum f A - sum f B` | ✗ |  |
| 92 | `surj f \<Longrightarrow> f ` (f -` A) = A` | ✓ |  |
| 93 | `symp_on A R\<inverse>\<inverse> = symp_on A R` | ✓ |  |
| 94 | `x = (y, z) \<Longrightarrow> fst x = y` | ✓ |  |
| 95 | `z \<le> 0 \<Longrightarrow> nat z = 0` | ✓ |  |
| 96 | `{(a,b). P} = (if P then UNIV else {})` | ✓ |  |
| 97 | `{0..Suc n} = insert 0 (Suc ` {0..n})` | ✓ |  |
| 98 | `{Suc 0..<n} = {..<n} - {0}` | ✓ |  |
| 99 | `{Suc 0..n} = {..n} - {0}` | ✓ |  |
| 100 | `{l..<u+1} = {l..(u::int)}` | ✓ |  |

## `hol_main_hard` — 67/100
| # | Goal | Strict | Wall (s) |
|---:|---|:-:|---:|
| 1 | `((P \<longleftrightarrow> Q) \<longleftrightarrow> R) \<longleftrightarrow> (P \` | ✓ |  |
| 2 | `((\<lambda>x. if x \<in> B then c else d) -` A) = (if c \<in> A then (if d \<in>` | ✓ |  |
| 3 | `(A, B) \<in> max_ext R \<Longrightarrow> (C, D) \<in> max_ext R \<Longrightarrow` | ✓ |  |
| 4 | `(LIM x F1. f x :> F2) \<longleftrightarrow> (\<forall>P. eventually P F2 \<longr` | ✗ |  |
| 5 | `(\<And>a b. x a b \<longrightarrow> y a b) \<Longrightarrow> x\<^sup>*\<^sup>* a` | ✓ |  |
| 6 | `(\<And>fa y. fa \<in> range f \<Longrightarrow> y \<in> range fa \<Longrightarro` | ✗ |  |
| 7 | `(\<And>x y. (x, y) \<in> r \<Longrightarrow> (\<And>z. (x, z) \<in> r \<Longrigh` | ✓ |  |
| 8 | `(\<And>x y. Grp P id x y \<Longrightarrow> Grp Q id (f x) (f y)) \<equiv> (\<And` | ✗ |  |
| 9 | `(\<And>x y. x \<in> A \<Longrightarrow> y \<in> A \<Longrightarrow> R x y \<Long` | ✓ |  |
| 10 | `(\<And>x y. x \<in> set xs \<Longrightarrow> y \<in> set xs \<Longrightarrow> f ` | ✓ |  |
| 11 | `(\<forall>\<^sub>Fx in F. C \<longrightarrow> P x) \<longleftrightarrow> (C \<lo` | ✓ |  |
| 12 | `(\<forall>x. \<not> P x ) \<Longrightarrow> \<not> trivial_limit net \<Longright` | ✓ |  |
| 13 | `(\<forall>x. if x = a then P x else Q x) \<longleftrightarrow> P a \<and> (\<for` | ✓ |  |
| 14 | `(\<lambda>x y. (x, y) \<in> R) \<sqinter> (\<lambda>x y. (x, y) \<in> S) = (\<la` | ✗ |  |
| 15 | `(a::'a::linordered_idom) * c < c \<longleftrightarrow> (0 \<le> c \<longrightarr` | ✓ |  |
| 16 | `(a::'a::linordered_ring_strict) * c < b * c \<longleftrightarrow> 0 < c \<and> a` | ✓ |  |
| 17 | `(a::'a::order) < f b \<Longrightarrow> (b::'b::order) < c \<Longrightarrow> (!!x` | ✓ |  |
| 18 | `(a::'a::order) <= b \<Longrightarrow> f b < (c::'c::order) \<Longrightarrow> (!!` | ✓ |  |
| 19 | `(a::'a::order) <= f b \<Longrightarrow> (b::'b::order) < c \<Longrightarrow> (!!` | ✓ |  |
| 20 | `(a::'a::order) <= f b \<Longrightarrow> (b::'b::order) <= c \<Longrightarrow> (!` | ✓ |  |
| 21 | `(a::'a::semilattice_sup) \<le> c \<Longrightarrow> b \<le> d \<Longrightarrow> a` | ✗ |  |
| 22 | `(a::'a::semiring_gcd) dvd d \<and> b dvd d \<and> normalize d = d \<and> (\<fora` | ✓ |  |
| 23 | `(case p of (a, b) \<Rightarrow> c a b) \<Longrightarrow> (\<And>x y. p = (x, y) ` | ✓ |  |
| 24 | `(if Q then x else y) = b \<longleftrightarrow> (Q \<longrightarrow> x = b) \<and` | ✓ |  |
| 25 | `(insert (a,b) r)\<^sup>* = r\<^sup>* \<union> {(x, y). (x, a) \<in> r\<^sup>* \<` | ✓ |  |
| 26 | `(insert (y, x) r)\<^sup>+ = r\<^sup>+ \<union> {(a, b). (a, y) \<in> r\<^sup>* \` | ✓ |  |
| 27 | `(of_int n / of_int m :: 'a :: {division_ring,ring_char_0}) \<in> \<int> \<longle` | ✓ |  |
| 28 | `(x, z) \<in> R ^^ Suc n \<Longrightarrow> (\<And>y. (x, y) \<in> R \<Longrightar` | ✓ |  |
| 29 | `(x,y) \<in> r\<^sup>* \<Longrightarrow> (xs, ys) \<in> (listrel1 r)\<^sup>* \<Lo` | ✗ |  |
| 30 | `(x::'a::bounded_semilattice_sup_bot) \<squnion> y = \<bottom> \<longleftrightarr` | ✗ |  |
| 31 | `(x::'a::semilattice_inf) \<le> a \<sqinter> b \<Longrightarrow> (x \<le> a \<Lon` | ✗ |  |
| 32 | `(xs = [] \<Longrightarrow> P) \<Longrightarrow>(\<And>ys y. xs = ys @ [y] \<Long` | ✓ |  |
| 33 | `(y = None \<Longrightarrow> P) \<Longrightarrow> (\<And>a. y = Some a \<Longrigh` | ✓ |  |
| 34 | `(y = [] \<Longrightarrow> P) \<Longrightarrow> (\<And>a list. y = a # list \<Lon` | ✓ |  |
| 35 | `0 \<le> (x::'a::linordered_idom) \<Longrightarrow> 0 \<le> y \<Longrightarrow> y` | ✓ |  |
| 36 | `A \<subseteq> Collect (case_prod (R \<inverse>\<inverse>)) \<Longrightarrow> (%(` | ✓ |  |
| 37 | `A \<subseteq> insert x B \<longleftrightarrow> (if x \<in> A then A - {x} \<subs` | ✓ |  |
| 38 | `A \<times> B = C \<times> D \<longleftrightarrow> A = C \<and> B = D \<or> (A = ` | ✓ |  |
| 39 | `Id \<subseteq> s \<Longrightarrow> (r\<^sup>* \<inter> s) O r \<subseteq> s \<Lo` | ✓ |  |
| 40 | `LIM x inf F (principal {x. P x}). f x :> G \<Longrightarrow> LIM x inf F (princi` | ✗ |  |
| 41 | `Lcm\<^sub>f\<^sub>i\<^sub>n A = 1 \<longleftrightarrow> (\<forall>(a::'a::semiri` | ✗ |  |
| 42 | `P (a - b) \<longleftrightarrow> \<not> (a < b \<and> \<not> P 0 \<or> (\<exists>` | ✗ |  |
| 43 | `P1 \<longrightarrow> Q1 \<Longrightarrow> P2 \<longrightarrow> Q2 \<Longrightarr` | ✓ |  |
| 44 | `R O S = Finite_Set.fold (\<lambda>(x,y) A. Finite_Set.fold (\<lambda>(w,z) A'. i` | ✗ |  |
| 45 | `Set.insert x R O S = Finite_Set.fold (\<lambda>(w,z) A'. if snd x = w then Set.i` | ✗ |  |
| 46 | `X \<noteq> {} \<Longrightarrow> bdd_above X \<Longrightarrow> (y::'a::conditiona` | ✓ |  |
| 47 | `\<And>p. (\<And>a b. p = (a, b) \<Longrightarrow> z \<in> c a b) \<Longrightarro` | ✓ |  |
| 48 | `\<bottom> = (x::'a::bounded_semilattice_sup_bot) \<squnion> y \<longleftrightarr` | ✗ |  |
| 49 | `\<forall>x\<in>A. \<forall>y\<in>A. g (f x) = g (f y) \<longleftrightarrow> g x ` | ✗ |  |
| 50 | `\<lbrakk> P (x::'a::order); \<And>y. P y \<Longrightarrow> x \<ge> y \<rbrakk> \` | ✓ |  |
| 51 | `\<lbrakk> i < size xs; j < size xs\<rbrakk> \<Longrightarrow> distinct(xs[i := x` | ✓ |  |
| 52 | `\<lbrakk> inj_on f (set xs); x \<in> set xs \<rbrakk> \<Longrightarrow> count_li` | ✓ |  |
| 53 | `\<lbrakk>(x @ u, x @ v) \<in> lexord r; (\<forall>a. (a,a) \<notin> r) \<rbrakk>` | ✓ |  |
| 54 | `\<lbrakk>R \<subseteq> B \<times> B\<rbrakk> \<Longrightarrow> relInvImage A R f` | ✗ |  |
| 55 | `\<lbrakk>distinct xs; x \<in> set xs\<rbrakk> \<Longrightarrow> dropWhile (\<lam` | ✓ |  |
| 56 | `\<lbrakk>l = k; \<And>x. x \<in> set l \<Longrightarrow> P x = Q x\<rbrakk> \<Lo` | ✓ |  |
| 57 | `\<lbrakk>x#ys \<in> L; y#zs \<in> L; x \<noteq> y \<rbrakk> \<Longrightarrow> Lo` | ✗ |  |
| 58 | `\<not> finite S \<longleftrightarrow> (\<exists>f::nat \<Rightarrow> 'a. inj f \` | ✓ |  |
| 59 | `a = (if Q then x else y) \<longleftrightarrow> (Q \<longrightarrow> a = x) \<and` | ✓ |  |
| 60 | `a = b \<Longrightarrow> l = k \<Longrightarrow> (\<And>a x. x \<in> set l \<Long` | ✓ |  |
| 61 | `a = f b \<Longrightarrow> b < c \<Longrightarrow> (!!x y. x < y \<Longrightarrow` | ✓ |  |
| 62 | `a = f b \<Longrightarrow> b <= c \<Longrightarrow> (!!x y. x <= y \<Longrightarr` | ✓ |  |
| 63 | `a dvd d \<and> b dvd d \<and> (\<forall>e. a dvd e \<and> b dvd e \<longrightarr` | ✗ |  |
| 64 | `antisymp_on A R \<Longrightarrow> x \<in> A \<Longrightarrow> y \<in> A \<Longri` | ✓ |  |
| 65 | `b \<in> range (\<lambda>x. f x) \<Longrightarrow> (\<And>x. b = f x \<Longrighta` | ✓ |  |
| 66 | `card (\<Union>A) = nat (\<Sum>I | I \<subseteq> A \<and> I \<noteq> {}. (- 1) ^ ` | ✗ |  |
| 67 | `card {T. T \<subseteq> S \<and> U \<subseteq> T \<and> even(card T)} = card {T. ` | ✗ |  |
| 68 | `class.linorder (\<lambda>c d. of_char c \<le> (of_char d :: nat)) (\<lambda>c d.` | ✗ |  |
| 69 | `d dvd a \<and> d dvd b \<and> (\<forall>e. e dvd a \<and> e dvd b \<longrightarr` | ✗ |  |
| 70 | `disjoint A \<Longrightarrow> a \<in> A \<Longrightarrow> b \<in> A \<Longrightar` | ✗ |  |
| 71 | `distinct xs = (\<forall>i < size xs. \<forall>j < size xs. i \<noteq> j \<longri` | ✓ |  |
| 72 | `distinct_adj (xs @ ys) \<longleftrightarrow> distinct_adj xs \<and> distinct_adj` | ✓ |  |
| 73 | `dom (\<lambda>x. if P x then f x else g x) = dom f \<inter> {x. P x} \<union> do` | ✓ |  |
| 74 | `equiv A r \<Longrightarrow> x \<in> A \<Longrightarrow> y \<in> A \<Longrightarr` | ✓ |  |
| 75 | `eventually P (filtercomap f at_top) \<longleftrightarrow> (\<exists>N::'a::linor` | ✓ |  |
| 76 | `finite (A//R) \<Longrightarrow> R \<subseteq> S \<Longrightarrow> equiv A R \<Lo` | ✓ |  |
| 77 | `finite (UNIV :: 'a set) \<Longrightarrow> finite (UNIV :: 'b set) \<Longrightarr` | ✓ |  |
| 78 | `finite A \<Longrightarrow> (\<And>M. M \<in> A \<Longrightarrow> finite M) \<Lon` | ✓ |  |
| 79 | `finite A \<Longrightarrow> \<forall>y\<in>A. eventually (\<lambda>x. P x y) net ` | ✗ |  |
| 80 | `finite A \<Longrightarrow> finite B \<Longrightarrow> A \<inter> B = {} \<Longri` | ✓ |  |
| 81 | `finite A \<Longrightarrow> r \<subseteq> A \<times> A \<Longrightarrow> X \<in> ` | ✓ |  |
| 82 | `finite X \<Longrightarrow> (x::'a::conditionally_complete_lattice) \<in> X \<Lon` | ✗ |  |
| 83 | `i \<notin> I \<Longrightarrow> disjoint_family_on A (insert i I) \<longleftright` | ✗ |  |
| 84 | `inj_on f A \<Longrightarrow> x \<in> A \<Longrightarrow> y \<in> A \<Longrightar` | ✓ |  |
| 85 | `inj_on f C \<Longrightarrow> A \<subseteq> C \<Longrightarrow> B \<subseteq> C \` | ✓ |  |
| 86 | `irrefl_on A r \<longleftrightarrow> (\<forall>(a, b) \<in> r. a \<in> A \<longri` | ✗ |  |
| 87 | `left_unique Q \<Longrightarrow> (\<And>x y. R x y \<Longrightarrow> Q x y) \<Lon` | ✓ |  |
| 88 | `length xs = length ys \<Longrightarrow> P [] [] \<Longrightarrow> (\<And>x xs y ` | ✗ |  |
| 89 | `length xs = length ys \<or> length us = length vs \<Longrightarrow> (xs@us = ys@` | ✓ |  |
| 90 | `map_of xs k = Some z \<Longrightarrow> P k z \<Longrightarrow> map_of (filter (c` | ✓ |  |
| 91 | `minus_list_mset (x#xs) ys = (if x \<in> set ys then minus_list_mset xs (remove1 ` | ✓ |  |
| 92 | `monotone_on A P (\<ge>) f \<Longrightarrow> monotone_on A P (\<ge>) g \<Longrigh` | ✗ |  |
| 93 | `monotone_on A P (\<ge>) f \<Longrightarrow> monotone_on A P (\<ge>) g \<Longrigh` | ✗ |  |
| 94 | `monotone_on A P (\<le>) f \<Longrightarrow> monotone_on A P (\<le>) g \<Longrigh` | ✗ |  |
| 95 | `n choose k = (if k > n then 0 else if 2 * k > n then n choose (n - k) else (fold` | ✓ |  |
| 96 | `r \<subseteq> s \<Longrightarrow> (r\<^sup>+ \<inter> s) O r \<subseteq> s \<Lon` | ✓ |  |
| 97 | `summable (\<lambda>n. f (Suc n) * z ^ n :: 'a::real_normed_div_algebra) = summab` | ✗ |  |
| 98 | `symp_on A R \<Longrightarrow> x \<in> A \<Longrightarrow> y \<in> A \<Longrighta` | ✓ |  |
| 99 | `totalp_on A R \<Longrightarrow> x \<in> A \<Longrightarrow> y \<in> A \<Longrigh` | ✓ |  |
| 100 | `|\<Union>(\<Union>((\<lambda>f. f x) ` X))| \<le>o hbd \<Longrightarrow> |(Union` | ✗ |  |

## `hol_main_mid` — 83/100
| # | Goal | Strict | Wall (s) |
|---:|---|:-:|---:|
| 1 | `(A \<inter> B) \<times> C = A \<times> C \<inter> B \<times> C` | ✓ |  |
| 2 | `(LIM x F. f x :> at_top) \<longleftrightarrow> (\<forall>Z. eventually (\<lambda` | ✗ |  |
| 3 | `(\<And>P. eventually P F' \<Longrightarrow> eventually P F) \<Longrightarrow> F ` | ✓ |  |
| 4 | `(\<And>a. a \<in> A \<Longrightarrow> (a, a) \<notin> r) \<Longrightarrow> irref` | ✓ |  |
| 5 | `(\<And>n. f n = g n) \<Longrightarrow> f sums c \<longleftrightarrow> g sums c` | ✓ |  |
| 6 | `(\<And>x y. R x y \<Longrightarrow> f x < f y) \<Longrightarrow> wfp R` | ✗ |  |
| 7 | `(\<And>x. P (f x) = Q x) \<Longrightarrow> f -` (Collect P) = Collect Q` | ✓ |  |
| 8 | `(\<Sum>k\<le>m. (2 * m + 1 choose k)) = 2 ^ (2 * m)` | ✓ |  |
| 9 | `(\<lambda>n. if n \<in> A then f n else g n) sums S'` | ✗ |  |
| 10 | `(\<lambda>x y. (x, y) \<in> R) \<le> (\<lambda>x y. (x, y) \<in> S) \<longleftri` | ✓ |  |
| 11 | `(a::'a::cancel_comm_monoid_add) + b = a \<longleftrightarrow> b = 0` | ✓ |  |
| 12 | `(a::'a::group_add) + b = 0 \<Longrightarrow> - a = b` | ✓ |  |
| 13 | `(a::'a::normalization_semidom) div unit_factor a = normalize a` | ✓ |  |
| 14 | `(a::'a::ordered_ab_group_add) < - b \<longleftrightarrow> b < - a` | ✓ |  |
| 15 | `(a::'a::semiring_gcd) dvd gcd b c \<Longrightarrow> a dvd c` | ✓ |  |
| 16 | `(a::'a::semiring_modulo) - a mod b = b * (a div b)` | ✓ |  |
| 17 | `(a::'a::semiring_no_zero_divisors) * b = 0 \<longleftrightarrow> a = 0 \<or> b =` | ✓ |  |
| 18 | `(f :: 'a \<Rightarrow> 'b) = g \<Longrightarrow> f x = g x` | ✓ |  |
| 19 | `(filter P xs = []) = (\<forall>x\<in>set xs. \<not> P x)` | ✓ |  |
| 20 | `(i::'a::linordered_semidom) + k \<le> n \<Longrightarrow> n \<le> j + k \<Longri` | ✓ |  |
| 21 | `(if P then if Q then x else y else y) = (if P \<and> Q then x else y)` | ✓ |  |
| 22 | `(inf r (\<noteq>))\<^sup>*\<^sup>* = r\<^sup>*\<^sup>*` | ✓ |  |
| 23 | `(k::'a::semiring_gcd_mult_normalize) * lcm a b = lcm (k * a) (k * b) * unit_fact` | ✓ |  |
| 24 | `(x, y) \<in> f <*mlex*> R \<longleftrightarrow> f x < f y \<or> f x = f y \<and>` | ✓ |  |
| 25 | `(x, y) \<in> inv_image r f \<longleftrightarrow> (f x, f y) \<in> r` | ✓ |  |
| 26 | `(x::'a::preorder) < y \<Longrightarrow> (\<not> y < x) \<longleftrightarrow> Tru` | ✓ |  |
| 27 | `(y::'a::semilattice_inf) \<le> x \<Longrightarrow> x \<sqinter> y = y` | ✗ |  |
| 28 | `0 < (a::'a::ordered_cancel_comm_monoid_add) \<Longrightarrow> b \<le> c \<Longri` | ✓ |  |
| 29 | `A = B \<longleftrightarrow> A \<subseteq> B \<and> B \<subseteq> A` | ✓ |  |
| 30 | `A \<subseteq> B \<Longrightarrow> x \<in> A \<longrightarrow> x \<in> B` | ✓ |  |
| 31 | `A \<times> insert y B = (\<lambda>x. (x, y)) ` A \<union> A \<times> B` | ✓ |  |
| 32 | `Collect P = {} \<longleftrightarrow> (\<forall>x. \<not> P x)` | ✓ |  |
| 33 | `Domain (A \<inter> B) \<subseteq> Domain A \<inter> Domain B` | ✓ |  |
| 34 | `Field (insert (a, b) r) = {a, b} \<union> Field r` | ✓ |  |
| 35 | `P \<le> Q \<Longrightarrow> P x y \<Longrightarrow> Q x y` | ✓ |  |
| 36 | `Suc (card {k. Suc k \<in> M \<and> k < i}) = card {k \<in> M. k < Suc i}` | ✗ |  |
| 37 | `\<And>x. x \<in> N \<Longrightarrow> f x = g x` | ✗ |  |
| 38 | `\<exists>(b::'a::linear_continuum). a < b \<or> b < a` | ✓ |  |
| 39 | `\<exists>(x::'a::linorder). x \<noteq> y \<and> P` | ✗ |  |
| 40 | `\<forall>x. (x, x) \<notin> r\<^sup>+ \<Longrightarrow> (x, y) \<in> r \<Longrig` | ✓ |  |
| 41 | `\<lbrakk>(l::'a::linorder) \<le> m; m \<le> u\<rbrakk> \<Longrightarrow> {l..m} ` | ✓ |  |
| 42 | `\<lbrakk>\<exists>\<^sub>\<le>\<^sub>1x. P x; P a\<rbrakk> \<Longrightarrow> (TH` | ✓ |  |
| 43 | `\<not> (n::'a::canonically_ordered_monoid_add) < 0` | ✓ |  |
| 44 | `\<not> P x \<Longrightarrow> takeWhile P (xs @ (x#l)) = takeWhile P xs` | ✓ |  |
| 45 | `\<top> \<le> (a::'a::order_top) \<longleftrightarrow> a = \<top>` | ✗ |  |
| 46 | `a \<circ> b = c \<circ> d \<Longrightarrow> a (b v) = c (d v)` | ✓ |  |
| 47 | `acyclic (insert (y, x) r) \<longleftrightarrow> acyclic r \<and> (x, y) \<notin>` | ✓ |  |
| 48 | `antisymp_on A (\<lambda>x y. (x, y) \<in> r) \<longleftrightarrow> antisym_on A ` | ✓ |  |
| 49 | `bij_betw f A A' \<Longrightarrow> a' \<in> A' \<Longrightarrow> f (inv_into A f ` | ✓ |  |
| 50 | `bij_betw f A B \<Longrightarrow> bij_betw (the_inv_into A f) B A` | ✓ |  |
| 51 | `c \<in> A \<inter> B \<Longrightarrow> c \<in> B` | ✓ |  |
| 52 | `card (A - {x}) = (if x \<in> A then card A - 1 else card A)` | ✓ |  |
| 53 | `coprime ((a::'a::algebraic_semidom) * c) (b * c) \<longleftrightarrow> is_unit c` | ✓ |  |
| 54 | `coprime 0 (a::'a::algebraic_semidom) \<longleftrightarrow> is_unit a` | ✓ |  |
| 55 | `disjnt (insert a X) Y \<longleftrightarrow> a \<notin> Y \<and> disjnt X Y` | ✓ |  |
| 56 | `distinct xs \<Longrightarrow> distinct (minus_list_set xs ys)` | ✓ |  |
| 57 | `distinct xs \<Longrightarrow> distinct ys \<Longrightarrow> distinct (List.produ` | ✗ |  |
| 58 | `drop n xs = [] \<longleftrightarrow> length xs \<le> n` | ✓ |  |
| 59 | `equiv A r \<Longrightarrow> equiv (lists A) (listrel r)` | ✓ |  |
| 60 | `eventually (\<lambda>x::'a::{no_bot, linorder}. x \<noteq> c) at_bot` | ✓ |  |
| 61 | `f -` (f ` A) = {y. \<exists>x\<in>A. f x = f y}` | ✓ |  |
| 62 | `f x = None \<Longrightarrow> dom f - insert x A = dom f - A` | ✓ |  |
| 63 | `finite A \<longleftrightarrow> (\<exists>n f. A = f ` {i::nat. i < n})` | ✗ |  |
| 64 | `foldl g a (map f xs) = foldl (\<lambda>a x. g a (f x)) a xs` | ✓ |  |
| 65 | `foldr f xs a = foldl (\<lambda>x y. f y x) a (rev xs)` | ✓ |  |
| 66 | `i \<le> j \<Longrightarrow> j \<le> k \<Longrightarrow> [i..k] = [i..j-1] @ [j..` | ✓ |  |
| 67 | `inj f \<Longrightarrow> (map f xs = map f ys) = (xs = ys)` | ✓ |  |
| 68 | `inj f \<Longrightarrow> filtermap f F = filtermap f G \<longleftrightarrow> F = ` | ✓ |  |
| 69 | `inj_on f (insert a A) \<longleftrightarrow> inj_on f A \<and> f a \<notin> f ` (` | ✓ |  |
| 70 | `inj_on f A \<Longrightarrow> f x = y \<Longrightarrow> x \<in> A \<Longrightarro` | ✓ |  |
| 71 | `irrefl_on B r \<Longrightarrow> A \<subseteq> B \<Longrightarrow> irrefl_on A r` | ✓ |  |
| 72 | `j - k \<le> i \<longleftrightarrow> j \<le> i + k` | ✓ |  |
| 73 | `k \<le> m \<Longrightarrow> k \<le> n \<Longrightarrow> m - k \<le> n - k \<long` | ✓ |  |
| 74 | `left_unique A \<Longrightarrow> left_unique (rel_set A)` | ✓ |  |
| 75 | `length (transpose xs) = (if xs = [] then 0 else length (xs ! 0))` | ✗ |  |
| 76 | `m \<ge> n \<Longrightarrow> gcd (m - n) n = gcd m n` | ✗ |  |
| 77 | `m \<noteq> n \<longleftrightarrow> m < n \<or> n < m` | ✓ |  |
| 78 | `map_filter_on X f F = Abs_filter (\<lambda>P. eventually (\<lambda>x. P (f x) \<` | ✓ |  |
| 79 | `mono Q \<Longrightarrow> mono (\<lambda>i x. Q i (f x))` | ✓ |  |
| 80 | `n < length xs \<Longrightarrow> (map f xs)!n = f(xs!n)` | ✓ |  |
| 81 | `n < length xs \<Longrightarrow> take n xs @ [hd (drop n xs)] = take (Suc n) xs` | ✓ |  |
| 82 | `n \<le> m \<Longrightarrow> Suc m - n = Suc (m - n)` | ✓ |  |
| 83 | `nat x \<le> n \<longleftrightarrow> x \<le> int n` | ✓ |  |
| 84 | `nat_of_natural (max k l) = max (nat_of_natural k) (nat_of_natural l)` | ✓ |  |
| 85 | `p \<in> R\<^sup>* \<Longrightarrow> \<exists>n. p \<in> R ^^ n` | ✓ |  |
| 86 | `prefix xs (ys @ [y]) \<longleftrightarrow> xs = ys @ [y] \<or> prefix xs ys` | ✗ |  |
| 87 | `prefix xs ys \<Longrightarrow> set xs \<subseteq> set ys` | ✗ |  |
| 88 | `r \<le> s \<Longrightarrow> antisymp s \<Longrightarrow> antisymp r` | ✓ |  |
| 89 | `r `` s = {y. \<exists>x\<in>s. (x, y) \<in> r}` | ✓ |  |
| 90 | `rel_set (eq_onp P) = eq_onp (\<lambda>A. Ball A P)` | ✓ |  |
| 91 | `replicate (length (filter (\<lambda>y. x = y) xs)) x = filter (\<lambda>y. x = y` | ✓ |  |
| 92 | `size_list f (map g xs) = size_list (f \<circ> g) xs` | ✓ |  |
| 93 | `strict_antimono_on S f \<longleftrightarrow> antimono_on S f \<and> inj_on f S` | ✗ |  |
| 94 | `subseq (zs @ xs) (zs @ ys) \<longleftrightarrow> subseq xs ys` | ✗ |  |
| 95 | `totalp_on A R \<Longrightarrow> totalp_on A (tranclp R)` | ✓ |  |
| 96 | `totalp_on A R\<inverse>\<inverse> = totalp_on A R` | ✓ |  |
| 97 | `x \<notin> set xs \<Longrightarrow> (f(xs[\<mapsto>]ys)) x = f x` | ✓ |  |
| 98 | `xs \<in> set (suffixes ys) \<longleftrightarrow> suffix xs ys` | ✗ |  |
| 99 | `y < x \<Longrightarrow> Sup {y..<x::'a::{conditionally_complete_linorder, dense_` | ✓ |  |
| 100 | `zs \<in> shuffles xs ys \<Longrightarrow> z # zs \<in> shuffles (z # xs) ys` | ✓ |  |

