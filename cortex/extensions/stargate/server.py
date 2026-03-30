import os
import secrets
import urllib.parse

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

# Stargate Extension for CORTEX
# Goal: Create a "Star to Unlock" gate for GitHub repos.

app = FastAPI(title="CORTEX Stargate")

# Environment Variables
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
TARGET_REPO = os.environ.get("STAR_TARGET_REPO", "borjamoskv/cortex-persist") # e.g. owner/repo
REWARD_URL = os.environ.get("STAR_REWARD_URL", "https://example.com/secret-reward")

# In-memory session store (for POC)
# Maps state -> user_data
sessions = {}

# Simple template rendering
# We will just return raw HTML string for the POC to avoid needing a templates folder.
UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stargate | CORTEX</title>
    <style>
        :root {
            --bg-color: #0A0A0A;
            --text-color: #E0E0E0;
            --accent-color: #2B3BE5; /* BlueYlb */
            --accent-hover: #1e2bc0;
            --border-color: #333;
        }
        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }
        .container {
            background: #111;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 40px;
            max-width: 400px;
            width: 100%;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        h1 {
            font-size: 24px;
            margin-bottom: 10px;
            font-weight: 600;
        }
        p {
            color: #888;
            margin-bottom: 30px;
            font-size: 15px;
            line-height: 1.5;
        }
        .btn {
            display: inline-block;
            background-color: var(--accent-color);
            color: #fff;
            padding: 12px 24px;
            border-radius: 4px;
            text-decoration: none;
            font-weight: 500;
            transition: background-color 0.2s ease;
            width: 100%;
            box-sizing: border-box;
            border: none;
            cursor: pointer;
            font-size: 16px;
        }
        .btn:hover {
            background-color: var(--accent-hover);
        }
        .footer {
            margin-top: 30px;
            font-size: 12px;
            color: #555;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .status-msg {
            margin-top: 20px;
            padding: 10px;
            border-radius: 4px;
            font-size: 14px;
        }
        .error {
            background-color: rgba(255, 50, 50, 0.1);
            color: #ff5555;
            border: 1px solid rgba(255, 50, 50, 0.3);
        }
        .success {
            background-color: rgba(50, 255, 50, 0.1);
            color: #55ff55;
            border: 1px solid rgba(50, 255, 50, 0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Unlock Reward</h1>
        <p>Star the repository <b>{target_repo}</b> on GitHub to unlock your exclusive access.</p>

        {message_html}

        {action_button}

        <div class="footer">
            Powered by CORTEX Stargate
        </div>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def stargate_ui(request: Request, error: str = None, success: str = None):
    """Render the main UI for the Stargate."""
    message_html = ""
    if error:
        message_html = f'<div class="status-msg error">{error}</div>'
    elif success:
        message_html = f'<div class="status-msg success">Reward unlocked! <a href="{REWARD_URL}" style="color:white; text-decoration:underline;">Click here to access</a></div>'

    if success:
        action_button = ""
    else:
        # Generate OAuth URL
        state = secrets.token_urlsafe(16)
        # Store state temporarily
        sessions[state] = {"status": "pending"}

        params = {
            "client_id": GITHUB_CLIENT_ID,
            "redirect_uri": str(request.url_for("auth_callback")),
            "scope": "read:user",
            "state": state
        }
        github_auth_url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
        action_button = f'<a href="{github_auth_url}" class="btn">Login with GitHub</a>'

    html = UI_HTML.format(
        target_repo=TARGET_REPO,
        message_html=message_html,
        action_button=action_button
    )
    return html

@app.get("/api/auth/callback")
async def auth_callback(request: Request, code: str, state: str):
    """Handle callback from GitHub OAuth."""
    if state not in sessions:
        return RedirectResponse(url="/?error=Invalid+session+state.+Please+try+again.")

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "state": state
            }
        )
        token_data = token_res.json()

        if "access_token" not in token_data:
            return RedirectResponse(url="/?error=Authentication+failed.+Could+not+get+token.")

        access_token = token_data["access_token"]

        # Verify the star
        star_res = await client.get(
            f"https://api.github.com/user/starred/{TARGET_REPO}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
        )

        if star_res.status_code == 204:
            # User has starred the repository!
            return RedirectResponse(url="/?success=1")
        elif star_res.status_code == 404:
            # User hasn't starred it
            return RedirectResponse(url="/?error=You+must+star+the+repository+to+unlock+the+reward!+Please+star+it+and+try+again.")
        else:
            return RedirectResponse(url=f"/?error=Error+checking+star+status.+Status+code:+{star_res.status_code}")

if __name__ == "__main__":
    import uvicorn
    # Minimal running hook
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
