from __future__ import annotations

import time
import re
import os
import signal
import threading
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FuturesTimeout
import hashlib

from planner.skeleton import (
    Skeleton, find_sorry_spans, propose_isar_skeleton, propose_isar_skeleton_diverse_best,
    _MIN_VIABLE_LLM_CALL_S,
)
from planner.budget import Deadline, DeadlineExceeded
from planner.repair import try_cegis_repairs, regenerate_whole_proof, _APPLY_OR_BY as _TACTIC_LINE_RE
from prover.config import ISABELLE_SESSION
from prover.isabelle_api import (
    build_theory, get_isabelle_client, last_print_state_block, start_isabelle_server,
    _extract_session_id,
)
from prover.prover import prove_goal
from planner.goals import _print_state_before_hole, _log_state_block, _effective_goal_from_state, _first_lemma_line, _extract_goal_from_lemma_line, _cleanup_resources, _verify_full_proof, _run_theory_with_timeout

def _hole_fingerprint(full_text: str, span: tuple[int, int], context: int = 120) -> str:
    """Stable key for a hole based on suffix context only.

    Using only text *after* the sorry means insertions above the hole (e.g. apply
    tactics prepended by Fill) don't change the key and repair stages survive across
    those edits.
    """
    _, e = span
    hi = min(len(full_text), e + context)
    snippet = full_text[e:hi]
    return hashlib.sha1(snippet.encode("utf-8")).hexdigest()[:16]

# Constants
_INLINE_BY_TAIL = re.compile(r"\s+by\s+.+$")
_BARE_DOT = re.compile(r"(?m)^\s*\.\s*$")
_HEAD_CMD_RE = re.compile(r"^\s*(have|show|obtain)\b")  # local copy to avoid new imports
_ISA_VERIFY_TIMEOUT_S = int(os.getenv("ISABELLE_VERIFY_TIMEOUT_S", "30"))

@dataclass(slots=True)
class PlanAndFillResult:
    success: bool
    outline: str
    fills: List[str]
    failed_holes: List[int]


# ============================================================================
# Hole Filling
# ============================================================================

def _fill_one_hole(isabelle, session: str, full_text: str, hole_span: Tuple[int, int], 
                  goal_text: str, model: Optional[str], per_hole_timeout: int, *, trace: bool = False) -> Tuple[str, bool, str]:
    """Fill single hole in proof."""
    
    # Check for stale hole
    try:
        s_line_start = full_text.rfind("\n", 0, hole_span[0]) + 1
        prev_line_end = s_line_start - 1
        prev_prev_nl = full_text.rfind("\n", 0, prev_line_end) + 1
        prev_line = full_text[prev_prev_nl:prev_line_end+1]
    except Exception:
        prev_line = ""
    
    if (_INLINE_BY_TAIL.search(prev_line) or _TACTIC_LINE_RE.match(prev_line) or 
        prev_line.strip() in {"done", "."}):
        s, e = hole_span
        return full_text[:s] + "\n" + full_text[e:], True, "(stale-hole)"
    
    state_block = _print_state_before_hole(isabelle, session, full_text, hole_span, trace)
    _log_state_block("fill", state_block, trace=trace)
    
    # orig_goal = _original_goal_from_state(state_block)
    eff_goal = _effective_goal_from_state(state_block, goal_text, full_text, hole_span, trace)
    
    # if trace:
    #     # if orig_goal:
    #     #     print(f"[fill] Original goal: {orig_goal}")
    #     print(f"[fill] Effective goal: {eff_goal}")
    
    res = prove_goal(
        isabelle, session, eff_goal, model_name_or_ensemble=model,
        beam_w=3, max_depth=6, hint_lemmas=6, timeout=per_hole_timeout,
        models=None, save_dir=None, use_sledge=True, sledge_timeout=10,
        sledge_every=1, trace=trace, use_color=False, use_qc=False,
        qc_timeout=2, qc_every=1, use_np=False, np_timeout=5, np_every=2,
        facts_limit=8, do_minimize=False, minimize_timeout=8,
        do_variants=False, variant_timeout=6, variant_tries=24,
        enable_reranker=True, initial_state_hint=state_block,
    )
    
    steps = [str(s) for s in res.get("steps", [])]

    # Fallbacks: some backends return finishers/applies in separate keys
    fin_candidates = []
    # singular fields
    for k in ("finisher", "finish", "final"):
        v = res.get(k)
        if isinstance(v, str):
            fin_candidates.append(v)
    # list fields
    for k in ("finishers", "sledge_finishers"):
        vs = res.get(k)
        if isinstance(vs, (list, tuple)):
            fin_candidates.extend([str(x) for x in vs if isinstance(x, str)])
    applies_from_keys = []
    for k in ("applies", "apply_steps"):
        vs = res.get(k)
        if isinstance(vs, (list, tuple)):
            applies_from_keys.extend([str(x) for x in vs if isinstance(x, str) and x.startswith("apply")])

    applies = [s for s in steps if s.startswith("apply")]
    if applies_from_keys:
        applies = applies or applies_from_keys  # prefer explicit list if steps were empty

    fin = next((s for s in steps if s.startswith("by ") or s.strip() == "done"), "")
    if not fin:
        fin = next((x for x in fin_candidates if isinstance(x, str) and (x.startswith("by ") or x.strip() == "done")), "")

    # If neither steps nor recognized finishers were returned, report no-steps
    if not (applies or fin):
        return full_text, False, "no-steps"
    
    # Handle finisher
    if fin:
        script_lines = applies + [fin]
        insert = "\n  " + "\n  ".join(script_lines) + "\n"
        s, e = hole_span
        new_text = full_text[:s] + insert + full_text[e:]
        
        try:
            verified = _verify_full_proof(isabelle, session, new_text)
        except Exception:
            verified = False
        if verified:
            return new_text, True, "\n".join(script_lines)
        return full_text, False, "finisher-unverified"
    
    # Handle apply-only  (NEVER mark success for apply-only scripts)
    if applies:
        # Decide if the hole sits under a have/show/obtain head; if so, we must NOT
        # leave a bare 'apply' there (illegal in 'prove' mode). Replace the hole with
        # a tiny subproof instead of inserting above the hole.
        s, e = hole_span
        # scan a small window upwards to find the enclosing head line
        head_line_start = full_text.rfind("\n", 0, s) + 1
        scan_start = max(0, full_text.rfind("\n", 0, max(0, head_line_start - 512)) + 1)
        segment = full_text[scan_start:s]
        lines = segment.splitlines()
        head_idx = None
        for i in range(len(lines) - 1, -1, -1):
            if _HEAD_CMD_RE.match(lines[i] or ""):
                head_idx = i
                break

        # Deduplicate against already-present lines in the local window
        dedup_window = segment
        dedup = [a for a in applies if a not in dedup_window]
        if not dedup:
            return full_text, False, "apply-duplicate"

        if head_idx is not None:
            # Apply-only inside have/show is illegal in 'prove' mode unless closed by 'by ...'.
            # Do NOT fabricate 'proof ... qed'. Leave the hole as-is and let the caller escalate to repair.
            if trace:
                print("[fill] apply-only inside have/show; not inserting proof/qed; escalating to repair.")
            return full_text, False, "apply-inside-have/show"
        else:
            # Non have/show context — keep existing behaviour (insert above, keep sorry)
            probe_text = _insert_above_hole_keep_sorry(full_text, hole_span, dedup)
            return probe_text, False, "\n".join(dedup)
    
    return full_text, False, "no-tactics"


