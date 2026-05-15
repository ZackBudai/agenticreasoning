#!/usr/bin/env python3
"""
generate_scripts.py — Generate two Isabelle theory files for comparison
                      WITHOUT running Isabelle locally.

Baseline:  comparison/baseline_results.thy  — sledgehammer calls only
Solution:  comparison/solution_results.thy  — LLM-proposed tactics (Ollama)

Run this to produce the .thy files, then open them in Isabelle/jEdit
or run:
    isabelle build -d comparison Comparison

Usage:
    python generate_scripts.py [--goals-file FILE] [--n N] [--model MODEL]
                               [--out-dir DIR] [--ollama-host HOST]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import requests as _req
    _SESSION = _req.Session()
except ImportError:
    _SESSION = None


# ─── CLI ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--goals-file", default="solution/datasets/lists.txt")
    p.add_argument("--n", type=int, default=5, help="Number of goals (default: 5)")
    p.add_argument("--model", default="qwen2.5-coder:1.5b",
                   help="Ollama model name (default: qwen2.5-coder:1.5b)")
    p.add_argument("--out-dir", default="comparison")
    p.add_argument("--ollama-host", default=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
    p.add_argument("--imports", default="Main")
    return p.parse_args()


# ─── Goal loading ─────────────────────────────────────────────────────────────

def load_goals(path: str, n: int) -> List[str]:
    goals = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                goals.append(line)
            if len(goals) >= n:
                break
    return goals


# ─── Unicode → ASCII Isabelle notation ───────────────────────────────────────

UNICODE_MAP = {
    "⟹": r"\<Longrightarrow>", "⇒": r"\<Longrightarrow>",
    "⟶": r"\<longrightarrow>",  "→": r"\<longrightarrow>",
    "⟷": r"\<longleftrightarrow>", "↔": r"\<longleftrightarrow>",
    "¬": r"\<not>",  "∧": r"\<and>",  "∨": r"\<or>",
    "∀": r"\<forall>", "∃": r"\<exists>", "⋀": r"\<And>",
    "≤": r"\<le>",  "≥": r"\<ge>",  "≠": r"\<noteq>",
    "⊆": r"\<subseteq>", "⊇": r"\<supseteq>",
    "∈": r"\<in>",  "∉": r"\<notin>",
    "∪": r"\<union>", "∩": r"\<inter>",
    "λ": r"\<lambda>",
}
_UNICODE_RE = re.compile("|".join(map(re.escape, sorted(UNICODE_MAP, key=len, reverse=True))))

def isa_escape(s: str) -> str:
    return _UNICODE_RE.sub(lambda m: UNICODE_MAP[m.group(0)], s)

def lemma_name(i: int, goal: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_]", "_", goal[:30]).strip("_")
    return f"goal_{i+1}_{slug}"


# ─── Ollama LLM call ──────────────────────────────────────────────────────────

_SYSTEM = textwrap.dedent("""\
    You are an Isabelle/HOL proof assistant. Given a goal, output ONLY the proof
    body — the lines that go after the 'lemma ... :' declaration.

    Rules:
    - Use standard Isabelle tactics: simp, auto, induct, arith, omega, blast, fastforce.
    - Prefer short proofs: try 'by simp', 'by auto', 'by (induct xs) auto' first.
    - For list goals use structural induction: apply (induct xs) then simp or auto.
    - Never use sorry.
    - Output ONLY the proof lines, no explanation, no imports, no lemma declaration.

    Examples:
      Goal: xs @ [] = xs
      Output:
        by (induct xs) auto

      Goal: rev (rev xs) = xs
      Output:
        by (induct xs) (auto simp: rev_append)

      Goal: length (xs @ ys) = length xs + length ys
      Output:
        by (induct xs) auto
