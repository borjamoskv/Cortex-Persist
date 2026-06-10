import shutil
from pathlib import Path

# C5-REAL LEA-Ω Purge Protocol
# Destroys all files in scratch/ directories of past conversations.

BRAIN_DIR = Path("/Users/borjafernandezangulo/.gemini/antigravity/brain")
CURRENT_CONVERSATION_ID = "06010fc6-136b-4da2-9395-e750fd30f4c1"


def purge_scratch_entropy():
    print(f"[LEA-Ω] Initiating strict entropy purge in {BRAIN_DIR}...")
    scratch_dirs = list(BRAIN_DIR.rglob("scratch"))

    total_files_deleted = 0
    total_bytes_freed = 0

    for scratch_dir in scratch_dirs:
        if CURRENT_CONVERSATION_ID in str(scratch_dir):
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
