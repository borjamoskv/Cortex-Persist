# ∴ CORTEX LinkedIn Follow Strike Agent (v1.0.0)

> **"Scale is the only truth. Zero-entropy follow automation for the AI Agents ecosystem."**

## ⚡ Quickstart

1.  **Launch the Strike:**
    ```bash
    python3 scripts/linkedin_follow_strike.py
    ```

2.  **Authentication Mode:**
    -   The script will open a **non-headless Chromium** instance.
    -   If you are not logged in, it will **wait for you** to enter your credentials.
    -   Once you are on the search results page, the strike will resume automatically.

3.  **Logs:**
    -   Every successful 'Follow' is registered in the CORTEX Ledger under the `linkedin-follow-strike` agent.
    -   Verify via: `cortex memory list --agent linkedin-follow-strike`

## ⚙️ Parameters

-   **URL:** You can pass a custom URL to the script:
    ```bash
    python3 scripts/linkedin_follow_strike.py "https://www.linkedin.com/search/results/people/?keywords=ai+agents"
    ```
-   **Limit:** Custom count (default 200/day):
    ```bash
    python3 scripts/linkedin_follow_strike.py [URL] 50
    ```

## ⚠️ Safety (Ω2 Thermodynamics)

-   The agent uses **Human-Like Jitter** (4s to 12s delays) to bypass basic LinkedIn anti-bot detection.
-   Recommended: Do not exceed 200 follows per 24h to avoid 'Account Restriction' flags from the LinkedIn safety gate.

---
*"The swarm verifies, the hardware remembers."*
