#!/bin/bash
# CORTEX — Emergency Push Script
# TOKEN must be set via: export GITHUB_TOKEN=<your_pat>

REPO_URL="https://github.com/borjamoskv/Cortex-Persist.git"
TOKEN="${GITHUB_TOKEN:?GITHUB_TOKEN env var required}"

echo "🚀 CORTEX: Preparing push to $REPO_URL"

# Ensure remote is correct
git remote set-url origin "https://x-access-token:$TOKEN@github.com/borjamoskv/Cortex-Persist.git"

# Fetch to check state
echo "📥 Fetching from remote..."
git fetch origin main

# Rebase or check status
echo "🔄 Checking branch status..."
LOCAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "   Local branch: $LOCAL_BRANCH"

# Push local to main
echo "📤 Pushing $LOCAL_BRANCH to main..."
git push origin "$LOCAL_BRANCH:main" --force-with-lease

if [ $? -eq 0 ]; then
    echo "✅ PUSH SUCCESSFUL"
else
    echo "❌ PUSH FAILED"
    exit 1
fi
