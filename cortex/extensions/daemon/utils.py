# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger("cortex.extensions.daemon.utils")

MAILTV_DIR = Path.home() / ".cortex" / "mailtv"
TOKEN_PATH = MAILTV_DIR / "token.json"


def _atomic_write_text(path: Path, content: str, mode: int = 0o600) -> None:
    """Persist sensitive text atomically with restrictive permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        dir=str(path.parent),
        delete=False,
        encoding="utf-8",
    ) as tmp_file:
        tmp_file.write(content)
        tmp_path = Path(tmp_file.name)
    os.chmod(tmp_path, mode)
    tmp_path.replace(path)


async def speak(state, text: str, voice: str = "Jorge", rate: int = 140):
    if state.daemons.get("mute", False):
        return
    try:
        entropy = state.daemons.get("cortex", {}).get("tech_debt", 0)
        if entropy > 85:
            rate = 95
            text = f"Ejem... oye... {text}"
        await asyncio.create_subprocess_exec("say", "-v", voice, "-r", str(rate), text)
        logger.debug("SPEAK (%s/%s): %s", voice, rate, text)
    except OSError as e:
        logger.error("Speak error: %s", e)


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
    except OSError:
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
                _atomic_write_text(TOKEN_PATH, creds.to_json())
            except (OSError, ValueError) as exc:
                logger.warning("Gmail token refresh failed: %s", exc)
                return None
        return creds
    return None


def get_gmail_service():
    creds = get_gmail_credentials()
    if not creds:
        return None
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=creds)
