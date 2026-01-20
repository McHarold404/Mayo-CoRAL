# #!/bin/bash

# # Make sure user site-packages don't interfere
# export PYTHONNOUSERSITE=1

# # ---------------------------
# # Shared model list & limits
# # ---------------------------
# models=(
#     "meta-llama/Meta-Llama-3.1-8B-Instruct"
#     "Qwen/Qwen2.5-7B-Instruct"
#     "mistralai/Mistral-7B-Instruct-v0.2"
# )

# # 1 = Test single, 10 = Small batch, 100 = Medium batch, -1 = ALL rows
# limits=(-1)

# # # ===========================
# # # PIPELINE 1: base_prompt.py
# # # ===========================

# # echo "================ PIPELINE 1 (base_prompt.py) - GENERATION ================"

# # for model in "${models[@]}"; do
# #     echo "========================================================"
# #     echo "🚀 [Pipeline 1] STARTING BATCH FOR MODEL: $model"
# #     echo "========================================================"
    
# #     for limit in "${limits[@]}"; do
# #         echo "   ... [Pipeline 1] Running limit: $limit"
        
# #         python base_prompt.py --mode run --model "$model" --limit "$limit"
# #         status=$?
        
# #         if [ $status -eq 0 ]; then
# #             echo "   ✅ [Pipeline 1] Success for limit $limit"
# #         else
# #             echo "   ❌ [Pipeline 1] FAILED for limit $limit (model: $model)"
# #             # Uncomment to abort everything on failure:
# #             # exit 1
# #         fi
        
# #         echo "   ---------------------------------------"
# #         sleep 15
# #     done
# # done

# # echo "================ PIPELINE 1 (base_prompt.py) - EVAL ================"

# # for model in "${models[@]}"; do
# #     echo "========================================================"
# #     echo "📊 [Pipeline 1] EVALUATING MODEL: $model"
# #     echo "========================================================"
    
# #     python base_prompt.py --mode eval --model "$model"
    
# #     echo "--------------------------------------------------------"
# # done


# # # ===========================
# # # PIPELINE 2: split_function.py
# # # ===========================

# # echo "================ PIPELINE 2 (split_function.py) - GENERATION ================"

# # for model in "${models[@]}"; do
# #     echo "========================================================"
# #     echo "🚀 [Pipeline 2] STARTING BATCH FOR MODEL: $model"
# #     echo "========================================================"
    
# #     for limit in "${limits[@]}"; do
# #         echo "   ... [Pipeline 2] Running limit: $limit"
        
# #         python split_function.py --mode run --model "$model" --limit "$limit"
# #         status=$?
        
# #         if [ $status -eq 0 ]; then
# #             echo "   ✅ [Pipeline 2] Success for limit $limit"
# #         else
# #             echo "   ❌ [Pipeline 2] FAILED for limit $limit (model: $model)"
# #             # Uncomment to abort everything on failure:
# #             # exit 1
# #         fi
        
# #         echo "   ---------------------------------------"
# #         sleep 15
# #     done
# # done

# # echo "================ PIPELINE 2 (split_function.py) - EVAL ================"

# # for model in "${models[@]}"; do
# #     echo "========================================================"
# #     echo "📊 [Pipeline 2] EVALUATING MODEL: $model"
# #     echo "========================================================"
    
# #     python split_function.py --mode eval --model "$model"
    
# #     echo "--------------------------------------------------------"
# # done

# # echo "🎉 ALL PIPELINES (base_prompt + split_function) COMPLETED."



# echo "================ PIPELINE 3 (split_verify.py) - GENERATION ================"

# for model in "${models[@]}"; do
#     echo "========================================================"
#     echo "🚀 [Pipeline 3] STARTING BATCH FOR MODEL: $model"
#     echo "========================================================"
    
#     for limit in "${limits[@]}"; do
#         echo "   ... [Pipeline 3] Running limit: $limit"
        
#         python split_verify.py --mode run --model "$model" --limit "$limit"
#         status=$?
        
#         if [ $status -eq 0 ]; then
#             echo "   ✅ [Pipeline 3] Success for limit $limit"
#         else
#             echo "   ❌ [Pipeline 3] FAILED for limit $limit (model: $model)"
#             # Uncomment to abort everything on failure:
#             # exit 1
#         fi
        
