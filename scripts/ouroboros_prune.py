import os
import shutil

scripts_dir = "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/scripts"
archive_dir = os.path.join(scripts_dir, ".archive")

# Safe core scripts that are actively used for infrastructure/deployment
whitelist = {
    "cortex-boot.sh",
    "cortex_persist.sh",
    "deploy_cortex_cloud.sh",
    "diagnose.sh",
    "zero_debt.sh",
    "radar_cron.sh",
    "auto_radar.sh",
    "sovereign_pre_commit.sh",
    "sovereign_pre_commit.py",
    "README.md",
    "ouroboros_prune.py"
}

if not os.path.exists(archive_dir):
    os.makedirs(archive_dir)

moved_count = 0
for filename in os.listdir(scripts_dir):
    filepath = os.path.join(scripts_dir, filename)
    if os.path.isfile(filepath) and filename not in whitelist and not filename.startswith("."):
        # Move to archive
        shutil.move(filepath, os.path.join(archive_dir, filename))
        moved_count += 1
        print(f"Moved {filename} to .archive/")

print(f"Ouroboros Pruning Complete. Moved {moved_count} experimental/dead scripts to {archive_dir}.")
