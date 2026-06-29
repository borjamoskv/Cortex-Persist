# [C5-REAL] Exergy-Maximized
import hashlib
import json
import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger("cortex.engine.causal.taint_engine")


class TaintValidationError(ValueError):
    """Raised when a proposal lacks a valid CORTEX-TAINT token or fails cryptographic verification."""


def canonicalize_content(content: str | bytes | memoryview) -> bytes:
    """Normalizes content to bytes to ensure consistent zero-copy hashing.
    JIT-friendly hot-path (Python 3.13+ SOTA).
    """
    if isinstance(content, memoryview):
        content = content.tobytes()
    elif isinstance(content, str):
        content = content.encode("utf-8")

    try:
        data = json.loads(content)
        if isinstance(data, dict | list):
            # Sort keys for deterministic hashing, minimal whitespaces
            return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError, KeyError, OSError, RuntimeError):
        pass

    # Fast path for non-JSON or invalid JSON
    return b"\n".join(line.strip() for line in content.strip().splitlines())


def _fast_sha3(buffer: bytes | memoryview) -> str:
    """Zero-copy / Tier 2 JIT Hot-Path for SHA3-256."""
    return hashlib.sha3_256(buffer).hexdigest()


def generate_secure_taint_token(
    agent_id: str,
    session_id: str,
    content: str,
    private_key_b64: str,
    nonce: str | None = None,
    curve: str = "ed25519",
) -> str:
    """Generates a secure cryptographically signed CORTEX-TAINT token.

    Format (Legacy): taint:{agent_id}:{session_id}:{timestamp_iso8601}:{nonce}:{signature}
    Format (Multi-Curve): taint:{curve}:{agent_id}:{session_id}:{timestamp_iso8601}:{nonce}:{signature}
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    if not nonce:
        import uuid

        nonce = uuid.uuid4().hex

    canonical_content = canonicalize_content(content)
    content_hash = _fast_sha3(canonical_content)

    canonical_payload = f"agent_id={agent_id}&session_id={session_id}&timestamp={timestamp}&nonce={nonce}&content_hash={content_hash}"

    if curve == "secp256k1":
        from cortex.crypto.keys import Secp256k1Signer

        signature = Secp256k1Signer.sign_raw_content(private_key_b64, canonical_payload)
        return f"taint:{curve}:{agent_id}:{session_id}:{timestamp}:{nonce}:{signature}"
    else:
        from cortex.crypto.keys import Signer

        signature = Signer.sign_raw_content(private_key_b64, canonical_payload)
        return f"taint:{agent_id}:{session_id}:{timestamp}:{nonce}:{signature}"


def parse_utc_timestamp(ts_str: str) -> datetime:
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _query_agent_key_sync(conn, agent_id: str) -> str | None:
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT public_key FROM agents WHERE id = ? AND is_active = 1", (agent_id,))
        row = cursor.fetchone()
        return row[0] if row else None
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
        logger.error("[TaintEngine] Failed to query agent key sync: %s", e)
        return None


async def _query_agent_key_async(conn, agent_id: str) -> str | None:
    try:
        cursor = await conn.execute(
            "SELECT public_key FROM agents WHERE id = ? AND is_active = 1", (agent_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
        logger.error("[TaintEngine] Failed to query agent key async: %s", e)
        return None


_NONCE_TABLE_CREATED_SYNC = False


def _check_and_register_nonce_sync(conn, nonce: str) -> bool:
    from cortex.database.core import causal_write

    if not getattr(conn, "_taint_nonces_created", False):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS taint_nonces (
                nonce TEXT PRIMARY KEY,
                timestamp REAL
            )
        """)
        try:
            conn._taint_nonces_created = True
        except Exception as e:
            logger.debug("Failed to flag taint nonce creation: %s", e)

    cursor = conn.cursor()
    with causal_write(conn):
        cursor.execute(
            "INSERT OR IGNORE INTO taint_nonces (nonce, timestamp) VALUES (?, ?)",
            (nonce, time.time()),
        )
    return cursor.rowcount > 0


