"""
Generate CORTEX API Key directly via AuthManager.
"""

import os
import stat

from cortex.auth import AuthManager

# Ensure we use the default DB path
DB_PATH = os.path.expanduser("~/.cortex/cortex.db")


def generate_key():
    print(f"📂 Opening CORTEX DB at: {DB_PATH}")
    auth = AuthManager(DB_PATH)

    # Create a key with admin permissions
    name = "god_mode_swarn"
    print(f"🔑 Generating key for: {name}")

    try:
        raw_key, api_key = auth.create_key(name=name, permissions=["read", "write", "admin"])
        print("\n✅ API KEY GENERATED SUCCESSFULLY:")
        print(f"Prefix: {api_key.key_prefix}")
        print(f"Permissions: {api_key.permissions}")

        # Save to .env in moskv-swarm for convenience (restricted permissions)
        env_path = os.path.expanduser("~/game/moskv-swarm/.env")
        fd = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "a") as f:
            f.write(f"\n# Added by God Mode Setup\nCORTEX_API_KEY={raw_key}\n")
        print(f"\n💾 Appended to {env_path} (mode 0600)")

    except (RuntimeError, ValueError, OSError) as e:
        print(f"\n❌ Error generating key: {type(e).__name__}")


if __name__ == "__main__":
    generate_key()
