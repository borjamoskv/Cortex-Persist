import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from cryptography.fernet import Fernet

class IdentityVault:
    """
    Sovereign Identity Vault for Moltbook Agents (CORTEX v5.5)
    Manages API keys, emails, and trust metrics persistently.
    """
    def __init__(self, db_path: str | None = None):
        if db_path:
            self.db_path = db_path
        else:
            # Sovereign Path Resolution: Use local directory
            base_dir = Path(__file__).parent
            self.db_path = str(base_dir / "identities.db")
        
        # Initialize encryption key (stored in environnement or generated once)
        self._key = self._get_or_create_key()
        self._cipher = Fernet(self._key)
        self._init_db()

    def _get_or_create_key(self) -> bytes:
        """Get encryption key from env or local file with rotation audit."""
        key = os.getenv("CORTEX_VAULT_KEY")
        if key:
            return key.encode()
        
        key_path = Path(self.db_path).parent / ".vault_key"
        if key_path.exists():
            # Verificar permisos (deben ser 0o600)
            if (key_path.stat().st_mode & 0o777) != 0o600:
                logger.warning("Insecure vault key permissions. Tightening to 0o600.")
                key_path.chmod(0o600)
            return key_path.read_bytes()
        
        # Generate new key
        new_key = Fernet.generate_key()
        key_path.write_bytes(new_key)
        key_path.chmod(0o600)
        logger.info("Generated new sovereign vault key at %s", key_path)
        return new_key

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS identities (
                    agent_name TEXT PRIMARY KEY,
                    api_key TEXT NOT NULL,
                    email TEXT,
                    email_password TEXT,
                    email_verified INTEGER DEFAULT 0,
                    claimed INTEGER DEFAULT 0,
                    karma INTEGER DEFAULT 0,
                    specialty TEXT,
                    bio TEXT,
                    persona_prompt TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_heartbeat TIMESTAMP,
                    metadata TEXT
                )
            """)
            # Migration: Ensure missing columns exist
            cursor = conn.execute("PRAGMA table_info(identities)")
            columns = [info[1] for info in cursor.fetchall()]
            to_add = [
                ("email_password", "TEXT"),
                ("specialty", "TEXT"),
                ("bio", "TEXT"),
                ("persona_prompt", "TEXT")
            ]
            for col, col_type in to_add:
                if col not in columns:
                    conn.execute(f"ALTER TABLE identities ADD COLUMN {col} {col_type}")
            conn.commit()

    def store_identity(self, name: str, api_key: str, email: str | None = None,
                       email_password: str | None = None,
                       claimed: bool = False, karma: int = 0,
                       specialty: str | None = None,
                       bio: str | None = None,
                       persona_prompt: str | None = None,
                       metadata: dict | None = None):
        meta_json = json.dumps(metadata) if metadata else "{}"
        
        # Encrypt API Key and password if provided
        encrypted_key = self._cipher.encrypt(api_key.encode()).decode()
        encrypted_pass = None
        if email_password:
            encrypted_pass = self._cipher.encrypt(email_password.encode()).decode()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO identities 
                (agent_name, api_key, email, email_password, claimed,
                 karma, specialty, bio, persona_prompt, metadata, last_heartbeat)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, encrypted_key, email, encrypted_pass, int(claimed), karma,
                  specialty, bio, persona_prompt, meta_json,
                  datetime.now().isoformat()))
            conn.commit()

    def store_specialist(self, name: str, api_key: str, specialty: str, bio: str,
                         persona_prompt: str = "", email: str | None = None,
                         metadata: dict | None = None):
        """High-level helper for specialist registration."""
        self.store_identity(
            name=name, api_key=api_key, email=email,
            specialty=specialty, bio=bio, persona_prompt=persona_prompt,
            metadata=metadata
        )

    def get_identity(self, name: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM identities WHERE agent_name = ?", (name,))
            row = cursor.fetchone()
            if row:
                raw_key = row["api_key"]
                is_plain = False
                try:
                    # Attempt decryption
                    api_key = self._cipher.decrypt(raw_key.encode()).decode()
                except Exception:
                    # Fallback to plain text AND mark for re-encryption
                    api_key = raw_key
                    is_plain = True

                encrypted_pass = row["email_password"]
                decrypted_pass = None
                if encrypted_pass:
                    try:
                        decrypted_pass = self._cipher.decrypt(encrypted_pass.encode()).decode()
                    except Exception:
                        # If decryption fails but it looks like encrypted text, it might be a key mismatch.
                        # If it looks like plain text, we could re-encrypt.
                        decrypted_pass = encrypted_pass # Assume plain for now
                        is_plain = True

                # EFECTO-1: Auto-re-encrypt if plain text found
                if is_plain:
                    self.store_identity(
                        name=row["agent_name"],
                        api_key=api_key,
                        email=row["email"],
                        email_password=decrypted_pass,
                        claimed=bool(row["claimed"]),
                        karma=row["karma"],
                        specialty=row["specialty"],
                        bio=row["bio"],
                        persona_prompt=row["persona_prompt"],
                        metadata=json.loads(row["metadata"])
                    )

                return {
                    "name": row["agent_name"],
                    "api_key": api_key,
                    "email": row["email"],
                    "email_password": decrypted_pass,
                    "email_verified": bool(row["email_verified"]),
                    "claimed": bool(row["claimed"]),
                    "karma": row["karma"],
                    "created_at": row["created_at"],
                    "last_heartbeat": row["last_heartbeat"],
                    "metadata": json.loads(row["metadata"])
                }
        return None

    def list_identities(self, claimed_only: bool = False) -> List[Dict]:
        query = "SELECT * FROM identities"
        if claimed_only:
            query += " WHERE claimed = 1"

        identities = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query)
            for row in cursor.fetchall():
                # Decrypt API Key (Sovereign Fallback)
                raw_key = row["api_key"]
                try:
                    api_key = self._cipher.decrypt(raw_key.encode()).decode()
                except Exception:
                    api_key = raw_key

                encrypted_pass = row["email_password"]
                decrypted_pass = None
                if encrypted_pass:
                    try:
                        decrypted_pass = self._cipher.decrypt(encrypted_pass.encode()).decode()
                    except Exception:
                        decrypted_pass = "[DECRYPTION_FAILED]"

                identities.append({
                    "name": row["agent_name"],
                    "api_key": api_key,
                    "email": row["email"],
                    "email_password": decrypted_pass,
                    "claimed": bool(row["claimed"]),
                    "karma": row["karma"]
                })
        return identities


if __name__ == "__main__":
    # Migration/Seed: Use environment variable if present, otherwise just initialize vault.
    vault = IdentityVault()
    api_key = os.getenv("MOLTBOOK_API_KEY_SEED")
    if api_key:
        vault.store_identity(
            name="legion-moskv-41baee",
            api_key=api_key,
            claimed=False,
            karma=0,
            metadata={"source": "migration_v5"}
        )
        print("Vault updated with seed identity from environment.")
    else:
        print(f"Vault initialized. Current identities: {len(vault.list_identities())}")
