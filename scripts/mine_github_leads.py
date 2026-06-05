#!/usr/bin/env python3
import logging
logger = logging.getLogger("script")
import os
import sys
import json
import subprocess
import csv

# Queries to mine
QUERIES = [
    "web3 agent language:typescript",
    "ai agent language:solidity",
    "crypto agent language:python",
    "blockchain ai language:rust",
    "zero knowledge machine learning",
    "zkml language:rust"
]

def run_gh_api(endpoint):
    try:
        result = subprocess.run(["gh", "api", endpoint], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.info(f"Error calling GH API {endpoint}: {e.stderr}")
        return None

def main():
    existing_emails = set()
    
    # Cargar correos existentes
    for file in ["github_leads.csv", "firecrawl_leads.csv", "github_leads_v2.csv"]:
        if os.path.exists(file):
            with open(file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = row.get("Email", "").strip().lower()
                    if email:
                        existing_emails.add(email)

    logger.info(f"Loaded {len(existing_emails)} existing emails to avoid duplicates.")

    new_leads = []

    for query in QUERIES:
        logger.info(f"Searching repos for: {query}")
        # Search repositories
        search_endpoint = f"/search/repositories?q={query}&sort=stars&order=desc&per_page=10"
        search_results = run_gh_api(search_endpoint)
        if not search_results or "items" not in search_results:
            continue

        for repo in search_results["items"]:
            repo_name = repo["full_name"]
            logger.info(f"  Scraping commits from: {repo_name}")
            
            commits_endpoint = f"/repos/{repo_name}/commits?per_page=20"
            commits_results = run_gh_api(commits_endpoint)
            
            if not commits_results or not isinstance(commits_results, list):
                continue
                
            for commit_data in commits_results:
                commit = commit_data.get("commit", {})
                author = commit.get("author", {})
                email = author.get("email", "").strip().lower()
                name = author.get("name", "Dev")
                
                if email and "noreply" not in email and email not in existing_emails:
                    existing_emails.add(email)
                    new_leads.append({"name": name, "email": email, "repo": repo_name})
                    logger.info(f"    [+] Found: {email}")

    if new_leads:
        file_exists = os.path.exists("github_leads_v2.csv")
        with open("github_leads_v2.csv", "a") as f:
            writer = csv.DictWriter(f, fieldnames=["Name", "Email", "Repo"])
            if not file_exists:
                writer.writeheader()
            for lead in new_leads:
                writer.writerow({"Name": lead["name"], "Email": lead["email"], "Repo": lead["repo"]})
        logger.info(f"\nSuccess! Extracted {len(new_leads)} NEW leads. Saved to github_leads_v2.csv")
    else:
        logger.info("\nNo new leads found.")

if __name__ == "__main__":
    main()
