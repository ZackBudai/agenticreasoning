#!/usr/bin/env bash
# report_metric_sweep.sh — broad-scope solution-only sweep for the report's headline numbers.
#
# Runs four goal files sequentially through `planner.experiments bench` from solution/
# only (baseline can be re-run later if there's time). Each set's results land under
# $OUT_DIR/<set>.log + <set>.csv. A final aggregated summary lands at $OUT_DIR/summary.md.
#
# Designed to fit a ~11h wall-clock window on qwen2.5-coder:7b with TIMEOUT=180, K=3.
#
# Usage:
#   nohup ./report_metric_sweep.sh > report_metric_sweep_run.log 2>&1 &
#
# Env overrides:
#   MODEL    (default: ollama:qwen2.5-coder:7b)
#   TIMEOUT  (default: 180)  per-goal cooperative deadline; F17 caps wall at 1.2×
#   K        (default: 3)
#   TEMPS    (default: 0.35,0.55,0.85)
#   OUT_DIR  (default: $ROOT/report_metric_sweep_<YYYYMMDD-HHMM>)
#   SETS     (default: "hard_25 mid_25 minif2f_30 holmain_50") space-separated stems
#            under datasets_subset/. Override to rerun a subset.
#   PRIORS   (default: $ROOT/solution/datasets/isar_priors.json)
#   HINTLEX  (default: $ROOT/solution/datasets/isar_hintlex.json)
#            Override to point at the F27 HOL-corpus RAG files
#            (isar_priors_hol.json / isar_hintlex_hol.json).
#   USE_NAME_VALIDATOR   (default: unset) Set to 1 to enable the F27 lemma-name
#                        validator. Requires solution/datasets/known_names.json.

set -u
cd "$(dirname "$0")"
ROOT="$(pwd -P)"
source solution/.venv/bin/activate

MODEL="${MODEL:-ollama:qwen2.5-coder:7b}"
TIMEOUT="${TIMEOUT:-180}"
K="${K:-3}"
TEMPS="${TEMPS:-0.35,0.55,0.85}"
SETS="${SETS:-hard_25 mid_25 minif2f_30 holmain_50}"
STAMP="$(date +%Y%m%d-%H%M)"
OUT_DIR="${OUT_DIR:-$ROOT/report_metric_sweep_$STAMP}"
LOG_DIR="$OUT_DIR/_logs"
mkdir -p "$LOG_DIR"

PRIORS="${PRIORS:-$ROOT/solution/datasets/isar_priors.json}"
HINTLEX="${HINTLEX:-$ROOT/solution/datasets/isar_hintlex.json}"
[ -s "$PRIORS"  ] || { echo "missing $PRIORS — build_rag.sh combined first" >&2; exit 2; }
[ -s "$HINTLEX" ] || { echo "missing $HINTLEX — build_rag.sh combined first" >&2; exit 2; }

EXTRA_FLAGS="--lib-templates --context-hints --priors $PRIORS --hintlex $HINTLEX"

echo "=== report_metric_sweep ==="
echo "stamp     : $STAMP"
echo "out_dir   : $OUT_DIR"
echo "model     : $MODEL"
echo "timeout   : ${TIMEOUT}s  (F17 wall-cap ~$(( TIMEOUT * 12 / 10 ))s)"
echo "k=$K  temps=$TEMPS"
echo "sets      : $SETS"
echo "extra     : $EXTRA_FLAGS"
echo "priors    : $PRIORS"
echo "hintlex   : $HINTLEX"
echo "validator : ${USE_NAME_VALIDATOR:-(off)}"
echo "start_utc : $(date -u +%FT%TZ)"
echo "==========================="

t_sweep_start=$(date +%s)

