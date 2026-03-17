# Cross-Platform Architecture

CORTEX runs natively on **macOS, Linux, and Windows** without Docker. This guide covers the platform abstraction layer that makes this possible.

---

## The `cortex.platform.sys` Module

All OS-dependent code is routed through a single abstraction layer. Direct OS checks scattered across the codebase are **prohibited**.

```python
from cortex.platform.sys import (
    is_macos, is_linux, is_windows,
    platform_name,
    get_cortex_dir, get_service_dir, get_python_executable,
    tail_file_command,
)
```

| Function | Returns |
|:---|:---|
| `is_macos()` | `True` on Darwin |
| `is_linux()` | `True` on Linux |
| `is_windows()` | `True` on Win32 |
| `platform_name()` | Human-readable: `"macOS"`, `"Linux"`, `"Windows"` |
| `get_cortex_dir()` | `~/.cortex` (Unix) or `%APPDATA%/cortex` (Windows) |
| `get_service_dir()` | `~/Library/LaunchAgents` (macOS), `~/.config/systemd/user` (Linux), `None` (Windows) |
| `get_python_executable()` | `sys.executable` — no hardcoded paths |
| `tail_file_command(path)` | `['tail', '-f', path]` (Unix) or `['powershell', 'Get-Content', path, '-Wait']` (Windows) |

**Dynamic executables**: Instead of hardcoding paths like `/Users/.../bin/python`, the architecture uses `get_python_executable()` (or `sys.executable`) to ensure daemons and subshells spawn using the correct Python binary regardless of install location.

---

## Native Notifications

The Notifier component (`cortex/daemon/notifier.py`) uses adaptive dispatch for system-native alerts:

| Platform | Method | Integration |
|:---|:---|:---|
| **macOS** | `osascript` | Notification Center |
| **Linux** | `notify-send` | libnotify |
| **Windows** | PowerShell | `System.Windows.Forms.NotifyIcon` (balloon tip) |
| **Fallback** | Logger | `INFO`/`WARNING` if no UI session |

---

## Daemons & Service Managers

The CLI command `moskv-daemon install` supports three system orchestrators, injecting CORTEX as a background service that starts automatically on boot:

### macOS — launchd

Creates a persistent `.plist` agent in `~/Library/LaunchAgents/`:

```bash
moskv-daemon install
# → Created ~/Library/LaunchAgents/com.cortex.daemon.plist
# → Loaded via launchctl
```

### Linux — systemd

Creates a user-level systemd unit in `~/.config/systemd/user/` — **no sudo required**:

```bash
moskv-daemon install
# → Created cortex-daemon.service
# → Enabled and started via systemctl --user
```

### Windows — Task Scheduler

Registers a Task Scheduler entry with `ONLOGON` trigger:

```powershell
moskv-daemon install
# → Registered scheduled task "CORTEX Daemon"
# → Runs on user login
```

Unified status checking across all platforms:

```bash
moskv-daemon status          # Rich table output
moskv-daemon status --json   # Machine-readable JSON
```

---

## Path Safety (Zero-Entropy Standard)

Hardcoding absolute paths that reference a specific host is **strictly prohibited**. All paths must be relative or derived dynamically:

```python
# ✅ Correct
from pathlib import Path
MODULE_DIR = Path(__file__).parent
DATA_PATH = MODULE_DIR / "data" / "target.json"

# ❌ Forbidden
DATA_PATH = "./data/target.json"
```

This ensures CORTEX remains deployable on any machine without code changes — the foundation of a truly sovereign, cross-platform agent infrastructure.