def _insert_above_hole_keep_sorry(text: str, hole: Tuple[int, int], lines_to_insert: List[str]) -> str:
    """Insert lines above hole while keeping sorry."""
    s, _ = hole
    ls = text.rfind("\n", 0, s) + 1
    le = text.find("\n", s)
    hole_line = text[ls:(le if le != -1 else len(text))]
    indent = hole_line[:len(hole_line) - len(hole_line.lstrip(" "))]
    payload = "".join(f"{indent}{ln.strip()}\n" for ln in lines_to_insert if ln.strip())
    return text[:s] + payload + text[s:]

# --- helper: pick the sorry-span nearest a target offset (to preserve focus) ---
def _nearest_sorry_span(spans: List[Tuple[int, int]], target_s: int) -> Optional[Tuple[int, int]]:
    if not spans:
        return None
    return min(spans, key=lambda sp: abs(sp[0] - target_s))


def _line_offset_1based(text: str, line_1based: int) -> Tuple[int, int]:
    """Return (start_offset, end_offset) of the 1-based line in `text` (end exclusive)."""
    idx = line_1based - 1
    if idx < 0:
        return (0, 0)
    pieces = text.splitlines(keepends=True)
    if idx >= len(pieces):
        return (len(text), len(text))
    start = sum(len(pieces[i]) for i in range(idx))
    end = start + len(pieces[idx])
    return (start, end)


_DIRECT_FINISHERS = ("by blast", "by auto", "by simp", "by metis", "by force", "by fastforce", "by presburger", "by argo", "by linarith")

# F19: card/sum domain-specialist finishers. Pruned to high-confidence one-shots
# so stage-A.5 caps spending around ~30s and leaves room for stage-B sledge.
# Confirmed closing goals 11, 14, 17, 18, 21 on hard_25.
_CARD_FINISHERS = (
    "by (simp add: card_Un_disjoint)",
    "by (simp add: card_Diff_subset)",
    "by (simp add: card_image)",
    "by (simp add: card_insert_if)",
    "by (simp add: card_Diff_singleton)",
    "by (auto simp: card_Un_disjoint)",
    "by (metis card_Un_disjoint)",
    "by (metis card_Int_Diff)",
)

_SUM_FINISHERS = (
    "by (simp add: sum.distrib)",
    "by (simp add: sum.If_cases)",
    "by (simp add: sum.If_cases Int_def)",
    "by (simp add: sum.cong)",
    "by (simp add: sum_constant)",
    "by (simp add: sum.neutral)",
    "by (auto simp: sum.distrib)",
    "by (metis sum.distrib)",
)

_GOAL_HAS_CARD_RE = re.compile(r"\bcard\b")
_GOAL_HAS_SUM_RE = re.compile(r"\bsum\b")
_CARD_SUM_TOKEN_RE = re.compile(r"\b(card|sum|finite|inj_on)\b")


# F29a — type-annotation retry trigger detection.
#
# When the bare stage-A finisher cascade fails on a goal that involves untyped
# numeric/order operators, the cause is often Isabelle's type inference picking
# the most general type-class (e.g. `'a :: {minus, one, power}`) under which
# the statement is *false*. Annotating the first free variable as `::int` /
# `::real` is usually enough — type inference propagates from one occurrence.
#
# Observed in hol_main_easy sweep 2026-05-28: g2 `(- 1) ^ (2*n) = 1`,
# g10 `- a < 0 \<longleftrightarrow> 0 < a` — both burned 70-127 s of budget
# before failing under bare type inference.
_UNTYPED_NUMERIC_RE = re.compile(
    r'\\<le>|\\<ge>|\\<less>|\\<greater>|\\<noteq>|'
    r'\b\d+\b|'                                 # numeric literal
    r'(?<!\w)\^(?!\w)'                          # power operator
)
# Lowercase identifiers used as free variables in mined HOL goals. Keep the
# regex broad; rely on the keyword set below to filter out Isar/HOL words.
_F29A_VAR_RE = re.compile(r"\b([a-z]\w*)\b")
_F29A_ISAR_KEYWORDS = frozenset({
    "and", "as", "assume", "by", "case", "do", "fix", "from", "fun",
    "have", "if", "in", "is", "lemma", "let", "moreover", "next",
    "obtain", "of", "on", "or", "proof", "qed", "show", "shows",
    "the", "then", "to", "ultimately", "where", "with",
    # Common HOL identifiers we don't want to wrap with a type — these are
    # constants/functions, not the free variables we should type-annotate.
    "set", "map", "rev", "length", "card", "sum", "finite",
    "True", "False", "None", "Some",
})
# Try `nat` first — most assignment goals are over nat. Then `int` (covers the
# negative-literal cases like `(- 1) ^ ...`). Then `real` for ordered-field
# inequalities like `- a < 0`.
_F29A_TYPE_HINTS = ("nat", "int", "real")
# Cheap finishers most likely to discharge numeric / order / linear goals
# once typed. `linarith` is the big win for inequality goals.
_F29A_FINISHERS = ("by simp", "by auto", "by linarith", "by arith")


