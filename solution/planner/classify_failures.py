"""classify_failures.py — Post-mortem failure-mode classifier for planner sweeps.

For the report's analysis section. Reads a sweep output dir, classifies every
attempted goal by the *leading* failure mode, and emits a markdown table the
report can paste directly.

Reads:
  <sweep_dir>/<set>.csv       — per-goal outcomes (sweep-script output)
  <sweep_dir>/_logs/<set>.log — full traces (for outline extraction)

Emits:
  <sweep_dir>/failure_modes.md
  <sweep_dir>/failure_modes.csv

Categories (tested in order, first match wins):
  success           — verified_ok && no sorry
  placeholder       — outline body matches F18/F28a placeholder regex
  truncation        — outline has F28b balance issue (unterminated string, etc.)
  hallucinated_id   — outline cites identifiers not in HOL known-names table (F27)
  deadline_overrun  — elapsed > timeout_s × 1.0
  sorry_leak        — verified_ok=True but had_sorry=True (--strict-no-sorry catches)
  verify_fail_other — verified_ok=False, none of the above
  unknown_failure   — fallthrough

Usage:
  python -m planner.classify_failures --sweep-dir ../report_metric_sweep_<ts>/
"""
from __future__ import annotations
import argparse
import csv
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

# Force validator into "on" mode for the analysis pass even if env var unset,
# then load known names. Done at import time so skeleton.py picks it up.
os.environ.setdefault("USE_NAME_VALIDATOR", "1")

from planner.skeleton import (
    _count_unknown_refs,
    _count_balance_issues,
    _count_comment_placeholders,
    _load_known_names,
)


GOAL_HEADER_RE = re.compile(r'\[planner\] ▶ goal:\s*(.+?)(?:\n|$)')
DONE_LINE_RE = re.compile(
    r'\[planner\]\s+done in\s+([0-9.]+)s\s+\|\s+'
    r'success=(\w+)\s+had_sorry=(\w+)\s+verified_ok=(\w+)'
)
OUTLINE_BLOCK_RE = re.compile(
    r'Current proof outline:\s*\n(.+?)(?=\n\[planner\]\s+(?:done in|verifying|▶ goal:)|\Z)',
    re.DOTALL,
)


def extract_per_goal(log_text: str) -> List[Dict]:
    """Walk log_text, return [{goal, outline, elapsed_s, success, had_sorry,
    verified_ok}, ...] in attempt order. Robust to missing fields when a goal
    was cut off mid-run (e.g. our killed minif2f_30 last attempt)."""
    blocks = re.split(r'(?=\[planner\] ▶ goal:)', log_text)
    rows: List[Dict] = []
    for blk in blocks:
        m_goal = GOAL_HEADER_RE.match(blk)
        if not m_goal:
            continue
        goal = m_goal.group(1).strip()
        outline_matches = list(OUTLINE_BLOCK_RE.finditer(blk))
        outline = outline_matches[-1].group(1).strip() if outline_matches else ""
        m_done = DONE_LINE_RE.search(blk)
        if m_done:
            rows.append({
                'goal': goal,
                'outline': outline,
                'elapsed_s': float(m_done.group(1)),
                'success': m_done.group(2).lower() == 'true',
                'had_sorry': m_done.group(3).lower() == 'true',
                'verified_ok': m_done.group(4).lower() == 'true',
                'cut_off': False,
            })
        else:
            rows.append({
                'goal': goal,
                'outline': outline,
                'elapsed_s': 0.0,
                'success': False,
                'had_sorry': False,
                'verified_ok': False,
                'cut_off': True,
            })
    return rows


