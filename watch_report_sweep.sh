#!/usr/bin/env bash
# watch_report_sweep.sh — live progress watcher for report_metric_sweep.sh.
# Auto-detects the newest report_metric_sweep_*/ out-dir and shows per-set progress.
# Ctrl-C stops the watcher (NOT the sweep).
#
# Usage:
#   ./watch_report_sweep.sh
# or:
#   source watch_report_sweep.sh && watch_report_sweep

watch_report_sweep() {
  local SCRIPT_DIR
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd -P)"
  cd "$SCRIPT_DIR" || return 1

  local START
  START=$(date +%s)
  local TIMEOUT_S="${TIMEOUT_S:-180}"
  local OVERRUN_FLAG=$((TIMEOUT_S * 6 / 5 + 30))
  # SETS overridable via env (space-separated stems). Default matches the
  # original 4-set sweep; for the 300-goal HOL/Main sweep set:
  #   SETS="hol_main_easy hol_main_mid hol_main_hard"
  # NOTE: capture the env value BEFORE declaring `local SETS`, otherwise the
  # `local` declaration shadows the inherited value with empty.
  local _SETS_ENV="${SETS:-}"
  local SETS
  if [ -n "$_SETS_ENV" ]; then
    # shellcheck disable=SC2206
    SETS=($_SETS_ENV)
  else
    SETS=(hard_25 mid_25 minif2f_30 holmain_50)
  fi

  while true; do
    clear
    local NOW ELAPSED HH MM SS
    NOW=$(date +%s)
    ELAPSED=$((NOW - START))
    HH=$((ELAPSED/3600))
    MM=$(((ELAPSED%3600)/60))
    SS=$((ELAPSED%60))
    printf '=== report-sweep watcher  %s  (watching for: %02d:%02d:%02d) ===\n\n' \
      "$(date +'%F %T')" $HH $MM $SS

    if pgrep -af 'report_metric_sweep.sh|planner.experiments bench' >/dev/null; then
      echo "STATUS: running"
      pgrep -af 'planner.experiments bench' | sed 's/^/  /'
    else
      echo "STATUS: NOT running (finished or crashed)"
    fi
    echo

    if curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
      echo "OLLAMA: reachable"
    else
      echo "OLLAMA: NOT REACHABLE"
    fi
    echo

    local OUT
    OUT=$(ls -dt report_metric_sweep_*/ 2>/dev/null | head -1)
    if [ -z "$OUT" ]; then
      echo "(out-dir not created yet)"
      sleep 20
      continue
    fi
    OUT=${OUT%/}
    echo "OUT_DIR: $OUT"
    echo

    echo "--- per-set progress ---"
    local active=""
    local stem L n ATT DONE STRICT SORRY ERR TAG
    for stem in "${SETS[@]}"; do
      L="$OUT/_logs/${stem}.log"
      if [ ! -f "$L" ]; then
        printf '  %-12s (not started)\n' "$stem"
        continue
      fi
      n=$(grep -cE '^[^#]' "datasets_subset/${stem}.txt" 2>/dev/null || echo 0)
      ATT=$(grep -cE '\[[0-9]+/' "$L" 2>/dev/null || echo 0)
      DONE=$(grep -cE 'done in .*success=' "$L" 2>/dev/null || echo 0)
      STRICT=$(grep -cE 'success=True had_sorry=False verified_ok=True' "$L" 2>/dev/null || echo 0)
      SORRY=$(grep -cE 'success=False had_sorry=True' "$L" 2>/dev/null || echo 0)
      ERR=$(grep -cE 'planner error' "$L" 2>/dev/null || echo 0)
      TAG=""
      if [ "$DONE" -lt "$n" ]; then
        TAG=" <- active"
        active="$stem"
      fi
      printf '  %-12s attempted=%-3s done=%-3s/%-3s strict=%-3s sorry=%-3s err=%-3s%s\n' \
        "$stem" "$ATT" "$DONE" "$n" "$STRICT" "$SORRY" "$ERR" "$TAG"
    done
    echo

    if [ -n "$active" ]; then
      L="$OUT/_logs/${active}.log"
      local MT GAP GH GM GS
      MT=$(stat -c %Y "$L")
      GAP=$((NOW - MT))
      GH=$((GAP/3600))
      GM=$(((GAP%3600)/60))
      GS=$((GAP%60))
      printf 'active log mtime gap: %02d:%02d:%02d  (>3min on 7b = likely stuck)\n' $GH $GM $GS
      echo
      echo "--- current goal (${active}) ---"
      grep -E '\[[0-9]+/' "$L" | tail -1 | sed 's/^/  /'
      echo
      echo "--- F11 fast-path (${active}) ---"
      local A B M
      A=$(grep -c 'F11 stage-A solved' "$L" 2>/dev/null || echo 0)
      B=$(grep -c 'F11 stage-B solved with prover' "$L" 2>/dev/null || echo 0)
      M=$(grep -cE 'F11 stage-B: prover returned success=False|F11 direct-prover crashed' "$L" 2>/dev/null || echo 0)
      printf '  stage-A=%-3s  stage-B=%-3s  stage-B-miss=%-3s\n' "$A" "$B" "$M"
      echo

      echo "--- F29 retry + bail (${active}) ---"
      local F29A_WIN F29B_BAIL
      F29A_WIN=$(grep -c 'F29a type-annotated' "$L" 2>/dev/null || echo 0)
      F29B_BAIL=$(grep -c 'F29b early-bail' "$L" 2>/dev/null || echo 0)
      printf '  F29a type-annot wins=%-3s  F29b early-bails=%-3s\n' "$F29A_WIN" "$F29B_BAIL"
      echo
    fi

    echo "--- overruns >${OVERRUN_FLAG}s ---"
    local HITS=0
    local line T
    for stem in "${SETS[@]}"; do
      L="$OUT/_logs/${stem}.log"
      [ -f "$L" ] || continue
      while IFS= read -r line; do
        T=$(echo "$line" | sed -nE 's/.*done in ([0-9.]+)s.*/\1/p')
        if [ -n "$T" ] && [ "${T%.*}" -gt "$OVERRUN_FLAG" ]; then
          echo "  [$stem] $line"
          HITS=$((HITS+1))
        fi
      done < <(grep -E 'done in .*success=' "$L")
    done
    [ "$HITS" = "0" ] && echo "  (none)"
    echo

    echo "--- recent errors / tracebacks ---"
    for stem in "${SETS[@]}"; do
      L="$OUT/_logs/${stem}.log"
      [ -f "$L" ] || continue
      grep -E 'Traceback|requests.exceptions|TimeoutError|planner error' "$L" 2>/dev/null \
        | tail -2 | sed "s/^/  [$stem] /"
    done
    echo

    if [ -f "$OUT/summary.md" ] && ! pgrep -af 'report_metric_sweep.sh' >/dev/null; then
      echo "=== SWEEP COMPLETE - final summary ==="
      cat "$OUT/summary.md"
      printf '\a'
      break
    fi
    sleep 30
  done
}

# If sourced, just define the function. If executed, run it.
if [ "${BASH_SOURCE[0]:-$0}" = "$0" ]; then
  watch_report_sweep
fi
