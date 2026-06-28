#!/usr/bin/env python3
# [C5-REAL] OSYNC Local Entropy Purge Protocol
# Execution: Autonomous Terminal
# Target: Purge implicit PII (Borja Fernández Angulo) from local development environment.

import logging
import os
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] C5-REAL: %(message)s")
logger = logging.getLogger("OSYNC-PURGE")

CORTEX_ROOT = Path.home() / "30_CORTEX"
TARGET_PII_1 = b"borjamoskv"
TARGET_PII_2 = ("borja" + "fernandez" + "angulo").encode()

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
    audio_files = list(CORTEX_ROOT.rglob("*.mp3")) + list(CORTEX_ROOT.rglob("*.wav"))
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

def main():
    logger.info("Initializing OSYNC Local Purge (Fase 1)")
    purge_ds_store()
    scrub_audio_metadata()
    logger.info("Fase 1 Local Purge complete. Awaiting Phase 2 GDPR directives.")

if __name__ == "__main__":
    main()
