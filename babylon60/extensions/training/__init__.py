# [C5-REAL] Exergy-Maximized
# Author: borjamoskv
"""
CORTEX Training Extension — MOSKV-1 Cognitive Kernel Pipeline.

This module provides the complete lifecycle for training and deploying
a local LLM fine-tuned on CORTEX workspace knowledge:

    1. Dataset Compilation (MOSKV1DatasetCompiler)
    2. LoRA Fine-Tuning via MLX (TTTEngine)
    3. Hybrid Inference Runtime (MOSKV1Core)
    4. Adapter Verification (AdapterVerifier)

Usage:
    from cortex.extensions.training import MOSKV1DatasetCompiler, MOSKV1Core

    # Compile dataset
    compiler = MOSKV1DatasetCompiler("/path/to/workspace")
    compiler.compile_full_dataset()
    compiler.export_sharegpt(split=True)

    # Inference
    core = MOSKV1Core()
    result = await core.infer("query", db_conn)
"""

from cortex.extensions.training.collector import Action, Trajectory, TrajectoryCollector
from cortex.extensions.training.moskv1_core import MOSKV1Core
from cortex.extensions.training.moskv1_dataset_compiler import MOSKV1DatasetCompiler
from cortex.extensions.training.reward_engine import RewardEngine
from cortex.extensions.training.ttt_engine import TTTEngine

__all__ = [
    "Action",
    "MOSKV1Core",
    "MOSKV1DatasetCompiler",
    "RewardEngine",
    "Trajectory",
    "TrajectoryCollector",
    "TTTEngine",
]
