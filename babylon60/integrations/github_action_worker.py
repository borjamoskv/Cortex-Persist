import logging
import os
import sys
from typing import Any

import requests

# Configure structured logging for CI/CD
# setup_cortex_logging()
logger = logging.getLogger("cortex-action-worker")

CORTEX_API_URL = os.environ.get("CORTEX_API_URL", "https://api.cortexpersist.com/api/v1/audit")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_EVENT_PATH = os.environ.get("GITHUB_EVENT_PATH")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")

def load_github_event() -> dict[str, Any]:
    """Loads the GitHub Actions event payload."""
    if not GITHUB_EVENT_PATH or not os.path.exists(GITHUB_EVENT_PATH):
        logger.error("GITHUB_EVENT_PATH not found. Are we running in GitHub Actions?")
        sys.exit(1)
        
    import json
    with open(GITHUB_EVENT_PATH) as f:
        return json.load(f)

def post_pr_comment(pr_number: int, markdown_body: str):
    """Posts a Markdown comment to the GitHub PR using the REST API."""
    if not GITHUB_TOKEN:
        logger.warning("GITHUB_TOKEN not found. Skipping PR comment.")
        return
        
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.post(url, json={"body": markdown_body}, headers=headers)
    if response.status_code != 201:
        logger.error(f"Failed to post comment: {response.text}")

def main():
    logger.info("Initializing CORTEX GitHub Action Worker (AX-041 C5-REAL)")
    
    event = load_github_event()
    pr_data = event.get("pull_request")
    
    if not pr_data:
        logger.info("Not a pull_request event. Exiting safely.")
        sys.exit(0)
        
    pr_number = pr_data.get("number")
    pr_title = pr_data.get("title", "Unknown Intent")
    
    logger.info(f"Evaluating PR #{pr_number} - {pr_title}")
    
    # Construct the Audit Payload
    payload = {
        "pr_id": str(pr_number),
        "tenant_id": GITHUB_REPOSITORY,
        "intent": pr_title,
        "additions": pr_data.get("additions", 0),
        "deletions": pr_data.get("deletions", 0),
        "changed_files": pr_data.get("changed_files", 0)
    }
    
    try:
        # In a real environment, you'd want to securely authenticate this call.
        logger.info(f"Dispatching payload to CORTEX Gatekeeper: {CORTEX_API_URL}")
        response = requests.post(CORTEX_API_URL, json=payload, timeout=15)
        response.raise_for_status()
        
        result = response.json()
        decision = result.get("decision", "ALLOW")
        risk_level = result.get("risk_level", "UNKNOWN")
        
        logger.info(f"CORTEX Decision: {decision} | Risk: {risk_level}")
        
        # Build PR Comment
        comment = f"## 🛡️ CORTEX Risk Audit\n\n**Decision**: `{decision}`\n**Risk Level**: `{risk_level}`\n\n"
        if decision == "BLOCK":
            comment += "> [!CAUTION]\n> CORTEX has blocked this PR due to excessive semantic drift or operational risk."
        else:
            comment += "> [!TIP]\n> CORTEX verified this PR. Entropy levels are within stable bounds."
            
        post_pr_comment(pr_number, comment)
        
        # Enforce the CI/CD Gate
        if decision == "BLOCK":
            logger.error("CORTEX blocked this PR. Exiting with failure.")
            sys.exit(1)
            
        logger.info("CORTEX approved this PR. Exiting with success.")
        sys.exit(0)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to reach CORTEX API: {str(e)}")
        # Fail-open or Fail-closed depends on strictness policy. Defaulting to Fail-open for MVP to avoid blocking teams on CORTEX downtime.
        logger.warning("Defaulting to FAIL-OPEN. PR is allowed.")
        sys.exit(0)

if __name__ == "__main__":
    main()
