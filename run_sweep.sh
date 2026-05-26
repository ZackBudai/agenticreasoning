#!/usr/bin/env bash
# run_sweep.sh — Run compare.py once per dataset, write per-dataset out-dirs,
# then emit comparison/summary.{csv,md} with baseline vs solution pass counts.
#
# Usage:
#   ./run_sweep.sh curated   # lists/logic/nat/sets
#   ./run_sweep.sh tests     # hol_main_*_test.txt
#   ./run_sweep.sh all       # both groups
set -u
cd "$(dirname "$0")"
source solution/.venv/bin/activate

MODEL="${MODEL:-ollama:qwen2.5-coder:32b}"
TIMEOUT="${TIMEOUT:-120}"
BASELINE_TIMEOUT="${BASELINE_TIMEOUT:-30}"
SLEDGE_TIMEOUT="${SLEDGE_TIMEOUT:-30}"
OUT_ROOT="${OUT_ROOT:-comparison}"

CURATED=(
  "solution/datasets/lists.txt"
  "solution/datasets/logic.txt"
  "solution/datasets/nat.txt"
  "solution/datasets/sets.txt"
)
TESTS=(
  "solution/datasets/hol_main_easy_goals_test.txt"
  "solution/datasets/hol_main_mid_goals_test.txt"
  "solution/datasets/hol_main_hard_goals_test.txt"
)

GROUP="${1:-curated}"
case "$GROUP" in
  curated) FILES=("${CURATED[@]}") ;;
  tests)   FILES=("${TESTS[@]}") ;;
  all)     FILES=("${CURATED[@]}" "${TESTS[@]}") ;;
  *) echo "usage: $0 {curated|tests|all}" >&2; exit 2 ;;
esac

mkdir -p "$OUT_ROOT"
LOG_DIR="$OUT_ROOT/_logs"
mkdir -p "$LOG_DIR"

for f in "${FILES[@]}"; do
  base="$(basename "$f" .txt)"
  out="$OUT_ROOT/$base"
  log="$LOG_DIR/$base.log"
  n=$(grep -cv '^\s*\(#\|$\)' "$f")
  echo "── $base ($n goals) → $out"
  mkdir -p "$out"
  python -u compare.py \
    --goals-file "$f" \
    --n "$n" \
    --model "$MODEL" \
    --timeout "$TIMEOUT" \
    --baseline-timeout "$BASELINE_TIMEOUT" \
    --sledge-timeout "$SLEDGE_TIMEOUT" \
    --out-dir "$out" \
    --trace > "$log" 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "  ! compare.py exited $rc (see $log)"
  fi
done

# ── Aggregate summary ────────────────────────────────────────────────────────
python - <<'PY' "$OUT_ROOT"
import re, sys, csv, pathlib
root = pathlib.Path(sys.argv[1])
rows = []
for log in sorted((root / "_logs").glob("*.log")):
    txt = log.read_text(errors="replace")
    name = log.stem
    m_total = re.search(r"RESULTS SUMMARY \((\d+) goals\)", txt)
    m_tot   = re.search(r"TOTAL.*?(\d+)/(\d+)\s+(\d+)/(\d+)", txt)
    total = int(m_total.group(1)) if m_total else None
    if m_tot:
        b_ok, b_tot, s_ok, s_tot = map(int, m_tot.groups())
    else:
        b_ok = s_ok = 0
        b_tot = s_tot = total or 0
    rows.append((name, b_tot, b_ok, s_ok))

with open(root / "summary.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["dataset", "n_goals", "baseline_proved", "solution_proved"])
    for r in rows: w.writerow(r)

md = ["| Dataset | Goals | Baseline | Solution |", "|---|---:|---:|---:|"]
for name, n, b, s in rows:
    md.append(f"| {name} | {n} | {b} | {s} |")
(root / "summary.md").write_text("\n".join(md) + "\n")
print("\n".join(md))
PY
