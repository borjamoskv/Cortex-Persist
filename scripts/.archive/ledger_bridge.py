#!/usr/bin/env python3
"""
∴ LKRGSER-BRIDGE: Cryptographic Web3 Agent Bridge (v1.0.0)
Reality Level: C5-REAL (Direct-Silicon JIT FFI & On-Chain RPC Verification)
Aesthetic: Industrial Noir 2026 (#0A0A0A / #2B3BE5)
Reference: Hito 04: Zero-Leak Memory Substrate
"""

import argparse
import ctypes
import hashlib
import logging
import os
import sys
from pathlib import Path

# Logger configuration
setup_cortex_logging()
logger = logging.getLogger("LedgerBridge")

# Define JIT paths
CORTEX_JIT_PATHS = [
    "/Users/borjafernandezangulo/10_PROJECTS/borjamoskv/Cortex-Persist/cortex/core/cortex_jit/target/release/libcortex_jit.dylib",
    "/Users/borjafernandezangulo/10_PROJECTS/borjamoskv/Cortex-Persist/cortex/core/cortex_jit/target/release/libcortex_jit.so",
    "./libcortex_jit.dylib",
    "./libcortex_jit.so",
]


class LedgerBridge:
    def __init__(self):
        self.jit_lib: ctypes.CDLL | None = None
        self.lib_path: str | None = None
        self.reality_level = "C4-SIM"

        # Attempt to load the native JIT library
        for path in CORTEX_JIT_PATHS:
            if os.path.exists(path):
                try:
                    self.jit_lib = ctypes.CDLL(path)
                    self.lib_path = path
                    self.reality_level = "C5-REAL"
                    logger.info(f"Successfully loaded JIT library from: {path}")

                    # Define parameter and return types for FFI functions
                    self.jit_lib.fetch_ultrathin_rpc_block.restype = ctypes.c_uint64
                    self.jit_lib.crystallize_skill.argtypes = [
                        ctypes.POINTER(ctypes.c_ubyte),
                        ctypes.c_size_t,
                        ctypes.POINTER(ctypes.c_ubyte),
                    ]
                    self.jit_lib.crystallize_skill.restype = ctypes.c_int32
                    break
                except Exception as e:
                    logger.warning(f"Failed to load JIT library from {path}: {e}")

        if not self.jit_lib:
            logger.warning("No native JIT library found. Falling back to C4-SIM execution mode.")

    def fetch_live_block(self) -> tuple[int, str]:
        """
        Retrieves current block number from the Ethereum blockchain.
        Returns: (block_number, reality_level)
        """
        if self.reality_level == "C5-REAL" and self.jit_lib:
            try:
                block = self.jit_lib.fetch_ultrathin_rpc_block()
                if block > 0:
                    return block, "C5-REAL"
                logger.warning(
                    "JIT block fetch returned 0. Total RPC collapse. Falling back to degraded simulation."
                )
                return 0, "C4-SIM"
            except Exception as e:
                logger.error(f"Error during JIT block fetch: {e}")
                return 0, "C4-SIM"
        else:
            # Degraded simulation fallback to maintain execution
            return 0, "C4-SIM"

    def crystallize_content(self, data: bytes) -> tuple[str, str]:
        """
        Uses the native Rust JIT implementation of SHA-256 for fast cryptographic sealing.
        Returns: (hex_hash, reality_level)
        """
        if self.reality_level == "C5-REAL" and self.jit_lib:
            try:
                # Prepare input buffer
                data_len = len(data)
                input_array = (ctypes.c_ubyte * data_len)(*data)

                # Prepare output buffer for 32-byte hash
                output_array = (ctypes.c_ubyte * 32)()

                res = self.jit_lib.crystallize_skill(input_array, data_len, output_array)

                if res == 0:
                    hash_hex = bytes(output_array).hex()
                    return hash_hex, "C5-REAL"
                logger.error(f"JIT crystallize function returned error code: {res}")
                return hashlib.sha256(data).hexdigest(), "C4-SIM"
            except Exception as e:
                logger.error(f"JIT crystallize failed: {e}. Falling back to standard hash.")
                return hashlib.sha256(data).hexdigest(), "C4-SIM"
        else:
            # Emulated hardware hash
            return hashlib.sha256(data).hexdigest(), "C4-SIM"

    def verify_system(self) -> dict:
        """
        Runs the full verification protocol and returns structured metrics.
        """
        import time

        start_time = time.perf_counter_ns()

        block, block_lvl = self.fetch_live_block()
        test_payload = b"CORTEX-CRYSTAL-VERIFY-2026"
        hash_val, hash_lvl = self.crystallize_content(test_payload)

        end_time = time.perf_counter_ns()
        latency_ms = (end_time - start_time) / 1_000_000.0

        active_level = "C5-REAL" if (block_lvl == "C5-REAL" and hash_lvl == "C5-REAL") else "C4-SIM"

        return {
            "status": "VERIFIED" if active_level == "C5-REAL" else "DEGRADED",
            "reality_level": active_level,
            "ethereum_block": block,
            "verification_hash": hash_val,
            "latency_ms": latency_ms,
            "jit_path": self.lib_path,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="∴ LKRGSER-BRIDGE CLI")
    parser.add_argument(
        "--verify", action="store_true", help="Execute complete system verification protocol"
    )
    parser.add_argument(
        "--crystallize", type=str, help="Crystallize target file content via JIT SHA-256"
    )

    args = parser.parse_args()
    bridge = LedgerBridge()

    if args.verify:
        metrics = bridge.verify_system()
        print("\n==================================================")
        print(" LKRGSER-BRIDGE SYSTEM VERIFICATION PROTOCOL")
        print("==================================================")
        print(f"Reality Level:    {metrics['reality_level']}")
        print(f"Status:           {metrics['status']}")
        print(f"Ethereum Block:   {metrics['ethereum_block']}")
        print(f"Verification SHA: {metrics['verification_hash']}")
        print(f"Latency:          {metrics['latency_ms']:.4f}ms")
        print(f"Native JIT Path:  {metrics['jit_path']}")
        print("==================================================\n")

        if metrics["reality_level"] == "C5-REAL":
            sys.exit(0)
        else:
            sys.exit(1)

    elif args.crystallize:
        target_path = Path(args.crystallize)
        if not target_path.exists():
            print(f"Error: Target file {target_path} does not exist.")
            sys.exit(2)

        with open(target_path, "rb") as f:
            content = f.read()

        hash_val, level = bridge.crystallize_content(content)
        print(f"File:           {target_path.name}")
        print(f"Reality Level:  {level}")
        print(f"SHA-256 Digest: {hash_val}")
        sys.exit(0)

    else:
        parser.print_help()
