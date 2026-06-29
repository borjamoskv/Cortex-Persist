# [C5-REAL] Exergy-Maximized
"""
Forensic Import Resolution Ledger for BABYLON-60.
Logs module resolution events at import-time with process-safe locking (fcntl)
and cryptographic verification (SHA-256 hash-chaining + Ed25519 signatures).
Conforms to BABYLON60-NATIVE-AI-MANIFESTO (Axiom Ω3).
"""

import os
import sys
import json
import time
import uuid
import fcntl
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

class ImportResolutionLedger:
    """
    Process-safe, cryptographically signed ledger for recording import resolutions.
    Maintains a tamper-evident global hash chain across concurrent processes.
    """
    def __init__(self, filepath: str = None):
        if filepath:
            self.filepath = Path(filepath)
        else:
            project_root = Path(__file__).resolve().parent.parent
            self.filepath = project_root / "import_resolution_ledger.jsonl"
            
        self.session_id = str(uuid.uuid4())
        self.pid = os.getpid()

        # Generate session keys for cryptographic traceability
        self._private_key = ed25519.Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        self.public_key_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

    def _write_entry(self, entry: dict):
        """Appends an entry to the JSONL ledger file using process-exclusive locking and hash chaining."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Open in read/write/append mode to acquire a lock and read the last hash
            with open(self.filepath, "a+", encoding="utf-8") as f:
                try:
                    fcntl.flock(f, fcntl.LOCK_EX)
                    
                    # Read the last line to link the cryptographic chain
                    f.seek(0)
                    lines = f.readlines()
                    non_empty = [l.strip() for l in lines if l.strip()]
                    
                    if non_empty:
                        try:
                            last_entry = json.loads(non_empty[-1])
                            prev_hash = last_entry.get("entry_hash", "GENESIS")
                        except Exception:
                            prev_hash = "GENESIS"
                    else:
                        prev_hash = "GENESIS"

                    # Populate chain references
                    entry["prev_hash"] = prev_hash
                    
                    # Compute entry hash based on content and prev_hash
                    payload = f"{entry['timestamp']}|{entry['event']}|{entry['session_id']}|{entry['pid']}|{prev_hash}"
                    if entry["event"] == "RESOLUTION":
                        payload += f"|{entry.get('caller')}|{entry.get('source')}|{entry.get('type')}|{entry.get('target')}"
                    elif entry["event"] == "SESSION_START":
                        payload += f"|{entry.get('public_key_pem')}"
                    
                    entry_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                    entry["entry_hash"] = entry_hash

                    # If ending the session, sign the final accumulated hash
                    if entry["event"] == "SESSION_END":
                        signature = self._private_key.sign(prev_hash.encode("utf-8")).hex()
                        entry["signature"] = signature
                        # Recalculate hash with signature for absolute integrity
                        payload_end = f"{payload}|{signature}"
                        entry["entry_hash"] = hashlib.sha256(payload_end.encode("utf-8")).hexdigest()

                    # Write to file
                    f.seek(0, 2)  # Ensure we are at the end
                    f.write(json.dumps(entry) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        except IOError as e:
            sys.stderr.write(f"\n[LEDGER ERROR] Failed to write import ledger: {e}\n")
            sys.stderr.flush()

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def start_session(self):
        """Logs the start of a tracing session with environment metadata and public key."""
        entry = {
            "timestamp": self._timestamp(),
            "event": "SESSION_START",
            "session_id": self.session_id,
            "pid": self.pid,
            "public_key_pem": self.public_key_pem,
            "metadata": {
                "python_version": sys.version,
                "os": sys.platform,
                "cwd": os.getcwd()
            }
        }
        self._write_entry(entry)

    def log_resolution(self, caller: str, source: str, resolution_type: str, target: str):
        """Logs a single import resolution decision."""
        entry = {
            "timestamp": self._timestamp(),
            "event": "RESOLUTION",
            "session_id": self.session_id,
            "pid": self.pid,
            "caller": caller,
            "source": source,
            "type": resolution_type,
            "target": target
        }
        self._write_entry(entry)

    def end_session(self):
        """Logs the completion of a tracing session and signs the state accumulator."""
        entry = {
            "timestamp": self._timestamp(),
            "event": "SESSION_END",
            "session_id": self.session_id,
            "pid": self.pid
        }
        self._write_entry(entry)

    @classmethod
    def verify_ledger(cls, filepath: str) -> dict:
        """
        Verifies the integrity of the import resolution ledger file.
        Ensures all hashes match their payloads and session signatures are valid.
        """
        path = Path(filepath)
        if not path.exists():
            return {"status": "failed", "reason": "file_not_found"}

        session_keys = {}
        expected_prev_hash = "GENESIS"
        line_num = 0

        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line_num += 1
                    if not line.strip():
                        continue
                    
                    entry = json.loads(line)
                    event = entry.get("event")
                    session_id = entry.get("session_id")
                    pid = entry.get("pid")
                    timestamp = entry.get("timestamp")
                    prev_hash = entry.get("prev_hash")
                    entry_hash = entry.get("entry_hash")

                    if prev_hash != expected_prev_hash:
                        return {
                            "status": "failed",
                            "line": line_num,
                            "reason": f"hash_chain_broken: expected {expected_prev_hash}, got {prev_hash}"
                        }

                    # Reconstruct expected hash
                    payload = f"{timestamp}|{event}|{session_id}|{pid}|{prev_hash}"
                    
                    if event == "SESSION_START":
                        pub_pem = entry.get("public_key_pem")
                        session_keys[session_id] = serialization.load_pem_public_key(pub_pem.encode("utf-8"))
                        payload += f"|{pub_pem}"
                        recomputed = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                        
                    elif event == "RESOLUTION":
                        payload += f"|{entry.get('caller')}|{entry.get('source')}|{entry.get('type')}|{entry.get('target')}"
                        recomputed = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                        
                    elif event == "SESSION_END":
                        signature = entry.get("signature")
                        pub_key = session_keys.get(session_id)
                        if not pub_key:
                            return {"status": "failed", "line": line_num, "reason": "session_key_not_found"}
                        
                        try:
                            pub_key.verify(bytes.fromhex(signature), prev_hash.encode("utf-8"))
                        except InvalidSignature:
                            return {"status": "failed", "line": line_num, "reason": "invalid_session_signature"}
                        
                        payload_end = f"{payload}|{signature}"
                        recomputed = hashlib.sha256(payload_end.encode("utf-8")).hexdigest()
                    else:
                        return {"status": "failed", "line": line_num, "reason": f"unknown_event: {event}"}

                    if recomputed != entry_hash:
                        return {"status": "failed", "line": line_num, "reason": "entry_hash_mismatch"}

                    expected_prev_hash = entry_hash
        except Exception as e:
            return {"status": "failed", "reason": f"exception_during_verification: {e}"}

        return {"status": "verified", "total_lines": line_num}
