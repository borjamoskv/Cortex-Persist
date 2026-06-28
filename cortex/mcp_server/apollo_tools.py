import threading

# [C5-REAL] Exergy-Maximized
"""Apollo API Tools for B2B Lead Extraction.

C5-REAL deterministic extraction of B2B Web3 AI leads via Apollo API.
Exergy-positive capital extraction vector.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger("cortex.mcp_server.apollo_tools")

# Attempt to load FastMCP from mcp.server.fastmcp
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore


def register_apollo_tools(mcp: FastMCP) -> None:  # pyright: ignore[reportInvalidTypeForm]
    """Register Apollo extraction tools on the MCP server."""

    @mcp.tool()
    def cortex_apollo_extract_leads(
        target_leads: int = 10, output_filename: str = "apollo_leads_c5.json"
    ) -> str:
        """C5-REAL deterministic extraction of B2B Web3 AI leads via Apollo API.

        Extracts Founders, CEOs, CTOs from Web3, Crypto, and AI Agent domains.
        Requires APOLLO_API_KEY environment variable.
        """
        api_key = os.environ.get("APOLLO_API_KEY")
        if not api_key:
            logger.error("[P0] Singularity: APOLLO_API_KEY not detected. Aborting.")
            return "❌ Rejected: APOLLO_API_KEY environment variable is missing."

        output_path = Path(os.getcwd()) / output_filename

        logger.info(f"[*] Iniciando extracción C5-REAL: Objetivo {target_leads} leads.")

        url = "https://api.apollo.io/v1/mixed_people/search"
        headers = {"Cache-Control": "no-cache", "Content-Type": "application/json"}

        data = {
            "api_key": api_key,
            "q_organization_domains": "",
            "page": 1,
            "per_page": min(100, target_leads),
            "organization_num_employees_ranges": ["1,10", "11,50", "51,200"],
            "person_titles": ["founder", "ceo", "cto", "developer", "lead"],
            "organization_keywords": ["web3", "ai agent", "blockchain", "zk", "tee"],
        }

        extracted_leads = []

        while len(extracted_leads) < target_leads:
            try:
                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
                contacts = response.json().get("contacts", [])

                if not contacts:
                    break

                for contact in contacts:
                    if len(extracted_leads) >= target_leads:
                        break
                    extracted_leads.append(
                        {
                            "Name": contact.get("name"),
                            "Title": contact.get("title"),
                            "Company": contact.get("organization_name"),
                            "Email": contact.get("email"),
                            "LinkedIn": contact.get("linkedin_url"),
                        }
                    )

                data["page"] += 1
                threading.Event().wait(1)  # noqa: TID251 # Synchronous rate limiting

            except Exception as e:
                logger.error(f"[!] Apollo Extraction Error: {e}")
                return f"❌ Apollo Extraction Error: {e}"

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(extracted_leads, f, indent=2, ensure_ascii=False)
        except (ValueError, TypeError, OSError, KeyError) as e:
            return f"❌ Failed to write JSON output: {e}"

        return f"✅ C5-REAL Lead Extraction complete. Extracted {len(extracted_leads)} leads to {output_path}"
