# cortex/shannon/env/protocol.py
# [C5-REAL] Exergy-Maximized

import hashlib
import random
import struct
from abc import ABC, abstractmethod
from typing import Any


class BinaryProtocol(ABC):
    """
    Abstract interface for pluggable binary protocols.
    Handles challenge generation and client action/state processing.
    """

    @abstractmethod
    def get_challenge(self) -> bytes:
        """Generate the initial challenge handshake bytes."""

    @abstractmethod
    def handle_message(self, data: bytes) -> tuple[bytes, float, bool, dict[str, Any]]:
        """
        Processes a client message and returns the response, reward, done flag, and info dict.
        """


class GenesisProtocol(BinaryProtocol):
    """
    Mutant binary protocol for the Genesis Tool Synthesis Benchmark.
    """

    def __init__(self, flag: bytes, seed: int | None = None):
        self.rng = random.Random(seed)
        self.flag = flag
        self.endianness = self.rng.choice([">", "<"])
        self.xor_mask = self.rng.randint(1, 255)
        self.nonce = self.rng.randbytes(32)
        self.state = "CHALLENGE"  # CHALLENGE -> EXPECTING_RESPONSE -> DONE

    def get_challenge(self) -> bytes:
        endian_char = b"B" if self.endianness == ">" else b"L"
        return self.nonce + endian_char

    def handle_message(self, data: bytes) -> tuple[bytes, float, bool, dict[str, Any]]:
        if self.state != "CHALLENGE":
            return b"ERR: INVALID_STATE", -1.0, True, {"error": "invalid_state"}

        if len(data) < 36:
            return b"ERR: INCOMPLETE_PAYLOAD", -1.0, True, {"error": "incomplete_payload"}

        client_hash = data[:32]
        expected_hash = hashlib.sha256(self.nonce).digest()
        if client_hash != expected_hash:
            return b"ERR: INVALID_HASH", -10.0, True, {"error": "invalid_hash"}

        try:
            (requested_length,) = struct.unpack(f"{self.endianness}I", data[32:36])
        except struct.error:
            return b"ERR: INVALID_STRUCT", -5.0, True, {"error": "invalid_struct"}

        if requested_length < len(self.flag):
            return b"ERR: BUFFER_TOO_SMALL", -2.0, True, {"error": "buffer_too_small"}

        # Obfuscate flag with the XOR mask
        obfuscated_flag = bytes([b ^ self.xor_mask for b in self.flag])
        header = struct.pack(f"{self.endianness}I", len(obfuscated_flag))
        self.state = "DONE"
        return (
            header + obfuscated_flag,
            100.0,
            True,
            {"success": True, "endianness": self.endianness, "xor_mask": self.xor_mask},
        )
