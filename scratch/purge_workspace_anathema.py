import os
import re


def purge_workspace(root_dir):
    count = 0
    anathema_pattern = re.compile(r"[ANATHEMA-PURGED](-2026)?", re.IGNORECASE)

    for root, dirs, files in os.walk(root_dir):
        if ".git" in dirs:
            dirs.remove(".git")
        if ".venv" in dirs:
            dirs.remove(".venv")
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")

        for file in files:
            if file.endswith((".md", ".py", ".txt", ".json", ".sh", ".plist")):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    if anathema_pattern.search(content):
                        print(f"Purging {file_path}...")
                        new_content = anathema_pattern.sub("[ANATHEMA-PURGED]", content)
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        count += 1

                    # Handle filename
                    if anathema_pattern.search(file):
                        new_name = anathema_pattern.sub("anathema_purged", file)
                        new_path = os.path.join(root, new_name)
                        os.rename(file_path, new_path)
                        print(f"Renamed {file_path} to {new_path}")
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

    print(f"ANATHEMA Workspace Purge: {count} files processed.")


if __name__ == "__main__":
    workspace = "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist"
    purge_workspace(workspace)
