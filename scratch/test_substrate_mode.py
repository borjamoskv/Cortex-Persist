import sys
import logging
from unittest.mock import patch


def mock_exists(path_obj):
    path_str = str(path_obj)
    if "cortex-sovereign" in path_str or "30_CORTEX" in path_str:
        return False
    return True


# Mock SOVEREIGN_CORTEX.exists() to return False
with patch("pathlib.Path.exists", side_effect=mock_exists):
    # Now import and run sovereignty
    # Reset sys.path if needed
    if "cortex.sovereignty" in sys.modules:
        del sys.modules["cortex.sovereignty"]

    import cortex.sovereignty as sovereignty

    # Setup logging
    # Note: logging might have been already configured, so we reset it
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    sovereignty.initialize()
    print(f"Status: {sovereignty.status()}")

    if sovereignty.status() == "C5-SUBSTRATE (Open Core / Stubs)":
        from cortex import extensions

        print(f"Calling extensions.any_func(): {extensions.any_func()}")
