# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a 3806ICT (Logic and Automated Reasoning, Griffith University) group assignment to build an **LLM-powered agent that interacts with the Isabelle/HOL theorem prover** to perform automated reasoning tasks.

The reference implementation to build on (or study for design guidance) is: https://github.com/zhehou/llm-isabelle

## Assignment Goals

The system has two main components:

### 1. Stepwise Prover (`prover/` folder)
- LLM guesses tactics
- Combined with `nitpick`, `quickcheck`, and `sledgehammer`
- Beam search for suitable tactics
- ML reranker for tactics
- Premise selection using encoders and transformers

### 2. Isar-style Proof Outline Generator / Planner (`planner/` folder)
- LLM generates a structured Isar proof outline (induction, cases, helper facts; may include `sorry` placeholders)
- Micro RAG extracted from AFP (Archive of Formal Proofs)
- Calls the stepwise prover to fill in details
- **CEGIS-style iterative proof repair** (this is the main WIP feature to implement)

## CEGIS Proof Repair Loop (WIP Design)

The repair procedure to implement:

1. Generate initial proof outline with LLM. Easy goals may be solved directly (e.g., `by simp`); harder goals use structured Isar with `sorry` placeholders.
2. Run Isabelle on the candidate script. If it passes with no `sorry`, done.
3. Always focus on the **earliest failure point** (first error Isabelle reports) — keeps the procedure deterministic.
4. If the earliest failure is a `sorry`: trigger **Fill** — extract the exact subgoal context at that location (assumptions + goal), call the stepwise prover to produce a replacement fragment, replace the `sorry`, re-run Isabelle. Continue top-down until all holes are solved or one cannot be filled.
5. If Fill cannot solve a hole, or Isabelle fails at a non-hole line: trigger **Repair** (staged from small to large edits):
   - Edit the specific `have`/`show` block
   - Edit the enclosing subproof (a case branch or inner `proof ... qed`)
   - Edit the full proof
   - After any repair edit, run Fill again on newly introduced `sorry` placeholders, then re-check with Isabelle.
6. A repair attempt fails if it cannot be verified (no `sorry`) or introduces holes Fill cannot discharge.
7. Use simple budgets: a small number of attempts per repair stage before escalating, and a global timeout. Optionally maintain a few alternative candidate scripts and prefer those that verify further or reduce remaining holes.

## Evaluation Requirements

- Find or generate benchmark datasets (balanced: easy and hard formulae)
- Compare against the baseline (the reference repo as-is)
- Document dataset generation or cite online sources

## Report Requirements (LNCS format, ≤8 pages + appendix)

- Abstract (≤500 words), Introduction, Related Work, Implementation & Experiments, Discussion/Conclusion
- Document all generative AI usage in an Appendix (queries + responses)
- Do **not** use generative AI for writing
- Cite all libraries and code not developed by yourselves

## Setup & Commands

All development work goes in `solution/`. The `baseline/` folder is a frozen reference copy — never modify it. Run all commands from within the relevant subfolder (`cd solution/` or `cd baseline/`).

```bash
# Python environment (3.10–3.12 only; 3.13 breaks some PyTorch packages)
cd solution
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install -r requirements.txt

# For CPU-only PyTorch
pip install torch --index-url https://download.pytorch.org/whl/cpu

# For premise selection training
pip install -U sentence-transformers datasets
```

Isabelle/HOL must be installed and `isabelle` on `$PATH` (tested with Isabelle2025).

### LLM Backends

Configure via model string prefix:
- **Ollama (local):** `"qwen3-coder:30b"` or `"ollama:model-name"`
- **Gemini CLI:** `"gemini:gemini-3-flash-preview"`
- **Hugging Face:** `"hf:meta-llama/Llama-3.1-8B-Instruct"`

Key env vars: `OLLAMA_MODEL`, `OLLAMA_HOST`, `GEMINI_API_KEY`, `LLM_DEBUG=1`

### Running the Prover

