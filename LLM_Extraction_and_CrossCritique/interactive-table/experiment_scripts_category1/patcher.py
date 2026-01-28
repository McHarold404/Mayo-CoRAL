#!/usr/bin/env python3
import os
import re
import shutil
from pathlib import Path

TARGETS = [
    "/mnt/data1/srchowd3/Mayo-CoRAL/LLM_Extraction_and_CrossCritique/interactive-table/experiment_scripts/base_prompt.py",
    "/mnt/data1/srchowd3/Mayo-CoRAL/LLM_Extraction_and_CrossCritique/interactive-table/experiment_scripts/self_consistency.py",
    "/mnt/data1/srchowd3/Mayo-CoRAL/LLM_Extraction_and_CrossCritique/interactive-table/experiment_scripts/split_function.py",
    "/mnt/data1/srchowd3/Mayo-CoRAL/LLM_Extraction_and_CrossCritique/interactive-table/experiment_scripts/split_verify.py",
]

ARG_FLAG = "--gpu-mem-util"

def patch_file(path: Path) -> None:
    src = path.read_text(encoding="utf-8")

    # Safety backup
    backup = path.with_suffix(path.suffix + ".bak")
    if not backup.exists():
        shutil.copy2(path, backup)

    changed = False

    # -------------------------
    # 1) Add argparse argument
    # -------------------------
    if ARG_FLAG not in src:
        # Insert right after "parser = argparse.ArgumentParser()"
        # We compute default from env inside main() so it respects .env (dotenv already loaded in your scripts).
        insert_block = (
            "    # vLLM memory utilization (default from .env: GPU_MEMORY_UTILIZATION)\n"
            "    default_gpu_mem_util = float(os.getenv(\"GPU_MEMORY_UTILIZATION\", \"0.50\"))\n"
            "    parser.add_argument(\n"
            "        \"--gpu-mem-util\",\n"
            "        type=float,\n"
            "        default=default_gpu_mem_util,\n"
            "        help=\"vLLM gpu_memory_utilization (overrides .env GPU_MEMORY_UTILIZATION).\"\n"
            "    )\n\n"
        )

        # Find the parser creation line
        m = re.search(r"(?m)^(?P<indent>\s*)parser\s*=\s*argparse\.ArgumentParser\([^\)]*\)\s*$", src)
        if not m:
            raise RuntimeError(f"Could not find argparse.ArgumentParser() in {path}")

        indent = m.group("indent")
        # Ensure insert block uses same indentation as other parser.add_argument lines
        # (we wrote it with 4 spaces; adjust if indent differs)
        if indent != "":
            insert_block = re.sub(r"(?m)^", indent, insert_block)

        insert_at = m.end()
        src = src[:insert_at] + "\n" + insert_block + src[insert_at:]
        changed = True

    # ---------------------------------------------
    # 2) Replace gpu_memory_utilization=... in LLM
    # ---------------------------------------------
    # Replace any "gpu_memory_utilization = <number>" inside LLM(...) with args.gpu_mem_util
    # Keep commas/spacing intact.
    def repl(match: re.Match) -> str:
        nonlocal changed
        changed = True
        prefix = match.group(1)
        suffix = match.group(3) or ""
        return f"{prefix}args.gpu_mem_util{suffix}"

    # This targets patterns like:
    # gpu_memory_utilization=0.50,
    # gpu_memory_utilization = 0.9
    pattern = r"(gpu_memory_utilization\s*=\s*)([0-9]*\.?[0-9]+)(\s*,?)"
    src2, n = re.subn(pattern, repl, src)
    src = src2

    # ---------------------------------------------
    # 3) Optional: guard for bad values
    # ---------------------------------------------
    # If you want, you can keep this minimal. We’ll only add it if not present.
    if "args.gpu_mem_util <=" not in src:
        # Put a small validation after args = parser.parse_args()
        validate_block = (
            "\n"
            "    # Validate gpu memory utilization\n"
            "    if not (0.0 < args.gpu_mem_util <= 1.0):\n"
            "        raise ValueError(f\"--gpu-mem-util must be in (0, 1]. Got {args.gpu_mem_util}\")\n"
        )
        m2 = re.search(r"(?m)^\s*args\s*=\s*parser\.parse_args\(\)\s*$", src)
        if m2:
            insert_at = m2.end()
            src = src[:insert_at] + validate_block + src[insert_at:]
            changed = True

    if changed:
        path.write_text(src, encoding="utf-8")
        print(f"[PATCHED] {path}")
    else:
        print(f"[SKIP]    {path} (already patched)")

def main():
    for p in TARGETS:
        path = Path(p)
        if not path.exists():
            print(f"[MISSING] {path}")
            continue
        patch_file(path)

if __name__ == "__main__":
    main()
