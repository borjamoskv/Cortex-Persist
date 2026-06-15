#!/usr/bin/env python3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"

def main():
    if not ENV_PATH.exists():
        print(f"Error: {ENV_PATH} not found.")
        return

    print("Parsing .env file...")
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    env_vars = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            # Strip quotes if present
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            env_vars[key] = val

    for key, val in env_vars.items():
        print(f"Injecting {key} into Vercel...")
        for env in ["production", "preview", "development"]:
            # Run vercel env add using subprocess and stdin
            cmd = ["vercel", "env", "add", key, env, "--yes", "--force"]
            try:
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = proc.communicate(input=val)
                if proc.returncode != 0:
                    print(f"  [!] Failed to add {key} to {env}: {stderr.strip()}")
                else:
                    print(f"  ✓ Added {key} to {env}")
            except Exception as e:
                print(f"  [!] Exception adding {key}: {e}")

if __name__ == "__main__":
    main()
