# [C5-REAL] Exergy-Maximized
"""Migration 29: Thermodynamic Bridge Pointers (AX-051).

Converts existing duplicated bridge facts into NEXUS_SYMLINK pointers
to eradicate physical entropy in the storage layer.
"""

import json

import aiosqlite


async def _migration_029_thermodynamic_bridges(conn: aiosqlite.Connection) -> None:
    """Find bridge facts that duplicate knowledge and convert them to pointers."""

    # Extract all active bridge facts
    async with conn.execute(
        "SELECT id, tenant_id, project, content, metadata FROM facts WHERE fact_type = 'bridge' AND is_tombstoned = 0 AND valid_until IS NULL"
    ) as cursor:
        bridges = await cursor.fetchall()

    for row in bridges:
        fact_id, tenant_id, project, content_encrypted, metadata_encrypted = row

        async with conn.execute("SELECT hash FROM facts WHERE id = ?", (fact_id,)) as cur:
            h_row = await cur.fetchone()
            bridge_hash = h_row[0] if h_row else None

        if not bridge_hash:
            continue

        # Find the original fact that shares this hash but is NOT a bridge.
        async with conn.execute(
            "SELECT hash FROM facts WHERE tenant_id = ? AND project != ? AND hash = ? AND fact_type != 'bridge' AND valid_until IS NULL",
            (tenant_id, project, bridge_hash),
        ) as cur:
            orig = await cur.fetchone()

        if orig:
            target_hash = orig[0]
            from cortex.crypto import get_default_encrypter

            try:
                enc = get_default_encrypter()

                # Metadata is encrypted as of recent migrations!
                meta = {}
                if metadata_encrypted:
                    try:
                        meta = json.loads(enc.decrypt_str(metadata_encrypted, tenant_id=tenant_id))
                    except Exception:
                        pass

                old_content = (
                    enc.decrypt_str(content_encrypted, tenant_id=tenant_id)
                    if content_encrypted
                    else ""
                )

                # If already symlinked, skip
                if str(old_content).startswith("NEXUS_SYMLINK:"):
                    continue

                meta["bridge_adaptation"] = old_content
                meta["bridge_target_hash"] = target_hash

                new_content = f"NEXUS_SYMLINK:{target_hash}"
                new_content_encrypted = enc.encrypt_str(new_content, tenant_id=tenant_id)
                new_meta_encrypted = enc.encrypt_str(json.dumps(meta), tenant_id=tenant_id)

                await conn.execute(
                    "UPDATE facts SET content = ?, metadata = ? WHERE id = ?",
                    (new_content_encrypted, new_meta_encrypted, fact_id),
                )
            except Exception:
                pass  # Skip if crypto fails or not available