def classify(row: Dict, timeout_s: float) -> str:
    if row['cut_off']:
        return 'cut_off_by_sweep_kill'
    if row['success']:
        return 'success'
    outline = row.get('outline', '')
    # Order matters — pick the *leading* / cheapest-to-detect cause.
    if _count_comment_placeholders(outline) > 0:
        return 'placeholder'
    if _count_balance_issues(outline) > 0:
        return 'truncation'
    if _count_unknown_refs(outline) > 0:
        return 'hallucinated_id'
    if row['elapsed_s'] > timeout_s:
        return 'deadline_overrun'
    if row['had_sorry'] and row['verified_ok']:
        return 'sorry_leak'
    if not row['verified_ok']:
        return 'verify_fail_other'
    return 'unknown_failure'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--sweep-dir', required=True,
                    help='Sweep output dir (contains _logs/ and per-set .csv files)')
    ap.add_argument('--timeout-s', type=float, default=180.0,
                    help='Per-goal timeout the sweep used (default 180)')
    ap.add_argument('--known-names-path', default=None,
                    help='Override path to known_names.json (default: probe '
                         '<sweep>/../solution/datasets/known_names.json)')
    args = ap.parse_args()

    sweep = Path(args.sweep_dir).expanduser().resolve()
    logs = sweep / '_logs'
    if not sweep.is_dir() or not logs.is_dir():
        print(f'ERROR: not a sweep dir with _logs/: {sweep}', file=sys.stderr)
        return 1

    # Probe known_names.json
    if args.known_names_path:
        os.environ['KNOWN_NAMES_PATH'] = args.known_names_path
    else:
        # Default sweep dirs live under .../agenticreasoning/; known_names.json
        # lives under .../agenticreasoning/solution/datasets/.
        candidate = sweep.parent / 'solution' / 'datasets' / 'known_names.json'
        if candidate.exists():
            os.environ['KNOWN_NAMES_PATH'] = str(candidate)
    # Force-load now with the right env
    import planner.skeleton as sk
    sk._KNOWN_NAMES_CACHE = None  # force re-load with current env
    sk._KNOWN_NAMES_PROBED = False
    _load_known_names()

    sets: Dict[str, List[Dict]] = {}
    for log_path in sorted(logs.glob('*.log')):
        stem = log_path.stem
        rows = extract_per_goal(log_path.read_text(errors='replace'))
        for r in rows:
            r['mode'] = classify(r, args.timeout_s)
        sets[stem] = rows

    # ---- markdown ----
    md_path = sweep / 'failure_modes.md'
    with md_path.open('w', encoding='utf-8') as f:
        f.write(f'# Failure-mode classification — `{sweep.name}`\n\n')
        f.write('Generated by `solution/planner/classify_failures.py`. Each attempted '
                'goal is classified by the **leading** detectable failure mode '
                f'(categories tested in order). Wall-time threshold for '
                f'`deadline_overrun`: > {args.timeout_s:.0f} s. The four detectors '
                '(`placeholder`, `truncation`, `hallucinated_id`, `verify_fail_other`) '
                'mirror the F18 / F28a / F28b / F27 scoring penalties applied to '
                'outlines at generation time — so this is a direct map between '
                'what the runtime *could have rejected pre-verify* if those guards '
                'had been on during the sweep.\n\n')

        all_modes: Counter = Counter()
        for stem, rows in sets.items():
            modes = Counter(r['mode'] for r in rows)
            total = sum(modes.values())
            n_success = modes.get('success', 0)
            n_fail = total - n_success - modes.get('cut_off_by_sweep_kill', 0)
            n_cut = modes.get('cut_off_by_sweep_kill', 0)
            f.write(f'## {stem}\n\n')
            f.write(f'**Attempts:** {total}.  **Strict-pass:** {n_success}'
                    f' ({100*n_success/max(1,total):.0f}%).')
            if n_cut:
                f.write(f'  **Cut off by sweep kill:** {n_cut}.')
            f.write(f'  **Failures:** {n_fail}.\n\n')
            f.write('| Mode | Count |\n|---|---:|\n')
            for mode, ct in sorted(modes.items(), key=lambda x: (-x[1], x[0])):
                f.write(f'| `{mode}` | {ct} |\n')
            f.write('\n')
            f.write('| # | Goal | Mode | Wall (s) |\n|---:|---|---|---:|\n')
            for i, r in enumerate(rows, 1):
                g = r['goal']
                if len(g) > 90:
                    g = g[:87] + '…'
                f.write(f"| {i} | `{g}` | `{r['mode']}` | {r['elapsed_s']:.0f} |\n")
            f.write('\n')
            for m, c in modes.items():
                all_modes[m] += c

        # Cross-set summary
        total_all = sum(all_modes.values())
        n_succ_all = all_modes.get('success', 0)
        n_cut_all = all_modes.get('cut_off_by_sweep_kill', 0)
        n_fail_all = total_all - n_succ_all - n_cut_all
        f.write('## Cross-set summary\n\n')
        f.write(f'**Total attempts:** {total_all}. ')
        f.write(f'**Strict-pass:** {n_succ_all} '
                f'({100*n_succ_all/max(1,total_all):.1f}%). ')
        if n_cut_all:
            f.write(f'**Cut off:** {n_cut_all}. ')
        f.write(f'**Failures classified:** {n_fail_all}.\n\n')
        f.write('| Failure mode | Count | % of failures | % of attempts |\n')
        f.write('|---|---:|---:|---:|\n')
        for mode in [
            'placeholder', 'truncation', 'hallucinated_id', 'deadline_overrun',
            'sorry_leak', 'verify_fail_other', 'unknown_failure',
        ]:
            ct = all_modes.get(mode, 0)
            if ct == 0:
                continue
            pct_f = 100 * ct / max(1, n_fail_all)
            pct_a = 100 * ct / max(1, total_all)
            f.write(f'| `{mode}` | {ct} | {pct_f:.0f}% | {pct_a:.0f}% |\n')

    # ---- csv ----
    csv_path = sweep / 'failure_modes.csv'
    with csv_path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['set', 'goal', 'success', 'mode', 'elapsed_s',
                    'had_sorry', 'verified_ok', 'cut_off'])
        for stem, rows in sets.items():
            for r in rows:
                w.writerow([
                    stem, r['goal'], r['success'], r['mode'],
                    f"{r['elapsed_s']:.2f}", r['had_sorry'], r['verified_ok'],
                    r['cut_off'],
                ])

    print(f'Wrote {md_path}')
    print(f'Wrote {csv_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
