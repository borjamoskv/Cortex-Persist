#!/usr/bin/env python3
# [C5-REAL] GDPR Notice Generator for OSINT Purge
# Orchestrates legal payloads based on the PII Audit Database.
# Output is routed directly to the secure Conversation Brain folder to avoid git PII leaks.

import json
import os
from pathlib import Path

# Dynpath generation to prevent static username leakage in Git
home_dir = Path.home()
BRAIN_DIR = home_dir / ".gemini/antigravity/brain/595b7176-16a8-4225-b919-aeff80dd3d21"
DB_PATH = BRAIN_DIR / "scratch/PII_Audit_Database.json"
OUTPUT_DIR = BRAIN_DIR / "scratch/generated_emails"

TEMPLATE = """Subject: URGENT: GDPR Article 17 Erasure Request (Right to be Forgotten) - Borja Moskv
To: {dpo_email}

TO THE DATA PROTECTION OFFICER / PRIVACY TEAM:

I am writing to you to formally request the erasure of personal data concerning me under Article 17 of the General Data Protection Regulation (GDPR) and the equivalent provisions of the CCPA, if applicable.

Identification Details:
- Legal Name: Borja Fernández Angulo
- Public/Artistic Alias: Borja Moskv
- Target URL: {target_url}

Nature of the Breach:
Your platform is currently scraping, linking, and publicly exposing my legal identity ("Borja Fernández Angulo") inextricably bound to my artistic pseudonym ("Borja Moskv"). I have not granted explicit, informed consent for your platform to index, aggregate, or distribute this cross-linked Personal Identifiable Information (PII) on the open web.

Required Action (Erasure):
I request that you permanently delete the profile, or completely scrub my legal name ("Borja Fernández Angulo") from all public-facing pages, metadata tags, and internal databases associated with the pseudonym "Borja Moskv".

Please confirm in writing within 30 days that you have complied with this request, as mandated by GDPR Article 12(3).

Sincerely,

Borja Fernández Angulo
"""

def main():
    if not DB_PATH.exists():
        print(f"Error: Audit database not found at {DB_PATH}")
        return

    with open(DB_PATH) as f:
        db = json.load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Target DPO emails
    dpo_map = {
        "Viberate": "privacy@viberate.com",
        "YouTube Music / Auto-Generated Topic Channels": "yt-privacy@google.com",
        "Deezer": "privacy@deezer.com",
        "Joox": "privacy@joox.com"
    }

    generated_count = 0
    for source in db.get("sources", []):
        if source.get("status") in ["GDPR_NOTICE_GENERATED", "AWAITING_SOURCE_FIX"]:
            platform = source.get("platform")
            dpo_email = dpo_map.get(platform, "privacy@target-platform.com")
            
            email_content = TEMPLATE.format(
                dpo_email=dpo_email,
                target_url=source.get("url")
            )
            
            safe_name = platform.replace(" ", "_").replace("/", "_").lower()
            output_file = OUTPUT_DIR / f"gdpr_request_{safe_name}.eml"
            
            with open(output_file, "w") as out:
                out.write(email_content)
            
            print(f"Generated secure legal payload: {output_file}")
            generated_count += 1

    print(f"Total legal payloads written to Brain: {generated_count}")

if __name__ == "__main__":
    main()
