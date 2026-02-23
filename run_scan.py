import sys
import os
from pathlib import Path
sys.path.append(os.getcwd())
from cortex.mejoralo.scan import scan

def main():
    project_path = "/Users/borjafernandezangulo/cortex"
    try:
        result = scan("cortex", project_path, brutal=True)
        print(f"Project: {result.project}")
        print(f"Score: {result.score}/100")
        print(f"Stack: {result.stack}")
        print(f"Total Files: {result.total_files}")
        print(f"Total LOC: {result.total_loc}")
        print("\nDimensions:")
        for d in result.dimensions:
            print(f"- {d.name}: {d.score} (Weight: {d.weight})")
            if d.findings:
                for f in d.findings[:5]:
                    print(f"  - {f}")
    except Exception as e:
        print(f"Error during scan: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
