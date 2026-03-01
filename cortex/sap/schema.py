"""CORTEX v5.0 — SAP OData Schema Parser.

Isolates XML parsing for SAP $metadata payloads.
"""

from __future__ import annotations

import logging
from xml.etree import ElementTree

logger = logging.getLogger("cortex.sap.schema")

__all__ = ["parse_metadata_xml"]


def parse_metadata_xml(xml_text: str) -> dict[str, list[str]]:
    """Parse an OData V2 $metadata XML payload into an entity map.

    Returns:
        A dict mapping EntitySet names to a list of their Property names.
    """
    entity_sets: dict[str, list[str]] = {}
    try:
        root = ElementTree.fromstring(xml_text)
        # OData V2 namespace
        for entity_type in root.iter(
            "{http://schemas.microsoft.com/ado/2008/09/edm}EntityType"
        ):
            name = entity_type.attrib.get("Name", "")
            props = [
                p.attrib.get("Name", "")
                for p in entity_type.iter(
                    "{http://schemas.microsoft.com/ado/2008/09/edm}Property"
                )
            ]
            if name:
                entity_sets[name] = props
    except ElementTree.ParseError:
        logger.warning("Failed to parse $metadata XML — returning empty.")

    return entity_sets
