# scripts/link_multi_repo.py
# [C5-REAL] Exergy-Maximized
"""Singularity Multi-Repo Symlink Bootstrapper.

Establishes structural symlinks between the root project structures 
and the newly created multi-repo workspace folders, preventing 
physical duplication of context.
"""

import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("link_multi_repo")

def setup_links():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    workspace_dir = os.path.join(root_dir, "workspace-multi-repo")
    
    frontend_target = os.path.join(workspace_dir, "frontend")
    backend_target = os.path.join(workspace_dir, "backend")
    
    # Symlinks for Frontend
    fe_links = {
        "cortex_ui/src": "src",
        "cortex_ui/package.json": "package.json",
        "cortex_ui/tsconfig.json": "tsconfig.json",
        "cortex_ui/vite.config.ts": "vite.config.ts",
        "cortex_ui/wrangler.toml": "wrangler.toml",
    }
    
    # Symlinks for Backend
    be_links = {
        "babylon60": "babylon60",
        "cortex": "cortex",
        "pyproject.toml": "pyproject.toml",
        "tests": "tests",
    }
    
    logger.info("Setting up frontend symlinks...")
    for rel_src, target_name in fe_links.items():
        src_path = os.path.join(root_dir, rel_src)
        target_path = os.path.join(frontend_target, target_name)
        create_symlink(src_path, target_path)
        
    logger.info("Setting up backend symlinks...")
    for rel_src, target_name in be_links.items():
        src_path = os.path.join(root_dir, rel_src)
        target_path = os.path.join(backend_target, target_name)
        create_symlink(src_path, target_path)

def create_symlink(src: str, dest: str):
    if not os.path.exists(src):
        logger.error(f"Source does not exist: {src}")
        return
        
    if os.path.islink(dest) or os.path.exists(dest):
        logger.warning(f"Destination already exists, removing: {dest}")
        if os.path.islink(dest):
            os.unlink(dest)
        elif os.path.isdir(dest):
            import shutil
            shutil.rmtree(dest)
        else:
            os.remove(dest)
            
    os.symlink(src, dest)
    logger.info(f"Symlinked: {dest} -> {src}")

if __name__ == "__main__":
    setup_links()
