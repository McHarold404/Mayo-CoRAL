GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
echo "==== GPU Usage by User ===="
echo ""
GPU_INFO=$(nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader 2>/dev/null)
PROCESS_INFO=$(nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv,noheader 2>/dev/null)
GPU_UUIDS=$(nvidia-smi --query-gpu=index,uuid --format=csv,noheader 2>/dev/null)
# Create UUID to index mapping
declare -A UUID_TO_INDEX
while IFS=", " read -r idx uuid; do
    UUID_TO_INDEX["$uuid"]="$idx"
done <<< "$GPU_UUIDS"
declare -A GPU_PROCESSES
while IFS=", " read -r gpu_uuid pid mem; do
    idx=${UUID_TO_INDEX["$gpu_uuid"]}
    if [[ -n "$idx" ]]; then
        if [[ -z "${GPU_PROCESSES[$idx]}" ]]; then
            GPU_PROCESSES[$idx]="$pid"
        else
            GPU_PROCESSES[$idx]="${GPU_PROCESSES[$idx]} $pid"
        fi
    fi
done <<< "$PROCESS_INFO"
while IFS="," read -r idx util mem_used mem_total; do
    # Clean up and convert to integers
    util=$(echo "$util" | tr -d ' %')
    mem_used=$(echo "$mem_used" | tr -d ' MiB')
    mem_total=$(echo "$mem_total" | tr -d ' MiB')
    
    util=${util:-0}
    mem_used=${mem_used:-0}
    mem_total=${mem_total:-1}  
    
    mem_percent=$((mem_used * 100 / mem_total))
    processes="${GPU_PROCESSES[$idx]}"
    
    if [[ -z "$processes" && $util -lt 5 && $mem_percent -lt 5 ]]; then
        echo -e "GPU $idx: ${GREEN}FREE${NC} (Util: ${util}%, Mem: ${mem_used}/${mem_total} MiB, ${mem_percent}%)"
    else
        if [[ $util -gt 50 || $mem_percent -gt 50 ]]; then
            status="${RED}BUSY${NC}"
        else
            status="${YELLOW}IN USE${NC}"
        fi
        
        echo -e "GPU $idx: $status (Util: ${util}%, Mem: ${mem_used}/${mem_total} MiB, ${mem_percent}%)"
        
        if [[ -n "$processes" ]]; then
            echo "   Users:"
            for pid in $processes; do
                user=$(ps -o user= -p "$pid" 2>/dev/null)
                cmd=$(ps -o cmd= -p "$pid" 2>/dev/null | cut -c 1-80)
                if [[ -n "$user" ]]; then
                    echo "   - $user: $cmd"
                fi
            done
        fi
    fi
    echo ""
done <<< "$GPU_INFO"