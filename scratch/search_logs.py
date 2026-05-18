import json
import os

log_path = (
    "/Users/borjafernandezangulo/.gemini/antigravity/brain"
    "/eae0826c-300e-4e4b-bf48-3ca2510cb3d9/.system_generated/logs/overview.txt"
)

if os.path.exists(log_path):
    with open(log_path) as f:
        for i, line in enumerate(f):
            try:
                data = json.loads(line)
                content = data.get("content", "")
                if not content and "tool_calls" in data:
                    # check tool call outputs if any
                    pass

                start = content.find("Margolus")
                if start != -1:
                    print(f"--- Found in line {i} ---")
                    print(content[max(0, start - 200) : start + 800])

                # Also search for "5." in case it's numbered differently
                if "5." in content:
                    start_5 = content.find("5.")
                    print(f"--- Found '5.' in line {i} ---")
                    print(content[start_5 : start_5 + 800])
            except Exception:
                continue
else:
    print("Log path not found")
