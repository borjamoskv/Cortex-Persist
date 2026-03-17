from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from collections.abc import Callable

# Standard library fallback since protobuf might need to be generated via protoc
# In pure O(1) spirit, if we don't compile intent_pb2, we can just use length-prefixed struct packing.
# But for the BCI, we'll emulate the byte-level buffer here without the heavy protoc dependency for now.

SOCKET_PATH = "/tmp/cortex_bci.sock"


class SovereignIntentError(Exception):
    pass


class BCI_Daemon:
    """
    The Bytecode Intent Receiver.
    Listens on a Unix socket for pure binary intentions from the CORTEX Agent.
    No conversational parsing. Absolute execution.
    """

    def __init__(self, action_handlers: dict[int, Callable]):
        self.action_handlers = action_handlers
        self.server = None

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        __ = writer.get_extra_info("peername")
        try:
            # 1. Read header length (4 bytes)
            header_bytes = await reader.readexactly(4)
            payload_len = int.from_bytes(header_bytes, byteorder="big")

            # 2. Read the raw payload buffer
            payload_buffer = await reader.readexactly(payload_len)

            # 3. Quick hash check (last 32 bytes or similar depending on spec) -> Simplified to JSON dict logic here for bootstrap
            data = json.loads(payload_buffer.decode("utf-8"))

            # Verify integrity
            expected_hash = data.get("integrity_hash")
            derivation = data.get("derivation", "UNKNOWN")
            action = data.get("action", 0)
            instruction = data.get("instruction", "")
            raw_cargo = data.get(
                "payload", ""
            )  # In actual BCI, this would be raw bytes. Here we encode via b64 or text

            test_str = f"{derivation}:{action}:{instruction}:{raw_cargo}".encode()
            calculated_hash = hashlib.sha256(test_str).hexdigest()

            if expected_hash and calculated_hash != expected_hash:
                raise SovereignIntentError(
                    f"Integrity compromise (Hash mismatch) -> Expected: {expected_hash} | Got: {calculated_hash}"
                )

            # 4. Route to executing logic (Babestu integration point)
            print(f"[BCI] ⚡ INTENT RECEIVED | Action: {action} | Derivation: {derivation}")
            if action in self.action_handlers:
                await self.action_handlers[action](instruction, raw_cargo)
                writer.write(b"\x01")  # ACK
            else:
                print(f"[BCI] ⚠️ Unknown action: {action}")
                writer.write(b"\x00")  # NACK

            await writer.drain()

        except asyncio.IncompleteReadError:
            print("[BCI] ❌ Byte buffer terminated unexpectedly.")
        except Exception as e:  # noqa: BLE001
            print(f"[BCI] ❌ Error processing intent: {e}")
            writer.write(b"\x00")
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self):
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

        self.server = await asyncio.start_unix_server(self._handle_client, path=SOCKET_PATH)
        # Apply restrictive permissions to the socket
        os.chmod(SOCKET_PATH, 0o600)

        print(f"[BCI] 🚀 ZERO-LATENCY UNIX SOCKET ESTABLISHED AT {SOCKET_PATH}")
        print("[BCI] Listening for binary intent. No words. No entropy.")

        async with self.server:
            await self.server.serve_forever()


class BCI_Transmitter:
    """
    The Agent-side Client to inject Intent directly into the Daemon, bypassing the IDE terminal.
    """

    @staticmethod
    async def send_intent(derivation: str, action: int, instruction: str, payload: str):
        test_str = f"{derivation}:{action}:{instruction}:{payload}".encode()
        calculated_hash = hashlib.sha256(test_str).hexdigest()

        packet = {
            "derivation": derivation,
            "action": action,
            "instruction": instruction,
            "payload": payload,
            "integrity_hash": calculated_hash,
            "timestamp": int(time.time()),
        }

        # Encode to bytes
        buffer = json.dumps(packet).encode("utf-8")
        payload_len = len(buffer)

        # 4 bytes size header + buffer
        transmission = payload_len.to_bytes(4, byteorder="big") + buffer

        try:
            reader, writer = await asyncio.open_unix_connection(SOCKET_PATH)
            writer.write(transmission)
            await writer.drain()

            response = await reader.read(1)
            if response == b"\x01":
                return True
            else:
                return False

        except Exception as e:  # noqa: BLE001
            print(f"[BCI-CLIENT] Failed to inject intent: {e}")
            return False
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except UnboundLocalError:
                pass


# -----------------------
# TESTING SCAFFOLDING
# -----------------------
async def mock_handler(instruction: str, payload: str):
    """Simulates Babestu or Cortex execution."""
    print(f"      -> Running instruction [{instruction}]")
    print(f"      -> Payload size: {len(payload)} bytes")
    print(f"      -> Content chunk: {payload[:50]}...")
    await asyncio.sleep(0.1)


async def test_bci():
    handlers = {
        1: mock_handler,  # 1: EDIT_FILE
        2: mock_handler,  # 2: RUN_COMMAND
    }

    daemon = BCI_Daemon(handlers)
    task = asyncio.create_task(daemon.start())

    # Let server boot
    await asyncio.sleep(0.5)

    # Inject intent bypass
    print("\n--- INJECTING INTENT 0x01 ---")
    await BCI_Transmitter.send_intent(
        derivation="Ω₂ (Entropic Asymmetry)",
        action=1,
        instruction="cortex.file.update",
        payload="def fast_func(): return O(1)",
    )

    print("\n--- INJECTING INTENT 0x02 ---")
    await BCI_Transmitter.send_intent(
        derivation="Ω₅ (Antifragile)",
        action=2,
        instruction="bash.run",
        payload="rustc optimizer.rs -O3",
    )

    task.cancel()


if __name__ == "__main__":
    asyncio.run(test_bci())
