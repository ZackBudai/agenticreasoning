"""sample_hol_tiered.py — Curate easy / mid / hard HOL/Main goal files from
the F27 corpus mine.

Reads `solution/datasets/hol_corpus.jsonl` (produced by extract_hol.py) and
emits three .txt files under `agenticreasoning/datasets_subset/` with N goals
each, tiered by a length-based heuristic on the recorded outline.

Tiering (default):
  easy  — outline ≤ 50 chars  (basically `by simp` / `by auto` one-liners)
  mid   — outline 50–200 chars
  hard  — outline > 200 chars (structured Isar with multiple `have`/`show`)

Filters before sampling (keep things that look standalone-parseable in Main):
  - statement length between 15 and 300 chars
  - source theory is in the Main-resident whitelist
    (so e.g. Polynomial, Topological_Spaces, Bali theorems are dropped)
  - no exotic notation: record syntax, NSA `*f*`, sequents `\\<turnstile>`,
    analysis-specific predicates (`holomorphic_on`, `field_differentiable`)
  - no schematic variables (`?` other than `?thesis` / `?case`)
  - no triple-dotted qualified names (`A.B.C.foo`)
  - no `==>` (legacy ASCII meta-impl)
  - exclude exact duplicates of pre-existing datasets_subset/*.txt goals

Usage (from agenticreasoning/):
  cd solution && source .venv/bin/activate
  python -m planner.sample_hol_tiered \\
      --corpus datasets/hol_corpus.jsonl \\
      --out-dir ../datasets_subset \\
      --n 100 \\
      --seed 42
"""
from __future__ import annotations
import argparse
import json
import random
import re
import sys
from pathlib import Path
from typing import List, Set


# Theories that are reliably brought in by `imports Main` in Isabelle2025.
# Derived from inspecting HOL/Main.thy + its transitive imports plus a few
# commonly-importable extras from HOL/Library that the existing assignment
# datasets (mid_25, holmain_50) draw on. Anything outside this set is dropped
# at sample time so we don't ship Analysis/NSA/Bali/Polynomial theorems that
# wouldn't typecheck in the bench's `imports Main` wrapper.
_MAIN_THEORIES = frozenset({
    # Core HOL
    'List', 'Set', 'Fun', 'HOL', 'Pure', 'Sledgehammer',
    'Nat', 'Int', 'Power', 'Series', 'Numeral_Simprocs', 'Numeral_Type',
    'Orderings', 'Lattices', 'Groups', 'Rings', 'Wellfounded', 'Wfrec',
    'Finite_Set', 'Equiv_Relations', 'Relation', 'Transitive_Closure',
    'Option', 'Sum_Type', 'Product_Type', 'Map',  'String',
    'Boolean_Algebra', 'Hilbert_Choice', 'Lifting', 'Lifting_Set',
    # BNFs / Predicate compilation (loaded by Main)
    'BNF_Greatest_Fixpoint', 'BNF_Least_Fixpoint', 'BNF_Composition',
    'BNF_Def', 'BNF_Fixpoint_Base', 'Predicate_Compile',
    'Quickcheck_Narrowing', 'Quickcheck_Random', 'Quickcheck_Exhaustive',
    'Extraction', 'Nunchaku', 'Mirabelle',
    # Conditionally-Main / commonly imported library
    'Filter', 'GCD', 'Binomial', 'Conditionally_Complete_Lattices',
    'Code_Numeral', 'Code_Evaluation', 'Code_Generator', 'Code_Real_Approx_By_Float',
    'Inequalities', 'Sublist', 'Cardinality',
    'Disjoint_Sets', 'Set_Interval', 'Sums', 'Lattices_Big',
    'Groups_Big',
})

# Filters
_RECORD_RE = re.compile(r'\\<lparr>|\\<rparr>')
_SCHEMATIC_RE = re.compile(r'\?[A-Za-z_]\w*(?<!thesis)(?<!case)')
_DEEP_QUAL_RE = re.compile(r'\b[A-Z]\w*\.[A-Z]\w*\.[A-Za-z_]\w*')
_LEGACY_IMP_RE = re.compile(r'==>')
_EXOTIC_PATTERNS = re.compile(
    r'\\<turnstile>|\\<bar>.*?\\<bar>|'
    r'has_sum\b|holomorphic_on\b|field_differentiable\b|'
    r'complex_differentiable\b|continuous_map\b|'
    r'\(\s*\*[a-z][a-z0-9_]*\*\)|'                     # NSA *f* *p2*
    r'\bmset\b|\bmultiset\b|\bfset\b|\bllist\b|\bstream\b|'
    r'\\<succ>|\\<langle>|\\<rangle>|'
    r'\\<Squnion>|\\<Sqinter>|'
    r'\bpoly\b|\bcoeff\b|\\<Sum>\\<infinity>|'
    r'\bnsa\b|\bnonstandard\b|\bstar_n\b'
)
# Goal must contain at least one propositional/relational connective —
# otherwise it's a pure type expression like `'a \<Rightarrow> nat` that
# `iter_lemmas_with_proofs` accidentally picked up from definitions / consts.
# Plain `<` / `>` excluded because they appear inside `\<NAME>` markers and
# would let every goal through; comparisons use `\<le>` / `\<ge>` instead.
_PROP_CONNECTIVE_RE = re.compile(
    r'=|\\<noteq>|\\<equiv>|'
    r'\\<Longrightarrow>|\\<longrightarrow>|\\<longleftrightarrow>|'
    r'\\<le>|\\<ge>|\\<in>|\\<notin>|\\<subseteq>|\\<subset>|'
    r'\\<and>|\\<or>|\\<not>|'
    r'\\<exists>|\\<forall>'
)
# Type-signature heads — drop entries that look like consts / definition
# headers leaked through the lemma miner.
_TYPE_HEAD_RE = re.compile(r"^\s*'[a-z]\s+\\<Rightarrow>")


