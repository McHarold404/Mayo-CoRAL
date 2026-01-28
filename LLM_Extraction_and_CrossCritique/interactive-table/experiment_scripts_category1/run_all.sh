#!/bin/bash
set -euo pipefail

# ============================================================
# run_all.sh
# - Runs selected pipelines (1..4) over selected models & limits
# - Resolves HF repo IDs to *shared cache snapshot paths*
# - Supports shared cache layouts:
#     A) /mnt/shared/shared_hf_home/hub/models--ORG--NAME/snapshots/<hash>  (your working layout)
#     B) /mnt/shared/shared_hf_home/models--ORG--NAME/snapshots/<hash>
# - Forces offline mode to prevent downloads/locks
# - Optional: set CUDA_VISIBLE_DEVICES to control GPUs
# ============================================================

# ---------------------------
# Shared HF cache root (IMPORTANT: NOT /hub)
# ---------------------------
SHARED_HF_HOME="/mnt/shared/shared_hf_home"

# Force HF tooling to use shared cache + offline
export HF_HOME="$SHARED_HF_HOME"
export HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_ENABLE_HF_TRANSFER=0
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONNOUSERSITE=1

CUDA_VISIBLE_DEVICES_DEFAULT="${CUDA_VISIBLE_DEVICES:-}"

usage() {
cat <<EOF
Usage: $0 [-p pipelines] [-m models] [-l limits] [-g gpus]

  -p  Comma-separated list of pipelines to run. Default: 1,2,3,4
      1 = base_prompt.py
      2 = split_function.py
      3 = split_verify.py
      4 = self_consistency.py

  -m  Comma-separated list of HF models to use (repo ids OR local snapshot paths).
      Default:
        meta-llama/Meta-Llama-3.1-8B-Instruct,
        Qwen/Qwen2.5-7B-Instruct,
        mistralai/Mistral-7B-Instruct-v0.2

  -l  Comma-separated list of limits to pass to --limit. Default: -1
  -g  Comma-separated CUDA_VISIBLE_DEVICES (e.g., "4,5,6,7"). Default: leave as-is.

Example:
  $0 -p 1 -m "meta-llama/Llama-3.1-8B" -l 1 -g 5
EOF
}

DEFAULT_MODELS=(
  "meta-llama/Meta-Llama-3.1-8B-Instruct"
  "Qwen/Qwen2.5-7B-Instruct"
  "mistralai/Mistral-7B-Instruct-v0.2"
)
DEFAULT_LIMITS=(-1)
DEFAULT_PIPELINES=("1" "2" "3" "4")

MODELS=("${DEFAULT_MODELS[@]}")
LIMITS=("${DEFAULT_LIMITS[@]}")
PIPELINES=("${DEFAULT_PIPELINES[@]}")

hf_cache_dirname() {
  local repo="$1"
  local org="${repo%%/*}"
  local name="${repo#*/}"
  echo "models--${org}--${name}"
}

# Check whether snapshot dir has usable weights (files or symlinks that resolve)
snapshot_has_weights() {
  local snapdir="$1"

  # direct files
  if find "$snapdir" -maxdepth 1 -type f \( -name "*.safetensors" -o -name "*.bin" -o -name "*.index.json" \) | grep -q .; then
    return 0
  fi

  # symlinks that resolve to real files
  while IFS= read -r -d '' lnk; do
    local tgt
    tgt="$(readlink -f "$lnk" 2>/dev/null || true)"
    if [[ -n "$tgt" && -f "$tgt" ]]; then
      return 0
    fi
  done < <(find "$snapdir" -maxdepth 1 -type l \( -name "*.safetensors" -o -name "*.bin" -o -name "*.index.json" \) -print0)

  return 1
}

