import base64
import json
import requests
import subprocess


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
        "15130670999620354965": "Okay, thank you. You can finish the task.",
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


if __name__ == "__main__":
    reply_tasks()
