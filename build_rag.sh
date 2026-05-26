#!/usr/bin/env bash
# build_rag.sh — Build the micro-RAG hint lexicon + priors for the planner.
#
# Usage:
#   ./build_rag.sh holstdlib                # extract from Isabelle's bundled HOL/
#   ./build_rag.sh afp /path/to/afp/thys    # extract from a local AFP checkout
#   ./build_rag.sh combined /path/to/afp/thys
#                                           # extract from BOTH HOL/ and AFP, merge
#
# Output (in solution/datasets/):
#   isar_pairs_<source>.jsonl  — raw (goal, outline, theory, ...) records
#   isar_priors.json           — aggregated pattern/lemma priors
#   isar_hintlex.json          — token -> recommended-lemma map for --hintlex
#
# After running, point the planner at:
#   --priors solution/datasets/isar_priors.json
#   --hintlex solution/datasets/isar_hintlex.json
#   --context-hints
set -eu
cd "$(dirname "$0")"
ROOT="$(pwd -P)"
source solution/.venv/bin/activate

MODE="${1:-holstdlib}"
AFP_DIR="${2:-}"
OUT_DIR="$ROOT/solution/datasets"
mkdir -p "$OUT_DIR"

# Resolve Isabelle's bundled HOL directory.
ISA_HOL="$(isabelle env 2>/dev/null | sed -nE 's/^ISABELLE_HOME=(.+)$/\1/p')/src/HOL"
[ -d "$ISA_HOL" ] || { echo "FATAL: Isabelle HOL directory not found at $ISA_HOL" >&2; exit 2; }
echo "Isabelle HOL: $ISA_HOL"

extract_from() {
  local src="$1"
  local out_jsonl="$2"
  # Truncate the output file before mining so reruns don't accumulate stale records.
  : > "$out_jsonl"
  echo "── mining $src → $out_jsonl"
  ( cd "$ROOT/solution" && python - "$src" "$out_jsonl" <<'PY'
import sys
from planner.extract import mine_afp_corpus_rich
src_dir, out_jsonl = sys.argv[1], sys.argv[2]
mine_afp_corpus_rich(src_dir=src_dir, out_jsonl=out_jsonl)
PY
)
  local n
  n=$(wc -l < "$out_jsonl")
  echo "  ${n} records"
}

case "$MODE" in
  holstdlib)
    extract_from "$ISA_HOL" "$OUT_DIR/isar_pairs_holstdlib.jsonl"
    INPUTS=("$OUT_DIR/isar_pairs_holstdlib.jsonl")
    ;;
  afp)
    [ -d "$AFP_DIR" ] || { echo "FATAL: AFP directory not found at $AFP_DIR" >&2; exit 2; }
    extract_from "$AFP_DIR" "$OUT_DIR/isar_pairs_afp.jsonl"
    INPUTS=("$OUT_DIR/isar_pairs_afp.jsonl")
    ;;
  combined)
    [ -d "$AFP_DIR" ] || { echo "FATAL: AFP directory not found at $AFP_DIR" >&2; exit 2; }
    extract_from "$ISA_HOL" "$OUT_DIR/isar_pairs_holstdlib.jsonl"
    extract_from "$AFP_DIR" "$OUT_DIR/isar_pairs_afp.jsonl"
    cat "$OUT_DIR/isar_pairs_holstdlib.jsonl" "$OUT_DIR/isar_pairs_afp.jsonl" > "$OUT_DIR/isar_pairs_combined.jsonl"
    echo "  combined: $(wc -l < "$OUT_DIR/isar_pairs_combined.jsonl") records"
    INPUTS=("$OUT_DIR/isar_pairs_combined.jsonl")
    ;;
  *)
    echo "Usage: $0 {holstdlib | afp <afp-thys-dir> | combined <afp-thys-dir>}" >&2
    exit 1
    ;;
esac

echo ""
echo "── aggregating priors + hintlex"
( cd "$ROOT/solution" && python -m planner.priors \
    --input "${INPUTS[@]}" \
    --priors "$OUT_DIR/isar_priors.json" \
    --hintlex "$OUT_DIR/isar_hintlex.json" \
    --min-count 3 --topk 8 )

echo ""
echo "── outputs ──"
ls -la "$OUT_DIR/isar_priors.json" "$OUT_DIR/isar_hintlex.json"
echo ""
echo "Priors summary:"
python3 -c "
import json
p = json.load(open('$OUT_DIR/isar_priors.json'))
h = json.load(open('$OUT_DIR/isar_hintlex.json'))
print(f'  priors:    {len(p) if isinstance(p, list) else len(p.get(\"rules\", []))} rules')
print(f'  hintlex:   {len(h)} tokens mapped to lemma sets')
# Show a sample
if isinstance(h, dict):
    sample = list(h.items())[:5]
    print('  sample tokens:', ', '.join(f'{t}->{len(v)}' for t, v in sample))
"
echo ""
echo "To use in a sweep, add to EXTRA_FLAGS:"
echo "  --priors solution/datasets/isar_priors.json --hintlex solution/datasets/isar_hintlex.json"
echo "(note: --context-hints is already on, --hintlex/--priors add the RAG layer)"
