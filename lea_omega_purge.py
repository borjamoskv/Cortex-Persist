import shutil
from pathlib import Path

# C5-REAL LEA-Ω Purge Protocol
# Destroys all files in scratch/ directories of past conversations.

BRAIN_DIR = Path("/Users/borjafernandezangulo/.gemini/antigravity/brain")
EXCLUDED_CONVERSATION_IDS = {
    "d1cf3b0e-795d-431e-9b1b-16a850263b53",  # Active Antigravity session
    "d3c86edd-a327-4422-8b1c-6fcf4beb7f29",  # User-specified active session
}


def purge_scratch_entropy():
    print(f"[LEA-Ω] Initiating strict entropy purge in {BRAIN_DIR}...")
    scratch_dirs = list(BRAIN_DIR.rglob("scratch"))

    total_files_deleted = 0
    total_bytes_freed = 0

    for scratch_dir in scratch_dirs:
        if any(exc_id in str(scratch_dir) for exc_id in EXCLUDED_CONVERSATION_IDS):
            print(f"[SKIP] Bypassing active session: {scratch_dir}")
            continue

        for item in scratch_dir.iterdir():
            if item.is_file() or item.is_symlink():
                size = item.stat().st_size
                total_bytes_freed += size
                total_files_deleted += 1
                item.unlink()
            elif item.is_dir():
                # calculate size
                for subitem in item.rglob("*"):
                    if subitem.is_file() or subitem.is_symlink():
                        total_bytes_freed += subitem.stat().st_size
                        total_files_deleted += 1
                shutil.rmtree(item)

    freed_mb = total_bytes_freed / (1024 * 1024)
    print("\n[LEA-Ω] PURGE COMPLETE")
    print("Status: C5-REAL (Annihilation Confirmed)")
    print(f"Tokens/Files Destroyed: {total_files_deleted}")
    print(f"Entropy Cleared: {freed_mb:.2f} MB")


if __name__ == "__main__":
    purge_scratch_entropy()
