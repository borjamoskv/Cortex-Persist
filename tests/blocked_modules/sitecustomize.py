# [C5-REAL] Exergy-Maximized
import builtins

_real_import = builtins.__import__


def _blocked(name, *args, **kwargs):
    if name in [
        "aiohttp",
        "numpy",
        "aiofiles",
        "bs4",
        "arq",
        "email_validator",
        "watchdog",
        "yaml",
    ]:
        raise ImportError(f"{name} blocked by test harness")
    return _real_import(name, *args, **kwargs)


builtins.__import__ = _blocked
