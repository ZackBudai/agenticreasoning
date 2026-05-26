#!/usr/bin/env python3
"""
rerun_baseline.py — Re-run ONLY the sledgehammer baseline against the given
                    datasets, using compare.py's patched parser. Overwrites
                    <out-dir>/<dataset>/baseline_results.thy and emits
                    <out-dir>/<dataset>/baseline.json with verified counts.

This is separate from compare.py so we can repair a half-done sweep without
spending hours re-running the LLM-driven solution prover.

Usage:
    python rerun_baseline.py FILE [FILE ...] [--imports Main]
                             [--sledge-timeout 30] [--out-dir comparison]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List

# Reuse the patched helpers from compare.py
from compare import (
    _extract_session_id,
    isa_escape,
    lemma_name,
    proof_block,
    theory_file,
    load_goals,
    run_baseline_api,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="+", help="Goal files (one goal per line)")
    p.add_argument("--imports", default="Main")
    p.add_argument("--sledge-timeout", type=int, default=30)
    p.add_argument("--out-dir", default="comparison")
    p.add_argument("--trace", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_root = Path(args.out_dir)
    out_root.mkdir(exist_ok=True)

    from isabelle_client import start_isabelle_server, get_isabelle_client

    print("Starting Isabelle server...")
    server_info, proc = start_isabelle_server(name="baseline_rerun")
    isabelle = get_isabelle_client(server_info)
    session = _extract_session_id(isabelle.session_start(session="HOL"))
    print(f"  session_id: {session}\n")

    try:
        for path in args.files:
            base = Path(path).stem
            out_dir = out_root / base
            out_dir.mkdir(exist_ok=True)
            goals = load_goals(path, n=10**9)
            print(f"── {base}: {len(goals)} goals")
            t0 = time.monotonic()
            results = run_baseline_api(
                goals, isabelle, session,
                args.imports, args.sledge_timeout, args.trace,
            )

            blocks = []
            proved = 0
            details = []
            for i, (goal, (proof, ok)) in enumerate(zip(goals, results)):
                comment = "PROVED" if ok else "FAILED — no proof found"
                blocks.append(proof_block(lemma_name(i, goal), goal, proof, comment))
                if ok: proved += 1
                details.append({"goal": goal, "ok": ok, "proof": proof.strip()})

            (out_dir / "baseline_results.thy").write_text(
                theory_file("Baseline_Results", args.imports, blocks)
            )
            (out_dir / "baseline.json").write_text(json.dumps({
                "dataset": base,
                "n_goals": len(goals),
                "proved": proved,
                "results": details,
            }, indent=2))
            elapsed = time.monotonic() - t0
            print(f"  → {proved}/{len(goals)} proved in {elapsed:.0f}s\n")
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    main()
