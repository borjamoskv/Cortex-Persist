import glob
import json
import logging
import os

import yaml

logger = logging.getLogger(__name__)


def parse_markdown_table(filepath):
    entities = []
    try:
        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()

        in_table = False
        headers = []
        for line in lines:
            line = line.strip()
            if line.startswith("|") and "---" in line:
                continue
            if line.startswith("|"):
                cells = [cell.strip() for cell in line.split("|")[1:-1]]
                if not in_table:
                    headers = cells
                    in_table = True
                elif in_table:
                    entity = dict(zip(headers, cells, strict=False))
                    if entity.get("ID"):
                        entities.append(entity)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error parsing {filepath}: {e}")
    return entities


async def _log_compilation_to_ledger(yaml_path: str, sha256_hash: str) -> None:
    try:
        from babylon60.audit.ledger import EnterpriseAuditLedger
        from babylon60.database.core import connect_async_ctx

        db_path = "cortex_ledger.db"
        async with connect_async_ctx(db_path) as conn:
            ledger = EnterpriseAuditLedger(conn)
            audit_id = await ledger.log_action(
                tenant_id="borjamoskv",
                actor_role="PERSIST-EXECUTOR",
                actor_id="moskv-1-apex",
                action="COMPILE_ONTOLOGY",
                resource=f"{yaml_path}@sha256:{sha256_hash}",
                status="SUCCESS",
            )
            logger.info(f"[C5-REAL] Ledger event committed: {audit_id}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[C5-REAL] Failed to log compilation to ledger: {e}")


def compile_ontology(primitives_dir, output_json, output_yaml):
    logger.info("[C5-REAL] Iniciando Ontology Compiler...")

    ontology = {
        "M1_PRIMITIVES": [],
        "M2_INVARIANTS": [],
        "M3_ANTIPATTERNS": [],
        "M4_REDUNDANCIES": [],
        "M5_VECTORS": [],
    }

    mapping = {
        "MATRIZ_1": "M1_PRIMITIVES",
        "MATRIZ_2": "M2_INVARIANTS",
        "MATRIZ_3": "M3_ANTIPATTERNS",
        "MATRIZ_4": "M4_REDUNDANCIES",
        "MATRIZ_5": "M5_VECTORS",
    }

    md_files = glob.glob(os.path.join(primitives_dir, "MATRIZ_*_BATCH_*.md"))
    for file in md_files:
        filename = os.path.basename(file)
        for key, target in mapping.items():
            if filename.startswith(key):
                entities = parse_markdown_table(file)
                ontology[target].extend(entities)

    for k, v in ontology.items():
        # Sort by ID
        v.sort(key=lambda x: x.get("ID", ""))
        logger.info(f"Compiled {len(v)} entities for {k}")

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(ontology, f, indent=2, ensure_ascii=False)

    with open(output_yaml, "w", encoding="utf-8") as f:
        yaml.dump(ontology, f, allow_unicode=True, sort_keys=False)

    logger.info(f"[C5-REAL] Ontology crystallized in JSON and YAML at {primitives_dir}")

    try:
        import hashlib
        with open(output_yaml, "rb") as f:
            yaml_content = f.read()
        sha256_hash = hashlib.sha256(yaml_content).hexdigest()

        import asyncio
        asyncio.run(_log_compilation_to_ledger(output_yaml, sha256_hash))
    except Exception as e:  # noqa: BLE001
        logger.error(f"[C5-REAL] Error logging to ledger: {e}")



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    PRIMITIVES_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "agents", "primitives")
    )
    OUTPUT_JSON = os.path.join(PRIMITIVES_DIR, "CORTEX_ONTOLOGY.json")
    OUTPUT_YAML = os.path.join(PRIMITIVES_DIR, "CORTEX_ONTOLOGY.yaml")
    compile_ontology(PRIMITIVES_DIR, OUTPUT_JSON, OUTPUT_YAML)
