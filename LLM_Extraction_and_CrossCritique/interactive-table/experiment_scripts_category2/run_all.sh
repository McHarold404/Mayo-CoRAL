#!/usr/bin/env bash
# run_all.sh
#
# Run one-or-more CAT2 SQL eval scripts end-to-end across ALL questions (no --limit),
# with consistent config, resume support (via --run-id), per-run logs,
# and multiple models defined as a hardcoded bash array.
#
# GPU selection:
#   - Default GPU is 3
#   - Override with env: GPU=7 ./run_all.sh
#   - Or pass positional arg: ./run_all.sh 7
#
# Models:
#   MODELS entries are "load|name"
#     load: HF repo id OR local snapshot path
#     name: friendly/original name used for reporting + folder naming

set -euo pipefail

# -----------------------------
# Config (hardcode here)
# -----------------------------
SCRIPTS="cat2_simple_sql.py"
RESULTS_ROOT="results"
XLSX=""

# ---- MODELS ARRAY (EDIT THIS) ----
MODELS=(
  "/mnt/shared/shared_hf_home/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28|Qwen2.5-7B-Instruct"
  "/mnt/shared/shared_hf_home/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/0e9e39f249a16976918f6564b8830bc894c89659|Llama-3.1-8B-Instruct"
  "/mnt/shared/shared_hf_home/hub/models--mistralai--Mistral-7B-Instruct-v0.3/snapshots/0d4b76e1efeb5eb6f6b5e757c79870472e04bd3a|Mistral-7B-Instruct-v0.3"
  "/mnt/shared/shared_hf_home/hub/models--meta-llama--Llama-3.2-1B/snapshots/4e20de362430cd3b72f300e6b0f18e50e7166e08|Llama-3.2-1B"
  "/mnt/shared/shared_hf_home/hub/models--Orenguteng--Llama-3-8B-Lexi-Uncensored/snapshots/ff95e3bfcd6142759ce82099b58bc7a789ac241b|Lexi-Uncensored-8B"
)

TP="1"
GPU_MEM_UTIL="0.80"
MAX_MODEL_LEN="8192"
DTYPE="bfloat16"
TEMPERATURE="0.1"
MAX_TOKENS="600"

RELAXED_EM_THRESHOLD="0.70"
NUM_RUNS="1"
RUN_SQL="0"

# Default GPU (can override via env or positional arg)
GPU_DEFAULT="3"
GPU="${GPU:-$GPU_DEFAULT}"

RUN_ID_PREFIX="cat2_all"
LOG_DIR="logs"
EXTRA_ARGS=""

# -----------------------------
# GPU override from positional arg
# -----------------------------
if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
  GPU="$1"
  shift
fi

# Anything else passed becomes EXTRA_ARGS forwarded to the python script(s)
if [[ "$#" -gt 0 ]]; then
  EXTRA_ARGS="$*"
fi


# -----------------------------
# Helpers
# -----------------------------
ts_now() { date +"%Y%m%d_%H%M%S"; }

slugify() { echo "$1" | sed 's#/#_#g' | sed 's/[^A-Za-z0-9_.-]/_/g'; }

have_flag() {
  local script="$1"
  local flag="$2"
  python "$script" --help 2>/dev/null | grep -q -- "$flag"
}

split_model_pair() {
  local pair="$1"
  pair="$(echo "$pair" | sed 's/[;,]/|/g')"
  local load name
  if [[ "$pair" == *"|"* ]]; then
    load="${pair%%|*}"
    name="${pair#*|}"
  else
    load="$pair"
    name="$pair"
  fi
  load="$(echo "$load" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
  name="$(echo "$name" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
  [[ -z "$name" ]] && name="$load"
  printf "%s\n%s\n" "$load" "$name"
}

