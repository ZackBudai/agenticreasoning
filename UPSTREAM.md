# Upstream Files

All files below were taken verbatim from https://github.com/zhehou/llm-isabelle (MIT licence).

- `baseline/` — frozen copy; never modify.
- `solution/` — working copy; update the status column below as files are changed.

**Status legend**
- `upstream` — unchanged from source repo
- `modified` — original file extended or patched
- `replaced` — rewritten from scratch; no longer tracks upstream

---

## baselines

| File | Status |
|------|--------|
| `solution/baselines/sledge_only.py` | upstream |

## datasets

| File | Status |
|------|--------|
| `solution/datasets/hol_extract_goals.py` | upstream |
| `solution/datasets/hol_main_easy_goals.txt` | upstream |
| `solution/datasets/hol_main_easy_goals_test.txt` | upstream |
| `solution/datasets/hol_main_hard_goals.txt` | upstream |
| `solution/datasets/hol_main_hard_goals_test.txt` | upstream |
| `solution/datasets/hol_main_mid_goals.txt` | upstream |
| `solution/datasets/hol_main_mid_goals_test.txt` | upstream |
| `solution/datasets/hol_route_by_imports.py` | upstream |
| `solution/datasets/json2goals.py` | upstream |
| `solution/datasets/lists.txt` | upstream |
| `solution/datasets/logic.txt` | upstream |
| `solution/datasets/magnus2attempts.py` | upstream |
| `solution/datasets/mini_f2f/MiniF2F_Base.thy` | upstream |
| `solution/datasets/mini_f2f/ROOT` | upstream |
| `solution/datasets/mini_f2f/mini_f2f_test.txt` | upstream |
| `solution/datasets/mini_f2f/mini_f2f_validation.txt` | upstream |
| `solution/datasets/nat.txt` | upstream |
| `solution/datasets/putnambench/PutnamBench_Base.thy` | upstream |
| `solution/datasets/putnambench/ROOT` | upstream |
| `solution/datasets/putnambench/putnambench_goals.txt` | upstream |
| `solution/datasets/sample_goals.py` | upstream |
| `solution/datasets/sets.txt` | upstream |
| `solution/datasets/thys2goal.py` | upstream |

## isabelle_ui

| File | Status |
|------|--------|
| `solution/isabelle_ui/LLM_PlanFill.bsh` | upstream |
| `solution/isabelle_ui/LLM_PlanOutline.bsh` | upstream |
| `solution/isabelle_ui/LLM_Prove.bsh` | upstream |
| `solution/isabelle_ui/server.py` | upstream |

## logs

| File | Status |
|------|--------|
| `solution/logs/attempts.log-hol-all.jsonl` | upstream |
| `solution/logs/filter_positive_planner_logs.py` | upstream |
| `solution/logs/log_proof_parser.py` | upstream |
| `solution/logs/planner_log_stats.py` | upstream |
| `solution/logs/runs.log-hol-all.jsonl` | upstream |
| `solution/logs/split_json.py` | upstream |

## planner

| File | Status |
|------|--------|
| `solution/planner/__init__.py` | upstream |
| `solution/planner/cli.py` | upstream |
| `solution/planner/driver.py` | modified |
| `solution/planner/experiments.py` | upstream |
| `solution/planner/extract.py` | upstream |
| `solution/planner/goals.py` | modified |
| `solution/planner/priors.py` | upstream |
| `solution/planner/prompts.py` | modified |
| `solution/planner/repair.py` | modified |
| `solution/planner/repair_inputs.py` | upstream |
| `solution/planner/skeleton.py` | modified |

## prover

| File | Status |
|------|--------|
| `solution/prover/__init__.py` | upstream |
| `solution/prover/cli.py` | upstream |
| `solution/prover/config.py` | upstream |
| `solution/prover/context.py` | upstream |
| `solution/prover/experiments.py` | upstream |
| `solution/prover/features.py` | upstream |
| `solution/prover/heuristics.py` | upstream |
| `solution/prover/isabelle_api.py` | modified |
| `solution/prover/llm.py` | upstream |
| `solution/prover/minimize.py` | upstream |
| `solution/prover/premises.py` | upstream |
| `solution/prover/prompts.py` | modified |
| `solution/prover/prover.py` | modified |
| `solution/prover/ranker.py` | upstream |
| `solution/prover/tactics.py` | upstream |
| `solution/prover/train_premises.py` | upstream |
| `solution/prover/train_reranker.py` | upstream |
| `solution/prover/utils.py` | upstream |

## root

| File | Status |
|------|--------|
| `solution/requirements.txt` | upstream |
| `solution/tmp/ContextDemo.thy` | upstream |
| `solution/tmp/magnus_names.json` | upstream |