def _try_annotation_retry(isabelle, session: str, goal: str,
                          deadline: "Deadline", *, trace: bool = False) -> Optional[str]:
    """F29a: when bare F11 stage-A fails on a goal with untyped numeric ops,
    retry the cheap finisher cascade with a type annotation on the first free
    variable. Returns the verified `lemma "..."` text on success, or None.

    Worst-case wall: 3 type hints × 4 finishers × 4 s cap = 48 s. In practice
    1-3 attempts succeed when the goal is in this class. Returns None
    immediately when the trigger predicate doesn't match.
    """
    if deadline.remaining() < 5:
        return None
    if not _UNTYPED_NUMERIC_RE.search(goal):
        return None
    # Pick the first short lowercase identifier that isn't an Isar keyword
    var = None
    for m in _F29A_VAR_RE.finditer(goal):
        v = m.group(1)
        if v in _F29A_ISAR_KEYWORDS:
            continue
        var = v
        break
    if var is None:
        return None
    var_re = re.compile(r'\b' + re.escape(var) + r'\b')
    for type_hint in _F29A_TYPE_HINTS:
        if deadline.remaining() < 4:
            return None
        annotated_goal = var_re.sub(f'({var}::{type_hint})', goal, count=1)
        for tac in _F29A_FINISHERS:
            if deadline.remaining() < 3:
                return None
            candidate = f'lemma "{annotated_goal}"\n  {tac}'
            try:
                if _verify_full_proof(isabelle, session, candidate, timeout_s=4):
                    if trace:
                        print(f"[planner] F29a type-annotated `{var}::{type_hint}` solved with `{tac}`.")
                    return candidate
            except Exception:
                continue
    return None


def _ordered_card_sum_finishers(goal: str) -> Tuple[str, ...]:
    """Return finishers ordered by token relevance to the goal text.

    sum-only goal → sum finishers first; card-only → card first; both → sum
    first (sum goals tend to bind tighter to a single lemma like sum.distrib).
    """
    has_card = bool(_GOAL_HAS_CARD_RE.search(goal))
    has_sum = bool(_GOAL_HAS_SUM_RE.search(goal))
    if has_sum and not has_card:
        return _SUM_FINISHERS + _CARD_FINISHERS
    if has_card and not has_sum:
        return _CARD_FINISHERS + _SUM_FINISHERS
    if has_sum and has_card:
        return _SUM_FINISHERS + _CARD_FINISHERS
    return _CARD_FINISHERS + _SUM_FINISHERS


def _try_prover_direct(isabelle, session: str, goal: str, model: Optional[str],
                       deadline: "Deadline", *, trace: bool = False) -> Optional[str]:
    """F11 (hybrid fast path): try to close `goal` without invoking outline generation.

    Stage A: cheap one-shot finishers (`by blast/auto/simp/metis/force/...`) — typically 2-5s
             each. Most propositional + simple quantifier goals fall here.
    Stage B: if no finisher works, call `prove_goal` (beam-search prover with sledgehammer)
             with a longer sledge timeout (20s).

    Both stages strict-verify the resulting proof. Total budget ~40% of remaining deadline.
    """
    rem = deadline.remaining_int(cap=120, min_=1)
    if rem < 8:
        return None

    # ---- F19: build finisher list, specialist-first for card/sum goals ----
    # Tight 6s per-tactic verify cap so a single slow `simp` with congruence
    # rewriting can't burn the per-goal budget (observed: `by (simp add:
    # sum.cong)` taking 14s before F19 reordering closed it).
    is_card_sum = bool(_CARD_SUM_TOKEN_RE.search(goal))
    if is_card_sum:
        finisher_seq = _ordered_card_sum_finishers(goal) + _DIRECT_FINISHERS
    else:
        finisher_seq = _DIRECT_FINISHERS

    # `simp`/`auto` finishers run in 1-3s; `metis` with 1-2 lemmas can need 8-10s
    # while a wedge-rewriting metis sometimes runs longer. Use a wider cap when
    # the tactic starts with `metis` so it isn't cut off mid-reconstruction.
    for tac in finisher_seq:
        if deadline.remaining() < 4:
            break
        per_tac_s = 12 if "metis" in tac else 6
        candidate = f'lemma "{goal}"\n  {tac}'
        try:
            if _verify_full_proof(isabelle, session, candidate, timeout_s=per_tac_s):
                if trace:
                    print(f"[planner] F11 stage-A solved with `{tac}`.")
                return candidate
        except Exception:
            continue

    # ---- F29a: type-annotation retry (only fires for untyped-numeric goals) ----
    annotated = _try_annotation_retry(isabelle, session, goal, deadline, trace=trace)
    if annotated is not None:
        return annotated

    # ---- Stage B: full prover (beam + sledge) ----
    budget = max(8, min(90, int(rem * 0.40)))
    if budget < 10 or deadline.remaining() < budget:
        return None
    try:
        res = prove_goal(
            isabelle, session, goal, model_name_or_ensemble=model,
            beam_w=3, max_depth=6, hint_lemmas=6, timeout=budget,
            models=None, save_dir=None, use_sledge=True, sledge_timeout=20,
            sledge_every=1, trace=trace, use_color=False, use_qc=False,
            qc_timeout=2, qc_every=1, use_np=False, np_timeout=5, np_every=2,
            facts_limit=8, do_minimize=False, minimize_timeout=8,
            do_variants=True, variant_timeout=6, variant_tries=24,
            enable_reranker=True,
        )
    except Exception as ex:
        if trace:
            print(f"[planner] F11 stage-B raised: {type(ex).__name__}: {ex}")
        return None
    if not res.get("success"):
        if trace:
            print(f"[planner] F11 stage-B: prover returned success=False (keys={list(res.keys())})")
        return None
    steps = [str(s) for s in res.get("steps", [])]
    tactics = [t for t in steps if not t.lstrip().startswith("lemma ")]
    if not tactics:
        if trace:
            print(f"[planner] F11 stage-B: success=True but no non-lemma tactics in steps={steps!r}")
        return None
    body = "\n  ".join(t.strip() for t in tactics)
    proof_text = f'lemma "{goal}"\n  {body}'
    last = tactics[-1].strip()
    if not (last.startswith("by ") or last == "done"):
        proof_text += "\n  done"
    try:
        if _verify_full_proof(isabelle, session, proof_text):
            if trace:
                print(f"[planner] F11 stage-B solved with prover ({len(tactics)} tactics).")
            return proof_text
        else:
            if trace:
                print(f"[planner] F11 stage-B: prover PROVED but strict-verify rejected reconstructed proof:\n--- BEGIN ---\n{proof_text}\n--- END ---")
    except Exception as ex:
        if trace:
            print(f"[planner] F11 stage-B strict-verify raised: {type(ex).__name__}: {ex}")
        return None
    return None


