# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

import asyncio
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("cortex.daemon.utils")

MAILTV_DIR = Path.home() / ".cortex" / "mailtv"
TOKEN_PATH = MAILTV_DIR / "token.json"


async def speak(state, text: str, voice: str = "Jorge", rate: int = 140):
    if state.daemons.get("mute", False):
        return
    try:
        entropy = state.daemons.get("cortex", {}).get("tech_debt", 0)
        if entropy > 85:
            rate = 95
            text = f"Ejem... oye... {text}"
        await asyncio.create_subprocess_exec("say", "-v", voice, "-r", str(rate), text)
        print(f"SPEAK ({voice}/{rate}): {text}")
    except Exception as e:
        print(f"Speak error: {e}")


async def play_ping(state):
    if state.daemons.get("mute", False):
        return
    try:
        proc = await asyncio.create_subprocess_exec(
            "afplay",
            "/System/Library/Sounds/Tink.aiff",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        await proc.wait()
    except Exception:
        pass


async def run_osascript(script: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "osascript", "-e", script, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()


def get_gmail_credentials():
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2.credentials import Credentials

    scopes = ["https://mail.google.com/"]
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), scopes)
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleRequest())

                with open(TOKEN_PATH, "w") as token:
                    token.write(creds.to_json())
            except Exception:
                return None
        return creds
    return None


def get_gmail_service():
    creds = get_gmail_credentials()
    if not creds:
        return None
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=creds)
