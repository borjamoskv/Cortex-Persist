import os
import re

EXTENSIONS = [
    "adk",
    "aether",
    "agent",
    "agents",
    "alma",
    "axioms",
    "bci",
    "browser",
    "causality",
    "context",
    "cuatrida",
    "daemon",
    "episodic",
    "evolution",
    "federation",
    "fingerprint",
    "gate",
    "genesis",
    "git",
    "ha",
    "health",
    "hive",
    "hypervisor",
    "immune",
    "interfaces",
    "langbase",
    "launchpad",
    "llm",
    "manifold",
    "market_maker",
    "mejoralo",
    "metering",
    "moltbook",
    "music_engine",
    "nexus",
    "notifications",
    "perception",
    "platform",
    "policy",
    "protocols",
    "red_team",
    "revenue",
    "sap",
    "scraper",
    "security",
    "shannon",
    "signals",
    "skills",
    "songlines",
    "sovereign",
    "substrate",
    "swarm",
    "sync",
    "thinking",
    "timing",
    "training",
    "trust",
    "ttt",
    "ui",
    "ui_control",
    "vex",
    "wealth",
    "web3",
    "zkortex",
]


def process_file(filepath):
    with open(filepath) as f:
        content = f.read()

    original = content
    for ext in EXTENSIONS:
        # Match `from cortex.EXTENSION` or `import cortex.EXTENSION`
        # Need to be careful about word boundaries so we don't match partials.
        content = re.sub(rf"from cortex\.{ext}\b", rf"from cortex.extensions.{ext}", content)
        content = re.sub(rf"import cortex\.{ext}\b", rf"import cortex.extensions.{ext}", content)
        # Also handle multiline imports or deeper imports
        # Actually \b takes care of `from cortex.extensions.skills.xxx import ...`

    if content != original:
        with open(filepath, "w") as f:
            f.write(content)
        return True
    return False


root_dirs = ["cortex", "tests", "scripts"]
modified = 0
for d in root_dirs:
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                if process_file(path):
                    modified += 1
                    print(f"Modified {path}")
print(f"Total modified: {modified}")
