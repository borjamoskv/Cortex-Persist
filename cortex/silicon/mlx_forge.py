"""
CORTEX v6.0 — MLX Forge (C5-REAL)

Direct-Silicon JIT LoRA tuning + quantization on Apple Silicon.
Ω₉: Declares SIMULATION if hardware is insufficient.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

MODEL_ID = "Qwen/Qwen3.6-Coder-7B-Instruct"
DATASET_PATH = Path("cortex_dataset.jsonl")
ADAPTER_PATH = Path("adapters")
FUSED_PATH = Path("cortex-qwen-4bit")


def _check_apple_silicon() -> dict:
    """Verify Apple Silicon availability. Returns hardware info."""
    info = {
        "chip": "unknown",
        "memory_gb": 0,
        "is_apple_silicon": False,
        "level": "C4-SIMULATION",
    }
    if platform.system() != "Darwin":
        return info

    try:
        r = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,  # noqa: S607
        )
        info["chip"] = r.stdout.strip()
        info["is_apple_silicon"] = "Apple" in info["chip"]
    except Exception:  # noqa: S110
        pass

    try:
        r = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)  # noqa: S607
        info["memory_gb"] = int(r.stdout.strip()) // (1024**3)
    except Exception:  # noqa: S110
        pass

    if info["is_apple_silicon"] and info["memory_gb"] >= 8:
        info["level"] = "C5-REAL"

    return info


def _ensure_mlx():
    """Install mlx-lm if not present."""
    try:
        import mlx_lm  # noqa: F401

        print("[C5-REAL] mlx-lm already installed")
    except ImportError:
        print("[C5-REAL] Installing mlx-lm...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mlx-lm", "-q"])  # noqa: S603


def train_lora(
    model_id: str = MODEL_ID,
    dataset_dir: str = ".",
    iters: int = 1000,
    batch_size: int = 4,
    lora_layers: int = 16,
    adapter_path: Path = ADAPTER_PATH,
):
    """Execute LoRA fine-tuning via mlx_lm CLI. C5-REAL."""
    hw = _check_apple_silicon()
    print(f"[{hw['level']}] Hardware: {hw['chip']} | RAM: {hw['memory_gb']}GB")

    if hw["level"] != "C5-REAL":
        print("[C4-SIMULATION] Insufficient hardware for MLX tuning. Aborting.")
        return False

    _ensure_mlx()

    if not DATASET_PATH.exists():
        print(f"[GATE] Dataset not found: {DATASET_PATH}. Aborting.")
        return False

    adapter_path.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "mlx_lm.lora",
        "--model",
        model_id,
        "--train",
        "--data",
        dataset_dir,
        "--iters",
        str(iters),
        "--batch-size",
        str(batch_size),
        "--lora-layers",
        str(lora_layers),
        "--adapter-path",
        str(adapter_path),
    ]
    print(f"[C5-REAL] Executing: {' '.join(cmd)}")

    proc = subprocess.run(cmd, capture_output=False)  # noqa: S603
    if proc.returncode != 0:
        print(f"[ERROR] Training failed with code {proc.returncode}")
        return False

    print(f"[C5-REAL] LoRA adapters saved to {adapter_path}")
    return True


def fuse_and_quantize(
    model_id: str = MODEL_ID,
    adapter_path: Path = ADAPTER_PATH,
    output_path: Path = FUSED_PATH,
    q_bits: int = 4,
):
    """Fuse LoRA adapters and quantize to 4-bit. C5-REAL."""
    if not adapter_path.exists():
        print(f"[GATE] Adapter path missing: {adapter_path}. Run training first.")
        return False

    cmd = [
        sys.executable,
        "-m",
        "mlx_lm.fuse",
        "--model",
        model_id,
        "--adapter-path",
        str(adapter_path),
        "--quantize",
        "--q-bits",
        str(q_bits),
        "--save-path",
        str(output_path),
    ]
    print(f"[C5-REAL] Executing: {' '.join(cmd)}")

    proc = subprocess.run(cmd, capture_output=False)  # noqa: S603
    if proc.returncode != 0:
        print(f"[ERROR] Fusion failed with code {proc.returncode}")
        return False

    print(f"[C5-REAL] Quantized model at {output_path}")
    return True


if __name__ == "__main__":
    hw = _check_apple_silicon()
    print(f"\n{'=' * 50}")
    print(f"MLX Forge — {hw['level']}")
    print(f"Chip: {hw['chip']} | RAM: {hw['memory_gb']}GB")
    print(f"{'=' * 50}\n")

    if hw["level"] == "C5-REAL":
        ok = train_lora()
        if ok:
            fuse_and_quantize()
    else:
        print("[C4-SIMULATION] This machine cannot run MLX training.")
        print("Required: Apple Silicon (M1+) with >= 8GB unified memory.")
