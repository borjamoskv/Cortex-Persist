#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
# Author: borjamoskv
# License: Apache-2.0
"""
MOSKV-1 CLI v2.0 — Interfaz de línea de comandos para el Kernel Cognitivo Híbrido.

Commands:
    compile    — Compilar dataset instruccional desde CORTEX
    train      — Ejecutar LoRA fine-tuning con MLX
    register   — Registrar modelo en Ollama
    validate   — Validar calidad del dataset compilado
    stats      — Mostrar estadísticas del dataset compilado
    health     — Verificar estado de Ollama y modelos disponibles
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import os

# Secure absolute offline autarchy for HF model loading
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_CACHE"] = os.path.expanduser("~/.babylon60/huggingface")

import asyncio
import json
import math
import sys
from collections import Counter
from pathlib import Path


def cmd_compile(workspace: str | None = None) -> None:
    """Compile the full MOSKV-1 training dataset."""
    from babylon60.extensions.training.moskv1_dataset_compiler import MOSKV1DatasetCompiler

    ws = Path(workspace) if workspace else Path.cwd()
    compiler = MOSKV1DatasetCompiler(workspace_path=ws)

    logger.info("🔧 MOSKV-1 Dataset Compilation v2.0 — C5-REAL")
    logger.info(f"   Workspace: {ws}")
    logger.info()

    compiler.compile_full_dataset()

    # Export with train/val/test split
    sharegpt_path = compiler.export_sharegpt(split=True)
    alpaca_path = compiler.export_alpaca()

    logger.info()
    logger.info("═══ COMPILATION STATS ═══")
    logger.info(compiler.get_stats_yaml())
    logger.info()
    logger.info(f"📁 ShareGPT: {sharegpt_path}")
    logger.info(f"📁 Alpaca:   {alpaca_path}")

    # Show split info
    dataset_dir = compiler.output_dir
    for name in ["train", "valid", "test"]:
        path = dataset_dir / f"{name}.jsonl"
        if path.exists():
            lines = sum(1 for _ in open(path))
            logger.info(f"📁 {name}: {lines} entries ({path.stat().st_size / 1024:.1f} KB)")


def cmd_train(
    model: str = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
    iters: int = 600,
    batch_size: int = 2,
    lora_layers: int = 16,
    learning_rate: float = 2e-5,
) -> None:
    """Execute MLX LoRA fine-tuning."""
    import subprocess

    dataset_dir = Path.home() / ".babylon60" / "training" / "datasets"
    adapter_path = Path.home() / ".babylon60" / "training" / "adapters"
    adapter_path.mkdir(parents=True, exist_ok=True)

    # Check for train.jsonl (v2 split format) or moskv1_dataset.jsonl
    if not (dataset_dir / "train.jsonl").exists():
        if (dataset_dir / "moskv1_dataset.jsonl").exists():
            logger.info("⚠️ No train/val/test split found. Run 'compile' with v2.0 first.")
            logger.info("   Falling back to moskv1_dataset.jsonl")
        else:
            logger.info("❌ Dataset not found. Run 'compile' first.")
            sys.exit(1)

    # Use non-deprecated mlx_lm subcommand syntax
    cmd = [
        sys.executable,
        "-m",
        "mlx_lm",
        "lora",
        "--model",
        model,
        "--train",
        "--data",
        str(dataset_dir),
        "--adapter-path",
        str(adapter_path),
        "--fine-tune-type",
        "lora",
        "--optimizer",
        "adamw",
        "--mask-prompt",
        "--num-layers",
        str(lora_layers),
        "--iters",
        str(iters),
        "--batch-size",
        "1",  # Lower batch size to reduce memory usage
        "--grad-accumulation-steps",
        "2",  # Accumulate gradient to maintain effective batch size of 2
        "--learning-rate",
        str(learning_rate),
        "--steps-per-report",
        "10",
        "--steps-per-eval",
        "50",
        "--val-batches",
        "5",
        "--max-seq-length",
        "1280",  # Fit maximum character limit securely
        "--grad-checkpoint",  # Use gradient checkpointing to save VRAM
        "--save-every",
        "100",
        "--seed",
        "42",
    ]

    logger.info(f"🧠 MLX LoRA Training — {model}")
    logger.info(f"   Iterations: {iters} | Batch: 1 (Acc: 2) | Layers: {lora_layers}")
    logger.info(f"   Learning Rate: {learning_rate} | Optimizer: adamw")
    logger.info("   Max Seq Length: 1280 | Mask Prompt: True | Grad Checkpoint: True")
    logger.info(f"   Output: {adapter_path}")
    logger.info()

    result = subprocess.run(cmd, text=True)
    sys.exit(result.returncode)


def cmd_register() -> None:
    """Register MOSKV-1 model in Ollama."""
    from babylon60.extensions.training.moskv1_core import MOSKV1Core

    core = MOSKV1Core()
    modelfile = core.get_modelfile()

    modelfile_path = Path.home() / ".babylon60" / "training" / "adapters" / "Modelfile"
    modelfile_path.parent.mkdir(parents=True, exist_ok=True)
    modelfile_path.write_text(modelfile, encoding="utf-8")

    logger.info(f"📄 Modelfile written to: {modelfile_path}")
    logger.info()
    logger.info("To register in Ollama, run:")
    logger.info(f"  ollama create moskv1-core -f {modelfile_path}")


def cmd_validate() -> None:
    """Validate dataset quality with detailed diagnostics."""
    dataset_dir = Path.home() / ".babylon60" / "training" / "datasets"
    dataset_path = dataset_dir / "moskv1_dataset.jsonl"
    if not dataset_path.exists():
        logger.info("❌ No compiled dataset found. Run 'compile' first.")
        sys.exit(1)

    entries: list[dict] = []
    with open(dataset_path, encoding="utf-8") as f:
        for line in f:
            entries.append(json.loads(line))

    # ─── Quality Metrics ───────────────────────────────────────────
    output_lengths: list[int] = []
    instruction_lengths: list[int] = []
    has_code = 0
    has_yaml = 0
    has_structure = 0
    html_in_instruction = 0
    anergy_detected = 0

    anergy_words = [
        "hola",
        "buenos días",
        "espero que",
        "por supuesto",
        "aquí tienes",
        "here you go",
        "of course",
        "hope this helps",
    ]

    categories: Counter[str] = Counter()

    for e in entries:
        conversations = e.get("messages") or e.get("conversations") or []
        if len(conversations) < 3:
            continue

        instruction = conversations[1].get("content", "")
        output = conversations[-1].get("content", "")

        output_lengths.append(len(output))
        instruction_lengths.append(len(instruction))

        if "```" in output:
            has_code += 1
        if "yaml" in output.lower() or ": " in output:
            has_yaml += 1
        if "\n- " in output or "\n| " in output or "\n## " in output:
            has_structure += 1
        if "<!--" in instruction:
            html_in_instruction += 1

        for word in anergy_words:
            if word in output.lower():
                anergy_detected += 1
                break

        # Categorize by instruction pattern
        inst_lower = instruction.lower()
        if "clase" in inst_lower:
            categories["code_class"] += 1
        elif "módulo" in inst_lower or "module" in inst_lower:
            categories["code_module"] += 1
        elif "skill" in inst_lower:
            categories["skill"] += 1
        elif "directiva" in inst_lower:
            categories["directive"] += 1
        elif "memory vault" in inst_lower or "vault" in inst_lower:
            categories["memory_vault"] += 1
        elif "workflow" in inst_lower:
            categories["workflow"] += 1
        elif "ledger" in inst_lower or "hecho" in inst_lower:
            categories["ledger"] += 1
        else:
            categories["session/other"] += 1

    n = len(entries)
    avg_out = sum(output_lengths) / n if n else 0
    avg_inst = sum(instruction_lengths) / n if n else 0

    # Shannon entropy of output length distribution
    length_buckets = Counter(length // 100 * 100 for length in output_lengths)
    total_length = sum(length_buckets.values())
    len_entropy = (
        -sum(
            (c / total_length) * math.log2(c / total_length)
            for c in length_buckets.values()
            if c > 0
        )
        if total_length > 0
        else 0.0
    )

    # ─── Report ────────────────────────────────────────────────────
    logger.info("═══ MOSKV-1 DATASET VALIDATION v2.0 ═══")
    logger.info()
    logger.info(f"📊 Total entries: {n}")
    logger.info()
    logger.info("── Length Distribution ──")
    logger.info(f"  Avg output length:       {avg_out:.0f} chars")
    logger.info(f"  Avg instruction length:  {avg_inst:.0f} chars")
    logger.info(f"  Min output:              {min(output_lengths) if output_lengths else 0} chars")
    logger.info(f"  Max output:              {max(output_lengths) if output_lengths else 0} chars")
    logger.info(f"  Length entropy:          {len_entropy:.2f} bits")
    logger.info()
    logger.info("── Content Quality ──")
    logger.info(f"  Has code blocks:         {has_code} ({has_code / n * 100:.1f}%)")
    logger.info(f"  Has YAML/structured:     {has_yaml} ({has_yaml / n * 100:.1f}%)")
    logger.info(f"  Has lists/tables:        {has_structure} ({has_structure / n * 100:.1f}%)")
    logger.info()
    logger.info("── Defects ──")
    logger.info(
        f"  HTML in instructions:    {html_in_instruction} {'✅' if html_in_instruction == 0 else '❌'}"
    )
    logger.info(f"  Anergy detected:         {anergy_detected} {'✅' if anergy_detected == 0 else '⚠️'}")
    logger.info()
    logger.info("── Category Distribution ──")
    for cat, count in categories.most_common():
        bar = "█" * (count * 40 // n)
        logger.info(f"  {cat:20s} {count:5d} ({count / n * 100:5.1f}%) {bar}")

    # ─── Split Validation ──────────────────────────────────────────
    logger.info()
    logger.info("── Train/Val/Test Split ──")
    for name in ["train", "valid", "test"]:
        path = dataset_dir / f"{name}.jsonl"
        if path.exists():
            count = sum(1 for _ in open(path))
            logger.info(f"  {name:8s} {count:5d} entries  ({path.stat().st_size / 1024:.1f} KB)")
        else:
            logger.info(f"  {name:8s} NOT FOUND ❌")

    # ─── Overall Score ─────────────────────────────────────────────
    score = 0
    if html_in_instruction == 0:
        score += 200
    if anergy_detected < n * 0.01:
        score += 200
    score += min(int(has_code / n * 300), 200)  # Code density
    score += min(int(len_entropy * 50), 200)  # Length diversity
    score += min(int(len(categories) * 30), 200)  # Category diversity

    logger.info()
    logger.info(f"🎯 DATASET EXERGY SCORE: {score}/1000")
    if score >= 800:
        logger.info("   ✅ Dataset is production-ready for LoRA training")
    elif score >= 500:
        logger.info("   ⚠️ Dataset is acceptable but could be improved")
    else:
        logger.info("   ❌ Dataset quality is insufficient — review filter settings")

    # ─── Weights Verification ───
    adapter_path = Path.home() / ".babylon60" / "training" / "adapters"
    if (adapter_path / "adapters.safetensors").exists():
        logger.info()
        logger.info("═══ LoRA WEIGHTS VERIFICATION (C5-REAL) ═══")
        from babylon60.extensions.training.verifier import AdapterVerifier

        verifier = AdapterVerifier()
        base_model = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
        verdict = verifier.verify_adapter(adapter_path, base_model)

        if verdict["success"]:
            metrics = verdict["metrics"]
            logger.info("   Status:        ✅ PASSED")
            logger.info(f"   Total Tensors: {metrics['tensor_count']}")
            logger.info(f"   Parameters:    {metrics['total_params']:,}")
            logger.info("   Layers Check:  All weights finite, zero NaNs/infs.")
        else:
            logger.info("   Status:        ❌ FAILED")
            logger.info(f"   Error:         {verdict['error']}")
    else:
        logger.info()
        logger.info("💡 Tip: No adapter weights found in adapters/. Run 'train' to generate weights.")


def cmd_stats() -> None:
    """Show stats of the last compiled dataset."""
    dataset_path = Path.home() / ".babylon60" / "training" / "datasets" / "moskv1_dataset.jsonl"
    if not dataset_path.exists():
        logger.info("❌ No compiled dataset found.")
        sys.exit(1)

    entries = []
    with open(dataset_path, encoding="utf-8") as f:
        for line in f:
            entries.append(json.loads(line))

    total_tokens = (
        sum(
            sum(
                len(m.get("content", ""))
                for m in (e.get("messages") or e.get("conversations") or [])
            )
            for e in entries
        )
        // 4
    )

    logger.info(f"📊 Dataset: {dataset_path}")
    logger.info(f"   Entries: {len(entries)}")
    logger.info(f"   Estimated tokens: {total_tokens:,}")
    logger.info(f"   File size: {dataset_path.stat().st_size / 1024:.1f} KB")

    # Show split info
    dataset_dir = dataset_path.parent
    for name in ["train", "valid", "test"]:
        path = dataset_dir / f"{name}.jsonl"
        if path.exists():
            count = sum(1 for _ in open(path))
            logger.info(f"   {name}: {count} entries")


def cmd_health() -> None:
    """Check Ollama health and model availability."""
    from babylon60.extensions.training.moskv1_core import MOSKV1Core

    core = MOSKV1Core()
    result = asyncio.run(core.check_ollama_health())

    logger.info("═══ MOSKV-1 HEALTH CHECK ═══")
    logger.info()
    logger.info(f"Ollama reachable:    {'✅' if result['ollama_reachable'] else '❌'}")
    logger.info(f"MOSKV-1 available:   {'✅' if result['moskv1_available'] else '❌'}")
    logger.info(f"Fallback available:  {'✅' if result['fallback_available'] else '❌'}")
    logger.info()
    if result["models"]:
        logger.info("Available models:")
        for m in result["models"]:
            marker = " ◀ MOSKV-1" if "moskv1" in m else ""
            logger.info(f"  - {m}{marker}")
    else:
        logger.info("No models available (Ollama may not be running)")


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        logger.info("MOSKV-1 Cognitive Kernel — CLI v2.0")
        logger.info("Author: borjamoskv")
        logger.info()
        logger.info("Usage: python -m babylon60.extensions.training.moskv1_cli <command>")
        logger.info()
        logger.info("Commands:")
        logger.info("  compile    Compile CORTEX knowledge into training dataset")
        logger.info("  train      Run MLX LoRA fine-tuning")
        logger.info("  register   Generate Ollama Modelfile")
        logger.info("  validate   Validate dataset quality with diagnostics")
        logger.info("  stats      Show dataset statistics")
        logger.info("  health     Check Ollama availability")
        sys.exit(1)

    command = sys.argv[1]

    if command == "compile":
        workspace = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_compile(workspace)
    elif command == "train":
        iters = 600
        if len(sys.argv) > 2:
            try:
                iters = int(sys.argv[2])
            except ValueError:
                pass
        cmd_train(iters=iters)
    elif command == "register":
        cmd_register()
    elif command == "validate":
        cmd_validate()
    elif command == "stats":
        cmd_stats()
    elif command == "health":
        cmd_health()
    else:
        logger.info(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
