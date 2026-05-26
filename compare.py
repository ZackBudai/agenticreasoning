#!/usr/bin/env python3
"""
compare.py — Run baseline and solution provers on the same goals and emit
             two Isabelle theory files for side-by-side comparison.

Usage:
    python compare.py [--goals-file FILE] [--n N] [--model MODEL] [--timeout T]
                      [--out-dir DIR] [--sledge-only-baseline]

Requires:
    - isabelle on PATH  (set ISABELLE_BIN if non-standard location)
    - A local Ollama model (default: qwen2.5-coder:1.5b) OR
      ANTHROPIC_API_KEY set for the solution's Claude backend

Output:
    <out-dir>/baseline_results.thy   — sledgehammer-only proofs
    <out-dir>/solution_results.thy   — full prover + planner with improvements

Both files are valid Isabelle/HOL theories you can open in jEdit or run with
    isabelle build -d . Comparison
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
import textwrap
from pathlib import Path
from typing import List, Optional, Tuple


# ─── isabelle_client compatibility shim ─────────────────────────────────────

def _extract_session_id(responses) -> str:
    """Handle both old isabelle_client (returns str) and ≥1.0 (returns list)."""
    if isinstance(responses, str):
        return responses
    for r in responses:
        body = getattr(r, "response_body", None)
        if body is None:
            continue
        if hasattr(body, "session_id"):
            return str(body.session_id)
        if isinstance(body, dict) and "session_id" in body:
            return str(body["session_id"])
        try:
            d = body.dict() if hasattr(body, "dict") else {}
            if "session_id" in d:
                return str(d["session_id"])
        except Exception:
            pass
    raise RuntimeError("Could not extract session_id from session_start() responses")


def _clear_prover_modules() -> None:
    """Remove cached prover/planner modules so next sys.path takes effect."""
    to_del = [k for k in sys.modules if k.split(".")[0] in ("prover", "planner")]
    for k in to_del:
        del sys.modules[k]

# ─── CLI ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--goals-file", default="solution/datasets/lists.txt",
                   help="One goal per line (default: solution/datasets/lists.txt)")
    p.add_argument("--n", type=int, default=5,
                   help="Number of goals to prove (default: 5)")
    p.add_argument("--model", default="ollama:qwen2.5-coder:1.5b",
                   help="LLM model string for solution prover (default: ollama:qwen2.5-coder:1.5b)")
    p.add_argument("--timeout", type=int, default=60,
                   help="Per-goal timeout for the solution prover in seconds (default: 60)")
    p.add_argument("--baseline-timeout", type=int, default=None,
                   help="Per-goal timeout for the baseline prover in seconds (default: same as --timeout)")
    p.add_argument("--out-dir", default="comparison",
                   help="Output directory (default: comparison/)")
    p.add_argument("--imports", default="Main",
                   help="Isabelle imports (default: Main)")
    p.add_argument("--sledge-timeout", type=int, default=30,
                   help="Sledgehammer timeout per goal in seconds (default: 30)")
    p.add_argument("--sledge-only-baseline", action="store_true",
                   help="Use a sledgehammer-only baseline instead of the baseline/ prover")
    p.add_argument("--trace", action="store_true", help="Verbose prover output")
    return p.parse_args()


# ─── Goal loading ────────────────────────────────────────────────────────────

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



# ─── Isabelle theory file helpers ────────────────────────────────────────────

import re
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

def proof_block(name: str, goal: str, proof: str, comment: str = "") -> str:
    lines = []
    if comment:
        lines.append(f"(* {comment} *)")
    lines.append(f'lemma {name}: "{isa_escape(goal)}"')
    for ln in proof.splitlines():
        lines.append(ln)
    lines.append("")
    return "\n".join(lines)

def theory_file(theory_name: str, imports: str, blocks: List[str]) -> str:
    header = textwrap.dedent(f"""\
        theory {theory_name}
          imports {imports}
        begin

        """)
    footer = "\nend\n"
    return header + "\n".join(blocks) + footer


# ─── Baseline runner (sledgehammer only, no server management) ───────────────

# Sledgehammer suggestion regexes — mirror the broader patterns used by the
# solution prover (solution/prover/tactics.py) which work against Isabelle2025
# where 'Try this:' is prefixed with the prover name (e.g. 'cvc5: Try this: by ...').
_BASELINE_TRY_THIS = re.compile(r"(?i)(?:try this:\s*)?(by\s+\([^)]+\)|by\s+\w+(?:\s+[^)\n]*)?)")
_BASELINE_TIMING_TAIL = re.compile(r"\s*\(\s*\d+(?:\.\d+)?\s*(?:ms|s)\s*\)?\s*$", re.IGNORECASE)

def _baseline_extract_finisher(blob: str) -> Optional[str]:
    """Return first plausible 'by ...' finisher in a flattened sledgehammer response."""
    seen = set()
    candidates: List[str] = []
    for m in _BASELINE_TRY_THIS.finditer(blob):
        cand = m.group(1).strip()
        cand = _BASELINE_TIMING_TAIL.sub("", cand).rstrip(",;").strip()
        if not cand or not cand.startswith("by "):
            continue
        if cand in seen:
            continue
        seen.add(cand)
        candidates.append(cand)
    if not candidates:
        return None
    # Prefer simple 'by simp/auto/blast' first, then anything else
    priority = ("by simp", "by auto", "by blast", "by force", "by fastforce")
    for p in priority:
        for c in candidates:
            if c == p or c.startswith(p + " "):
                return c
    return candidates[0]


def _baseline_verify_proof(isabelle, session: str, imports: str,
                           goal: str, proof: str) -> bool:
    """Re-run the candidate proof to confirm it actually closes the goal (no errors)."""
    thy = (
        f"theory ScratchV\n"
        f"  imports {imports}\n"
        f"begin\n"
        f'lemma baseline_verify: "{isa_escape(goal)}"\n'
        f"  {proof}\n"
        f"end\n"
    )
    tmpdir = tempfile.mkdtemp()
    try:
        with open(os.path.join(tmpdir, "ScratchV.thy"), "w", encoding="utf-8") as f:
            f.write(thy)
        resps = list(isabelle.use_theories(
            theories=["ScratchV"], session_id=session, master_dir=tmpdir,
        ))
        for r in resps:
            body = getattr(r, "response_body", None)
            if body is None:
                continue
            blob = str(body)
            # If Isabelle reports any error, the proof failed
            if re.search(r"(?i)\bkind=['\"]?error['\"]?", blob) or "Failed to apply" in blob:
                return False
        return True
    except Exception:
        return False
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def run_baseline_api(goals: List[str], isabelle, session: str,
                     imports: str, sledge_timeout: int,
                     trace: bool) -> List[Tuple[str, bool]]:
    """
    Sledgehammer-only baseline. Per goal:
      1. Run a .thy that invokes sledgehammer
      2. Flatten the entire response_body to str (matches solution-prover approach)
      3. Regex-extract candidate `by ...` finishers
      4. Verify the top candidate actually closes the goal
    """
    results = []
    for g in goals:
        t0 = time.monotonic()
        sledge_cmd = f"sledgehammer [timeout = {int(sledge_timeout)}]"
        thy = (
            f"theory Scratch\n"
            f"  imports {imports}\n"
            f"begin\n"
            f'lemma baseline_goal: "{isa_escape(g)}"\n'
            f"  {sledge_cmd}\n"
            f"  sorry\n"
            f"end\n"
        )
        proof = "  sorry"
        ok = False
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "Scratch.thy"), "w", encoding="utf-8") as f:
                f.write(thy)
            resps = list(isabelle.use_theories(
                theories=["Scratch"],
                session_id=session,
                master_dir=tmpdir,
            ))
            # Flatten every response_body to text and scan for finishers
            blob_parts: List[str] = []
            for r in resps:
                body = getattr(r, "response_body", None)
                if body is not None:
                    blob_parts.append(str(body))
            blob = "\n".join(blob_parts)
            cand = _baseline_extract_finisher(blob)
            if cand:
                if _baseline_verify_proof(isabelle, session, imports, g, cand):
                    proof = f"  {cand}"
                    ok = True
                elif trace:
                    print(f"  [baseline] candidate '{cand}' did not verify", file=sys.stderr)
        except Exception as e:
            if trace:
                print(f"  [baseline] error on '{g[:40]}': {e}", file=sys.stderr)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        elapsed = time.monotonic() - t0
        if trace:
            status = "✓" if ok else "✗"
            print(f"  baseline {status} ({elapsed:.1f}s): {g[:50]}")
        results.append((proof, ok))
    return results


# ─── Prover runner (drives prover.prove_goal from either baseline/ or solution/) ─

def run_prover(folder: str, goals: List[str], isabelle, session: str, model: str,
               timeout: int, trace: bool, label: Optional[str] = None) -> List[Tuple[str, bool]]:
    """
    Run prover.prove_goal from the given source folder ("baseline" or "solution")
    on each goal. Both folders share the same module layout so we can swap
    sys.path between phases.

    label: tag used in trace output (defaults to folder name).
    """
    tag = label or folder
    _clear_prover_modules()
    sys.path.insert(0, str(Path(__file__).parent / folder))
    try:
        from prover.prover import prove_goal
        results = []
        for g in goals:
            t0 = time.monotonic()
            try:
                res = prove_goal(
                    isabelle,
                    session,
                    g,
                    model_name_or_ensemble=model,
                    beam_w=3, max_depth=8, hint_lemmas=6,
                    timeout=timeout,
                    use_sledge=True, sledge_timeout=15, sledge_every=1,
                    use_qc=True, qc_timeout=3, qc_every=1,
                    use_np=False,
                    facts_limit=6, do_minimize=True, minimize_timeout=10,
                    do_variants=True, variant_timeout=6, variant_tries=12,
                    enable_reranker=False,
                    trace=trace, use_color=False,
                )
                steps = res.get("steps", [])
                ok = res.get("success", False)
            except Exception as e:
                if trace:
                    print(f"  [{tag}] error on goal '{g[:40]}': {e}", file=sys.stderr)
                proof, ok = "  sorry", False
            else:
                tactics = [
                    str(s) for s in steps
                    if not str(s).lstrip().startswith("lemma ")
                ]
                if ok and tactics:
                    proof = "  " + "\n  ".join(tactics)
                    last = tactics[-1].strip()
                    if not (last.startswith("by ") or last in ("done", "qed")):
                        proof += "\n  done"
                else:
                    proof = "  sorry"

            elapsed = time.monotonic() - t0
            if trace:
                status = "✓" if ok else "✗"
                print(f"  {tag} {status} ({elapsed:.1f}s): {g[:50]}")
            results.append((proof, ok))
        return results
    except Exception as e:
        print(f"[{tag}] Import failed: {e}", file=sys.stderr)
        print(f"[{tag}] Make sure isabelle is on PATH and OLLAMA_HOST is reachable.",
              file=sys.stderr)
        return [("  sorry", False)] * len(goals)
    finally:
        sys.path.pop(0)


def run_solution(goals: List[str], isabelle, session: str, model: str,
                 timeout: int, trace: bool) -> List[Tuple[str, bool]]:
    """Backwards-compat wrapper: run the solution-folder prover."""
    return run_prover("solution", goals, isabelle, session, model, timeout, trace,
                      label="solution")


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(exist_ok=True)

    print(f"Loading {args.n} goals from {args.goals_file}...")
    goals = load_goals(args.goals_file, args.n)
    print(f"  {len(goals)} goals loaded.\n")

    # ── Single Isabelle server for the entire comparison run ─────────────────
    from isabelle_client import start_isabelle_server, get_isabelle_client

    print("Starting Isabelle server...")
    server_info, proc = start_isabelle_server(name="comparison")
    print(f"  {server_info.strip()}")
    isabelle = get_isabelle_client(server_info)
    session = _extract_session_id(isabelle.session_start(session="HOL"))
    print(f"  session_id: {session}\n")

    try:
        # ── Baseline ────────────────────────────────────────────────────────
        if args.sledge_only_baseline:
            print(f"Running BASELINE (sledgehammer only, timeout={args.sledge_timeout}s)...")
            baseline_results = run_baseline_api(
                goals, isabelle, session, args.imports, args.sledge_timeout, args.trace
            )
        else:
            baseline_to = args.baseline_timeout if args.baseline_timeout is not None else args.timeout
            print(f"Running BASELINE (baseline/ prover, model={args.model}, timeout={baseline_to}s)...")
            baseline_results = run_prover(
                "baseline", goals, isabelle, session, args.model,
                baseline_to, args.trace, label="baseline",
            )

        baseline_blocks = []
        for i, (goal, (proof, ok)) in enumerate(zip(goals, baseline_results)):
            comment = "PROVED" if ok else "FAILED — no proof found"
            block = proof_block(lemma_name(i, goal), goal, proof, comment)
            baseline_blocks.append(block)

        baseline_thy = theory_file("Baseline_Results", args.imports, baseline_blocks)
        baseline_path = out_dir / "Baseline_Results.thy"
        baseline_path.write_text(baseline_thy)
        n_base = sum(1 for _, ok in baseline_results if ok)
        print(f"  Baseline: {n_base}/{len(goals)} proved → {baseline_path}\n")

        # ── Solution ─────────────────────────────────────────────────────────
        print(f"Running SOLUTION (model={args.model}, timeout={args.timeout}s)...")
        solution_results = run_solution(
            goals, isabelle, session, args.model, args.timeout, args.trace
        )

        solution_blocks = []
        for i, (goal, (proof, ok)) in enumerate(zip(goals, solution_results)):
            comment = "PROVED" if ok else "FAILED — no proof found"
            block = proof_block(lemma_name(i, goal), goal, proof, comment)
            solution_blocks.append(block)

        solution_thy = theory_file("Solution_Results", args.imports, solution_blocks)
        solution_path = out_dir / "Solution_Results.thy"
        solution_path.write_text(solution_thy)
        n_sol = sum(1 for _, ok in solution_results if ok)
        print(f"  Solution: {n_sol}/{len(goals)} proved → {solution_path}\n")

        # ── Summary ──────────────────────────────────────────────────────────
        print("=" * 60)
        print(f"RESULTS SUMMARY ({len(goals)} goals)")
        print("=" * 60)
        print(f"{'Goal':<45}  {'Baseline':>8}  {'Solution':>8}")
        print("-" * 65)
        for goal, (_, b_ok), (_, s_ok) in zip(goals, baseline_results, solution_results):
            b = "PROVED" if b_ok else "failed"
            s = "PROVED" if s_ok else "failed"
            print(f"  {goal[:43]:<43}  {b:>8}  {s:>8}")
        print("-" * 65)
        print(f"  {'TOTAL':<43}  {n_base:>5}/{len(goals)}  {n_sol:>5}/{len(goals)}")
        print()
        print(f"Theory files written to {out_dir}/")
        print(f"  Load in Isabelle: isabelle jedit -d {out_dir} {baseline_path.name}")

        # Write ROOT so both theories form a session
        root = (out_dir / "ROOT")
        root.write_text(
            "session Comparison = HOL +\n"
            "  options [quick_and_dirty]\n"  # allow `sorry` for unproved goals
            "  theories\n"
            "    Baseline_Results\n"
            "    Solution_Results\n"
        )
        print(f"  Or build session: isabelle build -d {out_dir} Comparison")

    finally:
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    main()
