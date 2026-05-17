import os
import glob

knowledge_dir = "/Users/borjafernandezangulo/.gemini/antigravity/knowledge/"
cortex_dir = "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/"


def purge_dir(directory):
    files_to_check = glob.glob(directory + "**/*.*", recursive=True)
    count = 0
    for fpath in files_to_check:
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
            if "[ANATHEMA-PURGED]" in content.lower():
                new_content = content.replace("[ANATHEMA-PURGED]", "[ANATHEMA]")
                new_content = new_content.replace("[ANATHEMA-PURGED]", "[ANATHEMA]")
                new_content = new_content.replace("[ANATHEMA-PURGED]", "[ANATHEMA]")
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                count += 1

                if "[ANATHEMA-PURGED]" in os.path.basename(fpath).lower():
                    new_name = (
                        os.path.basename(fpath)
                        .replace("[ANATHEMA-PURGED]", "anathema")
                        .replace("[ANATHEMA-PURGED]", "Anathema")
                    )
                    new_path = os.path.join(os.path.dirname(fpath), new_name)
                    os.rename(fpath, new_path)
        except Exception:
            pass
    return count


if __name__ == "__main__":
    k_count = purge_dir(knowledge_dir)
    c_count = purge_dir(cortex_dir)
    print(f"ANATHEMA PURGE COMPLETE. Purged {k_count + c_count} files across memory and workspace.")
