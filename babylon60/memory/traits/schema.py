# [C5-REAL] Exergy-Maximized
import logging
import sqlite3
from typing import Any

from babylon60.guards.exergy_guard import calculate_exergy
from babylon60.utils import void_vec

try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None

logger = logging.getLogger(__name__)


from babylon60.memory.cortex_decay import cortex_decay


class SchemaTrait:
    _conn: sqlite3.Connection | None
    _db_path: str
    _ready: bool
    _vector_enabled: bool
    _hybrid: Any
    _sanitizer: Any
    _encoder: Any

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn

        if sqlite_vec is None:
            err = "sqlite_vec module not installed. Run 'pip install sqlite-vec'"
            raise RuntimeError(err)

        conn = sqlite3.connect(
            self._db_path,  # pyright: ignore[reportAttributeAccessIssue]
            check_same_thread=False,
            timeout=5.0,  # opening-policy: O(1) fail-fast
        )
        try:
            # runtime-policy: wait up to 5s for WAL write-lock contention (Axiom Ω6)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=5000")

            try:
                if hasattr(conn, "enable_load_extension"):
                    conn.enable_load_extension(True)
                sqlite_vec.load(conn)
                self._vector_enabled = True
                logger.info("✅ [VECTORS] sqlite-vec extension loaded successfully.")
            except (AttributeError, sqlite3.OperationalError, Exception) as e:  # noqa: BLE001
                logger.warning(
                    "⚠️ [VECTORS] Fallback Mode ACTIVE: Could not load sqlite-vec: %s. "
                    "Semantic search will be disabled but metadata storage is preserved.",
                    e,
                )
                self._vector_enabled = False

            conn.row_factory = sqlite3.Row

            # Register Sovereign Functions
            conn.create_function("cortex_decay", 4, cortex_decay)
            conn.create_function("cortex_exergy", 1, calculate_exergy)
            conn.create_function("void_dist", 2, void_vec.void_hamming_dist)

            # Initialization
            conn.execute("""
                CREATE TABLE IF NOT EXISTS facts_meta (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    content TEXT,
                    timestamp REAL,
                    is_diamond INTEGER,
                    is_bridge INTEGER,
                    confidence TEXT,
                    success_rate REAL,
                    cognitive_layer TEXT,
                    parent_decision_id TEXT,
                    metadata TEXT,
                    -- Double-Plane Facets (Ω₁₃)
                    category TEXT DEFAULT 'general',
                    quadrant TEXT DEFAULT 'ACTIVE',
                    storage_tier TEXT DEFAULT 'HOT',
                    facet_version INTEGER DEFAULT 2,
                    exergy_score REAL DEFAULT 1.0
                )
            """)
            if self._vector_enabled:
                # pyright: ignore[reportAttributeAccessIssue]
                sql = f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS vec_facts USING vec0(
                        embedding int8[{self._encoder.dimension}]
                    );
                    CREATE TABLE IF NOT EXISTS vec_void (
                        rowid INTEGER PRIMARY KEY,
                        embedding BLOB
                    );
                    CREATE TABLE IF NOT EXISTS vec_void_mih (
                        rowid INTEGER PRIMARY KEY,
                        s0 INTEGER, s1 INTEGER, s2 INTEGER, s3 INTEGER,
                        s4 INTEGER, s5 INTEGER, s6 INTEGER, s7 INTEGER,
                        s8 INTEGER, s9 INTEGER, s10 INTEGER, s11 INTEGER,
                        s12 INTEGER, s13 INTEGER, s14 INTEGER, s15 INTEGER
                    );
                    """
                conn.executescript(sql)

                for i in range(16):
                    conn.execute(  # nosec
                        f"CREATE INDEX IF NOT EXISTS idx_void_mih_s{i} ON vec_void_mih(s{i})"
                    )

            # Indexes for Zero-Trust and Speed
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tenant_proj ON facts_meta(tenant_id, project_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bridge ON facts_meta(is_bridge)")

            self._ready = True

            # Ω₀: Structural integrity migration
            migrations = [
                ("cognitive_layer", "TEXT"),
                ("parent_decision_id", "TEXT"),
                ("category", "TEXT DEFAULT 'general'"),
                ("quadrant", "TEXT DEFAULT 'ACTIVE'"),
                ("storage_tier", "TEXT DEFAULT 'HOT'"),
                ("facet_version", "INTEGER DEFAULT 2"),
                ("exergy_score", "REAL DEFAULT 1.0"),
            ]

            from babylon60.utils.sql_identifiers import validate_sql_identifier

            cursor = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name LIKE 'facts_meta%' AND sql NOT LIKE '%VIRTUAL%'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            for tb in tables:
                validate_sql_identifier(tb)
                info_cursor = conn.execute(f"PRAGMA table_info({tb})")  # nosec B608
                existing_cols = {row[1] for row in info_cursor.fetchall()}
                for col, col_type in migrations:
                    if col in existing_cols:
                        continue
                    validate_sql_identifier(col)
                    alter_query = f"ALTER TABLE {tb} ADD COLUMN {col} {col_type}"
                    conn.execute(alter_query)  # nosec B608
            conn.commit()
            self._conn = conn
        except (RuntimeError, ValueError, OSError):
            try:
                conn.close()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Suppressed exception: %s", exc)
            raise

        # Initialize L2HybridSearch (FTS5 mirror) after conn is established
        if self._hybrid is None:
            try:
                from babylon60.memory.l2_hybrid_search import L2HybridSearch

                self._hybrid = L2HybridSearch(self)  # pyright: ignore[reportArgumentType]
                self._hybrid.ensure_fts_table()
            except Exception as e:  # noqa: BLE001
                logger.warning("L2HybridSearch init failed (FTS5 unavailable): %s", e)
                self._hybrid = None

        return self._conn

    @property
    def hybrid_search(self):
        """Access the L2HybridSearch engine (None if FTS5 unavailable)."""
        return self._hybrid

    def _get_sanitizer(self):
        """Return the module-level PIISanitizer singleton."""
        if self._sanitizer is None:
            try:
                from babylon60.memory.pii_sanitizer import get_pii_sanitizer

                self._sanitizer = get_pii_sanitizer()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Suppressed exception: %s", exc)
        return self._sanitizer

    def _get_domain_tables(
        self, conn: sqlite3.Connection, tenant_id: str, project_id: str
    ) -> tuple[str, str, str | None, str | None]:
        """Axiom Ω8: Vertical Domain Cut.
        If a corpus weighs too much, we split the universe and migrate only distilled axioms.
        """
        from babylon60.utils.sql_identifiers import validate_sql_identifier

        safe_tenant = "".join(c for c in tenant_id if c.isalnum() or c == "_")
        safe_proj = "".join(c for c in project_id if c.isalnum() or c == "_")
        if not safe_tenant or not safe_proj:
            # Prevent silent fallback and potential tenant data leakage
            raise ValueError(
                f"Unsafe or empty tenant/project ID rejected: tenant={tenant_id!r}, project={project_id!r}"
            )

        validate_sql_identifier(safe_tenant)
        validate_sql_identifier(safe_proj)

        meta_tb = validate_sql_identifier(f"facts_meta_{safe_tenant}_{safe_proj}")
        vec_tb = validate_sql_identifier(f"vec_facts_{safe_tenant}_{safe_proj}")
        vec_void_tb = validate_sql_identifier(f"vec_void_{safe_tenant}_{safe_proj}")
        mih_tb = validate_sql_identifier(f"vec_void_mih_{safe_tenant}_{safe_proj}")

        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (meta_tb,))
        if cursor.fetchone():
            return meta_tb, vec_tb, vec_void_tb, mih_tb

        cursor.execute(
            "SELECT count(1) FROM facts_meta WHERE tenant_id = ? AND project_id = ?",
            (tenant_id, project_id),
        )
        row = cursor.fetchone()
        count = row[0] if row else 0

        if count >= self.MAX_DOMAIN_ENTROPY:  # pyright: ignore[reportAttributeAccessIssue]
            logger.warning(
                "🌌 [UNIVERSE SPLIT] Domain %s/%s reached mass %d. Sharding vector space.",
                tenant_id,
                project_id,
                count,
            )
            # Create sharded schema
            conn.execute(f"""  # nosec
                CREATE TABLE {meta_tb} (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    content TEXT,
                    timestamp REAL,
                    is_diamond INTEGER,
                    is_bridge INTEGER,
                    confidence TEXT,
                    success_rate REAL,
                    cognitive_layer TEXT,
                    parent_decision_id TEXT,
                    metadata TEXT,
                    category TEXT DEFAULT 'general',
                    quadrant TEXT DEFAULT 'ACTIVE',
                    storage_tier TEXT DEFAULT 'HOT',
                    facet_version INTEGER DEFAULT 2,
                    exergy_score REAL DEFAULT 1.0
                )
            """)
            emb_def = f"embedding int8[{self._encoder.dimension}]"  # pyright: ignore[reportAttributeAccessIssue]
            conn.execute(f"CREATE VIRTUAL TABLE {vec_tb} USING vec0({emb_def})")  # nosec
            conn.execute(f"CREATE TABLE {vec_void_tb} (rowid INTEGER PRIMARY KEY, embedding BLOB)")  # nosec
            # MIH sharded table
            vec_void_mih_tb = f"vec_void_mih_{safe_tenant}_{safe_proj}"
            conn.execute(f"""  # nosec
                CREATE TABLE {vec_void_mih_tb} (
                    rowid INTEGER PRIMARY KEY,
                    s0 INTEGER, s1 INTEGER, s2 INTEGER, s3 INTEGER,
                    s4 INTEGER, s5 INTEGER, s6 INTEGER, s7 INTEGER,
                    s8 INTEGER, s9 INTEGER, s10 INTEGER, s11 INTEGER,
                    s12 INTEGER, s13 INTEGER, s14 INTEGER, s15 INTEGER
                )
            """)
            for i in range(16):
                conn.execute(  # nosec
                    f"CREATE INDEX IF NOT EXISTS idx_{vec_void_mih_tb}_s{i} "
                    f"ON {vec_void_mih_tb}(s{i})"
                )

            # Dynamic table identifiers below come from _get_domain_tables(),
            # which constrains them to sanitized sqlite identifiers.
            # Migrate only distilled axioms (is_diamond = 1)
            shard_meta_sql = f"""
                INSERT INTO {meta_tb} (
                    rowid, id, tenant_id, project_id, content, timestamp,
                    is_diamond, is_bridge, confidence, success_rate,
                    cognitive_layer, parent_decision_id, metadata, exergy_score
                )
                SELECT
                    rowid, id, tenant_id, project_id, content, timestamp,
                    is_diamond, is_bridge, confidence, success_rate,
                    cognitive_layer, parent_decision_id, metadata, exergy_score
                FROM facts_meta
                WHERE tenant_id = ? AND project_id = ? AND is_diamond = 1
            """
            conn.execute(shard_meta_sql, (tenant_id, project_id))

            shard_vector_sql = f"""
                INSERT INTO {vec_tb}(rowid, embedding)
                SELECT v.rowid, v.embedding
                FROM vec_facts v
                JOIN facts_meta m ON v.rowid = m.rowid
                WHERE m.tenant_id = ? AND m.project_id = ? AND m.is_diamond = 1
            """
            conn.execute(shard_vector_sql, (tenant_id, project_id))

            # Aura-Omega Acceleration: Dedicated indexes for the shard
            conn.execute(  # nosec
                f"CREATE INDEX IF NOT EXISTS idx_{safe_tenant}_{safe_proj}_bridge "
                f"ON {meta_tb}(is_bridge)"
            )
            conn.execute(  # nosec
                f"CREATE INDEX IF NOT EXISTS idx_{safe_tenant}_{safe_proj}_layer "
                f"ON {meta_tb}(cognitive_layer)"
            )

            conn.commit()
            return meta_tb, vec_tb, vec_void_tb, vec_void_mih_tb

        return "facts_meta", "vec_facts", "vec_void", "vec_void_mih"
