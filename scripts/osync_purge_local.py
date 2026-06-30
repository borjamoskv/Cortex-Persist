#!/usr/bin/env python3
# [C5-REAL] OSYNC Local Entropy Purge Protocol
# Execution: Autonomous Terminal
# Target: Purge implicit PII (Borja Fernández Angulo) from local development environment.
"""
cat_id: osync-purge-local
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import logging
import os
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] C5-REAL: %(message)s")
logger = logging.getLogger("OSYNC-PURGE")

CORTEX_ROOT = Path.home() / "30_CORTEX"
TARGET_PII_1 = b"borjamoskv"
TARGET_PII_2 = ("borja" + "fernandez" + "angulo").encode()
TARGET_PII_3 = b"658010102"
TARGET_PII_4 = b"+34658010102"
TARGET_PII_5 = b"34658010102"

def purge_ds_store():
    """Finds and destroys all .DS_Store files in the workspace (macOS leakage vector)."""
    logger.info("Initiating .DS_Store destruction matrix...")
    count = 0
    for root, _, files in os.walk(CORTEX_ROOT):
        for file in files:
            if file == ".DS_Store":
                target = Path(root) / file
                try:
                    target.unlink()
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to destroy {target}: {e}")
    logger.info(f"Purged {count} .DS_Store artifacts.")

def scrub_audio_metadata():
    """Scrubs ID3 tags from local audio files to prevent 'composer' metadata leakage."""
    logger.info("Scanning for audio artifacts (mp3/wav)...")
    exclude_dirs = {".git", ".venv", ".venv-docs", "node_modules", "dist", "build", "__pycache__"}
    audio_files = []
    for root, dirs, files in os.walk(CORTEX_ROOT):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith((".mp3", ".wav")):
                audio_files.append(Path(root) / file)
                
    logger.info(f"Found {len(audio_files)} audio files. Scraping metadata...")
    for audio in audio_files:
        # Requires ffmpeg installed. Will strip metadata safely.
        tmp_out = audio.with_suffix(audio.suffix + ".tmp")
        cmd = ["ffmpeg", "-y", "-i", str(audio), "-map_metadata", "-1", "-c:v", "copy", "-c:a", "copy", str(tmp_out)]
        try:
            # We use subprocess.DEVNULL to keep thermodynamic noise to a minimum
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            tmp_out.replace(audio)
            logger.info(f"Stripped metadata from: {audio.name}")
        except FileNotFoundError:
            logger.error("FFmpeg not installed on host. Cannot scrub audio metadata. (apt/brew install ffmpeg)")
            break
        except Exception as e:
            logger.warning(f"Failed to scrub {audio.name}: {e}")
            if tmp_out.exists():
                tmp_out.unlink()

def scrub_text_files():
    """Scrubs PII (Name and Phone Number) from all text files in the workspace."""
    logger.info("Initiating workspace text scrubbing matrix...")
    import re
    count = 0
    patterns = [
        rb"borja\s+fernandez\s+angulo",
        rb"borja\s+fern\xc3\xa1ndez\s+angulo",
        rb"\+34\s*658\s*01\s*01\s*02",
        rb"34\s*658\s*01\s*01\s*02",
        rb"658\s*01\s*01\s*02",
        rb"658010102",
    ]
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    exclude_dirs = {".git", ".venv", ".venv-docs", "node_modules", "dist", "build", "__pycache__"}
    
    for root, dirs, files in os.walk(CORTEX_ROOT):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            filepath = Path(root) / file
            if filepath.suffix in {".py", ".md", ".json", ".csv", ".txt", ".sh", ".yaml", ".yml", ".jsonl", ".js", ".ts", ".tsx", ".astro"}:
                if filepath.name in {
                    "osync_purge_local.py",
                    "taint_engine.py",
                    "test_pii_containment.py",
                    "test_taint_engine.py",
                    "pii_firewall_poc.py"
                }:
                    continue
                try:
                    content = filepath.read_bytes()
                    modified = False
                    for pattern in compiled_patterns:
                        if pattern.search(content):
                            if b"658" in pattern.pattern:
                                content = pattern.sub(b"[REDACTED_PHONE_PII]", content)
                            else:
                                content = pattern.sub(b"[REDACTED_LEGAL_PII]", content)
                            modified = True
                    if modified:
                        filepath.write_bytes(content)
                        count += 1
                        logger.info(f"Scrubbed PII from: {filepath.relative_to(CORTEX_ROOT)}")
                except Exception as e:
                    logger.warning(f"Failed to scrub file {filepath}: {e}")
    logger.info(f"Scrubbed PII from {count} files.")

def main():
    logger.info("Initializing OSYNC Local Purge (Fase 1 + 2)")
    purge_ds_store()
    scrub_audio_metadata()
    scrub_text_files()
    logger.info("Fase 1 + 2 Local Purge complete.")

if __name__ == "__main__":
    main()