def _classify_earliest_failure(isabelle, session: str, full_text: str,
                               spans: List[Tuple[int, int]]) -> Tuple[Optional[int], Optional[Tuple[int, int]]]:
    """F4: Classify Isabelle's earliest reported error against the current sorry spans.

    Returns (error_line_1based, containing_sorry_span).
    - If text verifies cleanly → (None, None).
    - If earliest error is on a line that overlaps a sorry → (line, that_span).
    - If earliest error is on a non-sorry line → (line, None) — caller should route to repair.
    """
    try:
        _, errs = _quick_state_and_errors(isabelle, session, full_text)
    except Exception:
        return None, None
    err_lines = _extract_error_lines(errs)
    if not err_lines:
        return None, None
    line = min(err_lines)
    lo, hi = _line_offset_1based(full_text, line)
    for sp in spans:
        s, _ = sp
        if lo <= s < hi:
            return line, sp
    return line, None

# ============================================================================
# Repair
# ============================================================================

def _proof_bounds_top_level(text: str) -> Optional[Tuple[int, int]]:
    """Return (start,end) offsets of last top-level proof..qed block."""
    qed_matches = list(re.finditer(r"(?m)^\s*qed\b", text))
    if not qed_matches:
        return None
    
    end = qed_matches[-1].end()
    proof_matches = list(re.finditer(r"(?m)^\s*proof\b.*$", text[:qed_matches[-1].start()]))
    if not proof_matches:
        return None
    
    return (proof_matches[-1].start(), end)


def _tactic_spans_topdown(text: str) -> List[Tuple[int, int]]:
    """Top-down tactic line spans within last proof..qed block."""
    bounds = _proof_bounds_top_level(text)
    if not bounds:
        return []
    
    b0, b1 = bounds
    seg = text[b0:b1]
    lines = seg.splitlines(True)
    spans, off = [], b0
    
    for line in lines:
        if _TACTIC_LINE_RE.match(line or "") or _INLINE_BY_TAIL.search(line or ""):
            spans.append((off, off + len(line.rstrip("\n"))))
        off += len(line)
    
    return spans

def _repair_failed_proof_topdown(isa, session, full: str, goal_text: str, model: Optional[str],
                                 left_s, max_repairs_per_hole: int, trace: bool,
                                 *, deadline: Optional[Deadline] = None) -> Tuple[str, bool]:
    """Walk tactics from top; attempt CEGIS-repair on the first failing one.

    This must never crash the UI route. Timeouts / broken Isabelle responses are treated as
    'repair failed', and the caller may decide to fall back (e.g. open minimal sorries).
    """
    t_spans = _tactic_spans_topdown(full)
    if not t_spans:
        return full, False

    i = 0
    while i < len(t_spans) and left_s() > 3.0:
        if deadline is not None and deadline.expired():
            return full, False
        span = t_spans[i]
        try:
            st = _print_state_before_hole(isa, session, full, span, trace)
            eff_goal = _effective_goal_from_state(st, goal_text, full, span, trace)
        except Exception as ex:
            if trace:
                print(f"[repair] Could not extract state/goal before tactic (skipping): {ex}")
            i += 1
            continue

        per_budget = min(30.0, max(15.0, left_s() * 0.33))

        # F5: try_cegis_repairs now runs ONE stage per call. Escalate stage 1 → 2 here.
        patched, applied = full, False
        try:
            for stg in (1, 2):
                if deadline is not None and deadline.expired():
                    break
                if left_s() <= 6.0:
                    break
                patched, applied, _ = try_cegis_repairs(
                    full_text=full, hole_span=span, goal_text=eff_goal, model=model,
                    isabelle=isa, session=session, repair_budget_s=per_budget,
                    max_ops_to_try=max_repairs_per_hole, beam_k=2,
                    allow_whole_fallback=False, trace=trace, resume_stage=stg,
                    deadline=deadline,
                )
                if applied and patched != full:
                    break  # stop escalating once a stage produced a change
        except (TimeoutError, _FuturesTimeout, ValueError) as ex:
            # TimeoutError: verifier timed out; ValueError: isabelle_client returned unexpected/empty response
            if trace:
                print(f"[repair] CEGIS repair aborted (treat as failed): {type(ex).__name__}: {ex}")
            return full, False
        except Exception as ex:
            if trace:
                print(f"[repair] CEGIS repair crashed (treat as failed): {type(ex).__name__}: {ex}")
            return full, False

        if applied and patched != full:
            if _verify_full_proof(isa, session, patched):
                return patched, True

            # Partial progress: keep it, then try to open the failing spot into a 'sorry'
            if trace:
                print("[repair] Partial progress in topdown repair (unverified). Opening sorries...")
            full = patched
            full2, opened = _open_minimal_sorries(isa, session, full)
            if opened:
                full = full2
                t_spans = _tactic_spans_topdown(full)
                i = 0
                continue

        i += 1

    return full, False

def _quick_state_and_errors(isabelle, session: str, text: str, *, timeout_s: Optional[int] = None) -> Tuple[str, List[str]]:
    """Run a theory quickly and return (last_state_block, error_messages).

    Best-effort utility used only to locate an error line for opening with 'sorry'.
    It must be robust: on any exception, return empty state and a single error string.
    """
    try:
        ts = text.splitlines()
        thy = build_theory(ts, add_print_state=True, end_with=None)
        out = _run_theory_with_timeout(
            isabelle, session, thy,
            timeout_s=int(timeout_s) if timeout_s is not None else min(_ISA_VERIFY_TIMEOUT_S, 15),
        )
        state = ""
        try:
            state = last_print_state_block(out)
        except Exception:
            state = ""

        # Normalize messages to strings for simple scanning
        if isinstance(out, (list, tuple)):
            msgs = [str(m) for m in out]
        else:
            msgs = [str(out)]

        errs = [m for m in msgs if any(tok in m.lower() for tok in ("error", "exception", "failed"))]
        return state, errs
    except Exception as ex:
        return "", [str(ex)]
    
