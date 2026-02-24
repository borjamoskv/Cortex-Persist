# Cross-Platform Architecture

CORTEX runs natively on **macOS, Linux, and Windows** without Docker. This guide covers the platform abstraction layer that makes this possible.

---

## The `cortex.sys_platform` Module

All OS-dependent code is routed through a single abstraction layer. Direct OS checks scattered across the codebase are **prohibited**.

```python
from cortex.sys_platform import is_macos, is_linux, is_windows, get_cortex_dir
```

**Dynamic executables**: Instead of hardcoding paths like `/Users/.../bin/python`, the architecture uses `get_python_executable()` (or `sys.executable`) to ensure daemons and subshells spawn using the correct Python binary regardless of install location.

---

## Native Notifications

The Notifier component (`cortex/daemon/notifier.py`) uses adaptive dispatch for system-native alerts:

| Platform | Method | Integration |
|:---|:---|:---|
| **macOS** | `osascript` | Notification Center |
| **Linux** | `notify-send` | libnotify |
| **Windows** | PowerShell | BurntToast / Toast XML |
| **Fallback** | Logger | `INFO`/`WARNING` if no UI session |

---

## Daemons & Service Managers

The CLI command `cortex daemon install` supports three system orchestrators, injecting CORTEX as a background service that starts automatically on boot:

### macOS — launchd

Creates a persistent `.plist` agent in `~/Library/LaunchAgents/`:

```bash
cortex daemon install
# → Created ~/Library/LaunchAgents/com.cortex.daemon.plist
# → Loaded via launchctl
```

### Linux — systemd

Creates a user-level systemd unit in `~/.config/systemd/user/` — **no sudo required**:

```bash
cortex daemon install
# → Created cortex-daemon.service
# → Enabled and started via systemctl --user
```

### Windows — Task Scheduler

Registers a Task Scheduler entry with `ONLOGON` trigger:

```powershell
cortex daemon install
# → Registered scheduled task "CORTEX Daemon"
# → Runs on user login
```

Unified log viewing across all platforms:

```bash
cortex router logs
# Uses tail -f (Unix) or PowerShell equivalent (Windows)
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
DATA_PATH = "/Users/borja/cortex/data/target.json"
```

This ensures CORTEX remains deployable on any machine without code changes — the foundation of a truly sovereign, cross-platform agent infrastructure.