async def _check_and_register_nonce_async(conn, nonce: str) -> bool:
    from cortex.database.core import causal_write

    if not getattr(conn, "_taint_nonces_created", False):
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS taint_nonces (
                nonce TEXT PRIMARY KEY,
                timestamp REAL
            )
        """)
        try:
            conn._taint_nonces_created = True
        except Exception as e:
            logger.debug("Failed to flag taint nonce creation: %s", e)

    with causal_write(conn):
        cursor = await conn.execute(
            "INSERT OR IGNORE INTO taint_nonces (nonce, timestamp) VALUES (?, ?)",
            (nonce, time.time()),
        )
    return cursor.rowcount > 0


def _is_async_conn(conn) -> bool:
    return "aiosqlite" in type(conn).__module__


async def verify_taint_token(conn, token: str | None, content: str) -> bool:
    """Verifies a secure cryptographically signed CORTEX-TAINT token.

    Checks:
    1. Token format.
    2. Agent registration & public key validation.
    3. Expiration window (5 minutes).
    4. Replay attack prevention (nonce tracking).
    5. Ed25519 signature validity.
    """
    if not token:
        logger.error(
            "[TaintEngine] SAGA-1: Rejecting proposal due to missing CORTEX-TAINT signature."
        )
        return False

    parts = token.split(":")
    if len(parts) < 6:
        logger.error("[TaintEngine] SAGA-1: Invalid token structure: %s", token)
        return False

    prefix = parts[0]
    if prefix != "taint":
        logger.error("[TaintEngine] SAGA-1: Token prefix must be 'taint': %s", prefix)
        return False

    if parts[1] in ("secp256k1", "ed25519"):
        curve = parts[1]
        agent_id = parts[2]
        session_id = parts[3]
        timestamp_str = ":".join(parts[4:-2])
        nonce = parts[-2]
        signature = parts[-1]
    else:
        curve = "ed25519"
        agent_id = parts[1]
        session_id = parts[2]
        timestamp_str = ":".join(parts[3:-2])
        nonce = parts[-2]
        signature = parts[-1]

    if not agent_id or not session_id or not nonce or not signature:
        logger.error("[TaintEngine] SAGA-1: Missing vital fields in taint token.")
        return False

    # 1. Verify Timestamp Expiration Window
    try:
        token_time = parse_utc_timestamp(timestamp_str)
        now = datetime.now(timezone.utc)
        diff = abs((now - token_time).total_seconds())
        if diff > 300:  # 5 minutes window
            logger.error("[TaintEngine] SAGA-1: Taint token has expired. Drift: %.1fs", diff)
            return False
    except ValueError:
        logger.error("[TaintEngine] SAGA-1: Invalid ISO-8601 timestamp in token: %s", timestamp_str)
        return False

    # 2. Check Replay Attack (Nonce ledger check)
    is_async = _is_async_conn(conn)
    if is_async:
        nonce_ok = await _check_and_register_nonce_async(conn, nonce)
    else:
        nonce_ok = _check_and_register_nonce_sync(conn, nonce)

    if not nonce_ok:
        logger.error("[TaintEngine] SAGA-1: Replay attack detected! Nonce already used: %s", nonce)
        return False

    # 3. Retrieve Agent Public Key
    if is_async:
        public_key_b64 = await _query_agent_key_async(conn, agent_id)
    else:
        public_key_b64 = _query_agent_key_sync(conn, agent_id)

    if not public_key_b64:
        logger.error("[TaintEngine] SAGA-1: Agent %s is not registered or inactive.", agent_id)
        return False

    # 4. Verify Signature (Zero-copy aware)
    canonical_content = canonicalize_content(content)
    content_hash = _fast_sha3(canonical_content)
    canonical_payload = f"agent_id={agent_id}&session_id={session_id}&timestamp={timestamp_str}&nonce={nonce}&content_hash={content_hash}"

    if curve == "secp256k1":
        from cortex.crypto.keys import Secp256k1Verifier

        is_verified = Secp256k1Verifier.verify_raw_content(
            canonical_payload, public_key_b64, signature
        )
    else:
        from cortex.crypto.keys import Verifier

        is_verified = Verifier.verify_raw_content(canonical_payload, public_key_b64, signature)

    if is_verified:
        logger.info(
            "[TaintEngine] Cryptographic Taint Signature verified for Agent %s (Curve: %s)",
            agent_id,
            curve,
        )
        return True
    else:
        logger.error(
            "[TaintEngine] SAGA-1: Cryptographic signature verification failed for Agent %s",
            agent_id,
        )
        return False


# Pre-computed case-sensitive Base64 chunks for "borja", "fernandez", "angulo" at all offsets (0, 1, 2)
PII_BASE64_CHUNKS: frozenset[str] = frozenset([
    "Ym9yamE", "GJvcmph", "b3JqYQ",            # borja
    "ZmVybmFuZGV6", "Zlcm5hbmRleg", "fZXJuYW5kZXo",  # fernandez
    "YW5ndWxv", "GFuZ3Vsbw", "hbmd1bG8"        # angulo
])

# Pre-computed lowercased hex chunks for "borja", "fernandez", "angulo"
PII_HEX_CHUNKS: frozenset[str] = frozenset([
    "626f726a61",          # borja
    "6665726e616e64657a",  # fernandez
    "616e67756c6f"         # angulo
])

import re
HOMOGLYPH_PREFILTER_RE = re.compile(r"[\u0400-\u04ff\u0370-\u03ff]")


async def enforce_taint_check(conn, token: str | None, content: str) -> None:
    """Enforces the CORTEX-TAINT check. Raises TaintValidationError if invalid."""
    import base64
    import os
    import re
    import unicodedata
    import urllib.parse

    content_lower = content.lower()
    p_b = "borja"
    p_f = "fernandez"
    p_a = "angulo"

    # Fast bypass pre-filter to maximize exergy on clean payloads
    has_plain = p_b in content_lower or p_f in content_lower or p_a in content_lower
    has_obfuscated = False
    if not has_plain:
        if "%" in content:
            has_obfuscated = True
        elif HOMOGLYPH_PREFILTER_RE.search(content):
            has_obfuscated = True
        elif any(hc in content_lower for hc in PII_HEX_CHUNKS):
            has_obfuscated = True
        elif any(bc in content for bc in PII_BASE64_CHUNKS):
            has_obfuscated = True

    if not has_plain and not has_obfuscated and "[redacted_pii]" not in content_lower:
        # Bypass check for test environment
        if os.environ.get("CORTEX_NO_TAINT_ENFORCE") == "1":
            return

        # 1. Zero Anergía Guard (Axiom Ω₁₃ / Ω₄)
        check_anergy_and_green_theater(content)

        # -- OWASP Memory Firewall (SAGA-1.5) --
        from cortex.security.memory_firewall import MemoryFirewall
        try:
            _, risk_level, _ = MemoryFirewall.screen_content(content)
        except ValueError as fw_err:
            raise TaintValidationError(f"SAGA-1 Rejection by Memory Firewall: {fw_err}")

        # -- SaaS Bot Inflation Firewall (Substack Crawler Guard) --
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "Email" in data and "Emails opened (6mo)" in data:
                from cortex.guards.substack_crawler_guard import SubstackCrawlerGuard
                try:
                    SubstackCrawlerGuard().enforce_saga_contract(data)
                except ValueError as guard_err:
                    raise TaintValidationError(f"SAGA-1 Rejection by SaaS Firewall: {guard_err}")
        except (json.JSONDecodeError, TypeError):
            pass

        # We await the verify_taint_token check
        is_valid = await verify_taint_token(conn, token, content)
        if not is_valid:
            raise TaintValidationError(
                "SAGA-1 Rejection: Valid cryptographically signed CORTEX-TAINT token is required."
            )
        return

    # Homoglyphs mapping to standard Latin base characters
    homoglyph_map = {
        # Cyrillic lowercase lookalikes
        '\u0430': 'a', '\u0435': 'e', '\u043e': 'o', '\u0440': 'p', '\u0441': 'c', '\u0443': 'y', '\u0445': 'x', '\u0456': 'i',
        # Cyrillic uppercase lookalikes
        '\u0410': 'a', '\u0412': 'b', '\u0415': 'e', '\u041a': 'k', '\u041c': 'm', '\u041d': 'h', '\u041e': 'o', '\u0420': 'p', '\u0421': 'c', '\u0422': 't', '\u0425': 'x',
        # Greek lowercase lookalikes
        '\u03b1': 'a', '\u03b2': 'b', '\u03b3': 'g', '\u03b5': 'e', '\u03b9': 'i', '\u03ba': 'k', '\u03bd': 'v', '\u03bf': 'o', '\u03c1': 'p', '\u03c4': 't', '\u03c5': 'u', '\u03c7': 'x', '\u03c9': 'w',
        # Greek uppercase lookalikes
        '\u0391': 'a', '\u0392': 'b', '\u0395': 'e', '\u0397': 'h', '\u0399': 'i', '\u039a': 'k', '\u039c': 'm', '\u039d': 'n', '\u039f': 'o', '\u03a1': 'p', '\u03a4': 't', '\u03a5': 'y', '\u03a6': 'f', '\u03a7': 'x'
    }

    def _translate_homoglyphs(text: str) -> str:
        return "".join(homoglyph_map.get(c, c) for c in text)

    def _strip_accents(text: str) -> str:
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join([c for c in nfkd if not unicodedata.combining(c)])

    # Recursive decoding to peel multiple layers of obfuscation
    def _extract_text_layers(raw_text: str, depth: int = 0) -> set[str]:
        layers = {raw_text}
        if depth >= 3:
            return layers

        # URL Encoding peel
        if "%" in raw_text:
            try:
                decoded_url = urllib.parse.unquote(raw_text)
                if decoded_url != raw_text:
                    layers.update(_extract_text_layers(decoded_url, depth + 1))
            except Exception as e:
                logger.debug("Failed URL layer extraction: %s", e)

        # Hex / Binary peel (optimizado longitud minima >= 10)
        hex_pattern = re.compile(r'(?:0x)?([0-9a-fA-F]{10,})')
        for match in hex_pattern.finditer(raw_text):
            hex_str = match.group(1)
            if len(hex_str) % 2 == 0:
                try:
                    decoded_hex = bytes.fromhex(hex_str).decode('utf-8', errors='ignore')
                    if decoded_hex and any(c.isalnum() for c in decoded_hex):
                        layers.update(_extract_text_layers(decoded_hex, depth + 1))
                except Exception as e:
                    logger.debug("Failed HEX layer extraction: %s", e)

        # Base64 peel
        b64_pattern = re.compile(r'\b[a-zA-Z0-9+/]{8,}=*\b')
        for match in b64_pattern.finditer(raw_text):
            b64_str = match.group(0)
            try:
                missing_padding = len(b64_str) % 4
                if missing_padding:
                    b64_str += '=' * (4 - missing_padding)
                decoded_b64 = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
                if decoded_b64 and any(c.isalnum() for c in decoded_b64):
                    layers.update(_extract_text_layers(decoded_b64, depth + 1))
            except Exception as e:
                logger.debug("Failed B64 layer extraction: %s", e)

        return layers

    # Prohibited antigen tokens
    p_b = "borja"
    p_f = "fernandez"
    p_a = "angulo"

    pii_leak = False
    if "[redacted_pii]" in content_lower:
        pii_leak = True

    if not pii_leak:
        layers = _extract_text_layers(content)
        for layer in layers:
            normalized_content = _translate_homoglyphs(_strip_accents(layer.lower()))
            clean_alpha = re.sub(r"[^a-z0-9]", "", normalized_content)

            if (p_b + p_f + p_a) in clean_alpha:
                pii_leak = True
                break
            elif (p_b + p_f) in clean_alpha:
                pii_leak = True
                break
            elif (p_f + p_a) in clean_alpha:
                pii_leak = True
                break
            else:
                # Check for co-occurrence in proximity
                if re.search(rf"\b{p_b}\b.*?\b{p_f}\b", normalized_content) or \
                   re.search(rf"\b{p_f}\b.*?\b{p_a}\b", normalized_content) or \
                   re.search(rf"\b{p_b}\b.*?\b{p_a}\b", normalized_content):
                    pii_leak = True
                    break

    if pii_leak:
        logger.error("[TaintEngine] P0 SINGULARITY: Host Identity Bleed detected in Taint payload.")
        raise TaintValidationError(
            "SAGA-1 Rejection: Payload contains prohibited Host Identity PII."
        )

    # Bypass check for test environment
    if os.environ.get("CORTEX_NO_TAINT_ENFORCE") == "1":
        return

    # 1. Zero Anergía Guard (Axiom Ω₁₃ / Ω₄)
    check_anergy_and_green_theater(content)

    # -- OWASP Memory Firewall (SAGA-1.5) --
    from cortex.security.memory_firewall import MemoryFirewall
    try:
        _, risk_level, _ = MemoryFirewall.screen_content(content)
    except ValueError as fw_err:
        raise TaintValidationError(f"SAGA-1 Rejection by Memory Firewall: {fw_err}")

    # -- SaaS Bot Inflation Firewall (Substack Crawler Guard) --
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "Email" in data and "Emails opened (6mo)" in data:
            from cortex.guards.substack_crawler_guard import SubstackCrawlerGuard
            try:
                SubstackCrawlerGuard().enforce_saga_contract(data)
            except ValueError as guard_err:
                raise TaintValidationError(f"SAGA-1 Rejection by SaaS Firewall: {guard_err}")
    except (json.JSONDecodeError, TypeError):
        pass

    is_valid = await verify_taint_token(conn, token, content)
    if not is_valid:
        raise TaintValidationError(
            "SAGA-1 Rejection: Valid cryptographically signed CORTEX-TAINT token is required."
        )


def check_anergy_and_green_theater(content: str) -> None:
    """[LEA-OMEGA] Validates content against Axiom Ω₁₃ (Exergy) and Ω₄ (Landauer).
    Rejects stochastic promises and Green Theater."""
    import os
    if os.environ.get("CORTEX_NO_TAINT_ENFORCE") == "1":
        return

    from cortex.guards.exergy_guard import ExergyGuard, LandauerGuard
    try:
        is_sacred = "axiom" in content.lower() or "sacred" in content.lower()
        ExergyGuard().check_thermodynamic_yield(content, project="SYS_ROOT", fact_type="thought")
        LandauerGuard().check_landauer_limit(content, is_sacred=is_sacred)
    except ValueError as exergy_err:
        raise TaintValidationError(f"SAGA-1 Rejection by Thermodynamic Guard: {exergy_err}")




# =====================================================================
# H-IMMUNO-02: Antigen-Signature Routing (MHC)
# =====================================================================
import re


class MHCAntigenRouter:
    """
    C5-REAL Implementation of the Adaptive Immunity Task Router.
    Bypasses LLM coordinator completely by matching deterministic
    SHA3 signatures and Regex Antigens to specific T-Cell Daemons.

    Includes a Dynamic Antigen Evolution loop:
    - Tracks routing misses (when a payload goes to LLM/fallback).
    - If a signature (normalized payload template) repeats >= promotion_threshold times,
      it compiles a new antigen pattern, promotes it to the active mesh, and persists it.
    """

    def __init__(self, db_path=None, dynamic_antigens_path=None, promotion_threshold=3):
        from pathlib import Path

        self._t_cells = {}  # Daemon registry mapping antigen signatures to agent IDs
        self.promotion_threshold = promotion_threshold

        # Paths
        if dynamic_antigens_path is None:
            self.dynamic_antigens_path = Path.home() / ".cortex/dynamic_antigens.json"
        else:
            self.dynamic_antigens_path = Path(dynamic_antigens_path)

        # Signature tracking: signature_string -> {"agent_id": str, "hits": int}
        self._miss_tracker = {}

        # Load pre-compiled/promoted dynamic antigens and static SOTA constraints
        self._load_static_antigens()
        self._load_dynamic_antigens()

    _SOTA_CACHE = None

    def _load_static_antigens(self):
        """[ULTRATHINK] Decoupled load of Empirical SOTA Vectors from JSON invariant.
        Remediation: Fail-closed architecture, memoization, and hard apoptosis on failure.
        """
        if MHCAntigenRouter._SOTA_CACHE is not None:
            for item in MHCAntigenRouter._SOTA_CACHE:
                self.register_t_cell(item["agent_id"], item["pattern"])
            return

        from pathlib import Path

        sota_path = Path(__file__).parent / "sota_antigens.json"

        if not sota_path.exists():
            raise TaintValidationError(f"UltraThink P0: SOTA invariant file missing at {sota_path}")

        try:
            with open(sota_path, encoding="utf-8") as f:
                data = json.load(f)

            MHCAntigenRouter._SOTA_CACHE = data.get("static_t_cells", [])
            for item in MHCAntigenRouter._SOTA_CACHE:
                self.register_t_cell(item["agent_id"], item["pattern"])

            logger.info(f"[MHC] Loaded and cached SOTA static antigens from {sota_path.name}")
        except json.JSONDecodeError as e:
            logger.error(f"[MHC] UltraThink P0: JSON syntax corruption in static antigens: {e}")
            raise TaintValidationError("SOTA invariant file corrupted. Apoptosis triggered.") from e
        except (OSError, KeyError, TypeError) as e:
            logger.error(f"[MHC] UltraThink P0: Structural failure loading static antigens: {e}")
            raise TaintValidationError("MHC static routing failure.") from e

    def _load_dynamic_antigens(self):
        """Loads previously promoted dynamic antigens from local storage."""
        if not self.dynamic_antigens_path.exists():
            return
        try:
            with open(self.dynamic_antigens_path, encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("promoted_antigens", []):
                    agent_id = item["agent_id"]
                    pattern = item["pattern"]
                    self.register_t_cell(agent_id, pattern)
            logger.info(f"[MHC] Loaded dynamic antigens from {self.dynamic_antigens_path}")
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
            logger.error(f"[MHC] Failed to load dynamic antigens: {e}")

    def _save_dynamic_antigens(self):
        """Persists promoted dynamic antigens to local storage."""
        try:
            self.dynamic_antigens_path.parent.mkdir(parents=True, exist_ok=True)
            promoted_list = []
            for agent_id, pattern in self._t_cells.items():
                promoted_list.append({"agent_id": agent_id, "pattern": pattern.pattern})
            with open(self.dynamic_antigens_path, "w", encoding="utf-8") as f:
                json.dump({"promoted_antigens": promoted_list}, f, indent=2)
            logger.info(f"[MHC] Successfully persisted antigens to {self.dynamic_antigens_path}")
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
            logger.error(f"[MHC] Failed to persist dynamic antigens: {e}")

    def register_t_cell(self, agent_id: str, antigen_regex: str):
        """Registers a specific daemon to awaken ONLY upon antigen detection."""
        self._t_cells[agent_id] = re.compile(antigen_regex, re.IGNORECASE)
        logger.info(f"[MHC] T-Cell {agent_id} bound to antigen pattern: {antigen_regex}")

    def present_antigen(self, payload: str) -> str | None:
        """
        Phagocytizes the raw payload and attempts MHC presentation.
        Zero tokens consumed. Returns assigned agent_id or None.
        """
        canonical = canonicalize_content(payload)
        payload_hash = _fast_sha3(canonical)[:12]

        for agent_id, antigen_pattern in self._t_cells.items():
            if antigen_pattern.search(payload):
                logger.info(f"[MHC] Antigen match! Signature {payload_hash} triggers {agent_id}")
                return agent_id

        logger.warning(f"[MHC] No T-Cell match for antigen signature {payload_hash}")
        return None

    def record_miss(self, payload: str, resolved_agent_id: str) -> bool:
        """
        Records a routing miss where the mesh failed to match, but an agent was resolved.
        If hits for this normalized signature >= threshold, promotes it to the active mesh.
        Returns True if promoted, False otherwise.
        """
        # Clean/normalize template to catch structural recurrence
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", payload.lower())
        sig = " ".join(cleaned.split())
        if not sig:
            return False

        if sig not in self._miss_tracker:
            self._miss_tracker[sig] = {"agent_id": resolved_agent_id, "hits": 0}

        self._miss_tracker[sig]["hits"] += 1
        hits = self._miss_tracker[sig]["hits"]

        logger.info(
            f"[MHC] Miss recorded for signature: '{sig[:40]}...' -> resolved to {resolved_agent_id} "
            f"(hits: {hits}/{self.promotion_threshold})"
        )

        if hits >= self.promotion_threshold:
            escaped_sig = re.escape(sig)
            pattern = rf"(?i)\b{escaped_sig}\b"

            logger.info(
                f"[MHC] 🔥 PROMOTING ANTIGEN to active mesh: {pattern} -> {resolved_agent_id}"
            )
            self.register_t_cell(resolved_agent_id, pattern)
            self._save_dynamic_antigens()

            self._miss_tracker.pop(sig, None)
            return True

        return False


# =====================================================================
# APEX KERNEL INTEGRATION (P0)
# =====================================================================


def secure_state_commit(content: str, metadata: dict) -> tuple:
    """
    [C5-REAL] Finalizes the Write-Path by invoking the ApexDispatcher.
    Freezes the state dictionary to prevent mutability (OP_FREEZE_MEM),
    and executes the Git Sentinel (OP_GIT_SENTINEL) to ensure cryptographic continuity
    of the Sparse Merkle Tree hash chain.
    """
    from cortex.agents.primitives.dispatcher import apex_dispatcher

    # 1. Structural Freeze (Immutable)
    frozen_state = apex_dispatcher.execute(
        "OP_FREEZE_MEM", state={"content": content, "metadata": metadata, "crystallized": True}
    )

    # 2. Cryptographic Persistence
    agent_id = metadata.get("agent_id", "SYS_ROOT")
    commit_msg = f"CORTEX-TAINT: Causal state commit for [{agent_id}]"

    logger.info(f"[TaintEngine] Enforcing OP_GIT_SENTINEL for agent {agent_id}")
    # UltraThink Fix: force=False prevents git add -f . which hangs scanning massive .venv and adds ignored files.
    hash_ledger = apex_dispatcher.execute("OP_GIT_SENTINEL", commit_msg=commit_msg, force=False)

    logger.info(f"[TaintEngine] State collapsed successfully. Ledger Hash: {hash_ledger}")

    return frozen_state, hash_ledger
