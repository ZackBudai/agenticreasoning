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
                   help="Per-goal timeout in seconds (default: 60)")
    p.add_argument("--out-dir", default="comparison",
                   help="Output directory (default: comparison/)")
    p.add_argument("--imports", default="Main",
                   help="Isabelle imports (default: Main)")
    p.add_argument("--sledge-timeout", type=int, default=30,
                   help="Sledgehammer timeout per goal in seconds (default: 30)")
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

def run_baseline_api(goals: List[str], isabelle, session: str,
                     imports: str, sledge_timeout: int,
                     trace: bool) -> List[Tuple[str, bool]]:
    """
    Sledgehammer-only baseline using the provided Isabelle client and session.
    Builds a small theory per goal with a sledgehammer call and looks for
    'Try this: by ...' suggestions in the response messages.
    """
    results = []
    for g in goals:
        t0 = time.monotonic()
        sledge_cmd = f"sledgehammer (timeout: {sledge_timeout})"
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
            p = os.path.join(tmpdir, "Scratch.thy")
            with open(p, "w", encoding="utf-8") as f:
                f.write(thy)
            resps = list(isabelle.use_theories(
                theories=["Scratch"],
                session_id=session,
                master_dir=tmpdir,
            ))
            # Sledgehammer suggestions appear as writeln messages inside nodes
            for r in resps:
                body = getattr(r, "response_body", None)
                if body is None:
                    continue
                if not isinstance(body, dict):
                    try:
                        body = body.dict() if hasattr(body, "dict") else {}
                    except Exception:
                        body = {}
                # Check top-level messages (some builds) AND nodes[*].messages
                all_msgs = list(body.get("messages") or [])
                for node in (body.get("nodes") or []):
                    all_msgs.extend(node.get("messages") or [])
                for msg in all_msgs:
                    txt = str(msg.get("message", "")) if isinstance(msg, dict) else str(msg)
                    m = re.search(r"Try this:\s*(by\s+\S.*?)(?:\s*\(|$)", txt)
                    if m:
                        proof = f"  {m.group(1).strip()}"
                        ok = True
                        break
                if ok:
                    break
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


# ─── Solution runner (full prover + planner, no server management) ───────────

def run_solution(goals: List[str], isabelle, session: str, model: str,
                 timeout: int, trace: bool) -> List[Tuple[str, bool]]:
    """
    Run the solution prover (with LLM + all improvements) on each goal.
    Uses the provided Isabelle client and session — no server start/stop.
    """
    _clear_prover_modules()
    sys.path.insert(0, str(Path(__file__).parent / "solution"))
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
                # Strip the seed `lemma "..."` line the prover prepends — proof_block()
                # re-emits the lemma declaration itself, so keeping it here would
                # produce a duplicate `lemma "..."` inside the proof body (syntax error).
                tactic_steps = [
                    str(s) for s in steps
                    if not str(s).lstrip().startswith("lemma ")
                ]
                if ok and tactic_steps:
                    proof = "  " + "\n  ".join(s.strip() for s in tactic_steps)
                    last = tactic_steps[-1].strip()
                    if not (last.startswith("by ") or last in ("done", "qed")):
                        proof += "\n  done"
                else:
                    # No tactics returned, or prover did not succeed — emit sorry
                    # so the .thy file is at least syntactically valid.
                    proof = "  sorry"
                    ok = False
            except Exception as e:
                if trace:
                    print(f"  [solution] error on goal '{g[:40]}': {e}", file=sys.stderr)
                proof, ok = "  sorry", False

            elapsed = time.monotonic() - t0
            if trace:
                status = "✓" if ok else "✗"
                print(f"  solution {status} ({elapsed:.1f}s): {g[:50]}")
            results.append((proof, ok))
        return results
    except Exception as e:
        print(f"[solution] Import failed: {e}", file=sys.stderr)
        print("[solution] Make sure isabelle is on PATH and OLLAMA_HOST is reachable.",
              file=sys.stderr)
        return [("  sorry", False)] * len(goals)
    finally:
        sys.path.pop(0)


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
        print(f"Running BASELINE (sledgehammer only, timeout={args.sledge_timeout}s)...")
        baseline_results = run_baseline_api(
            goals, isabelle, session, args.imports, args.sledge_timeout, args.trace
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