for stem in $SETS; do
  goal_file="$ROOT/datasets_subset/${stem}.txt"
  if [ ! -f "$goal_file" ]; then
    echo "── skip ${stem}: goal file not found ($goal_file)"
    continue
  fi
  n=$(grep -cE '^[^#]' "$goal_file")
  set_log="$LOG_DIR/${stem}.log"
  echo
  echo "── ${stem} (${n} goals) → $set_log"
  echo "   start $(date +'%F %T')"

  # Snapshot the planner_results dir so we can identify the new CSV after the run.
  csv_dir="$ROOT/solution/datasets/planner_results"
  mkdir -p "$csv_dir"
  t0=$(date +%s)

  (cd "$ROOT/solution" && python -u -m planner.experiments bench \
      --file "$goal_file" \
      --mode auto \
      --diverse --k "$K" --temps "$TEMPS" \
      --strict-no-sorry --verify \
      --timeout "$TIMEOUT" \
      --model "$MODEL" \
      $EXTRA_FLAGS \
      --trace) > "$set_log" 2>&1
  rc=$?
  t1=$(date +%s)
  dt=$(( t1 - t0 ))

  # Find the CSV this run produced (newest *-${stem}-* in planner_results) and copy it
  # into the sweep's out dir with a stable name.
  newest_csv=$(ls -t "$csv_dir"/*"-${stem}-"*.csv 2>/dev/null | head -1)
  if [ -n "$newest_csv" ]; then
    cp "$newest_csv" "$OUT_DIR/${stem}.csv"
    echo "   csv → $OUT_DIR/${stem}.csv (source $(basename "$newest_csv"))"
  else
    echo "   !! no CSV emitted for ${stem}"
  fi

  strict=$(grep -cE 'success=True had_sorry=False verified_ok=True' "$set_log" || true)
  errored=$(grep -cE '❌ planner error' "$set_log" || true)
  echo "   done ${stem}  rc=$rc  strict=${strict}/${n}  errored=${errored}  wall=${dt}s"
done

echo
echo "── aggregating summary"
python - "$ROOT" "$OUT_DIR" <<'PY'
import csv, sys, pathlib, datetime

root, out_dir = map(pathlib.Path, sys.argv[1:3])

def load_csv(p: pathlib.Path):
    out = {}
    with p.open() as f:
        for row in csv.DictReader(f):
            out[row["goal"]] = row
    return out

def ok(row):
    return (
        row is not None
        and row.get("success", "").lower() == "true"
        and row.get("verified_ok", "").lower() == "true"
        and row.get("had_sorry", "").lower() != "true"
    )

sets = []
total_goals = 0
total_strict = 0
md = [
    f"# Report-metric sweep — {datetime.datetime.utcnow():%Y-%m-%d %H:%M UTC}",
    f"",
    f"All numbers are **solution-only**. Baseline can be re-run later if there's time.",
    f"",
    "| Set | Goals | Strict pass | % |",
    "|---|---:|---:|---:|",
]
per_set_tables = []
for csv_path in sorted(out_dir.glob("*.csv")):
    if csv_path.name == "summary.csv":
        continue
    stem = csv_path.stem
    goals_file = root / "datasets_subset" / f"{stem}.txt"
    if not goals_file.exists():
        continue
    goals = [
        ln.strip() for ln in goals_file.read_text().splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    rows = load_csv(csv_path)
    n = len(goals)
    s = sum(1 for g in goals if ok(rows.get(g)))
    pct = (100.0 * s / n) if n else 0.0
    md.append(f"| `{stem}` | {n} | {s} | {pct:.0f}% |")
    total_goals += n
    total_strict += s
    sets.append((stem, n, s, goals, rows))

if total_goals:
    md.append(f"| **total** | **{total_goals}** | **{total_strict}** | **{100.0*total_strict/total_goals:.0f}%** |")
md.append("")

for stem, n, s, goals, rows in sets:
    md.append(f"## `{stem}` — {s}/{n}")
    md.append("| # | Goal | Strict | Wall (s) |")
    md.append("|---:|---|:-:|---:|")
    for i, g in enumerate(goals, 1):
        r = rows.get(g)
        mark = "✓" if ok(r) else "✗"
        wall = r.get("seconds", r.get("elapsed", "")) if r else ""
        md.append(f"| {i} | `{g[:80]}` | {mark} | {wall} |")
    md.append("")

(out_dir / "summary.md").write_text("\n".join(md) + "\n")
with (out_dir / "summary.csv").open("w") as f:
    w = csv.writer(f)
    w.writerow(["set", "goals", "strict"])
    for stem, n, s, *_ in sets:
        w.writerow([stem, n, s])
    w.writerow(["total", total_goals, total_strict])
print(f"summary → {out_dir/'summary.md'}  ({total_strict}/{total_goals} strict total)")
PY

t_sweep_end=$(date +%s)
echo
echo "=== sweep complete ==="
echo "wall      : $(( t_sweep_end - t_sweep_start ))s"
echo "out_dir   : $OUT_DIR"
echo "summary   : $OUT_DIR/summary.md"
echo "end_utc   : $(date -u +%FT%TZ)"