""")

def _ask_ollama(goal: str, model: str, host: str) -> Optional[str]:
    if _SESSION is None:
        return None
    url = f"{host.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": f"[SYSTEM]\n{_SYSTEM}\n\n[USER]\nGoal: {goal}\nOutput:",
        "temperature": 0.1,
        "num_predict": 128,
        "stream": False,
    }
    try:
        resp = _SESSION.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        raw = resp.json().get("response", "").strip()
        return raw if raw else None
    except Exception as e:
        print(f"  [llm] error: {e}", file=sys.stderr)
        return None


def _clean_llm_proof(raw: str, goal: str) -> str:
    """
    Extract the first plausible proof line(s) from LLM output.
    Falls back to a structured proof guess based on the goal shape.
    """
    if not raw:
        return _fallback_proof(goal)

    lines = raw.splitlines()
    proof_lines = []
    in_proof = False

    for line in lines:
        stripped = line.strip()
        # Skip preamble lines that look like goal/output labels
        if stripped.lower().startswith("output:") or stripped.lower().startswith("goal:"):
            continue
        # Start collecting at first tactic keyword
        if re.match(r"^\s*(by |apply |proof|done|qed|using |from |have |show |obtain )", line):
            in_proof = True
        if in_proof:
            proof_lines.append(line if line.startswith(" ") else "  " + line)
            # Stop after a complete single-line proof or qed/done
            if stripped.startswith("by ") or stripped in ("done", "qed", ".."):
                break
            if stripped.startswith("apply") and not proof_lines:
                continue  # keep collecting

    if proof_lines:
        return "\n".join(proof_lines)

    # Couldn't parse — try the whole raw output as a single proof line
    first = lines[0].strip() if lines else ""
    if first.startswith("by ") or first.startswith("apply "):
        return "  " + first
    return _fallback_proof(goal)


def _fallback_proof(goal: str) -> str:
    """
    Rule-based fallback when the LLM output is unusable.
    Covers the most common patterns in the lists/logic datasets.
    """
    g = goal.strip()
    # Structural induction over a list variable
    if re.search(r"\b(rev|map|filter|length|append|@|xs|ys|zs)\b", g):
        return "  by (induct xs) auto"
    # Arithmetic
    if re.search(r"\b(n|m|k)\b.*[+\-*]|[+\-*].*\b(n|m|k)\b", g):
        return "  by auto"
    return "  by auto"


# ─── Theory file builder ──────────────────────────────────────────────────────

def theory_file(name: str, imports: str, blocks: List[str]) -> str:
    return (
        f"theory {name}\n"
        f"  imports {imports}\n"
        f"begin\n\n"
        + "\n".join(blocks)
        + "\nend\n"
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(exist_ok=True)

    goals = load_goals(args.goals_file, args.n)
    print(f"Loaded {len(goals)} goals from {args.goals_file}")

    # ── BASELINE: sledgehammer only ──────────────────────────────────────────
    print("\nGenerating BASELINE (sledgehammer) script...")
    baseline_blocks: List[str] = []
    for i, g in enumerate(goals):
        name = lemma_name(i, g)
        block = (
            f'(* Goal {i+1}: {g} *)\n'
            f'lemma {name}: "{isa_escape(g)}"\n'
            f"  by sledgehammer\n"
        )
        baseline_blocks.append(block)
        print(f"  [{i+1}/{len(goals)}] {g[:60]}")

    baseline_path = out_dir / "baseline_results.thy"
    baseline_path.write_text(theory_file("Baseline_Results", args.imports, baseline_blocks))
    print(f"  → {baseline_path}")

    # ── SOLUTION: LLM-proposed tactics ───────────────────────────────────────
    print(f"\nGenerating SOLUTION (Ollama:{args.model}) script...")
    solution_blocks: List[str] = []
    for i, g in enumerate(goals):
        name = lemma_name(i, g)
        print(f"  [{i+1}/{len(goals)}] {g[:60]} ... ", end="", flush=True)
        raw = _ask_ollama(g, args.model, args.ollama_host)
        proof = _clean_llm_proof(raw, g)
        print(f"{'ok' if raw else 'fallback'}")
        block = (
            f'(* Goal {i+1}: {g} *)\n'
            f'lemma {name}: "{isa_escape(g)}"\n'
            f"{proof}\n"
        )
        solution_blocks.append(block)

    solution_path = out_dir / "solution_results.thy"
    solution_path.write_text(theory_file("Solution_Results", args.imports, solution_blocks))
    print(f"  → {solution_path}")

    # ── ROOT session file ─────────────────────────────────────────────────────
    (out_dir / "ROOT").write_text(
        "session Comparison = HOL +\n"
        "  theories\n"
        "    Baseline_Results\n"
        "    Solution_Results\n"
    )

    print(f"\nDone. Open in Isabelle:")
    print(f"  isabelle jedit -d {out_dir} {baseline_path.name}")
    print(f"  isabelle jedit -d {out_dir} {solution_path.name}")
    print(f"  isabelle build -d {out_dir} Comparison")


if __name__ == "__main__":
    main()
