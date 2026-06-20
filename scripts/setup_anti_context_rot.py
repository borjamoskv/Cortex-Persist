#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
Setup Anti-Context Rot Daemon
Generates the launchd plist with active API keys, writes it to LaunchAgents,
and triggers launchctl to start the service.
"""

import os
import sys
from pathlib import Path

PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.borjamoskv.anti_context_rot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/borjafernandezangulo/.cortex/scripts/anti_context_rot_daemon.py</string>
        <string>run-once</string>
    </array>
    <key>StartInterval</key>
    <integer>300</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{path}</string>
        <key>GEMINI_API_KEY</key>
        <string>{gemini_key}</string>
        <key>OPENAI_API_KEY</key>
        <string>{openai_key}</string>
        <key>GROQ_API_KEY</key>
        <string>{groq_key}</string>
        <key>DEEPSEEK_API_KEY</key>
        <string>{deepseek_key}</string>
        <key>OPENROUTER_API_KEY</key>
        <string>{openrouter_key}</string>
        <key>KIMI_API_KEY</key>
        <string>{kimi_key}</string>
        <key>PERPLEXITY_API_KEY</key>
        <string>{perplexity_key}</string>
        <key>PYTHONPATH</key>
        <string>/Users/borjafernandezangulo/10_PROJECTS/cortex-persist</string>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/borjafernandezangulo/.cortex/anti_context_rot_out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/borjafernandezangulo/.cortex/anti_context_rot_err.log</string>
</dict>
</plist>
"""

def setup():
    launch_dir = Path.home() / "Library" / "LaunchAgents"
    launch_dir.mkdir(parents=True, exist_ok=True)
    
    plist_path = launch_dir / "com.borjamoskv.anti_context_rot.plist"
    
    # Ingest active environment keys
    path_val = os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    kimi_key = os.environ.get("KIMI_API_KEY", "")
    perplexity_key = os.environ.get("PERPLEXITY_API_KEY", "")
    
    # Fill template
    content = PLIST_TEMPLATE.format(
        path=path_val,
        gemini_key=gemini_key,
        openai_key=openai_key,
        groq_key=groq_key,
        deepseek_key=deepseek_key,
        openrouter_key=openrouter_key,
        kimi_key=kimi_key,
        perplexity_key=perplexity_key
    )
    
    # Write plist
    with open(plist_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"[C5-REAL] Plist written to {plist_path}")
    
    # Load daemon using launchctl
    # Unload first if already loaded
    os.system(f"launchctl unload {plist_path} 2>/dev/null")
    exit_code = os.system(f"launchctl load {plist_path}")
    if exit_code == 0:
        print("[C5-REAL] Anti-Context Rot Daemon successfully loaded in launchd.")
    else:
        print(f"❌ Failed to load daemon. Exit code: {exit_code}")

if __name__ == "__main__":
    setup()
