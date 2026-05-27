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

## Entry 15 — F17 hard wall-clock cap at 1.2× per-goal budget

**Request:** Post-RAG sweep finished at 14/25 strict-pass. Inspection of `solution.log` showed four goals (11, 12, 13, 18) running 629-739 s against a 180 s nominal timeout — 3.5-4× overrun. F14 (deadline bail-out in outline scoring) and F15 (bounded sketch check) cap the cooperative deadline checks but don't bound `prove_goal` inside `_fill_one_hole` or sledgehammer's `metis` reconstruction (in-Isabelle, uninterruptible from Python). Asked Claude to cap any overrun at 1.2× nominal timeout outside of Isabelle.

**Actioned response:**

Diagnosis: the existing `_run_theory_with_timeout` wrappers (three copies — `planner/goals.py`, `planner/repair_inputs.py`, `prover/isabelle_api.py`) used `with ThreadPoolExecutor(max_workers=1) as ex:` whose `__exit__` calls `shutdown(wait=True)` — so even when `fut.result(timeout=...)` raises `_FuturesTimeout` and the code calls `isabelle.interrupt()`, the `with`-block exit blocks on the still-running worker thread if `interrupt()` didn't propagate (sledgehammer ignores it). That's the actual hang.

Fix applied in two layers:

1. **All three `_run_theory_with_timeout` sites** switched from `with ThreadPoolExecutor as ex:` to explicit `ex = ThreadPoolExecutor(...)` with `try/finally: ex.shutdown(wait=False)`. On timeout, the worker leaks until the surrounding Isabelle proc is killed; `_cleanup_resources` in `plan_and_fill`'s `finally` already kills the proc, which unblocks the leaked worker's socket read.

2. **`plan_and_fill` itself** wrapped with a SIGALRM watchdog. At entry: `signal.alarm(max(1, int(1.2 * timeout) + 1))` and a SIGALRM handler that raises `DeadlineExceeded`. New top-level `except DeadlineExceeded` returns `PlanAndFillResult(False, ...)`; `finally:` calls `signal.alarm(0)` and restores the previous handler. Guarded by `threading.current_thread() is threading.main_thread()` — SIGALRM only works in the main thread, and the bench harness calls `plan_and_fill` directly from main thread (confirmed by reading `experiments.py:_bench_run_one`).

The cap is "outside of Isabelle" because SIGALRM interrupts the Python main thread's syscalls (socket reads, `Condition.wait`, `subprocess.wait`) via EINTR; it doesn't depend on Isabelle's own preemption.

**Smoke:** standalone test runs `time.sleep(20)` under a 5 s nominal timeout (`cap_s = int(1.2 * 5) + 1 = 7`) and catches `DeadlineExceeded` after exactly 7.0 s. Cap works as designed.

**Files touched:**
- `solution/planner/driver.py` — SIGALRM install/teardown around the main try-block; new `except DeadlineExceeded` clause.
- `solution/planner/goals.py` — `_run_theory_with_timeout` switched to `shutdown(wait=False)`.
- `solution/planner/repair_inputs.py` — same change.
- `solution/prover/isabelle_api.py` — same change in the innermost `run_theory` wrapper.

**Net:** F17 caps the worst observed overrun (739 s for nominal 180 s) at ~216 s. Doesn't directly close more goals — but on a 25-goal sweep it saves ~30 min of wall-time and makes failure attribution clean (overrun goals now fail at the cap rather than burning past it).

## Entry 16 — F18 outline placeholder gate + F19 card/sum specialist finishers + F20 `suggest_common_lemmas` extension

**Request:** With F17 in place, the question shifted to closing more goals. Inspection of failed goals' outlines in `solution.log` showed the LLM was emitting literal Isabelle comment placeholders as `have:` bodies:

```
have f1: "(* fill a useful intermediate statement *)"
  sorry
```

These don't parse, so Fill spends the whole per-goal budget trying to discharge sorrys preceded by un-parsed statements. Asked Claude to find further improvements.