def _extract_error_lines(errs: List[str]) -> List[int]:
    """Extract 1-based line numbers from Isabelle error messages (best-effort)."""
    if not errs:
        return []

    patts = [
        re.compile(r"(?i)\bline\s+(\d+)\b"),          # 'line 23'
        re.compile(r"(?i)\bLine\s+(\d+)\b"),          # 'Line 23'
        re.compile(r":(\d+):(\d+)\b"),                # 'Scratch.thy:23:5'
        re.compile(r"\((\d+),(\d+)\)"),               # '(23,5)'
    ]

    found: set[int] = set()
    for raw in errs:
        s = str(raw)
        for p in patts:
            for m in p.finditer(s):
                try:
                    n = int(m.group(1))
                    if n > 0:
                        found.add(n)
                except Exception:
                    pass

    return sorted(found)

def _open_minimal_sorries(isabelle, session: str, text: str) -> Tuple[str, bool]:
    """Localize a failing finisher with minimal opening (replace 1 tactic with 'sorry').

    Returns (new_text, opened). Never raises.
    """
    def _ensure_nl(s: str) -> str:
        return s if s.endswith("\n") else s + "\n"

    # First check if the whole thing passes
    def runs(ts):
        try:
            thy = build_theory(ts, add_print_state=False, end_with=None)
            _run_theory_with_timeout(isabelle, session, thy, timeout_s=_ISA_VERIFY_TIMEOUT_S)
            return True
        except Exception:
            return False

    try:
        if runs(text.splitlines()):
            return _ensure_nl(text), False
    except Exception:
        # If even 'runs' crashes, do nothing.
        return _ensure_nl(text), False

    # Document fails: find first error line, then open nearest tactic by turning it into 'sorry'
    try:
        _, errs = _quick_state_and_errors(isabelle, session, text)
        err_lines = _extract_error_lines(errs)
    except Exception:
        err_lines = []

    if not err_lines:
        return _ensure_nl(text), False

    failing_line_1based = min(err_lines)
    lines = text.splitlines()
    failing_idx = failing_line_1based - 1

    for i in range(min(failing_idx, len(lines) - 1), -1, -1):
        line = lines[i]

        if _TACTIC_LINE_RE.match(line) or line.strip() == "done" or _BARE_DOT.match(line):
            indent = line[:len(line) - len(line.lstrip(" "))]
            lines[i] = f"{indent}sorry"
            return _ensure_nl("\n".join(lines)), True

        m = _INLINE_BY_TAIL.search(line)
        if m:
            indent = line[:len(line) - len(line.lstrip(" "))]
            header = line[:m.start()].rstrip()
            lines[i] = header
            lines.insert(i + 1, f"{indent}sorry")
            return _ensure_nl("\n".join(lines)), True

    return _ensure_nl(text), False

# ============================================================================
# Public API
# ============================================================================

def plan_outline(goal: str, *, model: Optional[str] = None, outline_k: Optional[int] = None,
                outline_temps: Optional[Iterable[float]] = None, legacy_single_outline: bool = False,
                priors_path: Optional[str] = None, context_hints: bool = False,
                lib_templates: bool = False, alpha: float = 1.0, beta: float = 0.5,
                gamma: float = 0.2, hintlex_path: Optional[str] = None, hintlex_top: int = 8) -> str:
    """Generate Isar outline with 'sorry' placeholders."""
    server_info, proc = start_isabelle_server(name="planner", log_file="logs/planner_ui.log")
    isa = get_isabelle_client(server_info)
    session = _extract_session_id(isa.session_start(session=ISABELLE_SESSION))
    
    try:
        if legacy_single_outline:
            return propose_isar_skeleton(goal, model=model, temp=0.35, force_outline=True).text
        
        temps = tuple(outline_temps) if outline_temps else (0.35, 0.55, 0.85)
        k = int(outline_k) if outline_k is not None else 3
        
        best, _ = propose_isar_skeleton_diverse_best(
            goal, isabelle=isa, session_id=session, model=model, temps=temps, k=k,
            force_outline=True, priors_path=priors_path, context_hints=context_hints,
            lib_templates=lib_templates, alpha=alpha, beta=beta, gamma=gamma,
            hintlex_path=hintlex_path, hintlex_top=hintlex_top,
        )
        return best.text
    finally:
        _cleanup_resources(isa, proc)

