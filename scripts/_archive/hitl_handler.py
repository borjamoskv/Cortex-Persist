import time
import json
import hashlib
import subprocess
from datetime import datetime

# CORTEX-PERSIST: Asynchronous HITL Handler
# Sovereign Authorization via Ledger Polling & macOS Notifications

class HITLHandler:
    def __init__(self, program_id, poll_interval=5):
        self.program_id = program_id
        self.poll_interval = poll_interval
        try:
            from db import record_memory_event, query_events_native
            self.record_event = record_memory_event
            self.query_events = query_events_native
        except ImportError:
            print("[!] HITLHandler: DB logic missing. Falling back to CLI.")
            self.record_event = None

    def request_approval(self, prompt, evidence):
        """
        Registers an authorization request and waits for a response.
        """
        request_id = f"hitl_{hashlib.sha256((prompt + str(time.time())).encode()).hexdigest()[:8]}"
        
        print(f"\n[HITL-AUTH-REQUIRED] {request_id}")
        print(f"Program: {self.program_id}")
        print(f"Action:  {prompt}")
        print(f"Evidence: {evidence}")

        # 1. Record the request in the Sovereign Ledger
        if self.record_event:
            metadata = {
                "program_id": self.program_id,
                "evidence": evidence,
                "status": "pending",
                "requested_at": datetime.utcnow().isoformat() + "Z"
            }
            self.record_event("hitl_request", prompt, request_id, metadata)
            
            # 2. Trigger macOS Notification (High Visibility)
            self._trigger_macos_notification(prompt)
            
            # 3. Enter Polling Loop (Async/Headless)
            return self._wait_for_response(request_id)
        else:
            # Fallback to CLI if DB is detached
            return self._cli_fallback(prompt)

    def _trigger_macos_notification(self, prompt):
        """Sends a native macOS notification."""
        msg = f"CORTEX Auth Required: {self.program_id}"
        cmd = f'display notification "{prompt}" with title "{msg}" subtitle "Waiting for Human Sign-off..." sound name "Glass"'
        subprocess.run(["osascript", "-e", cmd])

    def _wait_for_response(self, request_id):
        """Polls the ledger for a hitl_response matching the request_id."""
        print(f"[HITL-POLL] Waiting for Dashboard Approval (ID: {request_id})...")
        start_time = time.time()
        timeout = 86400 # 24 hours
        
        while time.time() - start_time < timeout:
            responses = self.query_events("hitl_response", 10)
            for resp in responses:
                meta = json.loads(resp["metadata_json"])
                if meta.get("request_id") == request_id:
                    action = meta.get("action")
                    if action == "APPROVE":
                        print(f"\n[HITL-OK] Authorization SIGNED by {meta.get('signer')}")
                        return True
                    elif action == "REJECT":
                        print(f"\n[HITL-HALT] Authorization DENIED by {meta.get('signer')}")
                        return False
            
            time.sleep(self.poll_interval)
            
        print("[HITL-TIMEOUT] Authorization request expired.")
        return False

    def _cli_fallback(self, prompt):
        # Foundation CLI fallback for development
        val = input(f"\n[HITL] {prompt} (APPROVE/KILL): ").strip().upper()
        return val == "APPROVE"

if __name__ == "__main__":
    # Test execution
    handler = HITLHandler("test-program")
    # This will wait until someone (or we manually) records a response in the ledger
    print("Test run initiating... (Waiting for manual DB injection or timeout)")
    handler.request_approval("Authorize Test Action", "Test evidence of critical bug")
