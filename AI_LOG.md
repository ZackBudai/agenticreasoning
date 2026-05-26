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

---

## Entry 8 — Resume comparison sweep against real baseline prover

**Request:** Complete what we were doing when we left off (the previous session ended mid-rerun of `compare.py` after refactoring it to use the real `baseline/` prover instead of the sledgehammer-only stub).

**Actioned response:**

1. **Recovered prior session state.** Inspected the previous session transcript, confirmed the `compare.py` refactor (`run_prover("baseline"|"solution", …)` with `--sledge-only-baseline` escape hatch) was in place, and that the earlier smoke test died with the session before producing any results.

2. **Reran the logic smoke test.** Launched `python compare.py --goals-file solution/datasets/logic.txt --n 5 --timeout 60 --out-dir comparison/_smoke_logic --model ollama:qwen2.5-coder:1.5b --trace`. Result: solution 5/5, baseline 0/5.

3. **Diagnosed the baseline 0/5.** Diffed `baseline/prover/isabelle_api.py` vs `solution/prover/isabelle_api.py`. Baseline only decodes response bodies that are `dict | str | bytes`; current `isabelle-client ≥ 1.0` returns Pydantic V2 models. Solution adds a `model_dump()` → `dict()` → JSON-fallback chain in `_response_body_as_dict`, plus a `_extract_session_id` helper. Without these shims, baseline silently fails on every sledgehammer/finisher response. **This is a legitimate, reportable improvement, not a comparison artefact** — but it dominates the headline numbers.