def plan_and_fill(goal: str, model: Optional[str] = None, timeout: int = 100, *, mode: str = "auto",
                 outline_k: Optional[int] = None, outline_temps: Optional[Iterable[float]] = None,
                 legacy_single_outline: bool = False, repairs: bool = True,
                 max_repairs_per_hole: int = 2, trace: bool = False, repair_trace: bool = False,
                 priors_path: Optional[str] = None, context_hints: bool = False,
                 lib_templates: bool = False, alpha: float = 1.0, beta: float = 0.5,
                 gamma: float = 0.2, hintlex_path: Optional[str] = None,
                 hintlex_top: int = 8) -> PlanAndFillResult:
    """Plan and fill holes in Isar proofs.

    Notes:
      - 'repair_trace' is a backwards-compatible alias used by the UI. It enables 'trace'.
      - Repair/verification timeouts or broken Isabelle responses must not crash the caller.
        We treat them as repair failures, and (best-effort) restart Isabelle for subsequent calls.
    """
    if repair_trace and not trace:
        trace = True

    # F17: hard wall-clock cap at 1.2× nominal timeout via SIGALRM. The
    # cooperative `deadline` checks alone don't bound Isabelle subprocess time
    # (sledgehammer `metis` reconstruction is in-Isabelle and uninterruptible
    # from Python). SIGALRM in the main thread breaks any pending fut.result()
    # or socket read; the `finally:` cleanup kills the Isabelle proc, which
    # in turn unblocks any worker threads (shutdown(wait=False) so they leak
    # cleanly until proc-kill).
    _alarm_installed = False
    _prev_alarm_handler = None
    if threading.current_thread() is threading.main_thread():
        cap_s = max(1, int(1.2 * float(timeout)) + 1)
        def _alarm_handler(signum, frame):
            raise DeadlineExceeded(
                f"wall-clock cap {cap_s}s exceeded (1.2× of nominal {timeout}s)"
            )
        try:
            _prev_alarm_handler = signal.signal(signal.SIGALRM, _alarm_handler)
            signal.alarm(cap_s)
            _alarm_installed = True
        except (ValueError, OSError):
            _alarm_installed = False

    server_info, proc = start_isabelle_server(name="planner", log_file="logs/planner_ui.log")
    isa = get_isabelle_client(server_info)
    session = _extract_session_id(isa.session_start(session=ISABELLE_SESSION))

    deadline = Deadline(float(timeout))
    left_s = deadline.remaining

    restart_count = 0

    def _restart_isabelle(reason: str, ex: Optional[BaseException] = None) -> None:
        nonlocal isa, session, proc, restart_count
        if restart_count >= 2:
            return
        restart_count += 1
        if trace:
            msg = f"[planner] Restarting Isabelle (#{restart_count}) due to {reason}"
            if ex is not None:
                msg += f": {type(ex).__name__}: {ex}"
            print(msg)
        try:
            _cleanup_resources(isa, proc)
        except Exception:
            pass
        server_info2, proc2 = start_isabelle_server(name="planner", log_file="logs/planner_ui.log")
        isa2 = get_isabelle_client(server_info2)
        session2 = _extract_session_id(isa2.session_start(session=ISABELLE_SESSION))
        isa, session, proc = isa2, session2, proc2

    try:
        # F11: direct-prover fast path. Many goals (esp. ones sledge can close
        # in one shot) don't need outline+Fill at all; that overhead only adds
        # failure modes. Try the prover directly first.
        if mode == "auto":
            try:
                direct_proof = _try_prover_direct(isa, session, goal, model, deadline, trace=trace)
            except (TimeoutError, _FuturesTimeout, ValueError) as ex:
                _restart_isabelle("try_prover_direct", ex)
                direct_proof = None
            except Exception as ex:
                if trace:
                    print(f"[planner] F11 direct-prover crashed: {type(ex).__name__}: {ex}")
                direct_proof = None
            if direct_proof is not None:
                if trace:
                    print("[planner] F11 direct-prover path solved the goal; skipping outline+Fill.")
                return PlanAndFillResult(True, direct_proof, [direct_proof], [])

        # Generate outline (F9: bounded by per-goal deadline)
        if legacy_single_outline:
            # F23: extend the F22 viable-LLM-call floor to this path. The old
            # `max(3, min(30, deadline.remaining_int(cap=30, min_=3)))` collapsed
            # to 3 under a tight deadline, guaranteeing ReadTimeout on
            # qwen2.5-coder:7b regardless of prompt size.
            rem = deadline.remaining_int(cap=60, min_=_MIN_VIABLE_LLM_CALL_S)
            if rem < _MIN_VIABLE_LLM_CALL_S:
                full = ""  # bail rather than fire a doomed call
            else:
                single_to = max(_MIN_VIABLE_LLM_CALL_S, rem)
                try:
                    full = propose_isar_skeleton(goal, model=model, temp=0.35, force_outline=(mode == "outline"),
                                                 timeout_s=single_to).text
                except Exception:
                    full = ""
            if not full:
                return PlanAndFillResult(False, "", [], [0])
        else:
            temps = tuple(outline_temps) if outline_temps else (0.35, 0.55, 0.85)
            k = int(outline_k) if outline_k is not None else 3
            best, _ = propose_isar_skeleton_diverse_best(
                goal, isabelle=isa, session_id=session, model=model, temps=temps, k=k,
                force_outline=(mode == "outline"), priors_path=priors_path,
                context_hints=context_hints, lib_templates=lib_templates,
                alpha=alpha, beta=beta, gamma=gamma, hintlex_path=hintlex_path,
                hintlex_top=hintlex_top,
                deadline=deadline,
            )
            full = best.text

        spans = find_sorry_spans(full)

        if mode == "outline":
            return PlanAndFillResult(True, full, [], [])

        # Handle complete proofs
        if not spans:
            try:
                if _verify_full_proof(isa, session, full):
                    return PlanAndFillResult(True, full, [], [])
            except (TimeoutError, _FuturesTimeout, ValueError) as ex:
                _restart_isabelle("verify_full_proof", ex)

            if repairs and left_s() > 6.0:
                full, ok = _repair_failed_proof_topdown(isa, session, full, goal, model, left_s, max_repairs_per_hole, trace, deadline=deadline)
                if ok:
                    return PlanAndFillResult(True, full, [], [])

            full2, opened = _open_minimal_sorries(isa, session, full)
            full = full2 if opened else full
            if not opened:
                return PlanAndFillResult(False, full, [], [0])

        # Fill holes
        lemma_line = _first_lemma_line(full)
        if not lemma_line:
            return PlanAndFillResult(False, full, [], [0])

        goal_text = _extract_goal_from_lemma_line(lemma_line)
        fills: List[str] = []
        failed: List[int] = []
        repair_progress: dict[str, int] = {}
        stage_tries: dict[Tuple[str, int], int] = {}
        _skip_fill_logged_once: set[Tuple[str, int]] = set()
        # F29b: fires once when we'd otherwise enter repair on a substantial
        # sorry-laden outline that Fill couldn't make any progress on — the
        # signature of locale-context-dependent goals (hol_main_easy:g1/g7).
        _f29b_checked = False

        focused_hole_key: Optional[str] = None
        # F7: cap fresh-outline regenerations so the loop can't restart indefinitely.
        _MAX_FRESH_OUTLINES = 2
        fresh_outline_count = 0

        while "sorry" in full and left_s() > 0:
            if deadline.expired():
                if trace:
                    print(f"[planner] Deadline expired ({timeout}s); stopping main loop.")
                break
            spans = find_sorry_spans(full)
            if not spans:
                break
            # F6: prune stale entries — fingerprints for sorrys that no longer exist.
            current_keys = {_hole_fingerprint(full, sp) for sp in spans}
            for stale in [k for k in repair_progress if k not in current_keys]:
                repair_progress.pop(stale, None)
            for k in [k for k in stage_tries if k[0] not in current_keys]:
                stage_tries.pop(k, None)

            span = None
            if focused_hole_key is not None:
                for s in spans:
                    if _hole_fingerprint(full, s) == focused_hole_key:
                        span = s
                        break
                if span is None:
                    if trace:
                        print(f"[fill] Focused hole @{focused_hole_key} was closed. Moving on.")
                    focused_hole_key = None

            if span is None:
                # F4: spec requires "always focus on the earliest failure point".
                err_line, err_span = _classify_earliest_failure(isa, session, full, spans)
                if err_span is not None:
                    if trace:
                        print(f"[planner] Earliest failure @ line {err_line} is at sorry; focusing that span.")
                    span = err_span
                elif err_line is not None:
                    # Earliest error is on a non-sorry line (structural). Route the nearest
                    # sorry directly to repair (skip Fill, which can't help structural errors).
                    err_lo, _ = _line_offset_1based(full, err_line)
                    span = _nearest_sorry_span(spans, err_lo) or spans[0]
                    hk_pre = _hole_fingerprint(full, span)
                    if repair_progress.get(hk_pre, 0) < 1:
                        repair_progress[hk_pre] = 1
                        if trace:
                            print(f"[planner] Earliest failure @ line {err_line} is non-sorry; starting at repair stage 1.")
                else:
                    span = spans[0]

            hole_key = _hole_fingerprint(full, span)
            # Cap per-hole budget at half the remaining deadline so Fill leaves room for
            # the subsequent CEGIS repair pass in the same iteration (F1 enforcement).
            per_hole_budget = int(max(5, min(deadline.remaining() * 0.5, left_s() / max(1, len(spans)))))
            start_stage = repair_progress.get(hole_key, 0)

            # Always try fill first unless we're in escalated repair stages
            if start_stage == 0:
                try:
                    full2, ok, script = _fill_one_hole(
                        isa, session, full, span, goal_text, model,
                        per_hole_timeout=per_hole_budget, trace=trace
                    )
                except (TimeoutError, _FuturesTimeout, ValueError) as ex:
                    _restart_isabelle("fill_one_hole", ex)
                    full2, ok, script = full, False, "fill-exception"
                except Exception as ex:
                    if trace:
                        print(f"[fill] _fill_one_hole crashed: {type(ex).__name__}: {ex}")
                    full2, ok, script = full, False, "fill-exception"

                if ok and full2 != full:
                    full = full2
                    fills.append(script)
                    repair_progress.pop(hole_key, None)
                    focused_hole_key = None
                    continue
                elif not ok and full2 != full:
                    if trace:
                        print("[fill] Partial progress from fill (unverified). Opening sorries and staying focused...")
                    old_start = span[0]
                    full = full2
                    full2, opened = _open_minimal_sorries(isa, session, full)
                    if opened:
                        full = full2
                        new_spans = find_sorry_spans(full)
                        near = _nearest_sorry_span(new_spans, old_start)
                        focused_hole_key = _hole_fingerprint(full, near) if near else None
                        continue
                    else:
                        if trace:
                            print("[fill] Could not open sorries. Escalating to repair stage 1...")
                        repair_progress[hole_key] = 1
                        focused_hole_key = hole_key
                        start_stage = 1
                else:
                    if trace:
                        print("[fill] Fill made no progress. Escalating to repair stage 1...")
                    repair_progress[hole_key] = 1
                    focused_hole_key = hole_key
                    start_stage = 1
            else:
                if trace and (hole_key, start_stage) not in _skip_fill_logged_once:
                    print(f"[fill] Skipping fill for hole @{hole_key}; running repairs at stage {start_stage}")
                    _skip_fill_logged_once.add((hole_key, start_stage))

            # Try CEGIS repairs
            current_stage = repair_progress.get(hole_key, 0)
            # F29b: bail when the first Fill made zero progress on a substantial
            # sorry-laden outline and >50% of the per-goal budget is already
            # burned. Catches the "LLM wrote an outline Fill can't close"
            # pattern (typically locale-context-dependent goals). Saves ~60s
            # per occurrence; without this guard, the subsequent repair stages
            # would also fail and burn the remaining ~60s anyway.
            if not _f29b_checked and current_stage > 0:
                _f29b_checked = True
                _elapsed_frac = (timeout - left_s()) / max(1.0, float(timeout))
                if (
                    len(fills) == 0
                    and "sorry" in full
                    and len(full) > 200
                    and _elapsed_frac > 0.5
                ):
                    if trace:
                        print(f"[planner] F29b early-bail: 0 fills + sorry-laden outline "
                              f"({len(full)} chars) + {_elapsed_frac:.0%} of budget burned")
                    return PlanAndFillResult(False, full, [], [0])
            if current_stage > 0 and repairs and left_s() > 6:
                try:
                    state = _print_state_before_hole(isa, session, full, span, trace)
                    eff_goal = _effective_goal_from_state(state, goal_text, full, span, trace)
                except (TimeoutError, _FuturesTimeout, ValueError) as ex:
                    _restart_isabelle("print_state_before_hole", ex)
                    continue
                except Exception as ex:
                    if trace:
                        print(f"[repair] Could not compute effective goal: {type(ex).__name__}: {ex}")
                    continue

                try:
                    patched, applied, _ = try_cegis_repairs(
                        full_text=full, hole_span=span, goal_text=eff_goal, model=model,
                        isabelle=isa, session=session,
                        repair_budget_s=min(30.0, max(15.0, left_s() * 0.33)),
                        max_ops_to_try=max_repairs_per_hole, beam_k=2,
                        allow_whole_fallback=False, trace=trace, resume_stage=current_stage,
                        deadline=deadline,
                    )
                except (TimeoutError, _FuturesTimeout, ValueError) as ex:
                    _restart_isabelle("try_cegis_repairs", ex)
                    patched, applied = full, False
                except Exception as ex:
                    if trace:
                        print(f"[repair] try_cegis_repairs crashed: {type(ex).__name__}: {ex}")
                    patched, applied = full, False

                if patched != full:
                    try:
                        if _verify_full_proof(isa, session, patched):
                            if trace:
                                print(f"[repair] Stage {current_stage} repair verified! Clearing progress and moving on.")
                            full = patched
                            repair_progress.clear()
                            stage_tries.clear()
                            focused_hole_key = None
                            continue
                    except (TimeoutError, _FuturesTimeout, ValueError) as ex:
                        _restart_isabelle("verify_full_proof_after_repair", ex)

                    # F3: Per spec, "after any repair edit, run Fill again on any newly
                    # introduced sorry placeholders". Run Fill on each new sorry (location
                    # not present in pre-repair full), then re-verify.
                    pre_repair_spans = {sp for sp in find_sorry_spans(full)}
                    new_spans = [sp for sp in find_sorry_spans(patched) if sp not in pre_repair_spans]
                    if new_spans and not deadline.expired() and left_s() > 6:
                        if trace:
                            print(f"[repair] Re-running Fill on {len(new_spans)} new sorrys from repair patch...")
                        new_full = patched
                        any_progress = False
                        for ns in new_spans:
                            if deadline.expired() or left_s() < 6:
                                break
                            cur_spans = find_sorry_spans(new_full)
                            ns_now = _nearest_sorry_span(cur_spans, ns[0]) if cur_spans else None
                            if ns_now is None:
                                continue
                            sub_budget = int(max(5, min(deadline.remaining(), left_s() / max(1, len(new_spans)))))
                            try:
                                cand, ok, _scr = _fill_one_hole(
                                    isa, session, new_full, ns_now, goal_text, model,
                                    per_hole_timeout=sub_budget, trace=trace,
                                )
                            except (TimeoutError, _FuturesTimeout, ValueError) as ex:
                                _restart_isabelle("fill_after_repair", ex)
                                continue
                            except Exception as ex:
                                if trace:
                                    print(f"[repair] Fill-after-repair crashed: {type(ex).__name__}: {ex}")
                                continue
                            if ok and cand != new_full:
                                new_full = cand
                                any_progress = True
                        if any_progress:
                            try:
                                if _verify_full_proof(isa, session, new_full):
                                    if trace:
                                        print("[repair] Fill-after-repair closed the proof.")
                                    full = new_full
                                    repair_progress.clear()
                                    stage_tries.clear()
                                    focused_hole_key = None
                                    continue
                            except (TimeoutError, _FuturesTimeout, ValueError) as ex:
                                _restart_isabelle("verify_after_fill_after_repair", ex)
                            # Keep partial progress so the next iteration sees fewer sorrys.
                            patched = new_full

                    # Unverified change: count attempt and decide escalation
                    key = (hole_key, start_stage)
                    stage_tries[key] = stage_tries.get(key, 0) + 1

                    STAGE1_CAP = 2
                    STAGE2_CAP = 3

                    should_escalate = False
                    if start_stage == 1 and stage_tries[key] >= STAGE1_CAP:
                        should_escalate = True
                        if trace:
                            print(f"[repair] Stage 1 cap ({STAGE1_CAP}) reached. Escalating to stage 2...")
                    elif start_stage == 2 and stage_tries.get((hole_key, 2), 0) >= STAGE2_CAP:
                        should_escalate = True
                        if trace:
                            print(f"[repair] Stage 2 cap ({STAGE2_CAP}) reached. Regenerating whole proof...")

                    if should_escalate:
                        if start_stage < 2:
                            repair_progress[hole_key] = 2
                            focused_hole_key = hole_key
                            continue
                        else:
                            regen_budget = min(40.0, max(8.0, left_s() * 0.8))
                            try:
                                new_full, ok_re, _ = regenerate_whole_proof(
                                    full_text=full, goal_text=goal_text, model=model,
                                    isabelle=isa, session=session, budget_s=regen_budget,
                                    trace=trace, prior_outline_text=full,
                                    deadline=deadline,
                                )
                            except (TimeoutError, _FuturesTimeout, ValueError) as ex:
                                _restart_isabelle("regenerate_whole_proof", ex)
                                new_full, ok_re = full, False
                            except Exception as ex:
                                if trace:
                                    print(f"[repair] regenerate_whole_proof crashed: {type(ex).__name__}: {ex}")
                                new_full, ok_re = full, False

                            if ok_re and new_full != full:
                                full = new_full
                                repair_progress.clear()
                                stage_tries.clear()
                                focused_hole_key = None
                                continue

                            # F7: cap fresh-outline regenerations so we don't restart indefinitely.
                            if fresh_outline_count >= _MAX_FRESH_OUTLINES:
                                if trace:
                                    print(f"[repair] Whole regen failed and fresh-outline cap ({_MAX_FRESH_OUTLINES}) reached; giving up.")
                                break
                            if trace:
                                print(f"[repair] Whole regeneration failed; proposing fresh outline #{fresh_outline_count + 1}…")
                            temps = tuple(outline_temps) if outline_temps else (0.35, 0.55, 0.85)
                            k = int(outline_k) if outline_k is not None else 3
                            best, _ = propose_isar_skeleton_diverse_best(
                                goal_text, isabelle=isa, session_id=session, model=model, temps=temps, k=k,
                                force_outline=True, priors_path=priors_path, context_hints=context_hints,
                                lib_templates=lib_templates, alpha=alpha, beta=beta, gamma=gamma,
                                hintlex_path=hintlex_path, hintlex_top=hintlex_top,
                                deadline=deadline,
                            )
                            full = best.text
                            fresh_outline_count += 1
                            repair_progress.clear()
                            stage_tries.clear()
                            focused_hole_key = None
                            continue

                    if trace:
                        cap = STAGE1_CAP if start_stage == 1 else STAGE2_CAP
                        print(f"[repair] Stage {start_stage} changed but unverified (attempt {stage_tries[key]}/{cap}). Opening sorries...")
                    full = patched
                    full2, opened = _open_minimal_sorries(isa, session, full)
                    if opened:
                        full = full2
                        focused_hole_key = None
                        continue
                    else:
                        if trace:
                            print("[repair] Could not open sorries; escalating stage...")
                        if start_stage < 2:
                            repair_progress[hole_key] = 2
                            focused_hole_key = hole_key
                        continue

                # No change from repair: count attempt and escalate
                key = (hole_key, start_stage)
                stage_tries[key] = stage_tries.get(key, 0) + 1
                if start_stage < 2:
                    repair_progress[hole_key] = min(start_stage + 1, 2)
                    focused_hole_key = hole_key
                else:
                    repair_progress[hole_key] = 2
                    focused_hole_key = hole_key

        # Final verification
        success = ("sorry" not in full)
        if success:
            try:
                if _verify_full_proof(isa, session, full):
                    return PlanAndFillResult(True, full, fills, failed)
            except (TimeoutError, _FuturesTimeout, ValueError) as ex:
                _restart_isabelle("final_verify_full_proof", ex)

        return PlanAndFillResult(False, full, fills, failed)

    except DeadlineExceeded as ex:
        if trace:
            print(f"[planner] {ex}; terminating goal.")
        try:
            failed_full = full  # type: ignore[name-defined]
        except NameError:
            failed_full = ""
        try:
            failed_fills = fills  # type: ignore[name-defined]
        except NameError:
            failed_fills = []
        return PlanAndFillResult(False, failed_full, failed_fills, [0])

    finally:
        if _alarm_installed:
            try:
                signal.alarm(0)
            except (ValueError, OSError):
                pass
            if _prev_alarm_handler is not None:
                try:
                    signal.signal(signal.SIGALRM, _prev_alarm_handler)
                except (ValueError, OSError):
                    pass
        _cleanup_resources(isa, proc)