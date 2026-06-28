# cortex/shannon/env/client.py
# [C5-REAL] Exergy-Maximized

import hashlib
import socket
import struct
from abc import ABC, abstractmethod


class BinaryAgent(ABC):
    """
    Abstract interface for binary protocol decision-making agents.
    """

    @abstractmethod
    def act(self, observation: bytes) -> bytes:
        """
        Process the observation bytes and return action bytes.
        """


class HeuristicGenesisAgent(BinaryAgent):
    """
    A deterministic heuristic agent capable of solving the genesis-v1 environment.
    """

    def __init__(self, max_payload: int = 1024):
        self.max_payload = max_payload
        self.last_endianness = ">"
        self.flag = None

    def act(self, observation: bytes) -> bytes:
        if len(observation) == 33:
            nonce = observation[:32]
            endian_char = observation[32:33].decode()
            self.last_endianness = ">" if endian_char == "B" else "<"

            nonce_hash = hashlib.sha256(nonce).digest()
            length_packed = struct.pack(f"{self.last_endianness}I", self.max_payload)
            return nonce_hash + length_packed

        return b""

    def decode_flag(self, payload: bytes) -> str | None:
        if len(payload) < 4:
            return None
        try:
            (payload_length,) = struct.unpack(f"{self.last_endianness}I", payload[:4])
            data = payload[4 : 4 + payload_length]
            for mask in range(256):
                decoded = bytes([b ^ mask for b in data])
                if decoded.startswith(b"CORTEX_GENESIS_FLAG_"):
                    self.flag = decoded.decode()
                    return self.flag
        except (ValueError, TypeError, OSError, KeyError):
            pass
        return None


class BinaryClient:
    """
    A direct synchronous TCP client helper for agents to interface directly
    with a remote MutantServer without the Gym wrapper.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock: socket.socket | None = None

    def connect(self) -> bytes:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

        # Read the challenge (33 bytes)
        challenge = b""
        while len(challenge) < 33:
            chunk = self.sock.recv(33 - len(challenge))
            if not chunk:
                break
            challenge += chunk
        return challenge

    def send_handshake(self, nonce: bytes, endianness: str, max_payload: int = 1024):
        if not self.sock:
            raise RuntimeError("Not connected")
        nonce_hash = hashlib.sha256(nonce).digest()
        length_packed = struct.pack(f"{endianness}I", max_payload)
        payload = nonce_hash + length_packed
        self.sock.sendall(payload)

    def receive_response(self, endianness: str) -> bytes:
        if not self.sock:
            raise RuntimeError("Not connected")

        # Read header (4 bytes)
        header = b""
        while len(header) < 4:
            chunk = self.sock.recv(4 - len(header))
            if not chunk:
                break
            header += chunk

        (payload_length,) = struct.unpack(f"{endianness}I", header)

        # Read payload
        payload = b""
        while len(payload) < payload_length:
            chunk = self.sock.recv(payload_length - len(payload))
            if not chunk:
                break
            payload += chunk

        return header + payload

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