resolve_model_path() {
  local model="$1"

  # If user already passed a path
  if [[ -d "$model" ]]; then
    echo "$model"
    return 0
  fi

  local cache_name
  cache_name="$(hf_cache_dirname "$model")"

  # Try BOTH layouts: hub first (your real one), then non-hub
  local roots=(
    "${SHARED_HF_HOME}/hub/${cache_name}"
    "${SHARED_HF_HOME}/${cache_name}"
  )

  local snapshots=""
  for r in "${roots[@]}"; do
    if [[ -d "$r/snapshots" ]]; then
      snapshots="$r/snapshots"
      break
    fi
  done

  if [[ -z "$snapshots" ]]; then
    echo "ERROR: Could not find snapshots dir for '$model' in shared cache." >&2
    for r in "${roots[@]}"; do echo "  tried: $r/snapshots" >&2; done
    return 1
  fi

  # Choose newest snapshot that ACTUALLY has weights
  local snapdir=""
  while IFS= read -r snap; do
    [[ -z "$snap" ]] && continue
    local candidate="${snapshots}/${snap}"
    if [[ -d "$candidate" ]] && snapshot_has_weights "$candidate"; then
      snapdir="$candidate"
      break
    fi
  done < <(ls -1t "$snapshots" 2>/dev/null || true)

  if [[ -z "$snapdir" ]]; then
    echo "ERROR: Found snapshots dir but none have usable weights: $snapshots" >&2
    echo "Tip: the snapshot may contain only config/tokenizer links but missing blobs." >&2
    return 1
  fi

  # must have config
  if [[ ! -e "${snapdir}/config.json" && ! -e "${snapdir}/params.json" ]]; then
    echo "ERROR: No config.json/params.json in ${snapdir}" >&2
    return 1
  fi

  echo "$snapdir"
  return 0
}

while getopts ":p:m:l:g:h" opt; do
  case "$opt" in
    p) IFS=',' read -r -a PIPELINES <<< "$OPTARG" ;;
    m) IFS=',' read -r -a MODELS <<< "$OPTARG" ;;
    l) IFS=',' read -r -a LIMITS <<< "$OPTARG" ;;
    g) export CUDA_VISIBLE_DEVICES="$OPTARG" ;;
    h) usage; exit 0 ;;
    \?) echo "Unknown option: -$OPTARG" >&2; usage; exit 1 ;;
    :)  echo "Option -$OPTARG requires an argument." >&2; usage; exit 1 ;;
  esac
done

echo "============================================="
echo " Selected pipelines      : ${PIPELINES[*]}"
echo " Models                  : ${MODELS[*]}"
echo " Limits                  : ${LIMITS[*]}"
echo " Shared HF_HOME          : ${HF_HOME}"
echo " HF_HUB_OFFLINE          : ${HF_HUB_OFFLINE}"
echo " TRANSFORMERS_OFFLINE    : ${TRANSFORMERS_OFFLINE}"
echo " CUDA_VISIBLE_DEVICES    : ${CUDA_VISIBLE_DEVICES:-$CUDA_VISIBLE_DEVICES_DEFAULT}"
echo "============================================="

pipeline_enabled() {
  local needle="$1"
  for p in "${PIPELINES[@]}"; do
    if [[ "$p" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
}

run_pipeline() {
  local pipe_num="$1"
  local script="$2"

  echo "================ PIPELINE ${pipe_num} (${script}) - GENERATION ================"

  for model in "${MODELS[@]}"; do
    local model_path
    model_path="$(resolve_model_path "$model")"

    echo "========================================================"
    echo "🚀 [Pipeline ${pipe_num}] STARTING BATCH FOR MODEL: $model"
    echo "   -> Using shared snapshot: $model_path"
    echo "========================================================"

    for limit in "${LIMITS[@]}"; do
      echo "   ... [Pipeline ${pipe_num}] Running limit: $limit"

      MODEL_ID_FOR_NAMING="$model" \
      python "$script" --mode run --model "$model_path" --limit "$limit"

      echo "   ---------------------------------------"
      sleep 2
    done
  done

  echo "================ PIPELINE ${pipe_num} (${script}) - EVAL ================"

  for model in "${MODELS[@]}"; do
    local model_path
    model_path="$(resolve_model_path "$model")"

    echo "========================================================"
    echo "📊 [Pipeline ${pipe_num}] EVALUATING MODEL: $model"
    echo "   -> Using shared snapshot: $model_path"
    echo "========================================================"

    MODEL_ID_FOR_NAMING="$model" \
    python "$script" --mode eval --model "$model_path"

    echo "--------------------------------------------------------"
  done
}

if pipeline_enabled "1"; then run_pipeline "1" "base_prompt.py"; fi
if pipeline_enabled "2"; then run_pipeline "2" "split_function.py"; fi
if pipeline_enabled "3"; then run_pipeline "3" "split_verify.py"; fi
if pipeline_enabled "4"; then run_pipeline "4" "self_consistency.py"; fi

echo "🎉 SELECTED PIPELINES COMPLETED."
