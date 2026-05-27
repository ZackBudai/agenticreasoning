"""
extract_hol.py — Mine HOL/Main + HOL/Library (+optional HOL/Analysis) for the
planner RAG. Produces:

  <out_dir>/hol_corpus.jsonl   — rich record per lemma (mine_afp_corpus_rich shape),
                                 feeds the priors+hintlex aggregator.
  <out_dir>/known_names.json   — flat list of all declared identifier names in HOL,
                                 used by skeleton.py's post-hoc lemma-name validator
                                 (gated on USE_NAME_VALIDATOR=1).

This is additive — does not touch existing AFP-derived priors/hintlex.

Usage (from agenticreasoning/solution/):
  python -m planner.extract_hol --out-dir datasets
  python -m planner.priors --input datasets/hol_corpus.jsonl \\
      --priors datasets/isar_priors_hol.json \\
      --hintlex datasets/isar_hintlex_hol.json
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Set, List

from planner.extract import mine_afp_corpus_rich

NAME_DECL_RE = re.compile(
    r'^\s*(?:lemma|theorem|proposition|corollary|lemmas|definition|fun|function|'
    r'primrec|abbreviation|inductive|inductive_set|coinductive|coinductive_set|'
    r'datatype|codatatype|type_synonym|axiomatization|notation|consts|axioms|'
    r'locale|class|interpretation|sublocale)\s+'
    r'(?:\([^)]*\)\s+)?'                     # optional (in foo) locale/class params
    r'([A-Za-z_][A-Za-z0-9_\']*)',
    re.MULTILINE | re.UNICODE,
)

def extract_known_names(src_dirs: List[Path]) -> Set[str]:
    base: Set[str] = set()
    n_files = 0
    for src in src_dirs:
        for thy in src.rglob("*.thy"):
            n_files += 1
            try:
                text = thy.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for m in NAME_DECL_RE.finditer(text):
                base.add(m.group(1))
    print(f"[extract_hol] Scanned {n_files} .thy files, found {len(base):,} bare names")
    # Add the common auto-generated suffix variants Isabelle attaches to
    # definitions and inductive predicates so the validator doesn't flag them.
    names: Set[str] = set(base)
    for n in base:
        names.add(f"{n}_def")
        names.add(f"{n}.simps")
        names.add(f"{n}.induct")
        names.add(f"{n}.cases")
        names.add(f"{n}.elims")
        names.add(f"{n}.intros")
    return names

def main() -> int:
    ap = argparse.ArgumentParser(description="Mine HOL corpus + name table for RAG.")
    ap.add_argument("--isabelle-home",
                    default=os.environ.get("ISABELLE_HOME", ""),
                    help="Path to Isabelle install dir; default $ISABELLE_HOME")
    ap.add_argument("--out-dir", default="datasets",
                    help="Output directory (relative to cwd)")
    ap.add_argument("--include-analysis", action="store_true",
                    help="Also mine HOL/Analysis (~109 .thy files, slower)")
    ap.add_argument("--skip-corpus", action="store_true",
                    help="Only emit known_names.json; skip the rich corpus mine")
    args = ap.parse_args()

    home = Path(args.isabelle_home).expanduser() if args.isabelle_home else Path()
    if not home.is_dir():
        print(f"ERROR: ISABELLE_HOME not set or not a directory: {home}", file=sys.stderr)
        return 1

    hol = home / "src" / "HOL"
    if not hol.is_dir():
        print(f"ERROR: HOL source not found: {hol}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    src_dirs: List[Path] = [hol, hol / "Library"]
    if args.include_analysis:
        src_dirs.append(hol / "Analysis")
    src_dirs = [d for d in src_dirs if d.is_dir()]

    # 1. Name table — fast, always done.
    names = extract_known_names(src_dirs)
    names_path = out_dir / "known_names.json"
    with names_path.open("w", encoding="utf-8") as f:
        json.dump(sorted(names), f, ensure_ascii=False)
    print(f"[extract_hol] Wrote {len(names):,} names (with suffix variants) → {names_path}")

    if args.skip_corpus:
        return 0

    # 2. Rich corpus — slower; mine_afp_corpus_rich appends, so wipe first.
    corpus_path = out_dir / "hol_corpus.jsonl"
    if corpus_path.exists():
        corpus_path.unlink()
    for d in src_dirs:
        print(f"[extract_hol] Mining {d}...")
        mine_afp_corpus_rich(str(d), str(corpus_path))

    print()
    print(f"[extract_hol] Next: aggregate to priors/hintlex with")
    print(f"  python -m planner.priors --input {corpus_path} \\")
    print(f"    --priors {out_dir}/isar_priors_hol.json \\")
    print(f"    --hintlex {out_dir}/isar_hintlex_hol.json")
    return 0

if __name__ == "__main__":
    sys.exit(main())
