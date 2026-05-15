# AI Usage Log

All queries to Claude Code and summaries of actioned responses. Required for assignment appendix.

---

## Entry 1 — Repository initialisation

**Request:** Analyse the codebase and create CLAUDE.md with build commands and architecture overview.

**Actioned response:** Read assignment PDF (via zlib stream decompression), extracted all 9 required features and the CEGIS repair algorithm spec. Created `CLAUDE.md` with project overview, algorithm description, and dev notes.

---

## Entry 2 — Import reference implementation

**Request:** Get the relevant files from https://github.com/zhehou/llm-isabelle to build upon according to the assignment task.

**Actioned response:** Cloned `zhehou/llm-isabelle` to `/tmp`, read README and requirements, then rsync'd all source folders (`prover/`, `planner/`, `datasets/`, `baselines/`, `isabelle_ui/`, `logs/`, `tmp/`, `requirements.txt`) into the workspace root. Updated `CLAUDE.md` with actual commands and code structure.

---

## Entry 3 — Create upstream tracking document

**Request:** Create a document listing all files originally from the zhehou repo, to be updated as original files are added.

**Actioned response:** Created `UPSTREAM.md` with a table of all 63 upstream files, each marked `upstream`. Status column to be updated to `modified` or `replaced` as work progresses.

---

## Entry 4 — Assess implementation completeness

**Request:** How much of the implementation goals have been completed by the zhehou repo?

**Actioned response:** Spawned an Explore agent to read all 9 feature implementations. Finding: all 9 features are fully implemented despite README marking 2 as WIP. Reported this to user with a table and recommended focusing on benchmarking, improving performance, and adding a dataset.

---

## Entry 5 — Reorganise into baseline/solution folders

**Request:** Have two folders — one frozen baseline from zhehou, one clone to work upon.

**Actioned response:** Created `baseline/` and `solution/` directories. Copied all source files to `baseline/`, moved them to `solution/`. Updated `UPSTREAM.md` paths to `solution/` prefix. Updated `CLAUDE.md` to note all commands run from `solution/`.

---

## Entry 6 — Implement improvements

**Request:** Do what is expected for the task and keep a specific log of requests and actioned responses.

**Actioned response:** Spawned a deep audit agent to read `driver.py`, `repair.py`, `repair_inputs.py`, `skeleton.py`, `planner/prompts.py`, `prover/prompts.py` in full. Identified 47 concrete issues with line numbers. Prioritised and fixed the following (see entries below for each file):

### 6a — `solution/planner/driver.py`
Fixes applied:
- **Line 127**: Wrapped `_verify_full_proof()` call in try/except inside `_fill_one_hole()` to prevent unhandled exceptions crashing the loop; returns `(text, False, "verify-exception")` on failure.
- **Lines 88–110**: Strengthened prover result extraction — added type guards for non-string items in finisher/applies lists and unified the fallback key lookup.
- **Lines 582–590**: Replaced unstable fingerprint-based `hole_key` repair stage tracking with `(start, end)` span-based tracking so stages survive hole position shifts after edits.
- **Line 243**: Added a 3-second verification overhead buffer to `per_budget` calculation so the budget doesn't run dry during `finished_ok()` checks.

### 6b — `solution/planner/repair.py`
Fixes applied:
- **Lines 627, 644, 660**: After `finished_ok()`, added a secondary check that the hole span no longer appears in the patched text before returning `True`, preventing false-success returns.
- **Lines 745–747**: Fixed off-by-one — `_replace_failing_tactics_with_sorry()` was passed `start + 1` (1-based) where it expects 0-based; corrected to `start`.
- **Lines 778**: Recalculate `end` as `start + len(new_block_lines)` *after* the splice rather than before, so line index stays correct when the replacement has a different line count.

### 6c — `solution/planner/skeleton.py`
Fixes applied:
- **Line 463**: Added a check — if the outline already ends with `done` or `qed`, skip appending `end_with="sorry"` to avoid injecting invalid syntax.
- **Lines 754–757**: Clamped the scoring formula to `[0, 1000]` to prevent unbounded subgoal counts dominating; swapped sort key to `(subgoals, score, i)` so quality breaks ties over insertion order.

