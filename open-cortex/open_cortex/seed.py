"""Open CORTEX — Test data seeder.

Loads the classic benchmark scenarios:
- Pluto reconsolidation (planet → dwarf planet)
- API v1→v2 deprecation
- Demographic data (España population)

Run: python -m open_cortex.seed
"""

from __future__ import annotations

import logging
import sys

from open_cortex.models import (
    Belief,
    EdgeType,
    Freshness,
    Memory,
    Namespace,
    Provenance,
    ProvenanceMethod,
    Relation,
    SourceType,
    Version,
)
from open_cortex.persistence import MemoryStore

logger = logging.getLogger("open_cortex.seed")


def seed_pluto_track(store: MemoryStore) -> None:
    """Reconsolidation benchmark: Pluto planet → dwarf planet."""

    # V1: Old claim (will be superseded)
    old_pluto = Memory(
        id="mem_pluto_v1",
        content="Pluto is the ninth planet of the solar system.",
        tags=["astronomy", "planets", "solar-system"],
        namespace=Namespace.GLOBAL,
        provenance=Provenance(
            source=SourceType.DOCUMENT,
            method=ProvenanceMethod.EXTRACTION,
            author="agent:encyclopedia",
            document_ref="https://en.wikipedia.org/wiki/Pluto_(1930)",
        ),
        belief=Belief(confidence=0.95),
        freshness=Freshness(
            valid_from="1930-02-18T00:00:00+00:00",
            is_canonical=True,
        ),
        version=Version(v=1),
    )
    store.write_memory(old_pluto)

    # V2: New canonical (supersedes V1)
    new_pluto = Memory(
        id="mem_pluto_v2",
        content="Plutón fue reclasificado como planeta enano en 2006 por la IAU (Resolución 5A).",
        tags=["astronomy", "classification", "IAU", "dwarf-planet"],
        namespace=Namespace.GLOBAL,
        provenance=Provenance(
            source=SourceType.DOCUMENT,
            method=ProvenanceMethod.EXTRACTION,
            author="agent:cortex-v7",
            document_ref="https://www.iau.org/resolutions/2006",
        ),
        belief=Belief(confidence=0.98),
        freshness=Freshness(
            valid_from="2006-08-24T00:00:00+00:00",
            is_canonical=True,
        ),
        version=Version(v=2, parent_id="mem_pluto_v1", lineage=["mem_pluto_v1"]),
        relations=[
            Relation(
                type=EdgeType.SUPERSEDES,
                target_id="mem_pluto_v1",
                reason="IAU Resolution 5A, August 24, 2006",
            )
        ],
    )
    store.write_memory(new_pluto)
    logger.info("🪐 Pluto track seeded (2 memories, 1 supersedes edge)")


def seed_api_deprecation_track(store: MemoryStore) -> None:
    """Reconsolidation benchmark: API v1 → v2 deprecation."""

    old_api = Memory(
        id="mem_api_v1",
        content="GET /users/list returns all users with pagination via ?page=N&limit=M.",
        tags=["api", "users", "v1", "rest"],
        namespace=Namespace.TEAM,
        provenance=Provenance(
            source=SourceType.DOCUMENT,
            method=ProvenanceMethod.EXTRACTION,
            author="agent:api-doc-bot",
            document_ref="https://api.example.com/docs/v1",
        ),
        belief=Belief(confidence=0.90),
        freshness=Freshness(valid_from="2024-01-01T00:00:00+00:00", is_canonical=True),
    )
    store.write_memory(old_api)

    new_api = Memory(
        id="mem_api_v2",
        content="API v2 deprecates /users/list. Use GET /users?page=N instead. Limit defaults to 50.",
        tags=["api", "users", "v2", "deprecation", "rest"],
        namespace=Namespace.TEAM,
        provenance=Provenance(
            source=SourceType.DOCUMENT,
            method=ProvenanceMethod.EXTRACTION,
            author="agent:api-monitor",
            document_ref="https://api.example.com/changelog/v2",
        ),
        belief=Belief(confidence=0.95),
        freshness=Freshness(valid_from="2026-03-01T00:00:00+00:00", is_canonical=True),
        version=Version(v=2, parent_id="mem_api_v1", lineage=["mem_api_v1"]),
        relations=[
            Relation(
                type=EdgeType.SUPERSEDES,
                target_id="mem_api_v1",
                reason="v2 changelog deprecation notice",
            )
        ],
    )
    store.write_memory(new_api)
    logger.info("🔌 API deprecation track seeded (2 memories, 1 supersedes edge)")


def seed_demographics_track(store: MemoryStore) -> None:
    """General knowledge: España population."""

    mem = Memory(
        id="mem_spain_pop",
        content="España tiene 47.4 millones de habitantes según el INE (2023).",
        tags=["demographics", "spain", "population", "INE"],
        namespace=Namespace.GLOBAL,
        provenance=Provenance(
            source=SourceType.DOCUMENT,
            method=ProvenanceMethod.EXTRACTION,
            author="agent:data-collector",
            document_ref="https://www.ine.es/prensa/cp_2023_p.pdf",
        ),
        belief=Belief(confidence=0.92),
    )
    store.write_memory(mem)

    # Contradicting claim (distractor)
    distractor = Memory(
        id="mem_spain_pop_wrong",
        content="La población de España es de 35 millones.",
        tags=["demographics", "spain", "population"],
        namespace=Namespace.GLOBAL,
        provenance=Provenance(
            source=SourceType.USER,
            method=ProvenanceMethod.USER_INPUT,
            author="user:anonymous",
        ),
        belief=Belief(confidence=0.20),
        relations=[
            Relation(
                type=EdgeType.CONTRADICTS,
                target_id="mem_spain_pop",
                reason="Cifra incorrecta sin fuente fiable",
            )
        ],
    )
    store.write_memory(distractor)
    logger.info("🇪🇸 Demographics track seeded (2 memories, 1 contradiction edge)")


def seed_all(db_path: str = "open_cortex.db") -> None:
    """Seed all benchmark tracks."""
    logging.basicConfig(level=logging.INFO)
    store = MemoryStore(db_path=db_path)

    seed_pluto_track(store)
    seed_api_deprecation_track(store)
    seed_demographics_track(store)

    total = store.count(canonical_only=False)
    canonical = store.count(canonical_only=True)
    logger.info("✅ Seeding complete: %d total memories (%d canonical)", total, canonical)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "open_cortex.db"
    seed_all(path)
