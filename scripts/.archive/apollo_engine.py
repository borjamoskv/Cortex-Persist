#!/usr/bin/env python3
"""
Apollo-Extractor-OMEGA Engine
SYS_ID: APOLLO_EXTRACTOR_OMEGA
STATE: C5-REAL
AESTHETIC: INDUSTRIAL_NOIR_2026

Deterministic B2B Lead Extraction targeting Web3, zk, TEE, and AI Agent founders.
"""

import json
import logging
import os
import sys
from dataclasses import dataclass

import httpx

setup_cortex_logging()
logger = logging.getLogger("apollo_engine")


@dataclass
class ApolloConfig:
    api_key: str
    target_titles: list[str]
    keywords: list[str]
    limit: int = 100


def get_apollo_config() -> ApolloConfig:
    api_key = os.getenv("APOLLO_API_KEY")
    if not api_key:
        logger.error(
            "MANDATE [APOLLO_API_GATE]: Abort immediately. API key missing. Zero fallback to C4-SIM."
        )
        sys.exit(1)

    return ApolloConfig(
        api_key=api_key,
        target_titles=["CEO", "Founder", "Co-Founder", "CTO"],
        keywords=["Web3", "ZK", "TEE", "AI Agents", "Autonomous Systems"],
        limit=100,
    )


def extract_leads(config: ApolloConfig) -> list[dict]:
    url = "https://api.apollo.io/v1/mixed_people/search"
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "x-api-key": config.api_key,
    }

    payload = {
        "q_organization_domains": "",
        "page": 1,
        "per_page": config.limit,
        "person_titles": config.target_titles,
        "q_keywords": ",".join(config.keywords),
        "contact_email_status": ["verified"],
    }

    logger.info(f"Initiating C5-REAL extraction against {url}")
    logger.info(f"Targeting: {config.keywords} | Titles: {config.target_titles}")

    with httpx.Client() as client:
        response = client.post(url, headers=headers, json=payload, timeout=15.0)

    if response.status_code != 200:
        logger.error(
            f"Extraction failed with status {response.status_code}. Payload: {response.text}"
        )
        sys.exit(1)

    data = response.json()
    contacts = data.get("contacts", [])
    logger.info(f"Extracted {len(contacts)} high-exergy verified targets.")
    return contacts


def dump_ledger(contacts: list[dict], output_path: str = "leads_ledger.json"):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(contacts, f, indent=4)
    logger.info(f"Ledger crystallized at {output_path}. Ready for P2P-Comms injection.")


if __name__ == "__main__":
    logger.info("Booting Apollo-Extractor-OMEGA Sequence...")
    cfg = get_apollo_config()
    targets = extract_leads(cfg)
    dump_ledger(targets)
