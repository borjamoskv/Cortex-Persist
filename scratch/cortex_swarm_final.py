import sqlite3
import subprocess
import json
import concurrent.futures
from datetime import datetime

DB_PATH = "/Users/borjafernandezangulo/.cortex/cortex.db"
REPOS_FILE = "repos_list.txt"


def get_contributors(repo):
    try:
        print(f"[Agent-{repo}] Extracting...")
        cmd = ["gh", "api", f"repos/{repo}/contributors?per_page=100"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return []
        users = json.loads(result.stdout)
        leads = []
        for u in users:
            if u.get("type") == "User" and "noreply" not in u.get("login", ""):
                leads.append(
                    {
                        "email": f"{u['login']}@github.com",
                        "source": f"github.com/{repo}",
                        "segment": "Contributor",
                        "exergy_score": 75,
                    }
                )
        return leads
    except:
        return []


def ingest(leads):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    count = 0
    for lead in leads:
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO leads_target (email, source, segment, exergy_score)
                VALUES (?, ?, ?, ?)
            """,
                (lead["email"], lead["source"], lead["segment"], lead["exergy_score"]),
            )
            count += 1
        except:
            continue
    conn.commit()
    conn.close()
    return count


def run_swarm():
    with open("repos_batch_3.txt") as f:
        repos = [line.strip() for line in f if line.strip()]
    with open("repos_batch_4.txt") as f:
        repos += [line.strip() for line in f if line.strip()]

    repos = list(set(repos))  # Unique
    print(f"[Swarm] Deploying 100 agents over {len(repos)} sectors...")

    all_leads = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = {executor.submit(get_contributors, repo): repo for repo in repos}
        for future in concurrent.futures.as_completed(futures):
            all_leads.extend(future.result())

    print(f"[Swarm] Total candidates: {len(all_leads)}")
    ingested = ingest(all_leads)
    print(f"[Swarm] Success. Ingested: {ingested}")


if __name__ == "__main__":
    run_swarm()
