#!/usr/bin/env python3
import re
import subprocess

PROTECTED_BRANCHES = {"main", "master", "gh-pages", "ouroboros-containment", "ouroboros-core", "HEAD", "origin/HEAD", "origin/main", "origin/master", "origin/gh-pages", "origin/ouroboros-containment", "origin/ouroboros-core"}

def run_git_cmd(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout.strip()

def get_all_branches():
    stdout = run_git_cmd(["git", "branch", "-a"])
    if not stdout:
        return []
    
    branches = []
    for line in stdout.split('\n'):
        line = line.replace("*", "").strip()
        if not line:
            continue
        # Remove 'remotes/' prefix for unified handling
        if line.startswith("remotes/origin/"):
            b = line[len("remotes/"):]
        else:
            b = line
            
        if "->" in b:
            continue
            
        branches.append(b)
    return list(set(branches))

def get_merged_branches():
    stdout = run_git_cmd(["git", "branch", "-a", "--merged", "main"])
    if not stdout:
        return []
    
    merged = []
    for line in stdout.split('\n'):
        line = line.replace("*", "").strip()
        if not line:
            continue
        if line.startswith("remotes/origin/"):
            b = line[len("remotes/"):]
        else:
            b = line
        merged.append(b)
    return merged

def is_diff_empty(branch):
    # Try diff against main
    stdout = run_git_cmd(["git", "diff", "--shortstat", f"origin/main...{branch}"])
    if stdout is None:
        return False
    # If stdout is empty string, diff is 0 lines
    return stdout.strip() == ""

def is_agent_dead_branch(branch):
    patterns = [
        r"^origin/dependabot/",
        r"^dependabot/",
        r"^origin/subagent-",
        r"^subagent-",
        r"^origin/auto/",
        r"^auto/",
        r"^origin/refactor/",
        r"^refactor/",
        r"^origin/refactor-",
        r"^refactor-",
        r"^origin/codex/",
        r"^codex/",
        r"^origin/sqlite-vec-fallback",
        r"^sqlite-vec-fallback",
        r"^origin/fix-tests-and-hdc-store",
        r"^fix-tests-and-hdc-store",
        r"^origin/fix/",
        r"^fix/",
        r"^origin/optimize-website-performance",
        r"^optimize-website-performance",
        r"^origin/analyze-substack-traffic",
        r"^analyze-substack-traffic",
        r"^origin/pr-\d+",
        r"^pr-\d+"
    ]
    for p in patterns:
        if re.match(p, branch):
            return True
    return False

def main():
    print("🧹 [C5-REAL] Iniciando purga de ramas zombies...")
    
    print("Sincronizando y podando remotos...")
    subprocess.run(["git", "fetch", "--all", "--prune"], check=True)

    all_branches = get_all_branches()
    merged_branches = set(get_merged_branches())
    
    to_delete_remote = []
    to_delete_local = []
    
    for branch in all_branches:
        if branch in PROTECTED_BRANCHES:
            continue
            
        should_delete = False
        
        if branch in merged_branches:
            should_delete = True
            print(f"[{branch}] Marcada para borrar (Merged in main)")
        elif is_diff_empty(branch):
            should_delete = True
            print(f"[{branch}] Marcada para borrar (Diff vs main vacío - squashed)")
        elif is_agent_dead_branch(branch):
            should_delete = True
            print(f"[{branch}] Marcada para borrar (Agente inactivo/Zombi)")
            
        if should_delete:
            if branch.startswith("origin/"):
                remote_name = branch[len("origin/"):]
                if remote_name not in PROTECTED_BRANCHES:
                    to_delete_remote.append(remote_name)
            else:
                to_delete_local.append(branch)
                
    to_delete_remote = list(set(to_delete_remote))
    to_delete_local = list(set(to_delete_local))
    
    print(f"\nRamas Locales a purgar ({len(to_delete_local)}): {to_delete_local}")
    print(f"Ramas Remotas a purgar ({len(to_delete_remote)}): {to_delete_remote}")
    
    print("\nEjecutando purga...")
    
    for b in to_delete_local:
        res = subprocess.run(["git", "branch", "-D", b], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"✅ Local {b} eliminada.")
        else:
            print(f"❌ Error al eliminar local {b}: {res.stderr.strip()}")
            
    if to_delete_remote:
        batch_size = 10
        for i in range(0, len(to_delete_remote), batch_size):
            batch = to_delete_remote[i:i+batch_size]
            cmd = ["git", "push", "origin", "--delete"] + batch
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                print(f"✅ Remotas eliminadas: {batch}")
            else:
                print(f"❌ Error al eliminar remotas {batch}: {res.stderr.strip()}")

    print("\n🧹 Apoptosis completada. El DAG está limpio.")

if __name__ == "__main__":
    main()
