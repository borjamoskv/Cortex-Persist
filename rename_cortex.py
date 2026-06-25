import os

def replace_in_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "babylon60" in content:
            new_content = content.replace("babylon60", "cortex")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated {filepath}")
    except Exception as e:
        pass

for root, _, files in os.walk("cortex"):
    for file in files:
        if file.endswith(".py") or file.endswith(".yaml") or file.endswith(".json"):
            replace_in_file(os.path.join(root, file))
