#!/usr/bin/env python3
import subprocess

# Protected branches that should NEVER be deleted
PROTECTED = {
    "main",
    "gh-pages",
    "ouroboros-core",
    "ouroboros-containment",
}

# Head branches of currently open PRs
OPEN_PR_BRANCHES = {
    "fix-tests-and-hdc-store-fallback-16444316040086628297",
    "refactor/contradiction-guard-omega-2-3987285976772220881",
    "refactor-causality-module-3119446621715369186",
    "fix/hdc-store-pure-python-fallback-8918100402917059423",
    "sqlite-vec-fallback-15192472207405113111",
    "dependabot/github_actions/actions/checkout-7.0.0",
}

def run(cmd):
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return result.stdout.strip().splitlines()

def main():
    # 1. Prune local branches
    print("=== PRUNING LOCAL BRANCHES ===")
    local_branches = [line.strip().replace("* ", "") for line in run("git branch")]
    for branch in local_branches:
        if branch in PROTECTED or branch in OPEN_PR_BRANCHES:
            print(f"Skipping protected/active local branch: {branch}")
            continue
        
        print(f"Deleting local branch: {branch}")
        res = subprocess.run(f"git branch -D {branch}", shell=True, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error deleting local branch {branch}: {res.stderr.strip()}")

    # 2. Prune remote branches
    print("\n=== PRUNING REMOTE BRANCHES ===")
    remote_lines = run("git branch -r")
    remote_branches = []
    for line in remote_lines:
        line = line.strip()
        if not line or "->" in line:
            continue
        # Format is origin/branch-name
        if line.startswith("origin/"):
            branch = line.replace("origin/", "")
            remote_branches.append(branch)

    for branch in remote_branches:
        if branch in PROTECTED or branch in OPEN_PR_BRANCHES:
            print(f"Skipping protected/active remote branch: origin/{branch}")
            continue

        print(f"Deleting remote branch: origin/{branch}")
        res = subprocess.run(f"git push origin --delete {branch}", shell=True, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error deleting remote branch origin/{branch}: {res.stderr.strip()}")

if __name__ == "__main__":
    main()
