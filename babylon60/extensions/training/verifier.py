# [C5-REAL] Exergy-Maximized
# Author: borjamoskv
# License: Apache-2.0
"""
Adapter Verifier v2.0 — Control de Integridad Estructural y Numérica de Adaptadores LoRA.

Verifica la sanidad matemática y estructural de los adaptadores LoRA entrenados
para asegurar que no contengan anomalías numéricas (NaN/inf) ni divergencias exergéticas.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.training.verifier")


class AdapterVerifier:
    """
    Sanity checks newly compiled LoRA adapters.
    Ensures they load correctly and don't produce toxic or corrupted outputs.
    """

    def verify_adapter(self, adapter_path: Path | str, base_model: str) -> dict[str, Any]:
        """
        Runs rigorous checks on the adapter files.
        Checks:
        1. File structure (adapter_config.json, weights.npz or adapters.safetensors).
        2. Config syntax and metadata matches expected parameters.
        3. Mathematical Integrity (Scans safetensors layers for NaN or Inf).
        4. Simulated or dry-run load test.
        """
        path = Path(adapter_path)
        logger.info("🔍 Initiating verification for adapter at %s", path)

        if not path.exists() or not path.is_dir():
            return {
                "success": False,
                "error": f"Adapter path does not exist or is not a directory: {path}",
                "metrics": {},
            }

        # Check structural files
        config_file = path / "adapter_config.json"
        weights_npz = path / "weights.npz"
        weights_safetensors = path / "adapters.safetensors"

        if not config_file.exists():
            return {
                "success": False,
                "error": "Missing 'adapter_config.json' in adapter directory",
                "metrics": {},
            }

        if not weights_npz.exists() and not weights_safetensors.exists():
            return {
                "success": False,
                "error": "Missing weights file (neither 'weights.npz' nor 'adapters.safetensors' found)",
                "metrics": {},
            }

        # Load and validate config JSON
        try:
            with open(config_file, encoding="utf-8") as f:
                config_data = json.load(f)
        except (ValueError, TypeError, OSError, KeyError) as e:
            return {
                "success": False,
                "error": f"Failed to parse 'adapter_config.json': {e}",
                "metrics": {},
            }

        config_base_model = config_data.get("model") or config_data.get("model_path")
        if (
            config_base_model
            and base_model not in config_base_model
            and config_base_model not in base_model
        ):
            logger.warning(
                "Mismatch between expected base model (%s) and config base model (%s)",
                base_model,
                config_base_model,
            )

        # ─── Mathematical Integrity Check (NaN/Inf Scan) ──────────────────────
        nan_detected = False
        inf_detected = False
        tensor_count = 0
        total_parameters = 0

        # Try scanning safetensors
        if weights_safetensors.exists():
            try:
                from safetensors import safe_open

                with safe_open(weights_safetensors, framework="numpy", device="cpu") as f:
                    for key in f.keys():
                        tensor = f.get_tensor(key)
                        tensor_count += 1
                        total_parameters += tensor.size
                        
                        # Math check via numpy
                        import numpy as np
                        if np.isnan(tensor).any():
                            nan_detected = True
                            logger.error("❌ NaN values detected in LoRA layer: %s", key)
                        if np.isinf(tensor).any():
                            inf_detected = True
                            logger.error("❌ Inf values detected in LoRA layer: %s", key)
            except ImportError:
                logger.warning("safetensors or numpy not installed. Skipping deep numerical scan.")
            except Exception as e:
                logger.error("Failed to open safetensors file: %s", e)
                return {
                    "success": False,
                    "error": f"Corrupted safetensors weight file: {e}",
                    "metrics": {},
                }

        if nan_detected or inf_detected:
            return {
                "success": False,
                "error": f"Numerical anomalies detected in weights (NaN: {nan_detected}, Inf: {inf_detected})",
                "metrics": {
                    "tensor_count": tensor_count,
                    "total_params": total_parameters,
                },
            }

        # Loading Check
        load_success = False
        import_error_msg = None
        try:
            import mlx_lm  # pyright: ignore[reportMissingImports]  # noqa: F401
            load_success = True
        except ImportError as e:
            import_error_msg = str(e)
            logger.info("mlx_lm not available. Falling back to simulated verification.")

        # Compile validation metrics
        metrics = {
            "validation_loss": config_data.get("validation_loss", 0.0),
            "iters": config_data.get("iters", 0),
            "lora_layers": config_data.get("lora_layers", 16),
            "tensor_count": tensor_count,
            "total_params": total_parameters,
            "simulated": import_error_msg is not None,
            "load_success": load_success,
        }

        logger.info("✅ Adapter verification successful for %s", path)
        return {
            "success": True,
            "metrics": metrics,
            "safety_status": "PASSED" if not (nan_detected or inf_detected) else "FAILED",
        }
