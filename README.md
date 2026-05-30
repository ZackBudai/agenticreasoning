# agenticreasoning

An LLM-powered agent that drives **Isabelle/HOL** to prove theorems automatically.

This is the implementation for the **3806ICT Logic and Automated Reasoning** (Griffith University) Assignment 2, 2026. The system combines a stepwise tactic prover with an Isar proof-outline planner that performs **CEGIS-style iterative proof repair**, and is benchmarked against a frozen reference implementation.

Reference upstream: [`zhehou/llm-isabelle`](https://github.com/zhehou/llm-isabelle) (MIT). See [`UPSTREAM.md`](UPSTREAM.md) for the per-file modification status.

---

## Architecture at a glance

```
┌────────────────────┐         ┌──────────────────────────┐
│  baseline/  (FROZEN)│        │  solution/  (OUR WORK)    │
│  upstream copy      │        │  modified prover+planner  │
│  reference numbers  │  ←──→  │  F1–F29 fixes applied     │
└────────────────────┘         └──────────────────────────┘
        ▲                                    ▲
        │                                    │
        └────────┬───────────────────────────┘
                 │
        ┌────────┴────────┐
        │  compare.py     │  prover head-to-head (lists/logic/nat/sets)
        │  plan_compare.sh│  planner head-to-head (hard_25/mid_25/…)
        │  run_sweep.sh   │  multi-dataset compare.py sweep
        └─────────────────┘
```

The repo contains two complete copies of the system:

- **`baseline/`** — frozen upstream snapshot. **Never modified.** Produces the reference numbers.
- **`solution/`** — our working implementation with all improvements.

Both folders share the same module layout (`prover/`, `planner/`, `datasets/`, etc.), so the comparison harnesses can swap `sys.path` between them and exercise identical APIs.

### 1. Stepwise prover — `solution/prover/`

LLM proposes tactics; the prover beam-searches them with feedback from `nitpick`, `quickcheck`, and `sledgehammer`. ML reranker scores candidate tactics; bi/cross-encoder premise selection narrows the fact set.

Key entry point: `prover.prover.prove_goal(...)`.

### 2. Isar planner — `solution/planner/`

LLM generates a **structured Isar proof outline** (induction/cases/helper facts, possibly with `sorry` placeholders). The driver then:

1. **Fast-path**: tries canned finishers (`by blast`/`auto`/`simp`/…) and the stepwise prover directly. Many propositional / first-order goals close in <1s.
2. **Fill**: for each `sorry`, extracts the exact subgoal context (assumptions + goal) and asks the prover for a replacement.
3. **CEGIS repair** (`planner/repair.py`): on failure, staged edits from small to large — block → subproof → whole proof. After every repair, Fill is re-run on any newly introduced sorrys.

Key entry point: `planner.driver.plan_and_fill(...)`.

### The CEGIS repair loop

```
   ┌──────────────────────────────────────────────────────┐
   │ outline (LLM)                                         │
   │   │                                                   │
   │   ▼                                                   │
   │ Isabelle: any sorry left? any error?                  │
   │   │                                                   │
   │   ├─ all clean ───────────────────────────► SUCCESS  │
   │   │                                                   │
   │   ├─ earliest failure = sorry  →  Fill                │
   │   │                                                   │
   │   └─ earliest failure = non-sorry  →  Repair (stage 1)│
   │              │                                        │
   │              ├─ have/show block edit                  │
   │              ├─ enclosing subproof / case edit        │
   │              └─ whole-proof regeneration              │
   │              (after each: re-run Fill on new sorrys)  │
   │                                                       │
   │  Budgets: per-hole / per-stage / hard wall-clock      │
   └──────────────────────────────────────────────────────┘
```

All four budget layers are enforced — Fill, repair stages, fresh-outline regeneration, and a hard global deadline (`Deadline` in `solution/planner/budget.py`).

---

## Setup

### Requirements

- **Isabelle/HOL 2025** — `isabelle` must be on `$PATH`.
- **Ollama** (or another supported backend) reachable at `OLLAMA_HOST` (default `http://localhost:11434`).
- **Python 3.10–3.12** recommended (3.13 breaks some PyTorch packages — see `solution/requirements.txt`).

### Install

```bash
cd solution
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# CPU-only PyTorch (skip if you have a CUDA build already)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Optional: premise-selection model training
pip install -U sentence-transformers datasets
```

Repeat the same `pip install -r requirements.txt` inside `baseline/` if you want to run baseline benchmarks too.

### LLM backends

Configure via the model-string prefix passed to `--model`:

| Backend | Model string example | Env vars |
|---|---|---|
| Ollama (local) | `ollama:qwen2.5-coder:7b` | `OLLAMA_MODEL`, `OLLAMA_HOST`, `OLLAMA_TIMEOUT_S` |
| Gemini CLI | `gemini:gemini-3-flash-preview` | `GEMINI_API_KEY` |
| Hugging Face | `hf:meta-llama/Llama-3.1-8B-Instruct` | (model-dependent) |

Set `LLM_DEBUG=1` for verbose prompt/response logging, `DEBUG_VERIFY=1` for strict-verifier diagnostics in the planner.

---

## Running things

All paths below assume you're running from the repo root with the venv active.

### Prover — single goal

```bash
cd solution && python -m prover.cli \
  --goal 'rev (rev xs) = xs' \
  --model 'ollama:qwen2.5-coder:7b' \
  --beam 3 --max-depth 8 \
  --sledge --quickcheck --nitpick \
  --facts-limit 6 --variants
```

### Prover — dataset benchmark

```bash
cd solution && python -m prover.experiments bench --suite lists
```

### Planner — single goal (plan + fill + repair)

```bash
cd solution && python -m planner.cli \
  --timeout 60 --mode auto \
  --model 'ollama:qwen2.5-coder:7b' \
  "rev (rev xs) = xs"
```

Other modes: `--mode outline` (sketch only — no Fill/Repair), `--diverse-outlines --k 3 --temps "0.35,0.55,0.85"` (sample several outlines and pick the best).

### Planner — dataset benchmark

```bash
cd solution && python -m planner.experiments bench \
  --file datasets/lists.txt \
  --mode auto --diverse --k 3 --temps "0.35,0.55,0.85" \
  --timeout 120 --strict-no-sorry --verify \
  --model 'ollama:qwen2.5-coder:7b'
```

`--strict-no-sorry` requires the final proof to have zero `sorry`s; `--verify` runs the strict verifier on the assembled proof.

### Baseline — prover benchmark

The baseline prover is exercised through the same `prover.experiments bench` entry point that the comparison harnesses use:

```bash
cd baseline && source .venv/bin/activate && \
python -m prover.experiments bench \
  --file datasets/hol_main_easy_goals_test.txt \
  --model 'ollama:qwen2.5-coder:7b' \
  --timeout 60 --sledge --sledge-timeout 30
```

For head-to-head comparison use `compare.py` (prover) or `plan_compare.sh` (planner) from the repo root — those swap `sys.path` between `baseline/` and `solution/` automatically.

---

## Comparison harnesses

These run the same workload against `baseline/` and `solution/` and emit a side-by-side summary.

### `compare.py` — **prover** head-to-head

Drives `prover.prove_goal` from each folder on the same goals. Emits `comparison/Baseline_Results.thy`, `comparison/Solution_Results.thy`, and a ROOT for `isabelle build`.

```bash
python compare.py \
  --goals-file solution/datasets/lists.txt --n 5 \
  --model 'ollama:qwen2.5-coder:32b' \
  --timeout 120 --baseline-timeout 30 --sledge-timeout 30 \
  --out-dir comparison --trace
```

**Caveat:** `compare.py` exercises *only* the prover. For planner numbers use `plan_compare.sh` (below).

### `run_sweep.sh` — multi-dataset prover sweep

Loops `compare.py` across curated and/or test datasets, then aggregates a `summary.{csv,md}`.

```bash
./run_sweep.sh curated     # lists/logic/nat/sets
./run_sweep.sh tests       # hol_main_{easy,mid,hard}_goals_test.txt
./run_sweep.sh all         # both

# Override defaults
MODEL=ollama:qwen2.5-coder:32b TIMEOUT=120 BASELINE_TIMEOUT=30 ./run_sweep.sh curated
```

### `plan_compare.sh` — **planner** head-to-head

Runs `planner.experiments bench` from both `baseline/` and `solution/` and aggregates a `planner_comparison/summary.{csv,md}`.

```bash
./plan_compare.sh                                  # default: datasets_subset/hard_25.txt
MODEL=ollama:qwen2.5-coder:7b TIMEOUT=180 K=3 \
  ./plan_compare.sh datasets_subset/mid_25.txt
```

For the long assignment sweep there's a copy-paste runbook in [`../SWEEP_RUNBOOK.md`](../SWEEP_RUNBOOK.md) with launch commands, a live progress watcher (`watch_sweep`), and post-run archival steps.

---

## Results

### Prover comparison — curated suites
`ollama:qwen2.5-coder:7b`, solution-timeout=120s, baseline-timeout=30s (see [`comparison/summary.md`](comparison/summary.md)):

| Dataset | Goals | Baseline | Solution |
|---|---:|---:|---:|
| lists | 18 | 0 | 17 |
| logic | 5  | 0 | 5  |
| nat   | 9  | 0 | 4  |
| sets  | 8  | 0 | 8  |
| **Total** | **40** | **0** | **34** |

The baseline scores zero across every suite due to a Pydantic-decode bug in `isabelle_client ≥ 1.0` that the solution patches in `solution/prover/isabelle_api.py:_decode_body_to_dict`. Documented in [`AI_LOG.md`](AI_LOG.md) Entry 7.

### Planner comparison — hard_25
`hard_25.txt` (25 goals), K=3, T=180s, `ollama:qwen2.5-coder:7b`, strict-no-sorry (see [`planner_comparison/summary.md`](planner_comparison/summary.md)):

| Dataset | Goals | Baseline | Solution |
|---|---:|---:|---:|
| hard_25.txt | 25 | 0 | **22** |

Milestone snapshots of earlier fix stages are archived under `planner_comparison_*/summary.md`.

### Planner+prover — 300-goal HOL Main sweep (end-to-end)
`ollama:qwen2.5-coder:7b`, T=120s, strict-no-sorry+verify (see `report_metric_sweep_20260528-0204/summary.md`):

| Dataset | Goals | Baseline | Solution |
|---|---:|---:|---:|
| hol_main_easy | 100 | 0 | 75 |
| hol_main_mid  | 100 | 0 | 83 |
| hol_main_hard | 100 | 0 | 67 |
| **Total** | **300** | **0** | **225** |

### Prover-only — 300-goal HOL Main sweep
`ollama:qwen2.5-coder:7b`, T=120s (baseline T=60s), via `compare.py` harness (see `solution/datasets/results/`):

| Dataset | Goals | Baseline | Solution |
|---|---:|---:|---:|
| hol_main_easy | 100 | 0 | 72 |
| hol_main_mid  | 100 | 0 | 71 |
| hol_main_hard | 100 | 0 | 56 |
| **Total** | **300** | **0** | **199** |

---

## Key improvements

Detailed in [`AI_LOG.md`](AI_LOG.md) Entries 7–15. Headline list:

| # | What |
|---|---|
| F1 | Hard per-goal deadline enforcement (`Deadline`); Fill capped at 50% of remaining budget. |
| F2 | Unified strict verifier (`strict_verify_responses`) shared between Fill, repair, and the bench. |
| F3 | Re-run Fill after every repair edit on newly introduced `sorry`s. |
| F4 | Earliest-failure pivot — driver picks the span containing the first Isabelle error. |
| F5 | Per-stage round caps inside `try_cegis_repairs` (no implicit stage chaining). |
| F6 | Prune stale `repair_progress` entries when spans change. |
| F7 | Explicit cap on fresh-outline regenerations (`_MAX_FRESH_OUTLINES = 2`). |
| F8 | Store original LLM block in memo, not the sorry-injected version (no biased prompts). |
| F11 | Hybrid fast-path: canned finishers + direct prover call before outline generation. |
| F12 | Prover `try_finish` cross-checks `finished_ok` against the strict verifier. |
| F13 | **Load-bearing fix:** strict verifier now reads FINISHED-frame bodies the way `finished_ok` does (the previous protocol-mismatched implementation silently rejected every correct proof). |
| F14 | Deadline bail-out in outline diversity-scoring loop (prevents unbounded pre-Fill spend). |
| F15 | Bounded sketch check — skeleton validity gates before Fill is invoked. |
| F16 | Viable-LLM-call floor — guarantees the driver always has budget for at least one real attempt. |
| F17 | 1.2× wall-clock cap on total planner time; outline placeholder gate rejects degenerate skeletons early. |
| F18–F20 | Card/sum fast-path finishers; `suggest_common_lemmas` extended with cardinality and sum lemma families. |
| F21–F23 | Hand-crafted Isar templates for induction-over-sets goals (card partition, sum over indicator, etc.); template resilience for partial matches. |
| F24–F26 | LLM-call floor/ceiling (30–60 s per hole); legacy driver-path coverage; content-bug fixes (argument order in `from`, extraneous `using` in card_cartesian_product). |
| F27 | HOL-corpus RAG: `extract_hol.py` mines 471 K HOL/AFP names; env-gated unknown-reference validator (`USE_NAME_VALIDATOR=1`). |
| F28 | Widened placeholder regex catches `"..."` / TODO markers; `_count_balance_issues` detects malformed proof structure; `classify_failures.py` post-mortem classifier. |
| F29 | Type-annotation retry wraps free variables as `(_::nat\|int\|real)` on tactic failure; early bail when first Fill makes zero progress on a large outline past 50% budget. |

---

## Repository layout

```
agenticreasoning/
├── README.md                this file
├── CLAUDE.md                build/run guidance for Claude Code (and humans)
├── UPSTREAM.md              per-file upstream-vs-modified status
├── AI_LOG.md                generative-AI usage log (required for assignment appendix)
│
├── compare.py               prover head-to-head harness
├── plan_compare.sh          planner head-to-head wrapper
├── run_sweep.sh             multi-dataset compare.py sweep
├── generate_scripts.py      offline .thy generator (no Isabelle round-trip)
├── rerun_baseline.py        regenerate baseline results on an existing comparison dir
│
├── datasets_subset/         curated subsets for the assignment sweeps
│   ├── hard_25.txt
│   ├── mid_25.txt
│   ├── smoke_f11.txt
│   └── smoke_goal2_only.txt
│
├── comparison/              compare.py outputs (per-area subfolders + summary)
├── planner_comparison/      current plan_compare.sh output
├── planner_comparison_*/    archived plan_compare.sh snapshots per fix milestone
│
├── baseline/                FROZEN upstream copy — never modify
│   ├── planner/  prover/  datasets/  baselines/  isabelle_ui/  logs/
│   └── requirements.txt
│
└── solution/                working implementation
    ├── planner/
    │   ├── driver.py          plan_and_fill() — Fast-path → Fill → Repair → fresh outline
    │   ├── skeleton.py        LLM outline generation + diversity sampling
    │   ├── repair.py          CEGIS repair: try_cegis_repairs(), staged edits
    │   ├── repair_inputs.py   hole detection, error parsing, state extraction
    │   ├── goals.py           strict_verify_responses(), full-proof verification
    │   ├── budget.py          Deadline helper (F1)
    │   ├── extract.py         AFP corpus mining for micro-RAG
    │   ├── priors.py          Isar prior aggregation + hint lexicon
    │   └── prompts.py         outline / repair LLM templates
    ├── prover/
    │   ├── prover.py          beam-search tactic loop
    │   ├── isabelle_api.py    Isabelle server API (+ Pydantic-V2 decode shim)
    │   ├── llm.py             multi-backend LLM routing
    │   ├── ranker.py          XGBoost/AWR/DQN tactic reranker
    │   ├── premises.py        bi-encoder + cross-encoder premise selection
    │   ├── heuristics.py      nitpick / quickcheck / sledgehammer
    │   └── …
    ├── baselines/             sledgehammer-only baselines
    ├── datasets/              goal files (lists/logic/nat/sets, hol_main_*, MiniF2F, PutnamBench)
    ├── isabelle_ui/           jEdit HTTP server + .bsh macros for GUI integration
    └── logs/                  attempts.log.jsonl, runs.log.jsonl
```

---

## Documentation map

| Document | What's in it |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Build/run guidance, full code-structure walkthrough, WIP feature pointers |
| [`UPSTREAM.md`](UPSTREAM.md) | Per-file `upstream` / `modified` / `replaced` status for the whole `solution/` tree |
| [`AI_LOG.md`](AI_LOG.md) | All generative-AI interactions used to build this (required for the assignment report appendix) |
| [`../SWEEP_RUNBOOK.md`](../SWEEP_RUNBOOK.md) | Copy-paste commands for the long assignment-flavor sweep + live progress watcher |
| `comparison/summary.md` | Latest prover comparison numbers |
| `planner_comparison*/summary.md` | Planner comparison snapshots per fix milestone (through final) |

---

## Assignment requirements (3806ICT)

- Report in LNCS format, ≤8 pages + appendix.
- All generative-AI interactions documented in [`AI_LOG.md`](AI_LOG.md).
- Generative AI **not** used for writing the report itself.
- All libraries and non-original code cited.
- Datasets balanced across easy and hard formulae; provenance documented.

## Licence

Upstream code from `zhehou/llm-isabelle` is MIT-licensed. See [`UPSTREAM.md`](UPSTREAM.md) for what is/isn't original.
