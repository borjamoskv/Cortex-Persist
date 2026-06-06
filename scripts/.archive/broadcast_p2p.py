import csv
import json
import os
import subprocess

from dotenv import load_dotenv


def main():
    load_dotenv()
    smtp_user = os.getenv("P2P_SMTP_USER")
    smtp_pass = os.getenv("P2P_SMTP_PASSWORD")

    if not smtp_user or not smtp_pass:
        print("ERROR: Faltan credenciales SMTP (P2P_SMTP_USER / P2P_SMTP_PASSWORD) en .env")
        return

    # Payload copy (Proof of Work para Devs Web3/AI)
    subject = "AI Agent Infra + Web3 (CORTEX-Persist)"
    body = """
Hey {name},

I've been auditing the infrastructure layer of several SOTA Rust repositories and your work stood out to my agent's metrics.

I'm forging CORTEX-Persist, a C5-REAL persistent memory substrate for autonomous agents. I wanted to open a direct P2P channel. If you're open to exploring asymmetric synergies between Web3 and autonomous AI, reply to this email.

Best,
Borja
"""

    leads = []

    # Leer Firecrawl leads
    try:
        with open("firecrawl_leads.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Email"):
                    leads.append({"email": row["Email"], "name": row.get("Name", "Dev")})
    except Exception as e:
        print(f"No se pudo leer firecrawl_leads: {e}")

    # Leer GitHub leads
    try:
        with open("github_leads.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Email"):
                    leads.append({"email": row["Email"], "name": "Dev"})
    except Exception as e:
        print(f"No se pudo leer github_leads: {e}")

    print(f"Iniciando broadcast a {len(leads)} leads cristalizados...")

    p2p_script_path = "/Users/borjafernandezangulo/.gemini/config/skills/P2P-Comms-OMEGA/scripts/send_p2p_email.py"

    for lead in leads:
        formatted_body = body.format(name=lead["name"])
        payload = {"to": lead["email"], "subject": subject, "body": formatted_body}

        # Ejecución determinista C5-REAL
        cmd = ["python3", p2p_script_path, json.dumps(payload)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"C5-REAL: Enviado a {lead['email']} (Code: {result.returncode})")


if __name__ == "__main__":
    main()