#         echo "   ---------------------------------------"
#         sleep 15
#     done
# done

# echo "================ PIPELINE 3 (split_verify.py) - EVAL ================"

# for model in "${models[@]}"; do
#     echo "========================================================"
#     echo "📊 [Pipeline 3] EVALUATING MODEL: $model"
#     echo "========================================================"
    
#     python split_verify.py --mode eval --model "$model"
    
#     echo "--------------------------------------------------------"
# done

# echo "🎉 ALL PIPELINES (base_prompt + split_function + split_verify) COMPLETED."


#!/bin/bash

set -euo pipefail

# ---------------------------
# Help / usage
# ---------------------------
usage() {
    cat <<EOF
Usage: $0 [-p pipelines] [-m models] [-l limits]

  -p  Comma-separated list of pipelines to run.
      Pipelines:
        1 = base_prompt.py
        2 = split_function.py
        3 = split_verify.py
        4 = self_consistency.py
      Default: 1,2,3,4

  -m  Comma-separated list of HF models to use.
      Default:
        meta-llama/Meta-Llama-3.1-8B-Instruct,
        Qwen/Qwen2.5-7B-Instruct,
        mistralai/Mistral-7B-Instruct-v0.2

  -l  Comma-separated list of limits to pass to --limit.
      Default: -1

Examples:
  # Run all pipelines with defaults
  $0

  # Run only pipeline 3
  $0 -p 3

  # Run pipelines 3 and 4 with limit 100
  $0 -p 3,4 -l 100

  # Run pipeline 4 only on a single model
  $0 -p 4 -m "meta-llama/Meta-Llama-3.1-8B-Instruct"
EOF
}

# ---------------------------
# Defaults
# ---------------------------

export PYTHONNOUSERSITE=1

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

# ---------------------------
# Parse CLI options
# ---------------------------

while getopts ":p:m:l:h" opt; do
    case "$opt" in
        p)
            IFS=',' read -r -a PIPELINES <<< "$OPTARG"
            ;;
        m)
            IFS=',' read -r -a MODELS <<< "$OPTARG"
            ;;
        l)
            IFS=',' read -r -a LIMITS <<< "$OPTARG"
            ;;
        h)
            usage
            exit 0
            ;;
        \?)
            echo "Unknown option: -$OPTARG" >&2
            usage
            exit 1
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            usage
            exit 1
            ;;
    esac
done

echo "============================================="
echo " Selected pipelines : ${PIPELINES[*]}"
echo " Models             : ${MODELS[*]}"
echo " Limits             : ${LIMITS[*]}"
echo "============================================="

# Helper: check if a value is in PIPELINES array
pipeline_enabled() {
    local needle="$1"
    for p in "${PIPELINES[@]}"; do
        if [[ "$p" == "$needle" ]]; then
            return 0
        fi
    done
    return 1
}

# ===========================
# PIPELINE 1: base_prompt.py
# ===========================
if pipeline_enabled "1"; then
    echo "================ PIPELINE 1 (base_prompt.py) - GENERATION ================"

    for model in "${MODELS[@]}"; do
        echo "========================================================"
        echo "🚀 [Pipeline 1] STARTING BATCH FOR MODEL: $model"
        echo "========================================================"
        
        for limit in "${LIMITS[@]}"; do
            echo "   ... [Pipeline 1] Running limit: $limit"
            
            python base_prompt.py --mode run --model "$model" --limit "$limit"
            status=$?
            
            if [ $status -eq 0 ]; then
                echo "   ✅ [Pipeline 1] Success for limit $limit"
            else
                echo "   ❌ [Pipeline 1] FAILED for limit $limit (model: $model)"
                # Uncomment to abort everything on failure:
                # exit 1
            fi
            
            echo "   ---------------------------------------"
            sleep 15
        done
    done

    echo "================ PIPELINE 1 (base_prompt.py) - EVAL ================"

    for model in "${MODELS[@]}"; do
        echo "========================================================"
        echo "📊 [Pipeline 1] EVALUATING MODEL: $model"
        echo "========================================================"
        
        python base_prompt.py --mode eval --model "$model"
        
        echo "--------------------------------------------------------"
    done