```bash
# Quick demo
python -m prover.cli

# Single goal
python -m prover.cli --goal 'rev (rev xs) = xs' --model 'gemini:gemini-3-flash-preview'

# With all features
python -m prover.cli --goal 'rev (rev xs) = xs' \
  --model 'qwen3-coder:30b' --beam 3 --max-depth 8 \
  --sledge --quickcheck --nitpick --facts-limit 6 --variants

# Benchmark a dataset file
python -m prover.experiments bench --suite lists
```

### Running the Planner

```bash
# Plan + fill holes (CEGIS mode)
python -m planner.cli --timeout 60 --mode auto "rev (rev xs) = xs"

# Sketch outline only
python -m planner.cli --timeout 60 --mode outline "map f (xs @ ys) = map f xs @ map f ys"

# With diverse outlines
python -m planner.cli --timeout 60 --diverse-outlines --k 3 --temps "0.35,0.55,0.85" --mode auto "..."

# Benchmark
python -m planner.experiments bench --file datasets/lists.txt \
  --mode auto --diverse --k 3 --timeout 120 --strict-no-sorry --verify \
  --model 'qwen3-coder:30b'
```

### Baseline prover

Run the baseline prover the same way compare.py exercises it (from `baseline/`):

```bash
cd baseline
python -m prover.experiments bench --suite lists \
  --model 'ollama:qwen2.5-coder:7b' --timeout 30 --sledge --sledge-timeout 30
```

`sledge_only.py` is a standalone Isabelle-build script that bypasses the prover stack entirely and was not used for the comparison results.

### Training the Reranker

```bash
python -m prover.train_reranker --algo xgb-classifier --target bandit
python -m prover.train_reranker --algo awr --tau 0.6 --epochs 8 --batch 1024
```

### Training Premise Selection Models

```bash
python -m prover.train_premises --logs-glob 'logs/magnus_shards/shard_*' --out models \
  --train-bi --base-model sentence-transformers/all-MiniLM-L6-v2 --epochs 1 --batch-size 32
```

## Code Structure

All paths below are relative to `solution/`.

```
prover/          # Stepwise tactic prover
  isabelle_api.py  # Low-level Isabelle server API
  prover.py        # Beam-search tactic loop
  llm.py           # Multi-backend LLM routing (Ollama/Gemini/HF)
  ranker.py        # ML tactic reranker (XGBoost/AWR/DQN)
  premises.py      # Bi-encoder + cross-encoder premise selection
  features.py      # Feature extraction for reranker
  heuristics.py    # Nitpick/quickcheck/sledgehammer fallbacks

planner/         # Isar proof outline planner (WIP: Fill + CEGIS repair)
  driver.py        # Top-level plan_and_fill() — orchestrates outline→fill→repair loop
  skeleton.py      # LLM outline generation + diversity sampling
  repair.py        # CEGIS repair: try_cegis_repairs(), staged block/subproof/whole-proof edits
  repair_inputs.py # Helpers: hole detection, error parsing, Isabelle state extraction
  extract.py       # AFP corpus mining for micro-RAG
  priors.py        # Isar prior aggregation + hint lexicon generation
  prompts.py       # LLM prompt templates for outline and repair

datasets/        # Goal files (.txt), benchmark datasets (mini_f2f, putnambench)
logs/            # Training logs (attempts.log.jsonl, runs.log.jsonl)
baselines/       # Sledgehammer-only baseline
isabelle_ui/     # jEdit HTTP server + .bsh macros for GUI integration
```

## WIP Features

According to the reference repo README, these two planner features are incomplete and need to be properly implemented:
- **Fill** (`planner/driver.py:_fill_one_hole`) — call the stepwise prover on a `sorry` hole's subgoal context to produce a replacement fragment
- **CEGIS-style iterative proof repair** (`planner/repair.py:try_cegis_repairs`, `planner/driver.py:plan_and_fill`) — the staged repair loop described above

The core prover (`prover/`) and outline generation (`planner/skeleton.py`) are functional.
