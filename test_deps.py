import sys
import subprocess
print(subprocess.run([sys.executable, "-c", "import cortex.cli"], capture_output=True, text=True).stderr)
