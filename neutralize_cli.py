import re
from pathlib import Path

cli_dir = Path("babylon60/cli")

# Regex to find os.environ.get("CORTEX_SOMETHING", default)
get_pattern1 = re.compile(r'os\.environ\.get\("CORTEX_([A-Z0-9_]+)",\s*(.*?)\)')
# Regex to find os.environ.get("CORTEX_SOMETHING")
get_pattern2 = re.compile(r'os\.environ\.get\("CORTEX_([A-Z0-9_]+)"\)')
# Regex to find os.environ["CORTEX_SOMETHING"]
set_pattern = re.compile(r'os\.environ\["CORTEX_([A-Z0-9_]+)"\]')
# Regex to find from cortex. -> from babylon60.
import_pattern = re.compile(r'from cortex\.')

for filepath in cli_dir.rglob("*.py"):
    content = filepath.read_text()
    orig_content = content
    
    # from cortex. -> from babylon60.
    content = import_pattern.sub('from babylon60.', content)
    
    # os.environ.get("CORTEX_VAR", default) -> os.environ.get("MOSKV_VAR", os.environ.get("CORTEX_VAR", default))
    content = get_pattern1.sub(r'os.environ.get("MOSKV_\1", os.environ.get("CORTEX_\1", \2))', content)
    
    # os.environ.get("CORTEX_VAR") -> os.environ.get("MOSKV_VAR", os.environ.get("CORTEX_VAR"))
    content = get_pattern2.sub(r'os.environ.get("MOSKV_\1", os.environ.get("CORTEX_\1"))', content)
    
    # os.environ["CORTEX_VAR"] -> os.environ["MOSKV_VAR"]
    # Wait, setting it should set the new one, but for testing or fallback maybe set both.
    # We will just replace it with MOSKV_ for sets, and also set CORTEX_ for backwards compat
    # Actually, let's just do: os.environ["MOSKV_VAR"] for writes if it's not a generic fallback.
    # For now, let's just replace CORTEX_ with MOSKV_ in assignment if it's CORTEX_NO_EMBED etc.
    # A simple replace:
    content = set_pattern.sub(r'os.environ["MOSKV_\1"]', content)
    
    # Let's also fix some specific ones like CORTEX_DIR manually if needed.
    
    if content != orig_content:
        filepath.write_text(content)
        print(f"Updated {filepath}")

