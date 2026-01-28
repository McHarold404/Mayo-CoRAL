#!/usr/bin/env python3
"""
hf_vllm_snapshot_check.py

Scan a Hugging Face cache hub directory (e.g. /mnt/shared/shared_hf_home/hub),
inspect each model snapshot, and estimate whether vLLM can run it.

Default mode is *static* (no weights loading). Optional --probe attempts
to initialize vLLM (may allocate GPU memory and take time).

Usage:
  python hf_vllm_snapshot_check.py /mnt/shared/shared_hf_home/hub
  python hf_vllm_snapshot_check.py /mnt/shared/shared_hf_home/hub --only-yes
  python hf_vllm_snapshot_check.py /mnt/shared/shared_hf_home/hub --only-yes --print-paths
  python hf_vllm_snapshot_check.py /mnt/shared/shared_hf_home/hub --out report.csv
  python hf_vllm_snapshot_check.py /mnt/shared/shared_hf_home/hub --probe --limit 5

Notes:
- This is heuristic. vLLM support changes over time and some models require
  --trust-remote-code or specific quantization flags.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# A pragmatic list of decoder-only model types commonly supported by vLLM.
# Not exhaustive; unknowns are reported as "UNKNOWN" / "MAYBE".
VLLM_LIKELY_SUPPORTED_MODEL_TYPES = {
    # LLaMA-family and derivatives
    "llama", "mistral", "mixtral", "gemma", "gemma2",
    # Qwen-family
    "qwen", "qwen2", "qwen2_moe",
    # Others often supported
    "gpt_neox", "falcon", "mpt", "bloom", "opt", "gpt_bigcode",
    "baichuan", "internlm", "internlm2",
    "phi", "phi2", "phi3",
    "yi", "starcoder2",
    "deepseek_v2", "deepseek",
    # Some repos use these
    "cohere", "command-r", "command-r-plus",
}

# Quantization methods vLLM frequently supports (naming varies by model/config).
VLLM_COMMON_QUANT_METHOD_HINTS = {
    "awq", "gptq", "marlin", "squeezellm", "fp8", "int8", "bitsandbytes", "bnb",
    "gguf", "ggml",  # usually *not* supported by vLLM; kept for detection
}


@dataclass
class SnapshotCheck:
    model_repo_dir: str
    model_id_guess: str
    snapshot_dir: str
    snapshot_hash: str

    has_config: bool = False
    model_type: Optional[str] = None
    architectures: List[str] = field(default_factory=list)
    is_encoder_decoder: Optional[bool] = None
    trust_remote_code_hint: bool = False

    weight_files: List[str] = field(default_factory=list)
    weight_format: Optional[str] = None  # safetensors / pytorch_bin / other / none
    has_tokenizer: bool = False

    quantization_hint: Optional[str] = None

    static_verdict: str = "UNKNOWN"  # YES / NO / MAYBE / UNKNOWN
    reasons: List[str] = field(default_factory=list)

    # Optional probe results
    probe_attempted: bool = False
    probe_ok: Optional[bool] = None
    probe_error: Optional[str] = None


def guess_model_id_from_cache_dir(d: Path) -> str:
    """
    Convert HF cache repo folder name to model id:
      models--org--name  -> org/name
      models--name       -> name
    """
    name = d.name
    if not name.startswith("models--"):
        return name
    rest = name[len("models--"):]
    parts = rest.split("--")
    if len(parts) >= 2:
        return f"{parts[0]}/{ '/'.join(parts[1:]) }".replace("//", "/")
    return rest


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def list_weight_files(snapshot: Path) -> Tuple[List[str], Optional[str]]:
    """
    Detect common HF weight layouts:
      - *.safetensors or model.safetensors.index.json
      - pytorch_model*.bin or pytorch_model.bin.index.json
      - other unusual weight files
    """
    files: List[str] = []
    for p in snapshot.glob("*"):
        if p.is_file():
            files.append(p.name)

    safes = [f for f in files if f.endswith(".safetensors")]
    ptbin = [f for f in files if re.match(r"^pytorch_model.*\.bin$", f)]
    safe_index = "model.safetensors.index.json" in files
    pt_index = "pytorch_model.bin.index.json" in files

    weight_files: List[str] = []
    weight_format: Optional[str] = None

    if safes or safe_index:
        weight_format = "safetensors"
        weight_files.extend(safes)
        if safe_index:
            weight_files.append("model.safetensors.index.json")
    elif ptbin or pt_index:
        weight_format = "pytorch_bin"
        weight_files.extend(ptbin)
        if pt_index:
            weight_files.append("pytorch_model.bin.index.json")
    else:
        other = [f for f in files if any(f.endswith(ext) for ext in (".pt", ".ckpt", ".pth"))]
        if other:
            weight_format = "other"
            weight_files.extend(other)
        else:
            weight_format = "none"

    return sorted(set(weight_files)), weight_format


def has_tokenizer_files(snapshot: Path) -> bool:
    patterns = [
        "tokenizer.json",
        "tokenizer.model",
        "tokenizer_config.json",
        "vocab.json",
        "merges.txt",
        "special_tokens_map.json",
        "spiece.model",
    ]
    present = {p.name for p in snapshot.glob("*") if p.is_file()}
    return any(p in present for p in patterns)


def detect_quantization_hint(config: Dict[str, Any], snapshot: Path) -> Optional[str]:
    for key in ("quantization_config", "compression_config", "bnb_4bit_compute_dtype", "load_in_4bit", "load_in_8bit"):
        if key in config:
            val = config.get(key)
            if isinstance(val, dict):
                for k in ("quant_method", "quant_type", "backend", "format"):
                    if k in val and isinstance(val[k], str):
                        return val[k].lower()
            if isinstance(val, str):
                return val.lower()
            if isinstance(val, bool) and val:
                return key.lower()

    names = {p.name.lower() for p in snapshot.glob("*") if p.is_file()}
    joined = " ".join(sorted(names))
    for hint in sorted(VLLM_COMMON_QUANT_METHOD_HINTS):
        if hint in joined:
            return hint
    return None


def static_vllm_verdict(check: SnapshotCheck) -> SnapshotCheck:
    reasons: List[str] = []

    if not check.has_config:
        reasons.append("Missing config.json")
        check.static_verdict = "NO"
        check.reasons = reasons
        return check

    if check.weight_format in (None, "none"):
        reasons.append("No recognizable HF weight files (.safetensors or pytorch_model*.bin)")
        check.static_verdict = "NO"
        check.reasons = reasons
        return check

    if not check.has_tokenizer:
        reasons.append("Tokenizer files not found (may still work if tokenizer can be resolved externally)")

    if check.is_encoder_decoder is True:
        reasons.append("config indicates encoder-decoder model (is_encoder_decoder=true) — often not supported by vLLM")
        check.static_verdict = "NO"
        check.reasons = reasons
        return check

    if check.model_type:
        mt = check.model_type.lower()
        if mt in VLLM_LIKELY_SUPPORTED_MODEL_TYPES:
            reasons.append(f"model_type '{mt}' is commonly supported by vLLM")
            verdict = "YES"
        else:
            reasons.append(f"model_type '{mt}' not in known-supported list — may require newer vLLM or --trust-remote-code")
            verdict = "MAYBE"
    else:
        reasons.append("config missing model_type — may require --trust-remote-code or nonstandard config")
        verdict = "MAYBE"

    arch = " ".join(check.architectures).lower()
    if check.architectures:
        if "forcausallm" in arch or "causallm" in arch:
            reasons.append("architectures suggest CausalLM / decoder-only")
        elif "seq2seq" in arch or "conditionalgeneration" in arch:
            reasons.append("architectures suggest seq2seq/conditional generation — may not be supported")
            verdict = "MAYBE"
    else:
        reasons.append("config missing architectures — cannot confirm task type")

    if check.quantization_hint:
        qh = check.quantization_hint.lower()
        if qh in {"gguf", "ggml"}:
            reasons.append(f"quantization hint '{qh}' detected — vLLM generally does NOT run GGUF/GGML directly")
            verdict = "NO"
        else:
            reasons.append(f"quantization hint '{qh}' detected — may require specific vLLM flags/backend support")
            if verdict == "YES":
                verdict = "MAYBE"

    if check.trust_remote_code_hint:
        reasons.append("auto_map/custom code hint detected — may require --trust-remote-code")

    check.static_verdict = verdict
    check.reasons = reasons
    return check


def check_snapshot(model_repo_dir: Path, snapshot_dir: Path) -> SnapshotCheck:
    model_id_guess = guess_model_id_from_cache_dir(model_repo_dir)
    snapshot_hash = snapshot_dir.name

    check = SnapshotCheck(
        model_repo_dir=str(model_repo_dir),
        model_id_guess=model_id_guess,
        snapshot_dir=str(snapshot_dir),
        snapshot_hash=snapshot_hash,
    )

    cfg = read_json(snapshot_dir / "config.json")
    if cfg is None:
        check.has_config = False
        return static_vllm_verdict(check)

    check.has_config = True
    check.model_type = cfg.get("model_type")
    check.architectures = cfg.get("architectures") or []
    check.is_encoder_decoder = cfg.get("is_encoder_decoder")
    check.trust_remote_code_hint = bool(cfg.get("auto_map")) or bool(cfg.get("trust_remote_code"))

    wf, fmt = list_weight_files(snapshot_dir)
    check.weight_files = wf
    check.weight_format = fmt
    check.has_tokenizer = has_tokenizer_files(snapshot_dir)
    check.quantization_hint = detect_quantization_hint(cfg, snapshot_dir)

    return static_vllm_verdict(check)


def find_snapshots(hub_dir: Path) -> List[Tuple[Path, Path]]:
    pairs: List[Tuple[Path, Path]] = []
    if not hub_dir.exists():
        raise FileNotFoundError(f"Hub dir does not exist: {hub_dir}")

    for repo in sorted(hub_dir.glob("models--*")):
        snaps_root = repo / "snapshots"
        if not snaps_root.is_dir():
            continue
        for snap in sorted(snaps_root.iterdir()):
            if snap.is_dir():
                pairs.append((repo, snap))
    return pairs


def try_probe_with_vllm(check: SnapshotCheck, tp: int = 1, trust_remote_code: bool = False) -> SnapshotCheck:
    check.probe_attempted = True
    try:
        from vllm import LLM  # type: ignore

        _ = LLM(
            model=check.snapshot_dir,
            tokenizer=check.snapshot_dir,
            tensor_parallel_size=tp,
            trust_remote_code=trust_remote_code,
            max_model_len=16,
        )
        check.probe_ok = True
        check.probe_error = None
    except Exception as e:
        check.probe_ok = False
        check.probe_error = f"{type(e).__name__}: {e}"
    return check


def write_json(out_path: Path, rows: List[SnapshotCheck]) -> None:
    data = [asdict(r) for r in rows]
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(out_path: Path, rows: List[SnapshotCheck]) -> None:
    fieldnames = [
        "model_id_guess",
        "snapshot_hash",
        "static_verdict",
        "model_type",
        "is_encoder_decoder",
        "weight_format",
        "has_tokenizer",
        "trust_remote_code_hint",
        "quantization_hint",
        "snapshot_dir",
        "reasons",
        "probe_attempted",
        "probe_ok",
        "probe_error",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({
                "model_id_guess": r.model_id_guess,
                "snapshot_hash": r.snapshot_hash,
                "static_verdict": r.static_verdict,
                "model_type": r.model_type,
                "is_encoder_decoder": r.is_encoder_decoder,
                "weight_format": r.weight_format,
                "has_tokenizer": r.has_tokenizer,
                "trust_remote_code_hint": r.trust_remote_code_hint,
                "quantization_hint": r.quantization_hint,
                "snapshot_dir": r.snapshot_dir,
                "reasons": " | ".join(r.reasons),
                "probe_attempted": r.probe_attempted,
                "probe_ok": r.probe_ok,
                "probe_error": r.probe_error,
            })


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("hub_dir", type=str, help="HF cache hub dir, e.g. /mnt/shared/shared_hf_home/hub")
    ap.add_argument("--out", type=str, default="", help="Output file path (.json or .csv). If omitted, prints summary.")
    ap.add_argument("--limit", type=int, default=0, help="Only process first N snapshots (for quick tests).")
    ap.add_argument("--probe", action="store_true", help="Attempt to instantiate vLLM for each snapshot (heavy).")
    ap.add_argument("--tp", type=int, default=1, help="tensor_parallel_size for --probe")
    ap.add_argument("--trust-remote-code", action="store_true", help="Pass trust_remote_code=True in --probe")

    # Printing filters
    ap.add_argument("--only-yes", action="store_true", help="Print only snapshots with static_verdict==YES")
    ap.add_argument("--only-maybe", action="store_true", help="Print only snapshots with static_verdict==MAYBE")
    ap.add_argument("--only-no", action="store_true", help="Print only snapshots with static_verdict==NO")
    ap.add_argument("--print-paths", action="store_true", help="Also print snapshot_dir path (copy/paste for vLLM).")

    args = ap.parse_args()

    hub_dir = Path(args.hub_dir).expanduser().resolve()
    pairs = find_snapshots(hub_dir)
    if args.limit and args.limit > 0:
        pairs = pairs[:args.limit]

    results: List[SnapshotCheck] = []
    for repo_dir, snap_dir in pairs:
        chk = check_snapshot(repo_dir, snap_dir)
        if args.probe:
            chk = try_probe_with_vllm(chk, tp=args.tp, trust_remote_code=args.trust_remote_code)
        results.append(chk)

    # Sort: NO, MAYBE, YES, UNKNOWN then by model id
    order = {"NO": 0, "MAYBE": 1, "YES": 2, "UNKNOWN": 3}
    results.sort(key=lambda r: (order.get(r.static_verdict, 9), r.model_id_guess, r.snapshot_hash))

    if args.out:
        outp = Path(args.out).expanduser().resolve()
        outp.parent.mkdir(parents=True, exist_ok=True)
        if outp.suffix.lower() == ".json":
            write_json(outp, results)
        elif outp.suffix.lower() == ".csv":
            write_csv(outp, results)
        else:
            print(f"--out must end with .json or .csv (got {outp})", file=sys.stderr)
            return 2
        print(f"Wrote {len(results)} snapshot checks to {outp}")
        return 0

    # Summary
    yes = sum(1 for r in results if r.static_verdict == "YES")
    maybe = sum(1 for r in results if r.static_verdict == "MAYBE")
    no = sum(1 for r in results if r.static_verdict == "NO")
    unk = sum(1 for r in results if r.static_verdict == "UNKNOWN")
    print(f"Snapshots checked: {len(results)}  YES={yes}  MAYBE={maybe}  NO={no}  UNKNOWN={unk}")

    # Apply printing filter
    to_print = results
    if args.only_yes:
        to_print = [r for r in results if r.static_verdict == "YES"]
    elif args.only_maybe:
        to_print = [r for r in results if r.static_verdict == "MAYBE"]
    elif args.only_no:
        to_print = [r for r in results if r.static_verdict == "NO"]

    print("-" * 120)
    for r in to_print:
        reasons = "; ".join(r.reasons[:3]) + (" ..." if len(r.reasons) > 3 else "")
        wf = r.weight_format or "-"   # <- prevents None formatting crash
        mt = r.model_type or "-"
        base = f"{r.static_verdict:6}  {r.model_id_guess:40}  {r.snapshot_hash:12}  {wf:11}  {mt:14}  {reasons}"
        if args.print_paths:
            base += f"  |  {r.snapshot_dir}"
        print(base)

        if r.probe_attempted and not r.probe_ok:
            print(f"        probe_error: {r.probe_error}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
