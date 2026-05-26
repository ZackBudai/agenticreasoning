#!/usr/bin/env bash
# plan_compare.sh — Run planner.experiments bench from both baseline/ and solution/
# on the same goal file, then emit planner_comparison/summary.md.
#
# Usage:
#   ./plan_compare.sh <absolute-goal-file>
# Env vars: MODEL, TIMEOUT, K, TEMPS, OUT_ROOT
set -u
cd "$(dirname "$0")"
ROOT="$(pwd -P)"
source solution/.venv/bin/activate

GOALS="${1:-$ROOT/datasets_subset/hard_25.txt}"
MODEL="${MODEL:-ollama:qwen2.5-coder:32b}"
TIMEOUT="${TIMEOUT:-120}"
K="${K:-3}"
TEMPS="${TEMPS:-0.35,0.55,0.85}"
OUT_ROOT="${OUT_ROOT:-$ROOT/planner_comparison}"
LOG_DIR="$OUT_ROOT/_logs"
mkdir -p "$OUT_ROOT" "$LOG_DIR"

# Resolve to absolute path so it's accessible from both subfolders.
case "$GOALS" in
  /*) ;;
  *)  GOALS="$ROOT/$GOALS" ;;
esac
[ -f "$GOALS" ] || { echo "goal file not found: $GOALS" >&2; exit 2; }

for which in baseline solution; do
  log="$LOG_DIR/${which}.log"
  echo "── planner.${which} (goal-file=$(basename "$GOALS"), model=$MODEL, timeout=${TIMEOUT}s, k=$K) → $log"
  (cd "$ROOT/$which" && python -u -m planner.experiments bench \
      --file "$GOALS" \
      --mode auto \
      --diverse --k "$K" --temps "$TEMPS" \
      --strict-no-sorry --verify \
      --timeout "$TIMEOUT" \
      --model "$MODEL" \
      --trace) > "$log" 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "  ! planner.${which} exited $rc (see $log)"
  fi
done

# ── Aggregate the two latest planner_results CSVs into a side-by-side ────────
python - "$ROOT" "$OUT_ROOT" "$GOALS" <<'PY'
import csv, sys, pathlib

root, out_root, goals_path = map(pathlib.Path, sys.argv[1:4])

def latest_csv(folder: pathlib.Path) -> pathlib.Path | None:
    rd = folder / "datasets" / "planner_results"
    if not rd.exists():
        return None
    files = sorted(rd.glob("*.csv"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None

def load(csv_path: pathlib.Path) -> dict[str, dict]:
    out = {}
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            out[row["goal"]] = row
    return out

b_csv = latest_csv(root / "baseline")
s_csv = latest_csv(root / "solution")
if not (b_csv and s_csv):
    print("WARN: missing CSV — baseline:", b_csv, "solution:", s_csv); sys.exit(1)

b = load(b_csv); s = load(s_csv)
goals = [ln.strip() for ln in goals_path.read_text().splitlines()
         if ln.strip() and not ln.startswith("#")]

n = len(goals)
def ok(row):  # success_only-when-verified-no-sorry
    return row and row.get("success", "").lower() == "true" and row.get("verified_ok", "").lower() == "true"

bn = sum(1 for g in goals if ok(b.get(g)))
sn = sum(1 for g in goals if ok(s.get(g)))

md = []
md.append(f"# Planner comparison — `{goals_path.name}` ({n} goals)\n")
md.append(f"Baseline CSV: `{b_csv.relative_to(root)}`")
md.append(f"Solution CSV: `{s_csv.relative_to(root)}`\n")
md.append("| Metric | Baseline | Solution |")
md.append("|---|---:|---:|")
md.append(f"| Verified (success && verified_ok && no-sorry) | {bn}/{n} | {sn}/{n} |")
md.append("")
md.append("## Per-goal")
md.append("| # | Goal | Baseline | Solution |")
md.append("|---:|---|:-:|:-:|")
for i, g in enumerate(goals, 1):
    bs = "✓" if ok(b.get(g)) else "✗"
    ss = "✓" if ok(s.get(g)) else "✗"
    md.append(f"| {i} | `{g[:80]}` | {bs} | {ss} |")

(out_root / "summary.md").write_text("\n".join(md) + "\n")
(out_root / "summary.csv").write_text(
    "metric,baseline,solution\n"
    f"verified,{bn},{sn}\n"
    f"total,{n},{n}\n"
)
print(f"verified — baseline {bn}/{n}, solution {sn}/{n}")
print(f"  summary → {out_root/'summary.md'}")
PY