### 6d — `solution/planner/prompts.py`
Fixes applied:
- **Lines 186–206**: Replaced Unicode ellipsis `…` with Isar token `...` in style examples so examples are consistent with `_normalize_calculation_ellipsis()`.
- **Lines 30–32**: Extended LIGHT GRAMMAR to include `linarith`, `omega`, `decide`, `simp_all`, `blast`, `auto` as allowed tactics.
- **Line 168**: Clarified `. ` instruction — changed to "don't use `.` as a standalone closing tactic; use `done` or `by ...` instead".

### 6e — `solution/prover/prompts.py`
Fixes applied:
- **Lines 20–22**: Resolved conflicting `_def` instructions — merged into a single rule: "Never invent fact names; only cite names that appear verbatim in Helpful facts, including those ending in `_def`".
- **Line 62**: Qualified "use available facts" to "use facts listed in Helpful facts below; if none are listed, rely only on built-in tactics".

---

## Entry 7 — Fix the comparison agent so the solution emits valid + successful Isabelle scripts

**Request:** When `compare.py` was run, `comparison/Solution_Results.thy` was syntactically invalid (an extra `lemma "..."` echo inside each proof body) and reported 0/5 proved even on trivial list lemmas. Asked Claude to look at the buggy comparison output, find why the agent fails to produce valid + successful proofs, and fix it.

**Actioned response:** Traced the failure end-to-end with a probe script that dumped the raw `isabelle_client` responses, then applied three fixes:

### 7a — `solution/prover/isabelle_api.py` (root cause)
- **Lines 100–124 (`_decode_body_to_dict`)**: `isabelle_client ≥ 1.0` returns Pydantic models (e.g. `UseTheoriesResponseBody(ok=True, errors=[], nodes=[…])`) as `response_body`, but the decoder only handled `bytes` / `str` / `dict` and fell through to `None`. As a result `finished_ok()` skipped every FINISHED response and the prover misreported every proof as failed — including obviously-correct tactics like `by simp` on `rev (rev xs) = xs`. Added `model_dump()` / `dict()` fallbacks so Pydantic bodies are converted into plain dicts (recursively, so nested `NodeResult` / `Message` objects are also dicts). This is the fix that turned 0/5 into 5/5.

### 7b — `compare.py:run_solution`
- **Lines 249–266**: `prove_goal()` seeds its `steps` list with the `lemma "<goal>"` declaration (`solution/prover/prover.py:190`), but `proof_block()` already emits a `lemma <name>: "<goal>"` header — so the joined `proof` body produced a duplicated `lemma "..."` line that is a syntax error inside a proof. Fixed by filtering out the seed lemma step from `steps` before joining, and by falling back to `sorry` whenever `success=False` (even if `steps` is non-empty), so the produced `.thy` file is always at least syntactically valid.

### 7c — `compare.py` output naming and ROOT
- **Lines 312, 330**: Renamed the output paths from `baseline_results.thy` / `solution_results.thy` to `Baseline_Results.thy` / `Solution_Results.thy` so the file names match the `theory Baseline_Results` / `theory Solution_Results` declarations Isabelle requires.
- **Lines 354–360**: The auto-written `comparison/ROOT` now sets `options [quick_and_dirty]` so a partial run containing `sorry` placeholders still builds with `isabelle build -d comparison Comparison`.

### Verification
- Re-ran `python compare.py --n 5 --model "ollama:qwen2.5-coder:32b" --timeout 90 --sledge-timeout 25` on `solution/datasets/lists.txt`: solution now reports 5/5 proved.
- Ran `isabelle build -d comparison Comparison` end-to-end: session finishes cleanly (`Finished Comparison (0:00:04 elapsed time)`), confirming both theory files type-check in real Isabelle/HOL.
- Generated `Solution_Results.thy` contains five `by simp` proofs (one per goal), with no echoed `lemma "..."` lines and no syntax errors.
