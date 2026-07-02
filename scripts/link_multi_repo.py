# scripts/link_multi_repo.py
# [C5-REAL] Exergy-Maximized
"""Singularity Multi-Repo Symlink Bootstrapper.

Establishes structural symlinks between the root project structures 
and the newly created multi-repo workspace folders, preventing 
physical duplication of context.
"""

import logging
import os
import shutil

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("link_multi_repo")

def setup_links() -> None:
    root_dir: str = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    workspace_dir: str = os.path.join(root_dir, "workspace-multi-repo")
    
    frontend_target: str = os.path.join(workspace_dir, "frontend")
    backend_target: str = os.path.join(workspace_dir, "backend")
    
    # Symlinks for Frontend (Vite/React Strict Boundary)
    fe_links: dict[str, str] = {
        "cortex_ui/src": "src",
        "cortex_ui/public": "public",
        "cortex_ui/index.html": "index.html",
        "cortex_ui/package.json": "package.json",
        "cortex_ui/package-lock.json": "package-lock.json",
        "cortex_ui/tsconfig.json": "tsconfig.json",
        "cortex_ui/tsconfig.app.json": "tsconfig.app.json",
        "cortex_ui/tsconfig.node.json": "tsconfig.node.json",
        "cortex_ui/vite.config.ts": "vite.config.ts",
        "cortex_ui/wrangler.toml": "wrangler.toml",
        "cortex_ui/.gitignore": ".gitignore",
    }
    
    # Symlinks for Backend (FastAPI/Cortex Core)
    be_links: dict[str, str] = {
        "babylon60": "babylon60",
        "cortex": "cortex",
        "pyproject.toml": "pyproject.toml",
        "tests": "tests",
    }
    
    logger.info("Setting up frontend symlinks...")
    for rel_src, target_name in fe_links.items():
        src_path: str = os.path.join(root_dir, rel_src)
        target_path: str = os.path.join(frontend_target, target_name)
        create_symlink(src_path, target_path)
        
    logger.info("Setting up backend symlinks...")
    for rel_src, target_name in be_links.items():
        src_path: str = os.path.join(root_dir, rel_src)
        target_path: str = os.path.join(backend_target, target_name)
        create_symlink(src_path, target_path)

def create_symlink(src: str, dest: str) -> None:
    if not os.path.exists(src):
        logger.error(f"Source does not exist: {src}")
        return
        
    try:
        if os.path.islink(dest) or os.path.exists(dest):
            logger.warning(f"Destination already exists, removing: {dest}")
            if os.path.islink(dest):
                os.unlink(dest)
            elif os.path.isdir(dest):
                shutil.rmtree(dest)
            else:
                os.remove(dest)
                
        os.symlink(src, dest)
        logger.info(f"Symlinked: {dest} -> {src}")
    except OSError as e:
        logger.error(f"Failed to symlink {dest} -> {src}: {e}")

if __name__ == "__main__":
    setup_links()