build_args_for_script() {
  local script="$1"
  local model_load="$2"
  local model_name="$3"
  local args=()

  if have_flag "$script" "--model"; then args+=("--model" "$model_load"); fi
  if have_flag "$script" "--model-name"; then args+=("--model-name" "$model_name"); fi
  if [[ -n "$XLSX" ]] && have_flag "$script" "--xlsx"; then args+=("--xlsx" "$XLSX"); fi
  if have_flag "$script" "--tp"; then args+=("--tp" "$TP"); fi
  if have_flag "$script" "--gpu-mem-util"; then args+=("--gpu-mem-util" "$GPU_MEM_UTIL"); fi
  if have_flag "$script" "--max-model-len"; then args+=("--max-model-len" "$MAX_MODEL_LEN"); fi
  if have_flag "$script" "--dtype"; then args+=("--dtype" "$DTYPE"); fi
  if have_flag "$script" "--temperature"; then args+=("--temperature" "$TEMPERATURE"); fi
  if have_flag "$script" "--max-tokens"; then args+=("--max-tokens" "$MAX_TOKENS"); fi
  if have_flag "$script" "--results-root"; then args+=("--results-root" "$RESULTS_ROOT"); fi
  if have_flag "$script" "--relaxed-em-threshold"; then args+=("--relaxed-em-threshold" "$RELAXED_EM_THRESHOLD"); fi
  if have_flag "$script" "--num-runs"; then args+=("--num-runs" "$NUM_RUNS"); fi

  if [[ "$RUN_SQL" == "1" ]] && have_flag "$script" "--run-sql"; then
    args+=("--run-sql")
  fi

  # No --limit => run all questions

  local base
  base="$(basename "$script")"
  base="${base%.py}"
  local run_id="${RUN_ID_PREFIX}__${base}__$(ts_now)__$(slugify "$model_name")"

  if have_flag "$script" "--run-id"; then
    args+=("--run-id" "$run_id")
  fi

  if [[ -n "${EXTRA_ARGS// }" ]]; then
    # shellcheck disable=SC2206
    args+=($EXTRA_ARGS)
  fi

  printf "%s\0" "${args[@]}"
}

# -----------------------------
# Main
# -----------------------------
mkdir -p "$LOG_DIR"
export CUDA_VISIBLE_DEVICES="$GPU"

echo "========================================"
echo "RUN ALL - CAT2 (hardcoded models array)"
echo "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"
echo "SCRIPTS=$SCRIPTS"
echo "RESULTS_ROOT=$RESULTS_ROOT"
echo "RUN_SQL=$RUN_SQL"
echo "TP=$TP GPU_MEM_UTIL=$GPU_MEM_UTIL MAX_MODEL_LEN=$MAX_MODEL_LEN DTYPE=$DTYPE"
echo "TEMPERATURE=$TEMPERATURE MAX_TOKENS=$MAX_TOKENS"
echo "RELAXED_EM_THRESHOLD=$RELAXED_EM_THRESHOLD NUM_RUNS=$NUM_RUNS"
echo "LOG_DIR=$LOG_DIR"
echo "Models to run: ${#MODELS[@]}"
for i in "${!MODELS[@]}"; do
  readarray -t parts < <(split_model_pair "${MODELS[$i]}")
  echo "  [$i] load=${parts[0]}  name=${parts[1]}"
done
echo "========================================"

for script in $SCRIPTS; do
  if [[ ! -f "$script" ]]; then
    echo "[ERROR] Script not found: $script"
    exit 1
  fi

  for pair in "${MODELS[@]}"; do
    readarray -t parts < <(split_model_pair "$pair")
    model_load="${parts[0]}"
    model_name="${parts[1]}"

    base="$(basename "$script")"
    log_path="$LOG_DIR/${base%.py}__$(slugify "$model_name")__$(ts_now).log"

    echo ""
    echo "----------------------------------------"
    echo "[RUN] $script"
    echo "      model_load=$model_load"
    echo "      model_name=$model_name"
    echo "[GPU]  CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"
    echo "[LOG] $log_path"
    echo "----------------------------------------"

    mapfile -d '' -t ARGS < <(build_args_for_script "$script" "$model_load" "$model_name")

    echo "[CMD] python $script ${ARGS[*]}"
    python "$script" "${ARGS[@]}" 2>&1 | tee "$log_path"

    echo "[DONE] $script :: $model_name"
  done
done

echo ""
echo "========================================"
echo "ALL DONE"
echo "Results under: $RESULTS_ROOT/"
echo "Logs under: $LOG_DIR/"
echo "========================================"
