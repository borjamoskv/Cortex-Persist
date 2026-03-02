import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import List, Dict
from kimi_commander import KimiCommander


class GhostAuditDaemon:
    """Sovereign Daemon for periodic Ghost Audits (Ω₅ Antifragile).

    Scans for unresolved knowledge gaps and triggers a strategic
    mission for the kimi-swarm-1 to consolidate them into certitude.
    """

    def __init__(self, db_path: str = None):
        if not db_path:
            self.db_path = str(Path.home() / ".cortex" / "cortex.db")
        else:
            self.db_path = db_path

        self.commander = KimiCommander()
        self.logger = logging.getLogger("cortex.swarm.ghost_audit")

    async def run_forever(self, interval: int = 3600):
        """Main loop: Scan -> Audit -> Persist -> Sleep."""
        self.logger.info("💀 [GHOST-DAEMON] Sovereign Audit Loop Activated.")

        while True:
            try:
                # Part 1: Ghost Scan
                ghosts = self._scan_ghosts()
                if ghosts:
                    self.logger.info(f"🔍 Found {len(ghosts)} ghosts. Swarm Audit.")
                    
                    ids = [g['id'] for g in ghosts]
                    mission = (
                        f"Ghost Audit: Analyze and map {len(ghosts)} unresolved ghosts "
                        f"to existing facts using ghost-mapping. IDs: {ids}"
                    )
                    await self.commander.execute_mission(mission, dry_run=True)

                # Part 2: Signal Cluster Scan (Perfect Storms)
                clusters = self._scan_signal_clusters()
                if clusters:
                    self.logger.warning(f"🌪️ Detected {len(clusters)} signal clusters (Potential Storms).")
                    for c in clusters:
                        mission = (
                            f"Storm Analysis: Analyze cluster {c['root_id']} "
                            f"with {c['cluster_size']} events: {c['associated_types']}."
                        )
                        await self.commander.execute_mission(mission, dry_run=True)

                if not ghosts and not clusters:
                    self.logger.info("💤 System in homeostasis. No anomalies detected.")

            except Exception as e:
                self.logger.error(f"☠️ Daemon error: {e}")

            await asyncio.sleep(interval)

    def _scan_ghosts(self) -> List[Dict]:
        """Scans the DB for pending ghosts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        query = (
            "SELECT id, project, content FROM facts "
            "WHERE fact_type = 'ghost' AND valid_until IS NULL "
            "ORDER BY created_at DESC LIMIT 5"
        )
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            return [{"id": r[0], "project": r[1], "content": r[2]} for r in rows]
        finally:
            conn.close()

    def _scan_signal_clusters(self) -> List[Dict]:
        """Scans the DB for temporal signal clusters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # This is the same logic as the cluster-signals tool
        query = """
        WITH signal_times AS (
            SELECT id, event_type, project, created_at,
                   strftime('%s', created_at) as unix_time
            FROM signals
        ),
        clusters AS (
            SELECT s1.id as root_id, s1.event_type as root_type,
                   COUNT(s2.id) as cluster_size,
                   GROUP_CONCAT(s2.event_type) as associated_types
            FROM signal_times s1
            JOIN signal_times s2 ON s2.unix_time BETWEEN s1.unix_time - 30 AND s1.unix_time + 30
            GROUP BY s1.id
            HAVING cluster_size > 5
        )
        SELECT * FROM clusters ORDER BY cluster_size DESC LIMIT 3;
        """
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            return [{
                "root_id": r[0],
                "root_type": r[1],
                "cluster_size": r[2],
                "associated_types": r[3]
            } for r in rows]
        except Exception:
            return []
        finally:
            conn.close()


async def main():
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt)
    daemon = GhostAuditDaemon()
    await daemon.run_forever(interval=60)


if __name__ == "__main__":
    asyncio.run(main())