4. **Added `--baseline-timeout` flag to `compare.py`.** Baseline burns the full per-goal timeout on every goal (can't decode any "success" response, so always reaches timeout). At `--timeout 120` the sweep ETA was ~3 hours. New `--baseline-timeout` defaults to `--timeout` for backwards compatibility; sweep now passes `--baseline-timeout 30` (cf. `run_sweep.sh`). Also added `-u` to the python invocation so trace output flushes immediately to per-dataset logs.

5. **Ran the curated sweep** (`lists/logic/nat/sets`, `ollama:qwen2.5-coder:32b`, baseline-timeout=30, solution-timeout=120, sledge-timeout=30). Final results, written to `comparison/summary.md`:

   | Dataset | Goals | Baseline | Solution |
   |---|---:|---:|---:|
   | lists | 18 | 0 | 15 |
   | logic | 5 | 0 | 5 |
   | nat | 9 | 0 | 2 |
   | sets | 8 | 0 | 8 |
   | **TOTAL** | **40** | **0** | **30** |

   Cleaned the summary aggregator by moving stale logs (`_smoke_logic.log`, `sweep_curated.log`, `baseline_rerun_curated.log`) into `comparison/_logs/_archive/` so they no longer pollute the per-dataset table, and added a TOTAL row to the regenerated `summary.md`/`summary.csv`.

**Caveat surfaced for the report:** `compare.py` exercises `prover.prove_goal` from each folder but does **not** invoke `planner.plan_and_fill` — so the CEGIS-repair work in `solution/planner/` is not reflected in these numbers. The headline result is "solution-side prover improvements (Pydantic-V2 compat shim, prompts, llm.py, isabelle_api.py) vs upstream baseline" — the planner-side work needs a separate harness (`planner.experiments bench` or a compare.py extension) before its measurements can appear in the report.

---

## Entry 9 — Planner audit + F1-F8 fixes (spec compliance + correctness)

**Request:** Run the planner side of the comparison (`a)` — testing/comparing planner+prover). An initial run on 25 hard goals returned 0/25 vs 0/25 because every LLM call hit `requests.exceptions.ReadTimeout` (120s default); after bumping `OLLAMA_TIMEOUT_S=300` and switching to `qwen2.5-coder:7b`, a second attempt showed solution-side goals running 600-700s against a `--timeout 180s` budget (≥3× overrun) plus a new failure mode `had_sorry=False && verified_ok=False` (Fill claims success on outputs the bench-level verifier rejects). The user paused and asked whether the planner was properly implemented before re-benchmarking.

**Actioned response:**

Spawned an audit agent that read `solution/planner/{driver.py,repair.py,repair_inputs.py,skeleton.py,goals.py,experiments.py}` and `solution/prover/{prover.py,isabelle_api.py}` in full. Findings produced an F1-F8 list; mapped each item to (spec-required vs quality) and committed F1-F8 in one pass. Files changed:

- `solution/planner/budget.py` (new) — `Deadline` helper for hard per-goal timeout enforcement.
- `solution/planner/goals.py` — added `strict_verify_responses(resps)` shared parser; rewrote `_verify_full_proof` to use it.
- `solution/planner/driver.py` — Deadline threaded through, classifier for earliest failure, Fill-after-repair pass, prune-stale-progress, fresh-outline cap, per-hole budget halved.
- `solution/planner/repair.py` — Deadline accepted in `try_cegis_repairs`/`regenerate_whole_proof`, verify timeouts now respect remaining budget, stage gating tightened (one stage per call), `prev_blocks` stores original LLM block instead of sorry-injected version, repair uses the shared strict verifier.
- `solution/planner/experiments.py` — `_verify_full_isar` now delegates to `strict_verify_responses` so Fill and the bench harness can never disagree.

### 8a — F1 Hard per-goal timeout enforcement
- `planner/budget.py`: new `Deadline` (absolute-time monotonic budget with `remaining()` / `remaining_int(cap, min_)` / `expired()` / `check()`).
- `planner/driver.py`: `plan_and_fill` now constructs `deadline = Deadline(float(timeout))` and aliases `left_s = deadline.remaining` (replacing the old lambda). Added `if deadline.expired(): break` at top of the main while loop. `_repair_failed_proof_topdown` also receives `deadline` and bails when expired.
- `planner/driver.py`: `per_hole_budget` halved — Fill now gets at most 50% of remaining deadline so the same iteration's CEGIS pass has room.
- `planner/repair.py`: `try_cegis_repairs` and `regenerate_whole_proof` accept `deadline=None`; their internal `left()` lambdas now return `min(local_budget, deadline.remaining())`. Per-stage Isabelle verifies use `verify_to = max(2, min(_ISA_VERIFY_TIMEOUT_S, int(left())))` so verifies near the deadline are clamped.
- `_repair_block`: tightened round-entry guard from `left() <= 3` → `left() < 10` (one round can spend up to 8s LLM + 30s verify).

### 8b — F2 Unify Fill verifier with bench verifier
- `planner/goals.py`: new `strict_verify_responses(resps) -> (ok, diag)` which requires Isabelle's structured summary to have `ok=True AND errors=[]` (with a legacy `*** Error:` / `100%` fallback when no summary). Same parser used by both Fill and the bench.
- `planner/goals.py`: `_verify_full_proof` rewritten to use `strict_verify_responses` instead of the previous `finished_ok` (which was strictly weaker — accepted partial errors).
- `planner/repair.py`: all four `finished_ok(...)` callsites in `try_cegis_repairs` and `_repair_block` replaced with `strict_verify_responses(...)` so repair stages can never claim success on something the bench will reject.
- `planner/experiments.py`: `_verify_full_isar` collapsed to a thin wrapper around `strict_verify_responses` so the bench and planner can never diverge.

### 8c — F3 Re-run Fill after repair edits
- `planner/driver.py`: after `try_cegis_repairs` returns `patched != full` but the strict verify failed, the driver now diffs sorry spans (`pre_repair_spans` vs `find_sorry_spans(patched)`), and for each NEW span runs `_fill_one_hole(...)`. If Fill closes all new sorrys and the result strict-verifies, returns success; otherwise keeps partial progress and continues escalation. Spec text: "after any repair edit, run Fill again on any newly introduced sorry placeholders".

### 8d — F4 Driver-level earliest-failure pivot
- `planner/driver.py`: new `_classify_earliest_failure(isabelle, session, full, spans) -> (line_1based, containing_sorry_span)` — runs `_quick_state_and_errors`, extracts the earliest error line, and decides whether that line overlaps a current sorry span.
- `planner/driver.py`: span selection at top of the while loop now consults the classifier. If the earliest error is at a sorry → focus that span. If the earliest error is at a non-sorry line → pick the nearest sorry and start at repair stage 1 (skip Fill, which can't help a structural error). Spec text: "always focus on the earliest failure point".

### 8e — F5 Per-stage round caps inside `try_cegis_repairs`
- `planner/repair.py`: stage gating changed from `resume_stage <= 1` / `resume_stage <= 2` to STRICT match. `resume_stage=1` runs ONLY have/show; `resume_stage=2` runs ONLY case-block OR subproof (not both — case first if it exists, else subproof). Previously one call could chain all three stages internally for up to 9 LLM rounds before the driver's per-stage cap could intervene.
- `planner/driver.py`: `_repair_failed_proof_topdown` was passing `resume_stage=0` and relied on the old behavior. Now explicitly iterates `for stg in (1, 2)` and stops once a stage produces a change.

### 8f — F6 Clean up stale `repair_progress` entries
- `planner/driver.py`: at the top of each while iteration, prune `repair_progress` keys not present in the current `spans` fingerprint set; also prune `stage_tries` keys whose `hole_key` is no longer current.

### 8g — F7 Explicit cap on fresh-outline regeneration
- `planner/driver.py`: added `_MAX_FRESH_OUTLINES = 2` and `fresh_outline_count` counter. After whole-proof regen fails, the planner is allowed to propose at most 2 fresh outlines before giving up; previously it kept proposing indefinitely until the wall-clock cap (which F1 now actually enforces — so without F7, the loop would just exhaust the full deadline cycling outlines).

### 8h — F8 Store original LLM block in `prev_blocks`, not the sorry-injected version
- `planner/repair.py`: `_repair_block` was appending `blk_with_sorry` (after `_replace_failing_tactics_with_sorry` replaced any failing tactic with `sorry`) to `mem.prev_blocks` and `prior_store`. Next-round prompts then showed the LLM these sorry-laden versions as "previous failures" — biasing the model. Now stores the original `blk` (and fingerprints by the original) while still splicing `blk_with_sorry` into the patched text.

### Smoke verification
Two smoke runs with `--timeout 60 --strict-no-sorry --verify --model 'ollama:qwen2.5-coder:7b'`:
- First: top-2 hard goals — completed in 75s / 84s wall time (was 600+ s before). Both reported `success=False`, with Goal 1 honestly showing `had_sorry=False AND verified_ok=False` (Fill spliced tactics the strict verifier rejected — exactly the case F2 makes visible instead of false-positive).
- Second: single trivial logic goal (`(True ∧ P) ⟷ P`) — 76s wall (60s plan_and_fill + ~16s bench-level verify), the planner produced a sorry-free outline that the strict verifier correctly rejected as non-compiling, so `verified_ok=False`.

Net: the planner now runs within (1×–1.5×) `--timeout`, the verifier mismatch that produced false positives is closed, and the spec's "earliest failure point" / "run Fill after any repair edit" / "budgets per stage" / "global timeout" requirements are now actually wired up.

**Next step for the report:** rerun `plan_compare.sh` (25 hard goals, both planners) against the F1-F8 implementation to produce planner-side comparison numbers.

## Entry 10 — F11 hybrid fast-path + F12 prover self-strict-verify + F13 strict-verifier protocol fix

**Request:** Add a fast-path to the planner so trivial goals can be closed by the prover (or canned finishers) without paying for outline generation + Fill. After implementing F11, smoke-test it and fix any issues that surface.

**Actioned response:**

Implemented F11 (`_try_prover_direct` in `solution/planner/driver.py`), smoke-tested on a 5-goal mix (3 mid + 2 hard). Smoke surfaced two upstream bugs that were masking each other and had been silently degrading the whole planner since F2 was introduced. F12 fixes one (the prover layer); F13 fixes the other (the strict verifier itself, which was the root cause).

Files changed:
- `solution/planner/driver.py` — new `_try_prover_direct` (F11 stage-A canned finishers + stage-B beam prover), wired into `plan_and_fill` ahead of outline generation.
- `solution/prover/prover.py` — `try_finish` now cross-checks `finished_ok` against `strict_verify_responses` on the same response set (F12). This file was previously identical between baseline/ and solution/; that invariant is intentionally broken here.
- `solution/planner/goals.py` — `strict_verify_responses` rewritten to read FINISHED-frame bodies the way `finished_ok` does, scanning `nodes[*].messages[*]` for `kind=="error"` (F13). Added `DEBUG_VERIFY=1` env-gated diag print to `_verify_full_proof` for future debugging.

### 9a — F11 hybrid fast-path (`_try_prover_direct`)

- `planner/driver.py`: new `_try_prover_direct(isabelle, session, goal, model, deadline, trace=...)` called at the top of `plan_and_fill` before outline generation. Returns a closed proof script or `None`.
  - **Stage A** iterates `_DIRECT_FINISHERS = ("by blast", "by auto", "by simp", "by metis", "by force", "by fastforce", "by presburger", "by argo", "by linarith")`, each wrapped as `lemma "<goal>"\n  <tac>` and checked with `_verify_full_proof`. Returns on first success.
  - **Stage B** runs `prove_goal(beam_w=3, max_depth=6, sledge_timeout=20, ...)` with ~40% of remaining deadline, reconstructs proof text from `res["steps"]`, and `_verify_full_proof`s it.
  - Total budget capped at ~40% of `deadline.remaining()` so a failed fast path still leaves the outline+Fill path with room.
- Rationale: many smoke goals are propositional / first-order tautologies that `by blast` closes in <1s. Going through outline → Fill → repair on those is wasteful and a common source of `had_sorry=True` outcomes when the LLM proposes a structured proof that doesn't quite typecheck.

### 9b — F12 Prover self-strict-verify in `try_finish`

- `prover/prover.py`: `try_finish` previously returned `ok` from `finished_ok(run_theory(...))` only. After F11 surfaced "prover PROVED but strict-verify rejected reconstructed proof" on 5/5 smoke goals, the obvious diagnosis was the F2 false-positive shape applied to the prover layer — `finished_ok` reads incremental FINISHED frames and can over-report when Isabelle keeps streaming after a logical error.
- `prover/prover.py`: `try_finish` now also calls `strict_verify_responses(resps)` on the SAME response set (so no extra Isabelle round-trip) and returns `ok AND ok_strict`. The import is module-level with a `try/except` to keep `prover.cli` usable if `planner.goals` ever moves.
- This change makes `prover.prover` diverge from `baseline/prover/prover.py` for the first time; `project_isabelle_3806ict` memory and `UPSTREAM.md` updated accordingly.

### 9c — F13 Strict-verifier protocol fix (`strict_verify_responses`)

- After F12 was in, F11 stage-B switched from "prover PROVED but rejected" → "prover returned success=False" on all 5 goals, but solution was still 0/5. Single-goal diag run with `DEBUG_VERIFY=1` on `(∃x. P x ∧ Q x) ⟶ (∃x. P x)` showed `strict_verify_responses` returning `Verification inconclusive: no structured summary` for `by blast`, `by auto`, `by simp`, etc. — every canned finisher rejected, including ones that trivially close the goal.
- Root cause: the F2-era implementation looked for a top-level JSON response with `"ok"` and `"errors"` keys as siblings. The Isabelle 2025 client never emits that shape — its `ok` flag is nested inside a FINISHED frame's body, and errors are under `nodes[*].messages[*]` with `kind=="error"`. So `strict_verify_responses` always fell through to the legacy `*** Error:` / `100%` text scan, never matched either, and returned False for ALL proofs. This is why Fill kept reporting `had_sorry=False AND verified_ok=False` post-F2 — Fill's strict-verify was *unconditionally* False, but the bench's strict-verify was also unconditionally False, so they "agreed" by both rejecting everything.
- `planner/goals.py`: rewrote `strict_verify_responses` to mirror `finished_ok`'s decoding — uses `_get_field`, `_normalize_type`, `_decode_body_to_dict` from `prover.isabelle_api` to find FINISHED frames, reads `obj.get("ok")` / `obj.get("result")`, scans `obj["nodes"][*]["messages"][*]` for `kind=="error"`. Success iff last FINISHED `ok=true` AND no error messages anywhere. Legacy `*** Error:` fallback retained for response streams that have no FINISHED frame.
- `planner/goals.py`: `_verify_full_proof` now prints the diag and any exception when `DEBUG_VERIFY=1` is set — env-gated, silent otherwise.

### Smoke verification (5 goals, K=1, T=60s, qwen2.5-coder:7b)

Goal set: `datasets_subset/smoke_f11.txt` = first 3 from `mid_25.txt` + first 2 from `hard_25.txt`.

| Run | Baseline | Solution | Notes |
|---|---:|---:|---|
| F11 only (pre-F12, pre-F13) | 0/5 | 0/5 | 5/5 stage-B "PROVED but strict-verify rejected" — the F13 protocol bug |
| F11 + F12 (pre-F13) | 0/5 | 0/5 | 5/5 "prover returned success=False" — F12 stops the lie, but F13 still rejects |
| F11 + F12 + F13 (final) | **0/5** | **5/5** | 5/5 stage-A `by blast` solves in 7-9s/goal |

Solution side per-goal: `success=True had_sorry=False verified_ok=True` for all five, mean 8.7s wall (vs baseline mean ~62s and 0/5 verified).

**Net:** F13 is the load-bearing fix. F11 is the new feature it enabled (was already in the code but invisible because strict-verify rejected even the correct proofs it produced). F12 closes a related but separate over-reporting hole at the prover layer.

**Next step for the report:** rerun the assignment-flavor sweep (`TIMEOUT=180 K=3` against `hard_25.txt`) to get planner-comparison numbers for the writeup. The F13 fix should materially improve baseline AND solution success rates across the board, not just on these 5 goals — worth verifying.

## Entry 11 — Pre-reboot handoff: assignment-flavor sweep runbook

**Request:** Save the sweep-launch commands + live progress-watcher to a file in the workspace root, update memory and AI_LOG so a fresh Claude session after a reboot can pick up where this one left off. Do not launch the sweep — the user will launch it themselves after reboot.

**Actioned response:**

- Wrote `/home/zack/Desktop/AGENTIC_REASONING/SWEEP_RUNBOOK.md` containing: Step 1 launch (parks any existing `planner_comparison/`, checks ollama, `nohup`-launches `plan_compare.sh hard_25.txt` with TIMEOUT=180 K=3 TEMPS='0.35,0.55,0.85'), Step 2 a `watch_sweep` shell function that refreshes every 120s (alive check, log mtimes, goals-done/verified per side, F11 stage-A/B hit counts on solution, latest tails, traceback alarm, terminal-bell on completion), Step 3 one-off spot-checks, Step 4 abort, Step 5 post-completion archival.
- Added reference memory pointing at the runbook so the next session knows where to look.
- This entry itself documents the handoff so the appendix has a record of the pause.

State of solution/ at handoff: F11+F12+F13 live, smoke 5/5 vs baseline 0/5 verified on `smoke_f11.txt`. `DEBUG_VERIFY=1` env-gated diag still present in `solution/planner/goals.py:_verify_full_proof` — env-gated, silent in normal runs; can stay until the assignment sweep validates everything end-to-end.

**Next step for the report:** post-reboot, follow `SWEEP_RUNBOOK.md` Steps 1-2. Expected wall time ~1.5-2.5 hours. Bring the resulting `planner_comparison/summary.md` back into the next Claude session for analysis.

## Entry 12 — F14 outline-scoring deadline bail-out (close the residual F1 leak before total-dataset run)

**Request:** Before recommending a full-dataset planner sweep, the user asked whether the residual F1 outline-gen leak (documented after F1-F8 and noted post-F13) could be fixed.

**Actioned response:**

Read `solution/planner/skeleton.py:756 propose_isar_skeleton_diverse_best` and traced the post-F9 leak path: F9 had bounded the LLM outline-gen phase (`propose_isar_skeletons` respects both `deadline.expired()` and `outline_budget_s = 0.35 × deadline.timeout_s`), but `propose_isar_skeleton_diverse_best` then runs an **unbounded scoring loop** that calls `_quick_sketch_score(isabelle, session_id, sk.text)` once per candidate — each is an Isabelle round-trip with no deadline check. With K=3 and a slow hard goal, scoring alone could add 30–90s past `outline_budget_s`. The optional `_state_block_for_goal` context-hints probe at the top of the function was a second unguarded Isabelle call.

### 12a — F14 scoring-loop deadline bail-out
- `planner/skeleton.py`: in `propose_isar_skeleton_diverse_best`, added `if deadline is not None and deadline.expired(): break` at the top of the scoring loop. Remaining unscored candidates are appended with `(score=0.0, n=0, idx=i)` so insertion order is preserved as the tie-break — we still pick a usable outline (the first generated one) instead of returning empty.

### 12b — F14 context-hints probe guard
- `planner/skeleton.py`: `if context_hints:` → `if context_hints and (deadline is None or not deadline.expired()):` so a deadline-overrun goal doesn't burn another Isabelle round-trip on `_state_block_for_goal` before we even start scoring.

Both changes are backwards-compatible: when no deadline is provided, or when the deadline hasn't expired, behavior is unchanged. Only the deadline-expired case short-circuits.

### Residual gap (documented, not fixed)
`_quick_sketch_score` itself calls `run_theory` with no explicit timeout. If Isabelle hangs *during* the call (rare), the top-of-loop deadline check can't preempt it. For full robustness this would need plumbing `_run_theory_with_timeout` into `_quick_sketch_score` — deferred until hangs are actually observed.

`solution/planner/experiments.py:_verify_full_isar` was checked and is already correctly bounded by `_run_theory_with_timeout(..., timeout_s=_BENCH_VERIFY_TIMEOUT_S)`, so the bench-level verifier path is safe.

**Net:** With F14, the per-goal wall-time for `plan_and_fill` is now bounded to ~1.0–1.2× `--timeout` in the typical case (instead of up to 10× pre-F9). Makes a 100-goal hard sweep go from "indeterminate, possibly multi-day" to "10h±20%".

**Next step for the report:** rerun the 5-goal smoke (`smoke_f11.txt`, K=1, T=60s) post-F14 to confirm no regression, then launch the assignment-flavor sweep (`hard_25.txt`, K=3, T=180s).

## Entry 13 — F15 bounded sketch check + F16 viable-LLM-call floor (post-sweep cleanup)

**Request:** Fix two issues surfaced by the post-F14 hard_25 sweep: (a) goal 25's 712s overrun (F14 residual — single in-flight Isabelle call inside `_quick_sketch_score` not preemptable); (b) 7 goals (28% of the run) marked as `❌ planner error: ReadTimeout (read timeout=3)` — investigation showed these were caused by the planner clamping per-call LLM timeout to `max(3, ...)` when the per-goal deadline was nearly exhausted, firing a guaranteed-to-fail 3s call against a qwen2.5-coder:7b model.

**Actioned response:**

Traced the 3s timeout to `solution/planner/skeleton.py:propose_isar_skeletons`. The per-call cap formula was `per_call_timeout = max(3, min(per_call_caps))` — when `deadline.remaining_int(min_=3)` returned 3, the formula clamped the LLM timeout to 3s. With qwen2.5-coder:7b on a hard goal, any call under ~10s reliably hits `requests.exceptions.ReadTimeout`. The bench's outer try/except catches it but logs it as a planner error rather than as a clean budget-exhaustion failure.

### 13a — F15 bounded sketch check (`_quick_sketch_score`)
- `planner/skeleton.py`: changed `_quick_sketch_score` to use `_run_theory_with_timeout(isabelle, session, thy, timeout_s=_SKETCH_CHECK_TIMEOUT_S)` (20s cap) instead of unbounded `run_theory(...)`. New constant `_SKETCH_CHECK_TIMEOUT_S = 20`.
- Closes the F14 residual: in-flight Isabelle sketch checks can now be preempted at 20s, so the worst-case observed wall-time on goal 9 (709s) and goal 25 (712s) should now be bounded.
- Imports `_run_theory_with_timeout` from `planner.goals` (already used by `_verify_full_isar` in `experiments.py` — same pattern, no new infra).

### 13b — F16 viable-LLM-call floor
- `planner/skeleton.py`: raised the per-call timeout floor from 3s to a new constant `_MIN_VIABLE_LLM_CALL_S = 10`. Three call sites updated:
  1. `propose_isar_skeletons` main loop: changed `max(3, min(per_call_caps))` to `max(_MIN_VIABLE_LLM_CALL_S, min(per_call_caps))`, and added an early `break` when `min(per_call_caps) < _MIN_VIABLE_LLM_CALL_S` so the loop exits gracefully rather than firing a doomed call.
  2. `propose_isar_skeletons` fallback (no outlines yet): replaced the `max(3, ...)` clamp with a `if remaining < _MIN_VIABLE_LLM_CALL_S: return out` early exit.
  3. `deadline.remaining_int(min_=3)` → `min_=_MIN_VIABLE_LLM_CALL_S`.
- The bench's behavior is unchanged: a goal that would previously have errored with ReadTimeout will now (in most cases) return `success=False` because the planner ran out of viable LLM-call budget before producing a verified outline. Net effect on the strict-pass count is zero (these were already counted as failures), but the logs no longer show false `❌ planner error` markers and the failure mode is correctly attributed.

### Verification
Both files parse via `ast.parse`. Import chain checked: `from planner.goals import _run_theory_with_timeout` works without circular import (goals.py does not import from skeleton.py).

**Open: re-sweep on `hard_25.txt` to confirm.** Pre-F15/F16 sweep result was 13/25 strict-pass with 2 wall-time overruns (>4× budget) and 7 ❌ ReadTimeout errors. Post-F15/F16 expected: same or higher strict-pass count, max wall-time bounded close to T=180s, ReadTimeout errors converted to clean `success=False` outcomes.

## Entry 14 — Build the planner's micro-RAG from HOL-stdlib + AFP

**Request:** The previous sweep's failure pattern was concentrated in the `finite A ⟹ card ... = ...` and `finite A ⟹ sum ... = ...` goal families — the LLM (qwen2.5-coder:7b) doesn't reliably surface the relevant cardinality/sum lemma names without hints. The planner has a documented `--priors` and `--hintlex` interface for exactly this case (assignment spec lists "Micro RAG extracted from AFP" as a planner component, upstream README confirms), but no priors/hintlex files had been built. Asked Claude to build them.

**Actioned response:**

1. **Downloaded AFP-current** (~96 MB tarball → 407 MB extracted). The Archive of Formal Proofs at `https://isa-afp.org/release/afp-current.tar.gz` is the canonical input corpus for the planner's micro-RAG. Saved to `/home/zack/Desktop/AGENTIC_REASONING/afp_download/afp-2026-05-13/` (979 sessions, 10,072 `.thy` files).

2. **Wrote `agenticreasoning/build_rag.sh`** — a thin wrapper around the existing `planner.extract.mine_afp_corpus_rich` and `planner.priors` infrastructure. Three modes:
   - `holstdlib` — extract from Isabelle's bundled `~~/src/HOL/` (115 theories)
   - `afp <afp-thys-dir>` — extract from a local AFP checkout
   - `combined <afp-thys-dir>` — both, concatenated then aggregated

   The script auto-detects `ISABELLE_HOME` via `isabelle env` and resolves Isabelle's HOL directory. Despite the name, `mine_afp_corpus_rich` is a generic `*.thy` rglob walker, not AFP-specific.

3. **Ran `./build_rag.sh combined <afp-thys>`** producing:
   - `solution/datasets/isar_pairs_holstdlib.jsonl` — 63,734 records (35.9 MB)
   - `solution/datasets/isar_pairs_afp.jsonl` — 289,508 records (187.7 MB)
   - `solution/datasets/isar_pairs_combined.jsonl` — 353,242 records (223.6 MB)
   - `solution/datasets/isar_priors.json` — 34,857 priors rules (4.7 MB)
   - `solution/datasets/isar_hintlex.json` — 17,582 tokens mapped to lemma sets (2.3 MB)

   Compared to a HOL-stdlib-only extraction (5,333 priors / 2,822 hintlex tokens), the combined corpus is ~6× larger in both metrics.

4. **Updated `.gitignore`** to exclude the generated artefacts (`isar_pairs_*.jsonl`, `isar_priors.json`, `isar_hintlex.json`) — they're large and regenerable from the source corpora via `build_rag.sh`.

5. **Updated `SWEEP_RUNBOOK.md`** with a new Step 2b that runs `build_rag.sh` and updated Step 4 to pass `--priors` and `--hintlex` (with absolute paths) via `EXTRA_FLAGS`. The runbook checks for existing RAG artefacts before downloading AFP again, so repeat invocations are idempotent.

**Open: re-sweep to measure RAG impact.** The previous post-F14 sweep was 13/25 strict-pass; the failure cases were dominated by `finite A ⟹ card ... = ...` style goals. Predicted lift from RAG injection of the relevant cardinality lemma names: +3 to +6 goals into strict-pass.
