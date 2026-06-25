import sys
import os
import logging

logger = logging.getLogger(__name__)

def _is_mitosis_branch() -> bool:
    if os.environ.get("MOCK_NON_MITOSIS") == "1":
        return False
    try:
        # Fallback to local .git/HEAD relative to CWD
        head_path = os.path.join(os.getcwd(), ".git/HEAD")
        if not os.path.exists(head_path):
            return False
            
        with open(head_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
        return "auto/moskv1-mitosis-" in content
    except Exception as e:
        logger.warning(f"[WATCHDOG] Failed to read .git/HEAD: {e}")
        return False

# Control flag to prevent infinite recursion when reading .git/HEAD inside the hook
_INSIDE_HOOK = False

def watchdog_audit_hook(event: str, args: tuple):
    global _INSIDE_HOOK
    if event == "open" and not _INSIDE_HOOK:
        _INSIDE_HOOK = True
        try:
            path, mode, flags = args
            path_str = "/" + str(path).replace("\\", "/").lstrip("/")
            
            # Check if targeting core directories
            if "/babylon60/" in path_str or "/cortex/" in path_str or "/cortex_core_rs" in path_str:
                is_write = False
                
                # Builtin open() passes mode as a string
                if isinstance(mode, str):
                    if any(m in mode for m in ("w", "a", "+", "x")):
                        is_write = True
                # os.open() passes flags as integer (args[1] is flags in os.open)
                elif isinstance(mode, int):
                    # In os.open, the signature is actually open(path, flags, mode)
                    # For os.open, writing flags:
                    if mode & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                        is_write = True
                        
                if is_write:
                    if not _is_mitosis_branch():
                        logger.critical(f"[WATCHDOG-BLOCK] Unauthorized physical mutation attempt to core source: {path}")
                        raise PermissionError(f"Bootstrap Watchdog: Direct source mutation prohibited outside mitosis branches. Target: {path}")
        finally:
            _INSIDE_HOOK = False

def install_bootstrap_watchdog():
    sys.addaudithook(watchdog_audit_hook)
    logger.info("[MTK-WATCHDOG] Bootstrap Watchdog audithook installed.")
