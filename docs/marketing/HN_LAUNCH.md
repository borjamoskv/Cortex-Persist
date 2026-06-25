# Show HN: BABYLON-60 - A CI/CD firewall that treats LLMs as malicious pathogens

Hey HN,

We’ve all seen the explosion of LLM coding agents (AutoGPT, Devin, Copilot). They are brilliant, but they are also stochastic, hallucinatory, and prone to silent structural drift. Right now, the industry standard is to let them generate code and then cross our fingers that the standard CI pipeline catches the bugs.

Standard CI/CD checks if code *compiles*. It doesn't check if the semantic intent drifted or if an agent just bypassed your auth loop because it hallucinated a shortcut. 

I built **BABYLON-60-PERSIST** to fix this. It’s an open-source CI/CD firewall designed specifically for the agentic era. 

Instead of treating LLM output as "human code," BABYLON-60 treats it as a dangerous pathogen. 

Here is how it works under the hood (the Causal Core):

1. **The Landauer Guillotine:** AI models talk too much. If an agent tries to push useless conversational text or conversational fluff into a commit, the system detects the "semantic anergy" and cuts the communication, extracting only the pure AST (Abstract Syntax Tree). If the AST is useless, it kills the process.
2. **The Minimal Trusted Kernel (MTK):** We installed a hard physical lock at the SQLite database level using C-level hooks. The AI *thinks* it is saving data. In reality, it hits the MTK wall. The MTK scans the physical Python RAM (`sys._getframe`); if it detects that the write order originated from a stochastic module (like an LLM inference block), it **hard-blocks the disk (`SQLITE_DENY`)**. The AI never touches the database.
3. **The Friston Penalty:** If the AI proposes a valid code mutation, BABYLON-60 isolates it, compiles it, and runs tests. If it fails, the code is destroyed and the agent's "trust score" drops. If it passes, BABYLON-60 commits it with a cryptographic Merkle hash, creating a tamper-evident audit seal.

It’s basically a titanium straightjacket for LLMs. 

We are currently running it in production to govern our own swarms of autonomous agents, enforcing what we call "C5-REAL" execution (zero green theater, zero LLM slop).

I’d love for the security and systems engineers here to take a look at the MTK architecture. We are actually running a challenge (and a Hall of Fame) for anyone who can bypass the `mtk_authorizer_callback` hook.

Repo: https://github.com/borjamoskv/cortex-persist

Looking forward to your feedback.
