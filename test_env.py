import subprocess, sys, os
from pathlib import Path
tmp_path = Path("/tmp/test_env")
tmp_path.mkdir(exist_ok=True)
blocked = ["aiofiles", "aiohttp", "bs4", "arq", "email_validator", "watchdog", "yaml", "pythonosc", "radon", "neo4j", "prometheus_client"]
sitecustomize = tmp_path / "sitecustomize.py"
sitecustomize.write_text(
    "\n".join(
        [
            "import builtins",
            "import os",
            "import sys",
            "",
            "_real_import = builtins.__import__",
            f"_blocked_prefixes = {tuple(blocked)!r}",
            "def _blocked(name, globals=None, locals=None, fromlist=(), level=0):",
            "    for prefix in _blocked_prefixes:",
            "        if name == prefix or name.startswith(prefix + '.'):",
            "            raise ImportError(f'{prefix} blocked by test harness')",
            "    return _real_import(name, globals, locals, fromlist, level)",
            "builtins.__import__ = _blocked",
        ]
    ),
    encoding="utf-8",
)
env = os.environ.copy()
env["PYTHONPATH"] = str(tmp_path)
env["CORTEX_NO_EMBED"] = "1"
env["CORTEX_LLM_PROVIDER"] = ""
env["CORTEX_MASTER_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
env["CORTEX_TESTING"] = "1"
for k in ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
    env.pop(k, None)

result = subprocess.run([sys.executable, "-m", "cortex", "--version"], capture_output=True, text=True, env=env)
print("OUT:", result.stdout)
print("ERR:", result.stderr)