fi

# ===========================
# PIPELINE 2: split_function.py
# ===========================
if pipeline_enabled "2"; then
    echo "================ PIPELINE 2 (split_function.py) - GENERATION ================"

    for model in "${MODELS[@]}"; do
        echo "========================================================"
        echo "🚀 [Pipeline 2] STARTING BATCH FOR MODEL: $model"
        echo "========================================================"
        
        for limit in "${LIMITS[@]}"; do
            echo "   ... [Pipeline 2] Running limit: $limit"
            
            python split_function.py --mode run --model "$model" --limit "$limit"
            status=$?
            
            if [ $status -eq 0 ]; then
                echo "   ✅ [Pipeline 2] Success for limit $limit"
            else
                echo "   ❌ [Pipeline 2] FAILED for limit $limit (model: $model)"
                # Uncomment to abort everything on failure:
                # exit 1
            fi
            
            echo "   ---------------------------------------"
            sleep 15
        done
    done

    echo "================ PIPELINE 2 (split_function.py) - EVAL ================"

    for model in "${MODELS[@]}"; do
        echo "========================================================"
        echo "📊 [Pipeline 2] EVALUATING MODEL: $model"
        echo "========================================================"
        
        python split_function.py --mode eval --model "$model"
        
        echo "--------------------------------------------------------"
    done
fi

# ===========================
# PIPELINE 3: split_verify.py
# ===========================
if pipeline_enabled "3"; then
    echo "================ PIPELINE 3 (split_verify.py) - GENERATION ================"

    for model in "${MODELS[@]}"; do
        echo "========================================================"
        echo "🚀 [Pipeline 3] STARTING BATCH FOR MODEL: $model"
        echo "========================================================"
        
        for limit in "${LIMITS[@]}"; do
            echo "   ... [Pipeline 3] Running limit: $limit"
            
            python split_verify.py --mode run --model "$model" --limit "$limit"
            status=$?
            
            if [ $status -eq 0 ]; then
                echo "   ✅ [Pipeline 3] Success for limit $limit"
            else
                echo "   ❌ [Pipeline 3] FAILED for limit $limit (model: $model)"
                # Uncomment to abort everything on failure:
                # exit 1
            fi
            
            echo "   ---------------------------------------"
            sleep 15
        done
    done

    echo "================ PIPELINE 3 (split_verify.py) - EVAL ================"

    for model in "${MODELS[@]}"; do
        echo "========================================================"
        echo "📊 [Pipeline 3] EVALUATING MODEL: $model"
        echo "========================================================"
        
        python split_verify.py --mode eval --model "$model"
        
        echo "--------------------------------------------------------"
    done
fi

# ===========================
# PIPELINE 4: self_consistency.py
# ===========================
if pipeline_enabled "4"; then
    echo "================ PIPELINE 4 (self_consistency.py) - GENERATION ================"

    for model in "${MODELS[@]}"; do
        echo "========================================================"
        echo "🚀 [Pipeline 4] STARTING BATCH FOR MODEL: $model"
        echo "========================================================"
        
        for limit in "${LIMITS[@]}"; do
            echo "   ... [Pipeline 4] Running limit: $limit"
            
            python self_consistency.py --mode run --model "$model" --limit "$limit"
            status=$?
            
            if [ $status -eq 0 ]; then
                echo "   ✅ [Pipeline 4] Success for limit $limit"
            else
                echo "   ❌ [Pipeline 4] FAILED for limit $limit (model: $model)"
                # Uncomment to abort everything on failure:
                # exit 1
            fi
            
            echo "   ---------------------------------------"
            sleep 15
        done
    done

    echo "================ PIPELINE 4 (self_consistency.py) - EVAL ================"

    for model in "${MODELS[@]}"; do
        echo "========================================================"
        echo "📊 [Pipeline 4] EVALUATING MODEL: $model"
        echo "========================================================"
        
        python self_consistency.py --mode eval --model "$model"
        
        echo "--------------------------------------------------------"
    done
fi

echo "🎉 SELECTED PIPELINES COMPLETED."