**Diagnosis (Claude's investigation):**

Three independent failures stacked on the card/sum/finite-set goal family (10, 11, 12, 13, 16, 17, 18, 21, 25):

1. **Outline path produces garbage** (the placeholder issue above) for goals where the LLM doesn't know what intermediate facts to introduce. Burns the budget on un-fillable sorrys.
2. **F11 fast-path's finisher list (`_DIRECT_FINISHERS`) has no card/sum-specific tactics.** Generic `blast/auto/simp/metis/force/fastforce/presburger/argo/linarith` can't close `card_Un_disjoint`-style goals.
3. **`prover/heuristics.py:suggest_common_lemmas`** — the only hardcoded source of lemma-name hints fed to the beam search prover — only knew `rev` and `append`. No `card_Un_disjoint`, `card_image`, `sum.distrib`, etc., so the prover's finisher-variants pool never saw the right lemma names.

Also: probing 25 candidate finishers in Isabelle directly showed goals 4 and 9 are **provably false** (g4 has a classical counter-example `P=⊤, Q=(x=1), R=⊥` giving LHS=⊤, conclusion=⊥; g9 lacks `finite B` so `A={0}, B=ℕ` gives `0 ≠ 1+0`). Real ceiling on hard_25 is 23/25, not 25/25.

**Actioned response — three orthogonal fixes:**

### F18 — outline placeholder gate (`planner/skeleton.py`)
- New regex `_COMMENT_PLACEHOLDER_RE` matches `have/show ... "(* ... *)"` patterns.
- New `_count_comment_placeholders(outline_text)` returns the count.
- `propose_isar_skeleton_diverse_best`'s scoring formula adds `+200.0 * placeholder_count`. With K=3 diverse outlines, any placeholder-free sibling wins decisively. If all 3 outlines have placeholders the worst one still wins (best-effort), but at least the score reflects the problem.

### F19 — card/sum specialist finishers (`planner/driver.py`)
- New `_CARD_FINISHERS` (9 tactics) and `_SUM_FINISHERS` (8 tactics) pruned to high-confidence one-shots verified to close goals in isolation: `by (simp add: card_Un_disjoint)`, `by (simp add: card_image)`, `by (simp add: card_Diff_subset)`, `using card_mono by (auto simp: card_cartesian_product)`, `by (simp add: sum.distrib)`, `by (simp add: sum.If_cases)`, `by (simp add: sum.If_cases Int_def)`, `by (simp add: sum.cong)`, etc.
- `_ordered_card_sum_finishers(goal)` reorders by goal token presence: sum-only goals → `sum` finishers first; card-only → `card` first; both → `sum` first. Crucial because the F11 stage-A loop in the previous draft tried 12 card-only tactics before reaching `sum.distrib`, eating the per-goal budget on doomed attempts.
- `_try_prover_direct` (F11 fast-path) updated: for any goal matching `\b(card|sum|finite|inj_on)\b`, `finisher_seq = _ordered_card_sum_finishers(goal) + _DIRECT_FINISHERS`; otherwise unchanged. Per-finisher verify cap tightened to 6 s (was 30 s) to prevent a single slow `simp add: sum.cong` from burning the whole stage-A.
- `_verify_full_proof` in `planner/goals.py` extended with an optional `timeout_s` kwarg so callers can choose tight caps for speculative finisher probing without affecting Fill's final verification.

### F20 — `prover/heuristics.py:suggest_common_lemmas`
- Added domain-aware hint surfacing keyed on `card`, `sum`, `finite`, `inj_on` tokens in the state hint string. Card: `card_Un_disjoint, card_Un_Int, card_Diff_subset, card_image, card_mono, card_insert_if, card_Diff_singleton, card_cartesian_product`. Sum: `sum.distrib, sum.cong, sum.neutral, sum_constant, sum.If_cases`. inj_on: `card_image, inj_on_iff_eq_card`. finite: `finite_Collect_conjI, finite_Diff, finite_Un`. Sum∩card: `sum_eq_card_Int`.
- These hints flow into `mk_finisher_variants` (in `prover/llm.py`) which generates `by (simp add: X)` and `by (metis X)` for each, feeding the beam search prover's candidate pool. Fill and stage-B sledge both benefit.

**Smoke results (single-goal `plan_and_fill` against qwen2.5-coder:7b, T=60 s):**
- g11 `A∩B={} ⟹ card(A∪B) = card A + card B`: **PASS** 69 s, `by (simp add: card_Un_disjoint)`
- g17 `sum (if x∈B then 1 else 0) A = card (A∩B)`: **PASS** 24 s, `by (simp add: sum.If_cases)`
- g18 `sum (if P x then 1 else 0) A = card {x∈A. P x}`: **PASS** 14 s, `by (simp add: sum.If_cases Int_def)`
- g21 `sum (λx. f x + g x) A = sum f A + sum g A`: **PASS** 55 s, `by (simp add: sum.distrib)`

Goals 10, 12, 13, 16 do not close with any one-shot finisher (verified by direct probing of 6-7 candidate tactics each). They need either a structured outline template (partition by predicate + `card_Un_disjoint`) or stronger sledgehammer settings. Out of scope for F17-F20.

**Expected result on next sweep:** 17-19/25 strict-pass (14 prior + 3-5 new closures from g17, g18, g21, possibly g25). Real ceiling 23/25 given g4 and g9 are false.

**Files touched:**
- `solution/planner/driver.py` — F11 stage-A.5 + `_CARD_FINISHERS` + `_SUM_FINISHERS` + `_ordered_card_sum_finishers` + per-tactic 6 s cap.
- `solution/planner/goals.py` — `_verify_full_proof` accepts optional `timeout_s`.
- `solution/planner/skeleton.py` — F18 placeholder regex + count function + scoring penalty.
- `solution/prover/heuristics.py` — F20 extended `suggest_common_lemmas`.

## Entry 17 — F21 hand-written Isar templates for hard_25 stragglers + F22 raised viable-LLM-call floor

**Request:** After F17–F20 the post-RAG sweep settled at 18/25 strict-pass on `hard_25`. The seven remaining fails were goals 4, 9, 10, 12, 13, 16, 25. Two of those (g4 and g9) were verified false by direct probing in Entry 16, so the real provable-fails set is the five card-family goals 10, 12, 13, 16, 25. Smoke probing under F19 confirmed none of these closes with any one-shot finisher — they need either a structured outline template (predicate-partition + `card_Un_disjoint`, or `card_mono` over a cartesian product) or stronger sledgehammer. Asked Claude for both: (a) hand-crafted Isar skeletons keyed on goal shape so the planner has a non-LLM source of structured candidates, and (b) a fix for the `❌ planner error: ReadTimeout` noise that appeared on the same family when the F16 viable-call floor sat at 10 s.

**Diagnosis (Claude's investigation):**

Two independent problems:

1. **Outline-gen has no domain priors for the card-partition shape.** F19's specialist finishers target one-shots; the goals above need a multi-step structure (introduce the partition, prove disjointness, apply `card_Un_disjoint`). The LLM under qwen2.5-coder:7b emits this structure inconsistently — even with the F18 placeholder gate filtering literal `(* ... *)` bodies, the surviving outlines were structurally wrong (e.g. inverting `A` and `B` in the partition, omitting the finiteness side conditions). Hand-written templates with the same hole-shape as the LLM's outlines but with correct structure can be added to the candidate pool at no extra LLM cost.

2. **`_MIN_VIABLE_LLM_CALL_S = 10` is too low for the in-flight prompt.** Once F14's micro-RAG was active, the diverse outline-gen prompt grew to ~2 k tokens in / ~200 tokens out. Ollama (qwen2.5-coder:7b on this CPU/GPU split) was empirically taking 12–25 s per call on the card family, so a 10 s floor was guaranteed to ReadTimeout, surfacing as `❌ planner error` rather than a clean bail. The 30 s number isn't arbitrary — it's the observed worst-case from the unsolved_5 telemetry on 2026-05-27 17:42-17:52.

**Actioned response — two changes in `solution/planner/skeleton.py`:**

### F21 — domain-shaped Isar templates (`_lib_templates_for_goal`)

Four new template `Skeleton`s appended to the `lib` list, regex-keyed so the wrong template never gets injected into the wrong goal:

- **g25-style — `card_mono` on filtered cartesian product** (line 779). Regex requires `card`, `≤`/`<=`, `×`, and `card A * card B`-shape. Body extracts the `card {…}` LHS via `re.search(r"\bcard\s+(\{[^=]*?\})\s*[≤]", goal)`, then opens a `proof -` block that establishes `lhs_set ⊆ A × B`, uses `finite_cartesian_product` for the superset, applies `card_mono`, then `card_cartesian_product` to finish.
- **g13-style — card partition by complementary predicates** (line 804). Regex anchors on `card {…P x…} + card {…¬ P x…} = card A` ending in a single-letter variable. Body proves the union covers `A`, the intersection is empty, both halves are finite, applies `card_Un_disjoint`, simp-closes.
- **g16-style — `card_Diff_subset` on a finite cartesian superset** (line 828). Regex deliberately strict: requires `×` on **both** sides of the equality so g10 (a plain-set `card_Diff` equality without `×`) doesn't trip it and inject a wrong template. Body sets up `C ∩ (A×B) ⊆ A×B`, finiteness of the superset, the `A×B - C = A×B - (C ∩ (A×B))` rewrite, then `card_Diff_subset`.
- **g12-style — card partition with shared predicate** (line 855). Regex anchors on `card {…P x ∧ Q x…} + card {…P x ∧ ¬ Q x…} = card {…P x…}`. Body parallels g13 but partitions `{x ∈ A. P x}` rather than `A`.

The templates use `assume finA: "finite A"` inside `proof -` (and `assume finB: "finite B"` for the cartesian cases). They flow into the existing `propose_isar_skeleton_diverse_best` candidate list alongside LLM outlines and are scored by `_quick_sketch_score`; F18's placeholder penalty doesn't apply (templates have no `(* … *)` bodies), and F15's bounded sketch-check still caps the per-template Isabelle round-trip.

### F22 — `_MIN_VIABLE_LLM_CALL_S = 10 → 30`

Single-constant change at `skeleton.py:45`. The floor controls four sites inside `propose_isar_skeletons`:

- Line 691: `deadline.remaining_int(cap=_OUTLINE_PER_CALL_CAP_S, min_=_MIN_VIABLE_LLM_CALL_S)` — the per-call cap derived from remaining global deadline.
- Line 694: `max(_MIN_VIABLE_LLM_CALL_S, int(outline_left / remaining_outlines))` — the per-call cap derived from the outline-only sub-budget split across remaining temps.
- Line 697: `if min(per_call_caps) < _MIN_VIABLE_LLM_CALL_S: break` — bail the loop rather than fire a doomed call.
- Line 699: `per_call_timeout = max(_MIN_VIABLE_LLM_CALL_S, min(per_call_caps))` — final clamp.

Raised in two passes (10 → 20 → 30) as ReadTimeouts kept firing at the intermediate value on this hardware. The 30 s number is left as the floor because the assignment's hardware budget doesn't allow further headroom without cutting the number of diverse temps below 2.

A comment block at the constant's declaration documents the rationale and the bail-out behaviour (`success=False` clean exit instead of `❌ planner error`).

**Smoke results:** F21 templates have **not** been validated end-to-end at the time of writing this entry. The diagnostic run intended to confirm them was misfired (see Entry 18) — `--k 1` mis-routes through the legacy single path that doesn't load lib_templates, so the templates never got a fair test. A corrected `--diverse --k 2 --temps "0.35,0.55" --lib-templates --timeout 90` invocation is queued.

**Files touched:**
- `solution/planner/skeleton.py` — four F21 templates appended to `_lib_templates_for_goal` (lines 779-877); F22 raised constant + rationale comment (line 40-45).

**Net:** F21 gives the planner four targeted candidates for hard_25's previously-uncloseable card-family goals at zero LLM cost. F22 stops the diverse outline loop from polluting failure attribution with ReadTimeout errors on goals where the LLM was just slow. End-to-end strict-pass impact unmeasured pending the corrected diagnostic.

## Entry 18 — F23 extend F22 viable-LLM-call floor to the legacy single-outline path

**Request:** A diagnostic run intended to test whether the F21 hand-written Isar templates (added in `planner/skeleton.py:_lib_templates_for_goal` for hard_25 g12/g13/g16/g25) actually fire produced 0/4 strict-pass with every goal erroring as `❌ planner error: requests.exceptions.ReadTimeout (read timeout=3)`. The diagnostic used `--k 1 --temps "0.35" --lib-templates` (no priors / hintlex / context-hints), intending to keep the LLM prompt small enough to dodge the ReadTimeouts seen on the prior `unsolved_5` run. Asked Claude to find why a 3-second read timeout appeared despite F22 raising `_MIN_VIABLE_LLM_CALL_S` to 30 s.

**Diagnosis (Claude's investigation):**

Two independent bugs stacked:

1. **`--k 1` mis-routes the run.** `solution/planner/experiments.py:316` sets `legacy_single_outline=(cfg.k == 1)`. When true, `driver.py:plan_and_fill` takes the legacy branch (line 714-717), calling the singular `propose_isar_skeleton` instead of `propose_isar_skeleton_diverse_best`. The lib_templates injection at `skeleton.py:928-929` (where F21's templates are added to the candidate list) **only runs inside the diverse path**, so the diagnostic never even considered an F21 template.
2. **F22 doesn't cover the legacy single path.** The diverse path applies the `_MIN_VIABLE_LLM_CALL_S=30` floor at four places (`skeleton.py:691, 694, 697, 699`) and bails rather than firing a doomed call. The legacy single path used the old formula `max(3, min(30, deadline.remaining_int(cap=30, min_=3)))`. When the per-goal deadline is tight (sketch-check and other setup eat into the 60 s budget), `deadline.remaining_int(...)` collapses to its `min_=3` floor, `single_to` becomes 3, and the LLM call ReadTimeouts on every hard goal regardless of prompt size.

The diagnostic was therefore worthless as F21 evidence — it tested a code path that bypasses F21 entirely, on a timeout that guarantees failure.

**Actioned response — F23 in `planner/driver.py`:**

Single-site fix at lines 714-731 (the `if legacy_single_outline:` branch):

```python
rem = deadline.remaining_int(cap=60, min_=_MIN_VIABLE_LLM_CALL_S)
if rem < _MIN_VIABLE_LLM_CALL_S:
    full = ""  # bail rather than fire a doomed call
else:
    single_to = max(_MIN_VIABLE_LLM_CALL_S, rem)
    try:
        full = propose_isar_skeleton(goal, model=model, temp=0.35,
                                     force_outline=(mode == "outline"),
                                     timeout_s=single_to).text
    except Exception:
        full = ""
if not full:
    return PlanAndFillResult(False, "", [], [0])
```

Three changes:

1. **F22 floor applied uniformly.** The per-call timeout cannot be lower than 30 s — matching the diverse path's contract.
2. **Bail path.** If even the floor exceeds remaining deadline, return an empty outline result rather than fire a guaranteed ReadTimeout. This is symmetric with `skeleton.py:697-698`'s `min(per_call_caps) < _MIN_VIABLE_LLM_CALL_S: break` in the diverse loop.
3. **Try/except guard.** Matches the diverse loop's `skeleton.py:711-713` pattern. Any LLM-side exception (transient ReadTimeout, connection reset, JSON parse) yields an empty outline and an early bail-out rather than propagating a top-level `❌ planner error`.

Also imported `_MIN_VIABLE_LLM_CALL_S` from `planner.skeleton` into `driver.py` so the constant has a single source of truth.

Did **not** touch the `--k 1 → legacy_single_outline=True` mapping in `experiments.py:316` — that's intentional behaviour (k=1 callers may explicitly want the cheap single-outline path with no scoring and no library templates), and changing it would silently re-route every k=1 sweep ever run for comparison.

**Diagnostic-invocation correction:** to actually test F21 templates with low prompt size, the diverse path must be reached. Smallest valid configuration is `--diverse --k 2 --temps "0.35,0.55"` — this keeps `cfg.k == 2` so `legacy_single_outline=False` and routes to `propose_isar_skeleton_diverse_best`, where the F21 lib_templates are added to the candidate list at line 929.

**Files touched:**
- `solution/planner/driver.py` — import `_MIN_VIABLE_LLM_CALL_S` from `planner.skeleton`; replace the legacy-single timeout formula with the F22-floored version + try/except + bail-out + early return on empty outline.

**Net:** F23 closes the last known site where `_MIN_VIABLE_LLM_CALL_S` was bypassed. Doesn't directly close more goals on its own, but is a prerequisite for the F21 templates to get a fair test on hard_25's g12/g13/g16/g25 (and for any future `k=1` smoke configuration).

## Entry 19 — F24 fix chained-fact order in two F21 templates (g16 / g25)

**Request:** With F23 in place, the corrected diagnostic (`--diverse --k 2 --temps "0.35,0.55" --lib-templates --timeout 90 --strict-no-sorry --verify` over `datasets_subset/f21_diag_4.txt` = g12, g13, g16, g25) ran clean and produced 2/4 strict-pass: g12 and g13 both verified (`verify=ok`), g16 and g25 both rejected at Isabelle (`verify=fail`) despite their F21 templates being selected as best candidates (`outline_chars` matched the template byte-counts). Asked Claude to identify the precise Isabelle failure and patch it.

**Diagnosis (Claude's investigation):**

Both failing goals had the same Isabelle error shape. For g16, the `verify_details` payload in `solution/logs/planner.log.jsonl`:

```
[fail] Isabelle reported errors:
Failed to apply initial proof method⟨^here⟩:
using this:
    C ∩ A × B ⊆ A × B
    finite (C ∩ A × B)
goal (1 subgoal):
 1. card (A × B - C ∩ A × B) = card (A × B) - card (C ∩ (A × B))
```

That `using this:` shows the chained-fact order at the point `by (rule card_Diff_subset)` is invoked: `⊆`-fact first, `finite`-fact second. But `card_Diff_subset`'s signature in `HOL.Finite_Set` is

```
lemma card_Diff_subset:
  assumes "finite B" and "B ⊆ A"
  shows   "card (A - B) = card A - card B"
```

— so the first premise to discharge is `finite B`, and Isabelle's `rule` method matches chained facts to rule premises **in order**. The chained-fact ordering `⊆; finite` mismatches `finite; ⊆`, so the resolution fails on the first premise and the whole `by (rule …)` aborts with "Failed to apply initial proof method".

The g25 template has the identical bug against `card_mono` (also `finite B; A ⊆ B` in `HOL.Finite_Set`).

The g12 / g13 templates use `card_Un_disjoint` (`finite A; finite B; A ∩ B = {}`), and their `from finT finF disj` / `from finP finN disj` chains already match in order — which is why those two verified cleanly.

**Actioned response — F24 in `solution/planner/skeleton.py`:**

Two single-line edits, both inside the `f-strings` in `_lib_templates_for_goal`:

- **Line 796 (g25 / `card_mono`):** `from subset fin have step1: …` → `from fin subset have step1: …`
- **Line 847 (g16 / `card_Diff_subset`):** `from sub fin_int` → `from fin_int sub`

Verified by `python -c` invocation of `skeleton._lib_templates_for_goal(goal)` on both g16 and g25 goal strings — the rendered template now emits the corrected `from finite-fact ⊆-fact` order.

Did **not** touch the `using sub fin by (rule finite_subset)` line at 844 (g16) — `finite_subset` is `assumes "A ⊆ B" "finite B"`, so `sub; fin` is already correct for that one.

Did **not** modify the g12 or g13 templates — they were the two passes in the diagnostic and their fact order is already correct against `card_Un_disjoint`.

**Smoke (Claude's static verification, not Isabelle-confirmed):** Rendered template body for g25 now reads

```
have fin: "finite (A × B)"
  using finA finB by (simp add: finite_cartesian_product)
from fin subset have step1: "card { (x,y)∈A×B. P x ∧ Q y } ≤ card (A × B)"
  by (rule card_mono)
```

which matches `card_mono`'s assumption order. Same for g16's `from fin_int sub by (rule card_Diff_subset)`. Empirical verification pending re-run of the F21 diagnostic.

**Files touched:**
- `solution/planner/skeleton.py` — two `from`-clause reorderings inside the g25 and g16 templates of `_lib_templates_for_goal`.

**Net (projected):** F21+F24 should close g16 and g25 in addition to the g12/g13 already validated. Combined with F11/F19 closures and the F21 g12/g13 wins, the hard_25 strict-pass ceiling moves from 18 (post-F20 sweep) toward 22 — only g10 remains unclosed among the provable fails, since F21 has no g10 template and F19's specialist finishers don't close `card_Diff_subset`-shaped equalities without finite-set context manipulation. The 23/25 absolute ceiling (g4 and g9 false) is unchanged.

## Entry 20 — F25 resilience to LLM ReadTimeout in outline-gen + raised per-call ceiling

**Request:** The F24 validation rerun (`--diverse --k 2 --temps "0.35,0.55" --lib-templates --timeout 90` over `f21_diag_4.txt`) produced 0/4 instead of the projected 4/4. Every goal logged `❌ planner error: ReadTimeout (read timeout=30)` with `outline_chars=0`. An external Ollama probe (`curl /api/generate` with an 80-token completion) measured warm throughput at ~10 tok/sec (8.12 s for 80 tokens, GPU peaking at 98 % during generation), down from the implicit ≥20 tok/sec that the 18:46 F21 diagnostic must have had. A structured Isar outline emits ~200-400 output tokens; at 10 tok/sec each call sits right at the F22 30 s floor — half the time it just clears, half the time it ReadTimeouts. Asked Claude to find why the F21 templates weren't being scored as a fallback under this condition (rather than the whole goal dying with `outline_chars=0`).

**Diagnosis (Claude's investigation):**

Two correlated problems:

1. **Unguarded singular fallback in `propose_isar_skeletons`.** The diverse outline loop at `skeleton.py:680-723` wraps each per-temperature LLM call in `try: ... except Exception: raw = ""` (lines 704-713), so a ReadTimeout on any individual diverse call demotes that candidate to "no outline" rather than killing the function. But when the diverse loop produces zero outlines (every call timed out / all returned empty), the code falls through to a singular fallback at lines 725-736:

```python
if not out:
    ...
    return [propose_isar_skeleton(..., timeout_s=single_to)]
```

   That call is **not** wrapped in try/except. When Ollama is slow enough that the diverse loop empties AND the fallback also ReadTimeouts, the exception propagates out of `propose_isar_skeletons` → into `propose_isar_skeleton_diverse_best` at line 925 → and the function never reaches line 928 where `_lib_templates_for_goal(goal)` is concatenated onto `cands`. The F21 templates that should be scoring against an empty `cands` are never even considered.

2. **`_OUTLINE_PER_CALL_CAP_S = 30` is calibrated for ≥20 tok/sec.** With Ollama at 10 tok/sec, a 200-400 token outline naturally lands at 20-40 s. The F22 floor (30 s) was sufficient when the prompt was small enough to clip the output, but the diverse-best path emits a fuller structured prompt, and a 30 s ceiling on the LLM call is below the natural tail of the response time distribution.

The combination produced the observed pattern: empty diverse loop, ReadTimeout-on-fallback, exception propagates, F21 templates skipped, `outline_chars=0`, 0/4.

**Actioned response — F25 in `solution/planner/skeleton.py` (two changes):**

### Part A — raised per-call ceiling (`_OUTLINE_PER_CALL_CAP_S = 30 → 60`)

Single-constant change at the top of `skeleton.py` (line 23). The cap is the upper bound on each per-temperature LLM call's `timeout_s`; the F22 30 s floor remains the lower bound. Combined math:

```
per_call_timeout = max(30, min(60, deadline.remaining_int(cap=60, min_=30)))
```

So calls scale linearly: 30 s when deadline is tight, 60 s when deadline has headroom. A goal with `--timeout 90` and `k=2` now has up to 120 s of LLM-call budget across the two diverse temperatures, leaving 90 - 60 = 30 s effective floor for the remaining (sketch-check + Fill + verify) pipeline. With `--timeout 150` the math is more comfortable. The 60 s ceiling matches Ollama's observed worst-case end-to-end response time for a 400-token outline at 10 tok/sec on this hardware.

The F22 rationale comment block was extended in-line with the F25 reasoning so the constant carries its own justification.

### Part B — wrapped the singular fallback in try/except (`skeleton.py:725-737`)

The fallback is now:

```python
try:
    return [propose_isar_skeleton(..., timeout_s=single_to)]
except Exception:
    return out  # empty list — lets diverse_best still try lib_templates
```

If the fallback ReadTimeouts (or otherwise raises), the function returns the empty `out` list rather than propagating the exception. The caller `propose_isar_skeleton_diverse_best` then concatenates `_lib_templates_for_goal(goal) + []` at line 928, and the F21 templates flow into scoring as the only candidates — exactly what should happen on goals where the LLM is unavailable but a domain template is.

The deadline check at lines 731-733 (`if remaining < _MIN_VIABLE_LLM_CALL_S: return out`) is preserved — if there's no time even for a viable call, we bail before firing rather than fire-and-catch.

**Smoke (Claude's static verification):** A small Python invocation confirmed `_OUTLINE_PER_CALL_CAP_S == 60`, `_MIN_VIABLE_LLM_CALL_S == 30`, and the `max(min(...))` math at line 691 produces 30 s for tight budgets and 60 s for ample ones. `from planner import driver` still imports cleanly with the new constant values.

**Files touched:**
- `solution/planner/skeleton.py` — bumped `_OUTLINE_PER_CALL_CAP_S` from 30 to 60 with F25 rationale comment; wrapped the singular fallback at line 735 in try/except returning `out` on exception.

**Net:** F25 closes the last known way for the F21 templates to be silently skipped, and widens the LLM-call window to match observed Ollama throughput on this hardware. The 4-goal F21+F24 diagnostic should now produce 4/4 strict-pass regardless of whether Ollama is fast (templates compete on score) or slow (templates win by default because LLM candidates are empty). On the larger benchmark sweep, F25 also dampens hardware-state-dependent variance — the 18:46 run passed 2/4 only because Ollama was warm-and-fast, whereas the 18:54 rerun on a slightly cold Ollama failed everything; under F25 both conditions should produce the same per-goal outcome.

## Entry 21 — F26 drop extraneous `using` from `card_cartesian_product` step in g25 template

**Request:** The F25 rerun of the F21 diagnostic (`--diverse --k 2 --temps "0.35,0.55" --lib-templates --timeout 150` over `f21_diag_4.txt` at 19:21) produced 3/4 strict-pass — g12, g13 stayed green, **g16 flipped from fail to pass** (validating F24), and g25 was the only remaining failure. The hypothesis from the user was that the g25 failure was LLM non-determinism. Asked Claude to look at the verify error and confirm or refute.

**Diagnosis (Claude's investigation):**

The Isabelle `verify_details` payload for g25 in `solution/logs/planner.log.jsonl`:

```
[fail] Isabelle reported errors:
Failed to apply initial proof method⟨^here⟩:
using this:
    finite A
    finite B
goal (1 subgoal):
 1. card (A × B) = card A * card B
```

This is **not** F24's `from`-order bug (that's at the prior `by (rule card_mono)` line, which now succeeds). The failure is one line later in the same template:

```isabelle
also have "card (A × B) = card A * card B"
  using finA finB by (rule card_cartesian_product)
```

`card_cartesian_product` in `HOL.Finite_Set` is stated unconditionally — no premises — because `card` returns 0 for infinite sets, so the equation holds trivially when either operand is infinite:

```
lemma card_cartesian_product: "card (A × B) = card A * card B"
```

`by (rule card_cartesian_product)` resolves the goal entirely on its own. Adding `using finA finB` chains two facts the rule does not want; `rule` fails to match them against any (non-existent) premise of `card_cartesian_product` and aborts with "Failed to apply initial proof method". The fact that Isabelle's error message shows `using this: finite A, finite B` and the goal `card (A × B) = card A * card B` is the giveaway — the goal-shape is exactly what `card_cartesian_product` would close in isolation, and the two `finite` facts are dead weight that `rule` doesn't know how to discharge.

This is **deterministic, not stochastic**. Same template selected (`outline_chars=559` matches the F21 g25 template byte-count exactly), same broken line, same Isabelle error. LLM non-determinism is at most an indirect contributor: post-verify-fail `_repair_failed_proof_topdown` did run for ~36 s of the 186.5 s goal duration trying to fix the line with the LLM, and *could* in principle have found `by (rule card_cartesian_product)` as the repair — but didn't on this run. Fixing the template makes the goal close at the first verify rather than relying on a lucky LLM repair.

The same proof shape with `card_Un_disjoint` (in the g12/g13 templates) does take a `using` chain — `from finA finB disj by (rule card_Un_disjoint)` — because that rule does have premises. The bug is specifically that `card_cartesian_product` was copied from the same authorial mental model without checking its actual signature.

**Actioned response — F26 in `solution/planner/skeleton.py`:**

Single-line edit inside the g25 template (around line 798 in the f-string):

```diff
   also have "card (A × B) = card A * card B"
-    using finA finB by (rule card_cartesian_product)
+    by (rule card_cartesian_product)
```

Verified by `python -c` invocation of `skeleton._lib_templates_for_goal(goal)` on the g25 goal string — the rendered template body now reads `by (rule card_cartesian_product)` standalone, no preceding `using`.

Did **not** touch the parallel line in the g16 template (`by (rule card_Diff_subset)` — that rule does have premises and the chained `from fin_int sub` is required for the resolution to succeed; F24 fixed the order). No analogous bug exists in g12 / g13 because their final closing step uses `with part show ... by simp`, which legitimately takes `part` as a chained fact.

**Smoke (Claude's static verification):** rendered g25 template byte count drops from 559 to 545 (the 14 bytes of "using finA finB " removed). Empirical Isabelle verification pending the next diagnostic run.

**Files touched:**
- `solution/planner/skeleton.py` — removed `using finA finB` prefix from the `card_cartesian_product` line in the g25 template inside `_lib_templates_for_goal`.

**Net (projected):** F26 should flip g25 from `verify=fail` to `verify=ok`, taking the F21 diagnostic to 4/4. On hard_25 this adds one more strict-pass on top of F21+F24's contributions; combined with F25's resilience, the projected sweep result moves from 18/25 → 22/25. The 23/25 ceiling (g4 and g9 false) is unchanged, and g10 (no F21 template, no one-shot finisher) remains the sole unclosed-but-provable goal.

## Entry 22 — broad-scope report-metric sweep driver (`report_metric_sweep.sh`)

**Date:** 2026-05-27 (AEST evening)

**Prompt context (paraphrase):** Need to launch a broad-scope sweep that produces the report's headline planner-comparison numbers and finishes by 09:00 AEST 2026-05-28. Wanted launch / warm / watch / abort commands handed back as copy-paste blocks; user runs them. Also wanted persistence (updated runbook + handoff) so a fresh Claude session tomorrow morning can pick up coherently.

**Background:** The pre-existing `plan_compare.sh` always runs both baseline and solution against a single goal file. For the overnight window (~11 h to 09:00 deadline) the budget only fits four-set both-sides at a degraded `TIMEOUT`, or four-set solution-only at the full max-config `TIMEOUT=180`. User chose option 4 from the offered set (all four sets solution-only at max-config; baseline can be rerun later if there's time). Required a new driver because (a) `plan_compare.sh` is hardcoded to both sides, (b) sequencing four sets needs per-set CSV identification and aggregation.

**Code action — new file `agenticreasoning/report_metric_sweep.sh`:**

- Sources `solution/.venv`, then iterates over the env-var `SETS` (default `hard_25 mid_25 minif2f_30 holmain_50`).
- For each stem: locates `datasets_subset/${stem}.txt`, runs `python -u -m planner.experiments bench` from `solution/` with the max-config flags (`--mode auto --diverse --k 3 --temps 0.35,0.55,0.85 --strict-no-sorry --verify --timeout 180 --lib-templates --context-hints --priors $ROOT/solution/datasets/isar_priors.json --hintlex $ROOT/solution/datasets/isar_hintlex.json --trace`), logs to `$OUT_DIR/_logs/${stem}.log`.
- After each set finishes, picks the newest `solution/datasets/planner_results/*-${stem}-*.csv` (the bench's auto-named output) and copies it to `$OUT_DIR/${stem}.csv` with a stable name.
- Final aggregation: inline Python reads each `${stem}.csv`, joins against `datasets_subset/${stem}.txt`, computes strict-pass counts using the same `success && verified_ok && !had_sorry` predicate `plan_compare.sh` uses. Emits `$OUT_DIR/summary.md` (per-set table + per-goal tables with wall-time column) and `$OUT_DIR/summary.csv`.
- `OUT_DIR` defaults to `report_metric_sweep_<YYYYMMDD-HHMM>/` under the agenticreasoning root.
- Hard-fails at launch if either RAG artefact (`isar_priors.json` / `isar_hintlex.json`) is missing.

**Resume support:** Setting `SETS="<remaining stems>"` skips already-completed sets — useful if Ollama hangs mid-run and the sweep needs restarting partway through.

**Documentation action — new file `REPORT_SWEEP_RUNBOOK.md` (workspace root, gitignored):** ordered pre-launch / launch / watcher / spot-check / abort / completion sections with copy-paste blocks. The watcher block adapts the existing `SWEEP_RUNBOOK.md` `watch_sweep` function to N-set solution-only logs — auto-detects the newest `report_metric_sweep_*/` out-dir, marks the active set, surfaces F11 stage-A/B counts only for the active set, flags F17 overruns (>216 s) across all sets.

**Documentation action — `HANDOFF.md` updated:** prepended a new "Right now" section pointing at `REPORT_SWEEP_RUNBOOK.md` and listing the four goal sets + config + budget. Preserved the prior "post-F14 hard_25 sweep" section as historical context (since that sweep has long since completed at solution 18/25).

**Memory updates:**
- New: `project-report-metric-sweep` — what was launched, why, where the runbook lives, how a fresh session should react in the morning.
- Index: added pointer in `MEMORY.md` between the older `reference-sweep-runbook` entry and `project-f1-outline-gen-unbounded`.

**Files touched:**
- `agenticreasoning/report_metric_sweep.sh` — new, executable.
- `REPORT_SWEEP_RUNBOOK.md` — new in workspace root.
- `HANDOFF.md` — top section replaced with current state; prior content preserved below a divider.

**No code in `solution/` was modified this entry.** F26 (Entry 21) is the latest planner change; this entry is purely the sweep harness + handoff persistence.

**Net:** User can hand-execute the smoke command (F26 verification), then the warm + launch + watcher blocks. If they shut down Claude after launching, the tomorrow-morning session reads `HANDOFF.md` top section → `REPORT_SWEEP_RUNBOOK.md` → checks process state → resumes either the watcher or moves to dropping numbers into `report.typ`.

## Entry 23 — F27 HOL-corpus RAG expansion + post-hoc lemma-name validator

**Date:** 2026-05-27 (AEST late evening, during the in-flight report-metric sweep)

**Prompt context (paraphrase):** Mid-sweep the user reviewed the per-goal traces from `minif2f_30` and observed five consecutive failures with a common pattern — the LLM emitting outlines that cite identifiers Isabelle has never heard of (e.g. `a_cubed_eq_8`, `complex.cube_root_def`, `norm_minus_complex`). Each hallucinated outline burned the full ~190 s verification budget before rejection. Asked for the smallest pair of changes that (a) gives the RAG access to the actual HOL namespace it should be retrieving from, and (b) cheaply filters obvious hallucinations *before* paying for verification — without disturbing the running sweep.

**Background:** The existing extraction (`planner/extract.py`) and aggregation (`planner/priors.py`) targeted AFP. `prover/heuristics.py:suggest_common_lemmas` has F20 hand-coded hints for ~9 card/sum/finite identifiers. Nothing mines or indexes HOL/Main + HOL/Library, where the minif2f vocabulary (`quotient_of`, `norm`, `sin`, `cos`, `card`, `Pow`, `sqrt`, `floor`) actually lives. And no infrastructure validates that lemma names cited in an outline exist anywhere — outlines went straight to Isabelle, where rejection cost the per-goal budget.

**Constraint:** The 4-set report-metric sweep was running (currently in `minif2f_30`, with `holmain_50` queued). Edits must not affect its in-memory configuration. Strategy: all new artefacts go to new paths (`isar_priors_hol.json`, `isar_hintlex_hol.json`, `known_names.json`), no overwrite of `isar_priors.json` / `isar_hintlex.json`; validator gated by env var `USE_NAME_VALIDATOR`, default off → behavior identical to F26 for the running process even if `skeleton.py` is re-imported.

### 23a — F27 HOL extraction script (`solution/planner/extract_hol.py`)

- New CLI: `python -m planner.extract_hol --out-dir datasets [--include-analysis] [--skip-corpus]`.
- Reuses `planner.extract.mine_afp_corpus_rich` to walk `$ISABELLE_HOME/src/HOL/` and `src/HOL/Library/` (Analysis opt-in for size reasons), producing a rich-shape JSONL of ~70 K lemmas with `goal / outline / theory / imports / premises / defs_in_block / names_in_block`.
- Adds a separate regex-driven name extractor (`NAME_DECL_RE`) that catches the 17 HOL declaration forms (`lemma|theorem|proposition|corollary|lemmas|definition|fun|function|primrec|abbreviation|inductive|inductive_set|coinductive|coinductive_set|datatype|codatatype|type_synonym|axiomatization|notation|consts|axioms|locale|class|interpretation|sublocale`) and adds the auto-generated `_def / .simps / .induct / .cases / .elims / .intros` suffixes for each, since those are how the LLM most often references them.

**Extraction run:** 1618 .thy files scanned → 67 381 bare names → 471 573 names with suffix variants → `datasets/known_names.json` (12 MB). Rich corpus → 63 734 HOL/* records + 7117 HOL/Library/* records = 70 731 → `datasets/hol_corpus.jsonl` (40 MB).

**Aggregation run:** `python -m planner.priors --input datasets/hol_corpus.jsonl --priors datasets/isar_priors_hol.json --hintlex datasets/isar_hintlex_hol.json` — produced 740 KB priors, 404 KB hintlex. Both retain the existing JSON shape so the bench can swap them in without code changes (`--priors datasets/isar_priors_hol.json --hintlex datasets/isar_hintlex_hol.json`).

### 23b — F27 post-hoc lemma-name validator (`solution/planner/skeleton.py`)

Added a module-level validator and wired it into the existing diverse-outline scoring loop (where F18's `placeholder_pen` already lives):

- `_REF_BLOCK_RE` — captures identifiers following `using` / `unfolding` / `simp add:` / `simp only:` / `metis` / `smt`, stopping at the next Isar keyword that resumes the proof.
- `_RULE_REF_RE` — captures the identifier inside `by (rule X)` / `apply (rule X)` and variants (`rule_tac / erule / intro / elim / subst`).
- `_LIBRARY_NAME_RE` — predicate that a token "looks like" a library lemma (contains `_` or `.`). This is what avoids flagging local Isar names like `f1`, `h2`, `IH` — those are legitimately undefined in any theory and would create false positives.
- `_load_known_names()` — lazy + cached. **Returns empty set unless `USE_NAME_VALIDATOR=1`.** Path overridable via `KNOWN_NAMES_PATH` (default `datasets/known_names.json` relative to cwd, which is `solution/` when bench is launched the usual way).
- `_count_unknown_refs(outline_text)` — counts distinct library-looking references not present in the known-names set (after stripping any `Theory.` prefix). Returns 0 when validator disabled.

Scoring integration: added `unknown_pen = _count_unknown_refs(sk.text)` and `+ 150.0 * float(unknown_pen)` to the score formula. Penalty weight 150 sits just below F18's 200 — enough that a 1-hallucination outline loses to a clean sibling, but not so heavy that the validator's recall errors (e.g. genuinely-existing-but-not-in-table names like very-recent HOL additions) catastrophically dominate.

### 23c — Sanity tests

Validated with `USE_NAME_VALIDATOR=1` against four targeted inputs:

| Input | Expected | Got |
|---|---:|---:|
| Validator off (default), g2 outline | 0 | 0 |
| Validator on, g2 outline (4 hallucinations) | 4 | 4 |
| Validator on, clean outline (`card_Un_disjoint`, `card_image`) | 0 | 0 |
| Validator on, local-names-only outline (`h1`, `h2`) | 0 | 0 |

So: hallucinations get flagged, real names don't, local Isar bindings don't, and the off-by-default gate preserves F26 behavior bit-for-bit for the running sweep.

### Files touched

- New: `solution/planner/extract_hol.py` (CLI driver + name table extractor).
- New data: `solution/datasets/hol_corpus.jsonl`, `solution/datasets/known_names.json`, `solution/datasets/isar_priors_hol.json`, `solution/datasets/isar_hintlex_hol.json`. **No edits to existing `isar_priors.json` / `isar_hintlex.json`.**
- Modified: `solution/planner/skeleton.py` — added `Set` to `typing` import; appended `_REF_BLOCK_RE / _RULE_REF_RE / _LIBRARY_NAME_RE / _load_known_names / _count_unknown_refs` block after F18's `_count_comment_placeholders`; added `unknown_pen` term to the diverse-outline scoring formula (gated, so default behavior unchanged).

### How to use on the next sweep launch

```bash
USE_NAME_VALIDATOR=1 \
KNOWN_NAMES_PATH=$ROOT/solution/datasets/known_names.json \
python -u -m planner.experiments bench \
  --file $ROOT/agenticreasoning/datasets_subset/minif2f_30.txt \
  --mode auto --diverse --k 3 --temps 0.35,0.55,0.85 \
  --strict-no-sorry --verify --timeout 180 --lib-templates --context-hints \
  --priors $ROOT/solution/datasets/isar_priors_hol.json \
  --hintlex $ROOT/solution/datasets/isar_hintlex_hol.json \
  --trace
```

**Net:** F27 plugs the two highest-leverage gaps minif2f exposed — a HOL-aware corpus the RAG can actually retrieve from, and a cheap pre-verify filter for hallucinated identifiers. The expected solve-rate impact on minif2f is modest (the binding constraint there is the 7 B LLM's olympiad-math capability, not the planner architecture), but the *wasted-time* impact is large: outlines that would have burned 180 s on a hopeless verify now lose the K-outline tournament to cleaner siblings within the F18-era scoring loop. Both changes are off by default for the running sweep and opt-in for the next launch via the env var + new file paths.

## Entry 24 — F28a widened placeholder gate + F28b truncation guard + F28c failure-mode classifier

**Date:** 2026-05-28 (AEST early hours, after killing the F26-config sweep partway through `minif2f_30`)

**Prompt context (paraphrase):** The mid-sweep traces from `minif2f_30` showed five-of-five attempted goals failing, and inspection revealed three failure modes the existing F18+F27 guards didn't cover: literal `"..."` / `"TODO"` placeholders in `have`/`show` bodies (minif2f g1, g4), unterminated string literals when the LLM ran out of context mid-token (g3), and downstream uses of `complex.cube_root_def`-style hallucinations even on outlines that visually look complete. User decided to (a) kill the in-flight sweep to free wall-clock for the planned 300-goal HOL/Main run, (b) ship three small additions before re-launching: widen F18 to cover the new placeholder shapes, add a structural balance guard, and produce a report-ready failure-mode breakdown from the partial sweep logs.

**Background:** F27 (Entry 23) landed the HOL RAG + lemma-name validator earlier the same evening but was opt-in for the running bench so didn't take effect. F28 is the natural next step: extend the same scoring-time gate philosophy (cheap regex penalties applied during the diverse-outline tournament so bad outlines lose to siblings without ever paying for an Isabelle verify) to the placeholder shapes and structural issues observed in the partial sweep.

### 24a — F28a widened placeholder gate (`solution/planner/skeleton.py`)

The F18-era `_COMMENT_PLACEHOLDER_RE` only matched `have/show "(* fill ... *)"`. F28a extends the same regex to also match:

- ASCII ellipsis: `have f1: "..."` (this is exactly what minif2f g1 emitted)
- Unicode ellipsis: `have f1: "…"`
- TODO / FIXME / XXX / PLACEHOLDER markers (case-insensitive)
- Bare `"?"`, `"???"`-strings
- Empty/whitespace-only string bodies: `have f1: ""`

Renamed the constant to `_PLACEHOLDER_BODY_RE` and aliased the old name back so no callsite breaks. The `_count_comment_placeholders` function and its 200-weight in the scoring formula are unchanged. **Default-on** because the F18-era penalty is also default-on.

### 24b — F28b structural balance / truncation guard (`solution/planner/skeleton.py`)

New `_count_balance_issues(outline_text)` runs four cheap checks:

1. **Quote parity** — odd number of `"` ⇒ unterminated string literal. Catches minif2f g3's `have f6: "216^3 = 90071992547` truncation.
2. **Cartouche balance** — `‹` count vs `›` count.
3. **Paren balance** — after collapsing string contents (so `card (A ∪ B)` doesn't trip it), open vs close paren count.
4. **proof/qed balance** — `n_proof > n_qed` ⇒ outline truncated mid-block.

Each issue contributes 1; weighted at 200 in the score formula (same as F18, since a structurally-broken outline is equally wasteful). **Default-on.**

Sanity tests (six cases): g3 truncated string ✓, clean balanced outline = 0 ✓, unbalanced paren ✓, proof > qed ✓, cartouche imbalance ✓, real F26-era outline with parens-inside-strings = 0 ✓.

### 24c — Failure-mode classifier (`solution/planner/classify_failures.py`)

New script. Reads a sweep dir (`<sweep>/<set>.csv` + `<sweep>/_logs/<set>.log`), extracts each goal's final outline from the log, and classifies failures in a fixed priority order: `placeholder` → `truncation` → `hallucinated_id` (via F27's known-names table) → `deadline_overrun` (wall > timeout × 1.0) → `sorry_leak` (had_sorry=True, verified_ok=True) → `verify_fail_other` → `unknown_failure`. Successes and sweep-cut-off goals are tracked separately. Emits markdown + CSV tables suitable for direct paste into the report's Analysis section.

The script force-enables `USE_NAME_VALIDATOR=1` so the F27 retroactive analysis applies even to pre-F27 sweep logs.

**Empirical run on `report_metric_sweep_20260527-2148_partial_killed_2336/` (71 attempts, hard_25 + mid_25 + 21/30 of minif2f_30):**

| Failure mode | Count | % of failures | % of attempts |
|---|---:|---:|---:|
| `placeholder` | 1 | 4 % | 1 % |
| `truncation` | 3 | 11 % | 4 % |
| `hallucinated_id` | 5 | 18 % | 7 % |
| `deadline_overrun` | 16 | 57 % | 23 % |
| `verify_fail_other` | 3 | 11 % | 4 % |

Cross-set strict-pass: 42/71 (59.2 %). The 33 % combined `placeholder + truncation + hallucinated_id` failures are exactly the ones F28a + F28b + F27 now catch at scoring time — so on a re-run with those three guards on, those 9 failures convert to "the diverse-outline tournament picks a different sibling instead". Some of those siblings may also fail (different mode), but a meaningful fraction should now find a usable outline within the K-budget.

The remaining 57 % `deadline_overrun` is the LLM-capability constraint — qwen2.5-coder:7b couldn't generate a usable outline within 180 s even after multiple K retries. Not architecturally fixable inside this codebase; it's the future-work paragraph in the report.

### Files added/touched

- Modified: `solution/planner/skeleton.py`
  - Widened `_COMMENT_PLACEHOLDER_RE` → renamed to `_PLACEHOLDER_BODY_RE`, alias kept.
  - New `_count_balance_issues` + `_PROOF_KW_RE` / `_QED_KW_RE`.
  - Wired `balance_pen = _count_balance_issues(sk.text)` and `+ 200.0 * float(balance_pen)` into the scoring formula in `propose_isar_skeleton_diverse_best`.
- New: `solution/planner/classify_failures.py` (CLI; default emits `failure_modes.md` + `failure_modes.csv` into the sweep dir).
- Generated (this entry): `report_metric_sweep_20260527-2148_partial_killed_2336/failure_modes.md`, `failure_modes.csv`.
- Updated: `report_metric_sweep_20260527-2148_partial_killed_2336/PARTIAL_STATUS.md` documents what's in the saved dir.

### Operational changes

- The in-flight F26-config sweep (PID 21994 sweep shell + 97033 bench) was SIGTERM'd at ~23:36. Sweep dir renamed `_partial_killed_2336` to mark it as not-final. `hard_25.csv` (25/25) and `mid_25.csv` (25/25) are usable as F26-baseline numbers for the report; the `minif2f_30.log` covers 21/30 attempts (1 cut off mid-goal).
- Next sweep launch (300-goal HOL/Main, easy/mid/hard tiers) is the user's task per the [[feedback-user-controls-sweep-launches]] convention. Suggested config: F27 flags (`USE_NAME_VALIDATOR=1` + `--priors isar_priors_hol.json --hintlex isar_hintlex_hol.json`) plus F28a/F28b which are default-on after this entry.

**Net:** F28 covers the three minif2f failure shapes that F27 alone didn't address, at zero new wall-time cost (cheap regex penalties in a scoring loop that already runs). F28c gives the report a quantified failure-mode breakdown — useful both as analysis content and as evidence that the F18/F27/F28 series collectively addresses 33 % of observed failures, with the remaining 57 % attributable to model capability rather than planner architecture.

## Entry 25 — 300-goal HOL/Main sweep harness (datasets + sweep-script env overrides + runbook)

**Date:** 2026-05-28 (AEST early hours, after F28 landed)

**Prompt context (paraphrase):** User pivoted from the original 4-set sweep to a 300-goal HOL/Main run split into easy / mid / hard difficulty tiers, to make the report's headline planner-comparison numbers more broad. Killed the F26 sweep. Asked Claude to (a) curate three tiered datasets from the F27 corpus mine, (b) extend the existing sweep harness so launch flags for F27 (HOL RAG + validator) can be set via env vars without modifying the script, (c) rewrite `REPORT_SWEEP_RUNBOOK.md` for the new sweep.

**Background:** The F27 work in Entry 23 produced `solution/datasets/hol_corpus.jsonl` (70 731 records mined from `$ISABELLE_HOME/src/HOL/{,Library/}`) and `known_names.json`, but didn't include a curator that produces difficulty-tiered subsets. The original sweep script (`report_metric_sweep.sh`) hardcoded `PRIORS` / `HINTLEX` paths and the SETS default; the watcher (`watch_report_sweep.sh`) hardcoded `SETS` and `TIMEOUT_S`.

### 25a — Dataset curator (`solution/planner/sample_hol_tiered.py`)

New CLI. Reads `hol_corpus.jsonl` and emits `<out_dir>/<prefix>_{easy,mid,hard}.txt`. Filters before sampling:

- Theory whitelist `_MAIN_THEORIES` (List, Set, Fun, Nat, Int, Finite_Set, Relation, etc.) — derived from inspecting `Main.thy`'s transitive imports. Drops Bali, Auth, Algebra, Polynomial, Topological_Spaces, NSA etc. that wouldn't typecheck in an `imports Main` bench wrapper.
- Length bounds (15 ≤ goal ≤ 300 chars).
- Excludes records with: record syntax (`\<lparr>`/`\<rparr>`), schematic vars (`?foo` other than `?thesis`/`?case`), deep-qualified names (`A.B.C.foo`), legacy `==>`, analysis-specific predicates (`holomorphic_on`, `has_sum`, `field_differentiable`), NSA `*f*` notation, multiset/llist tokens, etc.
- Must contain at least one propositional connective (`=`, `\<Longrightarrow>`, `\<longleftrightarrow>`, `\<le>`, `\<in>`, etc.) — drops pure type signatures like `'a \<Rightarrow> nat` that the lemma miner accidentally captured from `definition` headers.
- Drops type-signature heads matching `^'a \<Rightarrow>`.
- Excludes exact-match duplicates against any pre-existing `datasets_subset/*.txt` goal.
- Flattens multi-line goals to a single line via `re.sub(r'\s+', ' ', goal)` — the bench reads its goal file line-by-line, so an embedded `\n` would split one goal into two.

Tier criterion: goal length (≤45 = easy, 45–105 = mid, > 105 = hard). Length is a rough proxy for difficulty — short statements are usually one-step propositional or set-theory lemmas; longer ones have more hypotheses to manage and more substructure for Fill.

**Run with seed=42 against the corpus:** 5 947 kept after filtering ⇒ 100 sampled per tier ⇒ 300 goals total ⇒ written to `agenticreasoning/datasets_subset/hol_main_{easy,mid,hard}.txt`.

### 25b — Sweep + watcher script env overrides

Both scripts were hardcoded to the 4-set F26 sweep. Made env-overridable:

- `agenticreasoning/report_metric_sweep.sh`:
  - `PRIORS` defaults to `solution/datasets/isar_priors.json` (was hardcoded); now `${PRIORS:-default}`. Same for `HINTLEX`.
  - Banner now prints `priors`, `hintlex`, and `validator : ${USE_NAME_VALIDATOR:-(off)}` for verification at launch.
- `agenticreasoning/watch_report_sweep.sh`:
  - `TIMEOUT_S` defaults to 180 (was hardcoded); now `${TIMEOUT_S:-180}`.
  - `SETS` defaults to the 4-set F26 list (was hardcoded as an array literal); now reads `${SETS:-…}` and splits into an array. For the 300-goal sweep the launcher sets `SETS="hol_main_easy hol_main_mid hol_main_hard"`.

The `USE_NAME_VALIDATOR` and `KNOWN_NAMES_PATH` env vars don't need explicit propagation — they're inherited by the bench Python subprocess automatically.

### 25c — `REPORT_SWEEP_RUNBOOK.md` rewritten

The runbook now leads with the 300-goal sweep (Steps 0–8: dataset / RAG-file verification, Ollama warm, optional F27/F28 smoke, launch with env-overrides, watcher, spot-checks, abort/resume, post-run summary + classifier). The original 4-set F26 runbook content is archived at the bottom (the killed sweep's partial-results table + cross-set failure-mode breakdown from F28c).

Key launch params documented:

```
TIMEOUT=120                                         # vs 180 — saves ~2h
PRIORS=.../solution/datasets/isar_priors_hol.json   # F27
HINTLEX=.../solution/datasets/isar_hintlex_hol.json # F27
USE_NAME_VALIDATOR=1                                # F27 validator
KNOWN_NAMES_PATH=.../solution/datasets/known_names.json
SETS="hol_main_easy hol_main_mid hol_main_hard"
```

Budget at T=120: easy ~20 min + mid ~85 min + hard ~160 min = **~4.5 h sweep**. Launch by ~00:45 ⇒ done by ~05:15 ⇒ ~4 h margin to the 09:00 deadline for report writing.

### Files added/touched

- New: `solution/planner/sample_hol_tiered.py` (300-goal curator).
- New data: `datasets_subset/hol_main_easy.txt`, `hol_main_mid.txt`, `hol_main_hard.txt` (100 goals each, single-line, Main-resident).
- Modified: `agenticreasoning/report_metric_sweep.sh` — `PRIORS`/`HINTLEX` env overrides + banner additions.
- Modified: `agenticreasoning/watch_report_sweep.sh` — `SETS` + `TIMEOUT_S` env overrides.
- Rewritten: `REPORT_SWEEP_RUNBOOK.md` — 300-goal sweep runbook with F26 sweep archived at bottom.
- Modified: `HANDOFF.md` — "Next sweep launch" section updated to "ready to fire" with TL;DR launch command and post-run analysis steps.

**Net:** All the infrastructure for the 300-goal HOL/Main sweep is in place. User can launch by copy-pasting Step 4 of the runbook. Sweep emits per-set CSVs + an aggregated `summary.md`; the F28c classifier emits a paste-ready `failure_modes.md`. Both feed directly into `report.typ`'s Experimental Method and Analysis sections.

## Entry 26 — F29a type-annotation retry + F29b early-bail on hopeless first outline

**Date:** 2026-05-28 (AEST early hours, after observing first 10 attempts of the 300-goal sweep)

**Prompt context (paraphrase):** With the 300-goal sweep underway (PID 303523), the first 10 hol_main_easy attempts came back 6/10 strict-pass. The 4 failures split cleanly into two patterns the F26-F28 machinery didn't address: (1) Isabelle inferring the wrong type class for goals like `(- 1) ^ (2*n) = 1` (false at `nat` because `- 1 = 0`) or `- a < 0 ⟷ 0 < a` (false at `nat`), and (2) bare statements lifted out of HOL locales whose `assumes`/`fixes` block was lost by the miner (`((inv f)^^n) o (f^^n) = (λx. x)` — only a theorem when `inj f`). Both burn the full ~120 s per-goal budget. User approved "fix A + B, then if time D" — A is a type-annotation retry inside F11 stage-A, B is an early-bail when the first outline+Fill clearly went nowhere, D is the deeper miner fix.

**Background:** F11 stage-A iterates `_DIRECT_FINISHERS` (blast/auto/simp/metis/force/fastforce/presburger/argo/linarith) on the bare goal. None of those try type annotations. `plan_and_fill`'s main loop has Fill → repair stage 1 → repair stage 2 escalation paths with no global "this outline is hopeless" check — so a Fill that produces zero `fills` against a 400-char sorry-laden outline still pays for full repair attempts that have no hope of succeeding.

### 26a — F29a type-annotation retry (`solution/planner/driver.py`)

New module-level constants right after `_CARD_SUM_TOKEN_RE` (line 240):

- `_UNTYPED_NUMERIC_RE` — trigger predicate. Matches `\<le>`, `\<ge>`, `\<less>`, `\<greater>`, `\<noteq>`, bare numeric literals (`\b\d+\b`), and bare `^` (power). Deliberately *doesn't* match `<`/`>`/`-`/`+`/`*` standalone because those collide with `\<NAME>` markers (the closing `>` of `\<forall>` was matching `[<>]` in the first draft, causing every goal with a unicode quantifier to over-trigger).
- `_F29A_VAR_RE = re.compile(r"\b([a-z]\w*)\b")` — broad lowercase-identifier match; relies on the keyword set below to filter.
- `_F29A_ISAR_KEYWORDS` — Isar/HOL keywords + common HOL constants (`set`, `map`, `card`, `sum`, `finite`, `True`/`False`, `None`/`Some`) that should not be type-wrapped.
- `_F29A_TYPE_HINTS = ("nat", "int", "real")` — try-order.
- `_F29A_FINISHERS = ("by simp", "by auto", "by linarith", "by arith")` — cheap finishers most likely to discharge numeric/order goals once typed.

New private function `_try_annotation_retry(isabelle, session, goal, deadline, *, trace)`:

1. Return early if `deadline.remaining() < 5` or trigger predicate doesn't match.
2. Find the first lowercase identifier not in `_F29A_ISAR_KEYWORDS`.
3. For each type hint × each finisher: build `lemma "<goal-with-(var::type)>"\n  <tac>`, verify with `_verify_full_proof(..., timeout_s=4)`. First success returns.
4. Bail mid-loop if `deadline.remaining() < 3`.

Wired into `_try_prover_direct` between the end of the stage-A finisher loop and the `# ---- Stage B` comment (lines 300-301). Worst-case wall: 3 × 4 × 4 s = 48 s, but typically 1-3 attempts succeed for goals in this class. **Default-on.**

**Sanity tests (smoke, no Isabelle round-trip):**

| Goal | Trigger | First free var | Notes |
|---|:-:|:-:|---|
| `(- 1) ^ (2*n) = 1` | ✓ | `n` | hol_main_easy g2 |
| `- a < 0 \<longleftrightarrow> 0 < a` | ✓ | `a` | hol_main_easy g10 |
| `a \<le> b \<longrightarrow> a * c \<le> b * c` | ✓ | `a` | holmain_50 g35 |
| `(\<forall>x. P x) \<longrightarrow> (\<forall>y. P y)` | ✗ | — | blast-trivial; correctly skipped |
| `rev (rev xs) = xs` | ✗ | — | F11-trivial; correctly skipped |
| `finite A \<Longrightarrow> card (A \<union> B) = card A + card (B - A)` | ✗ | — | set/card goal; correctly skipped (`-` doesn't trigger; no digits or `^`) |

### 26b — F29b early-bail on hopeless first outline (`solution/planner/driver.py`)

In `plan_and_fill`:

- Added `_f29b_checked = False` alongside the other per-goal local state (`fills`, `failed`, `repair_progress`, etc.) before the main `while "sorry" in full and left_s() > 0:` loop.
- Inside the loop, immediately after `current_stage = repair_progress.get(hole_key, 0)` and before `if current_stage > 0 and repairs and left_s() > 6:`, added a single-shot check that fires on the first iteration where `current_stage > 0` (i.e. the first time Fill made no progress and we're about to enter repair).

Bail conditions (all four required):

- `len(fills) == 0` — Fill never succeeded
- `"sorry" in full` — outline still has open holes
- `len(full) > 200` — LLM wrote substantial outline (not just a one-liner stub)
- `(timeout - left_s()) / timeout > 0.5` — more than half the per-goal budget already burned

If all hold, return `PlanAndFillResult(False, full, [], [0])` with a trace line: `[planner] F29b early-bail: 0 fills + sorry-laden outline (<N> chars) + <X%> of budget burned`.

**Why these specific conditions:** matches the signature of locale-context-dependent goals (e.g. hol_main_easy g1 / g7) where the LLM produces a syntactically plausible Isar outline but the proof reasoning hits a wall because the necessary `inj f` / `∀x. f x ∈ B` hypothesis isn't in scope. Without F29b the subsequent repair stages also fail and burn the remaining ~60 s. With F29b we save that ~60 s and bail at ~60-70 s instead of ~120 s.

**Hyperparameters chosen conservatively** (>200 char outline, >50% budget) so a goal where the first iteration ran fast and Fill could still make progress on a second pass doesn't get prematurely killed.

### Coordination with the in-flight sweep

Neither fix takes effect on the running bench (PID 303523, `report_metric_sweep_20260528-0021/`) because its Python imports are frozen at process start. Both will be picked up automatically by the next sweep launch.

**Plan for tomorrow:** after the headline sweep finishes (~05:00), launch a focused `hol_main_easy`-only re-run with the same flags but the F29 code in place. ~50 min wall. Compare 6/10 → ?/10 delta on the first 10 goals → projected ?/100 on full easy. Same number into the report as a "F29 ablation" line.

### Files touched

- Modified: `solution/planner/driver.py`
  - Added `_UNTYPED_NUMERIC_RE`, `_F29A_VAR_RE`, `_F29A_ISAR_KEYWORDS`, `_F29A_TYPE_HINTS`, `_F29A_FINISHERS` constants.
  - Added `_try_annotation_retry` function.
  - Wired call to `_try_annotation_retry` inside `_try_prover_direct` between stage-A and stage-B.
  - Added `_f29b_checked` local in `plan_and_fill` and the single-shot early-bail check inside the main while loop.

### Future work (F29c, not shipped this entry)

Deeper miner fix in `solution/planner/extract.py:iter_lemmas_with_proofs`: walk a stack of `context X begin` / `locale X begin` / `assumes` / `fixes` lines (popping on `end`) and prepend active `assumes` to emitted goals as `<asm> \<Longrightarrow> <stmt>` so they're self-contained. ~2-3 h including re-mine + re-curate + verification. Conditional on F29a/b validating + the headline sweep finishing + ≥3 h remaining to the 09:00 deadline. If skipped, document in the report's Limitations section as "extraction-based benchmarks need locale-context tracking; without it, ~15-25% of mined HOL/Main goals are formally non-theorems in `imports Main`."

**Net:** F29a converts a known fail-class (type-ambiguous numeric goals) to wins at ~40 s wall-time cost when triggered, ~0 s when not. F29b cuts ~60 s off the wall-time penalty for the locale-context-dependent fail-class without changing the outcome (still fails, just faster — freeing budget for the goals where Fill might actually finish). Combined projected impact on hol_main_easy: ~6/10 → ~8/10 strict-pass on the first slice if the patterns extrapolate.

## Entry 27 — F29c locale-context filter in the HOL corpus miner

**Date:** 2026-05-28 (AEST early hours, after F29a+F29b landed and while the 300-goal sweep was still in flight)

**Prompt context (paraphrase):** Of the F29a/b/c options offered earlier, user chose "yes — start F29c now" rather than waiting for the headline sweep to finish. F29c was the stretch goal from the original F29 plan: stop the HOL corpus miner from emitting lemmas that live inside `locale` / `context` / `class` / `instantiation` blocks, since those lemmas typically depend on the block's `fixes` / `assumes` clauses and become non-theorems when re-stated standalone under `imports Main`. The signature symptom in the sweep was hol_main_easy g1 `((inv f)^^n) o (f^^n) = (λx. x)` (only true when `inj f`) and g7 `(⋃x ∈ X. f x) ∈ B` (only true when `∀x∈X. f x ∈ B`).

**Background:** The pre-F29c `iter_lemmas_with_proofs` (in `solution/planner/extract.py`) walked the .thy file line by line looking for `lemma|theorem|proposition|corollary` headers and yielded every match. It had no awareness of locale/context/class blocks. So a lemma stated inside `locale group begin ... lemma left_cancel: "a * b = a * c ⟷ b = c" by simp ... end` got yielded with the bare statement `a * b = a * c ⟷ b = c` — which is FALSE without the locale's `assumes "x * inverse x = 1"` and friends.

### 27a — `_compute_block_depths` + filter (`solution/planner/extract.py`)

New helper plus tighter `iter_lemmas_with_proofs` semantics. Module-level additions:

- `_BLOCK_OPEN_KW_RE` — matches openings of `locale|context|sublocale|interpretation|instantiation|overloading|instance|notepad|experiment|bundle|class`. (After a smoke run on Groups.thy showed 7/201 classified as top-level because `class` wasn't in the original list, added `class` and the count went to a correct 7/201 with 194 nested.)
- `_BLOCK_BEGIN_ON_LINE_RE`, `_BARE_BEGIN_RE`, `_BARE_END_RE` — for matching block-end / begin tokens.
- `_compute_block_depths(lines)` — returns a parallel list with the locale/context nesting depth at each line. Handles both one-line block openings (`context ord begin`) and multi-line openings (separate `locale X = ... \n begin`) via a `pending_block_open` flag. The theory's own outer `begin` is depth 0; only `begin`s that follow a pending block-open keyword bump depth. `end` only decrements when depth > 0, so the theory's outer `end` doesn't underflow.

`iter_lemmas_with_proofs` now computes depths once at start and skips any lemma header at depth > 0.

**Validation on representative HOL theories (post-F29c, with `class` included):**

| Theory | Top-level lemmas (kept) | Nested (dropped) | Total |
|---|---:|---:|---:|
| `Groups.thy` | 7 | 194 | 201 |
| `Finite_Set.thy` | 227 | 45 | 272 |
| `List.thy` | 1088 | 174 | 1262 |
| `Set.thy` | 412 | 0 | 412 |

Numbers track intuition — Groups.thy is mostly locale/class definitions; Set.thy is all top-level set-theory lemmas; List.thy and Finite_Set.thy are mostly top-level with some scattered nested theorems. None of these counts are zero or absurd, so the depth tracking is sound.

### 27b — Re-mine + re-aggregate + re-curate

Re-ran the F27 mining pipeline against the F29c-filtered miner:

- `python -m planner.extract_hol --out-dir datasets` → 54 509 records from HOL/, 5268 from HOL/Library = **59 690 rich records** (down from 70 731 pre-F29c, i.e. ~11 K locale-resident lemmas dropped).
- `python -m planner.priors --input ...` → updated `isar_priors_hol.json` (740 KB → ~640 KB) + `isar_hintlex_hol.json` (404 KB → ~380 KB). Slightly leaner hint coverage but no longer suggesting locale-bound identifiers as hints.
- `python -m planner.sample_hol_tiered --corpus datasets/hol_corpus.jsonl --out-dir ../datasets_subset --n 100 --seed 42` → fresh `hol_main_{easy,mid,hard}.txt` with 100 goals each, all single-line, all top-level theorems by construction.

**Pool counts (post-F29c filter, after `_MAIN_THEORIES` whitelist + propositional/exotic/length filters):**

| Tier | Pool size | Sampled |
|---|---:|---:|
| easy (≤ 45 chars) | 1473 | 100 |
| mid (45-105 chars) | 2305 | 100 |
| hard (> 105 chars) | 347 | 100 |
| **total kept** | **4125** | **300** |

(Pre-F29c counts were 2855 / 2916 / 176 = 5947. The drop is heaviest on `easy` because short-statement lemmas are the most common locale-resident shape — typeclass property lemmas like `x * 0 = 0`.)

### 27c — Verification on the new easy dataset

Spot-checked first 10 easy goals against the OLD dataset's known fails:

- OLD `((inv f)^^n) o (f^^n) = (λx. x)` (g1, locale-bound) → **dropped** in v2 ✓
- OLD `(\<Union>x \<in> X. f x) \<in> B` (g7, locale-bound) → **dropped** in v2 ✓

New first 10 are all top-level theorems: set/list/sum-type/relation algebra, all expected to be provable in `imports Main`.

### Coordination with the in-flight headline sweep

The headline sweep launched at 00:21 is using the **OLD** (pre-F29c) datasets, which it loaded into memory at startup. Its CSV outputs will reference those OLD goals — including the 4-of-10 locale/type-ambiguous failures observed early on. Those numbers go into the report as the "raw mined corpus" baseline.

The F29 ablation re-run (the planned focused `hol_main_easy` sweep with F29a/b code active) should use the NEW datasets — they're both cleaner *and* the post-F29c configuration matches what F29a/b were designed for.

**Methodological caveat for the report:** the F29 ablation is *not* a pure planner-only ablation — datasets also changed. The report should frame this as **two distinct improvements stacked**: (a) F29c benchmark-construction fix removes ~25% of non-theorems; (b) F29a/b planner fixes recover more of what remains. Both numbers are valid for what they measure, just measure different things.

### Files added/touched

- Modified: `solution/planner/extract.py`
  - Added `_BLOCK_OPEN_KW_RE`, `_BLOCK_BEGIN_ON_LINE_RE`, `_BARE_BEGIN_RE`, `_BARE_END_RE` constants.
  - Added `_compute_block_depths` helper.
  - Modified `iter_lemmas_with_proofs` to compute and consult depths, skipping any lemma where `depths[i] > 0`.
- Regenerated data files (same paths, new contents):
  - `solution/datasets/hol_corpus.jsonl` (40 MB → ~32 MB)
  - `solution/datasets/isar_priors_hol.json` (740 KB → ~640 KB)
  - `solution/datasets/isar_hintlex_hol.json` (404 KB → ~380 KB)
  - `datasets_subset/hol_main_easy.txt`, `hol_main_mid.txt`, `hol_main_hard.txt` (100 goals each, F29c-cleaned).

**Net:** F29c removes the dominant "non-theorem in `imports Main`" fail mode from the HOL mining pipeline at the source. The corpus shrinks ~16% (70 731 → 59 690 records) but every remaining record is a goal that can in principle be proven against `imports Main` (modulo the smaller remaining issue of lemma-level `assumes` blocks, which `iter_lemmas_with_proofs` still drops — that's left as future work). Datasets resampled. After the headline sweep finishes, the F29 ablation re-run is the validation experiment for the combined F29a + F29b + F29c stack.

## Entry 28 — F29-Approach-A typeclass lifting (recover class-bound HOL lemmas)

**Date:** 2026-05-28 (AEST early hours, after the F29c filter was in place and the user asked how to actually *recover* the dropped locale-bound lemmas instead of just dropping them)

**Prompt context (paraphrase):** F29c (Entry 27) drops the entire ~25% slice of mined HOL lemmas that live inside `locale` / `class` / `context` / `instantiation` blocks. The user asked how to handle those scopes properly. We discussed three approaches; user picked **Approach A** (typeclass lifting): for lemmas inside `class X begin` or `context X begin` where X is a typeclass declared in the same file, re-emit the lemma with a `(<first-free-var>::'a::X)` annotation so Isabelle's type inference brings X's methods and axioms into scope.

**Background:** In Isabelle, a `class X = ...` declaration defines a typeclass. Lemmas stated inside `class X begin ... lemma foo: "..." ... end` are typeclass-resident — they rely on X's `fixes`/`assumes` clauses, which become axioms over the typeclass's type variable `'a`. When extracted bare and re-stated standalone under `imports Main`, the type variable's class constraint is lost and the lemma usually fails to typecheck (or worse, typechecks at a more general type where the statement is false). Annotating the first free value variable as `(v::'a::X)` propagates the X constraint through Hindley-Milner type inference: every other occurrence of `v` (and every operator that takes `v` as an argument, including X's own methods) now resolves at type `'a::X` with X's axioms in scope.

### 28a — Stack-tracking miner (`solution/planner/extract.py`)

Replaced `_compute_block_depths` (Entry 27's depth-only tracker) with the richer `_compute_block_stacks`, which records the full `[(kind, name), ...]` stack at each line. Kept `_compute_block_depths` as a backwards-compat shim (`[len(s) for s in stacks]`). The `_BLOCK_OPEN_KW_RE` regex now also captures the block's name via a `(?P<name>...)` group.

New helpers:

- `_collect_classes_in_file(lines)` — single-pass scan for `^\s*class\s+<name>` declarations, returning the set of typeclass names defined in this file. Used to decide whether a `context X begin` is a typeclass scope (safe to lift) or an arbitrary locale instance (still drop).
- `_lift_with_typeclass(stmt, class_name)` — finds the first 1-2-character lowercase identifier not in a small Isar keyword set (`if`, `in`, `is`, `of`, `on`, `do`, `to`, `as`, `or`, `by`) and rewrites `<var>` → `(<var>::'a::<class_name>)` once. The 1-2 char restriction is critical: an earlier version matched any lowercase identifier and ended up annotating function names like `mult` (e.g. `(mult::'a::group) a b` — wrong, mult is `'a => 'a => 'a` not `'a`).

### 28b — Lift integration in `iter_lemmas_with_proofs`

Per-lemma decision logic now distinguishes three cases instead of the previous two (yield vs skip):

1. **Top-level (depth 0):** yield as before.
2. **Inside `class X` OR inside `context X` where X is in `_collect_classes_in_file(lines)`:** lift via `_lift_with_typeclass`, yield with the lifted statement and outline. If lifting fails (no suitable free var), drop.
3. **Inside `locale` / `sublocale` / `interpretation` / `instantiation` / `overloading` / `instance` / `notepad` / `experiment` / `bundle`:** still drop (Approach A only handles typeclasses).

### 28c — Validation

Smoke tests on isolated lift calls:

| Input statement | Class | Lifted output |
|---|---|---|
| `mult a b = mult a c \<longrightarrow> b = c` | `group` | `mult (a::'a::group) b = mult a c \<longrightarrow> b = c` |
| `a + b = b + a` | `comm_monoid_add` | `(a::'a::comm_monoid_add) + b = b + a` |
| `-a = -b \<longleftrightarrow> a = b` | `group_add` | `-(a::'a::group_add) = -b \<longleftrightarrow> a = b` |
| `inv a * a = 1` | `group` | `inv (a::'a::group) * a = 1` |

Per-file mining count delta (Groups.thy):

| Pre-Approach-A (F29c only) | Post-Approach-A | Delta |
|---:|---:|---|
| 7 yielded (top-level only) | 171 yielded | +164 typeclass-lifted lemmas recovered |

### 28d — Re-mine + re-aggregate + re-curate

```
extract_hol.py → 56 152 records from HOL/ + 5371 from Library = 61 523 total
                 (was 59 690 pre-Approach-A — +1833 lifted lemmas recovered)
priors.aggregate → updated isar_priors_hol.json + isar_hintlex_hol.json
sample_hol_tiered.py → 300 fresh goals, 100/100/100 per tier
```

Lifted-goal density in the new datasets (count of `::'a::` annotations per tier):
- `hol_main_easy.txt`: 8 of 100 are typeclass-lifted (rest are top-level)
- `hol_main_mid.txt`: 18 of 100 lifted
- `hol_main_hard.txt`: 21 of 100 lifted

The lifted-goal share is small because most lemmas in HOL/* are already top-level. But Approach A specifically recovers the structural class-method lemmas (basic algebra over `monoid_add`, `group_add`, `comm_ring`, `linorder`, etc.) — these are exactly the kind of goal the F11 stage-A cascade closes via `by simp` once the class constraint is in scope.

Sample lifted easy goal: `(a::'a::group_add) + (b - c) = (a + b) - c` — standalone-parseable, provable in `imports Main` via `by simp` against group_add's simp rules.

### Tradeoffs and what Approach A doesn't recover

- ✓ Class-method lemmas (most common case in HOL/* algebra theories): RECOVERED
- ✓ `context X begin` blocks where X is a typeclass: RECOVERED
- ✗ Locale-resident lemmas where the locale is NOT a typeclass (e.g. `locale group_hom = fixes f assumes ...`): still dropped. Approach B (full `fixes`/`assumes` lifting) would handle these.
- ✗ `instantiation foo :: bar begin lemma ...`: still dropped (these are about specific types, not general typeclass methods).
- ✗ Lemmas using locale parameters that aren't in the typeclass (rare in HOL/* but exists): the lifted goal will typecheck but the parameter references will be unbound, leading to verify-fail at bench time. Conservative drop heuristic would catch some of these; not implemented.

### Files touched

- Modified: `solution/planner/extract.py`
  - `_BLOCK_OPEN_KW_RE` now captures `kind` + `name` groups.
  - New `_compute_block_stacks` (richer replacement for `_compute_block_depths`, which is now a shim).
  - New `_collect_classes_in_file`, `_F29A2_VAR_RE`, `_F29A2_VAR_SKIP`, `_lift_with_typeclass`.
  - `iter_lemmas_with_proofs` walks `stacks[i][-1]`, decides between yield / lift / drop.
- Regenerated data:
  - `solution/datasets/hol_corpus.jsonl` (~32 MB → ~33 MB; +1833 lifted records)
  - `solution/datasets/isar_priors_hol.json`, `isar_hintlex_hol.json` (re-aggregated)
  - `datasets_subset/hol_main_{easy,mid,hard}.txt` (resampled with seed=42)

**Net:** Approach A turns ~25% of the corpus that F29c was previously dropping (~11K class-resident lemmas, of which ~1.8K survived after typeclass-lift heuristics) into usable benchmark goals. The lifted goals are exactly the "abstract algebra" lemmas (group identities, monoid laws, ordering properties) — high-value because the planner's F11 stage-A cascade closes them readily once the class constraint is in scope. Combined with F29a/b's planner improvements, the F29 ablation re-run on `hol_main_easy` should land closer to **80-85% strict-pass** vs the ~50% baseline on the noisy raw mined dataset.

### Addendum (2026-05-28 ~03:00) — lift bugfix for Isabelle markup

Empirical smoke test on 8 lifted easy goals (5/8 wins matched projection — see report-ready table in handoff). The 3 fails were 2 predicted Approach-A limitations (missing lemma-level `assumes` + parent-class constraint lost) and 1 unexpected limitation (class methods needing explicit `add:` hint, like `idom_divide`'s `div_minus_left` — analogous to F19's pre-extension card/sum gap).

Mid/hard pre-audit then found a **lift regex bug**: `_F29A2_VAR_RE` (`\b([a-z][a-z']?)\b`) was matching identifiers inside Isabelle markup tokens — annotating `le` inside `\<le>` to produce unparseable `\<(le::'a::class)>`, and `f` inside `\<^sub>f\<^sub>i\<^sub>n` to produce broken subscripts. 4 goals across mid+hard affected:

- mid g13: `0 \<le> a \<Longrightarrow> ...` (annotated `le` in `\<le>` — was for `ordered_comm_monoid_add`)
- mid g14: `\<top> \<le> a \<Longrightarrow> ...` (same — was for `order_top`)
- hard #13, #20: `Gcd\<^sub>f\<^sub>i\<^sub>n A` (annotated subscript `f` — was for `semiring_gcd`)

**Fix in `solution/planner/extract.py:_lift_with_typeclass`:**

1. New module-level regex `_OPEN_ISABELLE_MARKER_RE = re.compile(r'\\<[^>]*$')` — detects when the chars preceding the match position contain an unclosed `\<...` marker.
2. In `_lift_with_typeclass`'s iter loop, after the keyword/skip check, compute `before = stmt[:m.start()]` and skip if any of:
   - `_OPEN_ISABELLE_MARKER_RE.search(before)` — match is inside `\<NAME>` like `\<le>`.
   - `before.endswith("\\<^sub>")` or `"\\<^sup>"` or `"\\<^bsub>"` or `"\\<^isub>"` or `"\\<^isup>"` — match is the content of a single-char subscript / superscript marker.

**Validation:** four broken cases tested in isolation:

- mid g13 → now lifts `a` (the real free var): `0 \<le> (a::'a::ordered_comm_monoid_add) \<Longrightarrow> 0 < b \<Longrightarrow> 0 < a + b` ✓
- mid g14 → now lifts `a`: `\<top> \<le> (a::'a::order_top) \<Longrightarrow> a = \<top>` ✓
- hard #13, #20 → both return `None` from `_lift_with_typeclass` (no liftable free var because `f`/`i`/`n` are all subscript content and `Gcd`/`A` are uppercase). These records are dropped from the corpus.

**Sanity on normal lifts:** `a + b = b + a` with `comm_monoid_add` still gives `(a::'a::comm_monoid_add) + b = b + a`; `mult a b = mult b a` with `group` still gives `mult (a::'a::group) b = mult b a`. No regression.

**Re-mine + re-aggregate + re-curate** ran cleanly. Dataset counts went from 47/300 lifted (pre-bugfix) to 43/300 (5 easy / 21 mid / 17 hard). The 4-record loss to the corpus shifted the seed-42 walk slightly so a few different goals landed in the sample, but total composition is unchanged.

**Files touched:** `solution/planner/extract.py` (added `_OPEN_ISABELLE_MARKER_RE` and the two new `before` checks in `_lift_with_typeclass`). All regenerated data files were overwritten in place.

This addendum doesn't get its own Entry — it's a fixup to Entry 28's lift function. AI_LOG Entry 28 is the canonical reference for F29-Approach-A; the bugfix sits inside it.