def is_kept(stmt: str, theory: str) -> bool:
    if not (15 <= len(stmt) <= 300):
        return False
    if not theory or theory not in _MAIN_THEORIES:
        return False
    if _RECORD_RE.search(stmt):
        return False
    if _SCHEMATIC_RE.search(stmt):
        return False
    if _DEEP_QUAL_RE.search(stmt):
        return False
    if _LEGACY_IMP_RE.search(stmt):
        return False
    if _EXOTIC_PATTERNS.search(stmt):
        return False
    # Cheap typing check: too many backslashes is usually ASCII-syntax cruft.
    if stmt.count('\\<') > 8:
        return False
    # Must look like a proposition, not a bare type signature.
    if not _PROP_CONNECTIVE_RE.search(stmt):
        return False
    if _TYPE_HEAD_RE.match(stmt):
        return False
    return True


def tier(goal: str) -> str:
    # Tier by *goal* length, not outline length: `iter_lemmas_with_proofs`
    # records a fixed skeleton `lemma "<goal>"\nproof\n  sorry\nqed\n` for every
    # entry, so outline length is just goal length + 28 chars of boilerplate
    # and doesn't actually correlate with proof difficulty. Goal length is a
    # rough but workable proxy: longer statements typically have more
    # hypotheses to manage and more sub-claims for Fill to close.
    n = len(goal or "")
    if n <= 45:
        return 'easy'
    if n <= 105:
        return 'mid'
    return 'hard'


def collect_exclusions(datasets_dir: Path) -> Set[str]:
    """Return the union of all goals already in datasets_subset/*.txt so the
    tiered sample doesn't overlap."""
    excl: Set[str] = set()
    for p in datasets_dir.glob('*.txt'):
        for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
            s = line.strip()
            if s and not s.startswith('#'):
                excl.add(s)
    return excl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default='datasets/hol_corpus.jsonl',
                    help='Rich JSONL from extract_hol.py')
    ap.add_argument('--out-dir', default='../datasets_subset',
                    help='Where to write hol_main_{easy,mid,hard}.txt')
    ap.add_argument('--n', type=int, default=100, help='Goals per tier')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--names', default='hol_main',
                    help='Filename prefix; produces <names>_easy.txt etc.')
    args = ap.parse_args()

    corpus = Path(args.corpus).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    excl = collect_exclusions(out_dir)
    print(f"[sample_hol_tiered] excluding {len(excl)} pre-existing goals")

    buckets: dict[str, List[str]] = {'easy': [], 'mid': [], 'hard': []}
    seen: Set[str] = set(excl)  # also dedupe within the corpus

    n_in = 0
    with corpus.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            goal = (rec.get('goal') or '').strip()
            theory = (rec.get('theory') or '').strip()
            if not goal:
                continue
            # Flatten multi-line goals onto one line: the bench reads its goal
            # file line-by-line, so embedded \n in a HOL source statement
            # would split one goal into two. Collapsing whitespace is safe
            # for Isabelle parsing (terms are token-sequenced, not whitespace-sensitive).
            goal = re.sub(r'\s+', ' ', goal).strip()
            if goal in seen:
                continue
            if not is_kept(goal, theory):
                continue
            t = tier(goal)
            buckets[t].append(goal)
            seen.add(goal)
            n_in += 1

    print(f"[sample_hol_tiered] kept {n_in} goals after filtering "
          f"(easy={len(buckets['easy']):,} mid={len(buckets['mid']):,} "
          f"hard={len(buckets['hard']):,})")

    rng = random.Random(args.seed)
    written = {}
    for t in ('easy', 'mid', 'hard'):
        pool = buckets[t]
        if len(pool) < args.n:
            print(f"  WARNING: only {len(pool)} goals in {t} tier, "
                  f"writing all of them (asked {args.n})")
            chosen = pool
        else:
            chosen = rng.sample(pool, args.n)
        # Sort for deterministic output ordering even with the same seed
        chosen.sort()
        out_path = out_dir / f"{args.names}_{t}.txt"
        out_path.write_text("\n".join(chosen) + "\n", encoding='utf-8')
        written[t] = (out_path, len(chosen))
        print(f"  → {out_path} ({len(chosen)} goals)")

    # Print runbook-ready summary
    print()
    print("=== ready to launch ===")
    print(f"Datasets: " + " ".join(str(p) for p, _ in written.values()))
    total = sum(n for _, n in written.values())
    print(f"Total goals: {total}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
