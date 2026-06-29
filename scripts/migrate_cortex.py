# [C5-REAL] Exergy-Maximized
"""
cat_id: migrate-cortex
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import os
import shutil
import subprocess


def is_tracked(path):
    return subprocess.run(["git", "ls-files", "--error-unmatch", path], capture_output=True).returncode == 0

def move(src, dst):
    if os.path.exists(dst) and os.path.isdir(dst):
        for item in os.listdir(src):
            if item == "__pycache__": continue
            move(os.path.join(src, item), os.path.join(dst, item))
    else:
        print(f"Moving {src} -> {dst}")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if is_tracked(src):
            subprocess.run(["git", "mv", src, dst], check=True)
        else:
            shutil.move(src, dst)

for item in os.listdir("cortex"):
    if item in ["__init__.py", "__pycache__"]:
        continue
    move(os.path.join("cortex", item), os.path.join("babylon60", item))
