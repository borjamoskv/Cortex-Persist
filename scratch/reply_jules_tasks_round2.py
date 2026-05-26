import base64
import json
import requests
import subprocess
import time


def get_keychain_token() -> str | None:
    try:
        out = subprocess.check_output(
            ["security", "find-generic-password", "-s", "jules-cli", "-a", "default", "-w"],
            text=True,
        ).strip()
        if out.startswith("go-keyring-base64:"):
            b64_part = out.split("go-keyring-base64:")[1]
            decoded = base64.b64decode(b64_part)
            token_data = json.loads(decoded.decode("utf-8"))
            return token_data.get("access_token")
    except Exception as e:
        print(f"Error getting keychain token: {e}")
    return None


def reply_tasks():
    token = get_keychain_token()
    if not token:
        print("Could not retrieve token.")
        return

    base = "https://aida.googleapis.com/v1/swebot"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    replies = {
        "781609244341062733": "Yes, please fix the test fixture in `test_p0_decoupling.py` to use `engine.init_db()` or handle the extension safely so the full test suite passes.",
        "13950756068036117908": "Por favor, enfócate en solucionar los fallos actuales en la suite de pruebas (como `test_ouroboros_forge.py` y `test_p0_decoupling.py`) y diseña pruebas adicionales robustas para asegurar la persistencia en `cortex/memory/manager.py`.",
        "2192151720868170616": "Please push your changes to origin, or open a PR so your branch can be merged. Once done, you can finalize the task.",
        "15130670999620354965": "Perfect. Please mark the task as failed or completed since it is cancelled.",
    }

    for tid, feedback in replies.items():
        print(f"\nSending reply to Task {tid}...")
        url = f"{base}/tasks/{tid}:interact"
        payload = {"userActivity": {"feedbackGiven": {"feedback": feedback}}}
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        if r.status_code == 200:
            print(f"-> SUCCESS: Replied to {tid}")
        else:
            print(f"-> FAILED: {r.status_code} - {r.text}")
        time.sleep(0.5)


if __name__ == "__main__":
    reply_tasks()
