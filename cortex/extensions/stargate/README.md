# CORTEX Stargate: Star to Unlock

Stargate is a sovereign CORTEX extension that allows creators to gate rewards (e.g., PDFs, secret links, app features) behind a "Star the GitHub Repository" action. Similar to "Repost to Download" gates on SoundCloud or Spotify, it forces user interaction in exchange for value.

## Features
- **Zero Database Required:** Temporary state tracking in memory.
- **GitHub OAuth Integration:** Secure, instant verification of Stars using the `user/starred/{owner}/{repo}` endpoint.
- **Industrial Noir UI:** Implemented using CORTEX aesthetic principles (BlueYlb accents, dark mode).

## Setup Instructions

### 1. Register a GitHub OAuth App
Go to your GitHub Developer Settings -> OAuth Apps -> **New OAuth App**.
- **Application name:** CORTEX Stargate
- **Homepage URL:** `http://localhost:8000` (or your production URL)
- **Authorization callback URL:** `http://localhost:8000/api/auth/callback`

Generate a Client Secret.

### 2. Configure Environment Variables
You must set the following variables before running the server:

```bash
export GITHUB_CLIENT_ID="your_client_id"
export GITHUB_CLIENT_SECRET="your_client_secret"
export TARGET_REPO="borjamoskv/cortex-persist" # Repo they must star
export REWARD_URL="https://example.com/reward" # Where they are redirected after success
```

### 3. Run the Server
The Stargate requires `fastapi`, `uvicorn`, and `httpx`.

```bash
pip install fastapi uvicorn httpx
python /path/to/cortex/extensions/stargate/server.py
```

The server will start at `http://127.0.0.1:8000`. Direct users to this URL to unlock the reward.
