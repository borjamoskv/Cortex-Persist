import sqlite3
import os
import sys

try:
    import resend
    import litellm
except ImportError:
    print("[CORTEX] Install dependencies first: pip install resend litellm")
    sys.exit(1)

# [REQUIRES C5-REAL TOKENS]
resend.api_key = os.environ.get("RESEND_API_KEY")
os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")  # Necesario para litellm

if not resend.api_key:
    print("[CORTEX] FATAL: RESEND_API_KEY no encontrada. Aborting C5-REAL dispatch.")
    sys.exit(1)

DB_PATH = "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/engine/cortex.db"
FROM_EMAIL = "nexus@cortexpersist.com"

# ─────────────────────────────────────────────────────────
# BASE ZERO-NOISE PAYLOAD
# ─────────────────────────────────────────────────────────
SUBJECT_BASE = "CORTEX-Persist: O(1) Sovereign Execution vs Architectural Entropy"

HTML_BASE = """
<div style="font-family: monospace; background-color: #0A0A0A; color: #FFFFFF; padding: 20px; border: 1px solid #2B3BE5;">
    <h2 style="color: #2B3BE5;">[CORTEX DIRECTIVE]</h2>
    <p>Your recent commits in the LLM Agent space have been tracked by the CORTEX Swarm.</p>
    <p>Current frameworks suffer from severe thermodynamic entropy: they prioritize conversational context collapse over verifiable state machines.</p>
    <p><strong>CORTEX-Persist</strong> is a local-first, O(1) Sovereign Engine. We enforce:</p>
    <ul>
        <li>Cryptographic ledger persistence for agent actions.</li>
        <li>Deterministic bypass using Z3 Theorem Proving (C5-REAL audits).</li>
        <li>10,000 parallel node orchestration with Zero-Noise architecture.</li>
    </ul>
    <p>We are replacing simulation with extraction. Review the architecture and latest Bounty Strikes at the nexus:</p>
    <p><a href="https://www.cortexpersist.com" style="color: #2B3BE5;">www.cortexpersist.com</a></p>
    <br>
    <p><em>End of signal.</em></p>
</div>
"""


def localize_payload(email: str, base_html: str) -> tuple[str, str]:
    """Uses LLM to deduce language from email (TLD, name) and translates the payload and subject."""

    prompt = f"""
    You are an apex translation module.
    Recipient Email: {email}
    
    Task:
    1. Deduce the probable native language of the recipient based on their name, domain, or TLD (e.g., .kz -> Kazakh/Russian, .il -> Hebrew, .fr -> French, Chinese names -> Mandarin). If unknown or generic (.com), default to English.
    2. Translate the following Subject and HTML Body into that language. 
    3. You MUST preserve the exact HTML structure, inline CSS, and technical terms (O(1), Z3 Theorem Proving, CORTEX Swarm, Zero-Noise).
    4. Output ONLY a valid JSON object with keys "subject" and "html". No markdown blocks, no other text.
    
    Subject to translate: {SUBJECT_BASE}
    HTML to translate: {base_html}
    """

    print(f"[*] Inferring and translating for {email}...")
    try:
        response = litellm.completion(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        import json

        result = json.loads(response.choices[0].message.content)
        return result.get("subject", SUBJECT_BASE), result.get("html", base_html)
    except Exception as e:
        print(f"[!] Translation failed for {email}, defaulting to English. Err: {e}")
        return SUBJECT_BASE, base_html


def execute_dispatch():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Extraemos leads Top Tier
    cursor.execute("SELECT email FROM leads_target WHERE exergy_score >= 0.9 LIMIT 15;")
    targets = cursor.fetchall()

    print(f"[CORTEX] Initiating Dynamic Translation Strike on {len(targets)} high-exergy nodes...")

    for row in targets:
        target_email = row[0]

        # 1. Adaptación dinámica (LLM JIT)
        localized_subject, localized_html = localize_payload(target_email, HTML_BASE)

        # 2. Envío de impacto
        try:
            r = resend.Emails.send(
                {
                    "from": f"CORTEX Nexus <{FROM_EMAIL}>",
                    "to": target_email,
                    "subject": localized_subject,
                    "html": localized_html,
                }
            )
            print(f"[SUCCESS] Dispatched Native Payload to -> {target_email} | ID: {r.get('id')}")
        except Exception as e:
            print(f"[FAILED] {target_email} -> {e}")

    conn.close()


if __name__ == "__main__":
    execute_dispatch()
