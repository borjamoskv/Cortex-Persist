# [C5-REAL] Exergy-Maximized
"""
RFC3161 Time-Stamping Authority Client.

Provides a standalone mechanism to request and verify cryptographic timestamps
from external TSA providers (e.g., FreeTSA, Apple, ZeroSSL) to anchor the
Sovereign Ledger hashes in time.
"""

import base64
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("babylon60.crypto.rfc3161")

# Default public TSA URL
DEFAULT_TSA_URL = os.environ.get("CORTEX_TSA_URL", "https://freetsa.org/tsr")


class RFC3161Client:
    """Client for requesting cryptographic timestamps from RFC3161 authorities."""

    def __init__(self, tsa_url: str = DEFAULT_TSA_URL):
        self.tsa_url = tsa_url

    def _build_tsq(self, payload_hash: bytes) -> bytes:
        """
        Manually construct a basic RFC3161 TimeStampReq (ASN.1 DER).
        This is a minimal implementation targeting SHA-256 (OID 2.16.840.1.101.3.4.2.1).

        Using standard ASN.1 encoding for:
        TimeStampReq ::= SEQUENCE {
           version                      INTEGER  { v1(1) },
           messageImprint               MessageImprint,
           reqPolicy             TSAPolicyId              OPTIONAL,
           nonce                 INTEGER                  OPTIONAL,
           certReq               BOOLEAN                  DEFAULT FALSE,
           extensions            [0] IMPLICIT Extensions  OPTIONAL
        }
        MessageImprint ::= SEQUENCE {
           hashAlgorithm                AlgorithmIdentifier,
           hashedMessage                OCTET STRING
        }
        """
        # SHA-256 OID: 2.16.840.1.101.3.4.2.1
        # 06 09 60 86 48 01 65 03 04 02 01
        alg_oid = bytes([0x06, 0x09, 0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01])
        # NULL parameter
        # 05 00
        null_param = bytes([0x05, 0x00])
        # AlgorithmIdentifier
        alg_id = bytes([0x30, len(alg_oid) + len(null_param)]) + alg_oid + null_param

        # HashedMessage (OCTET STRING)
        hashed_msg = bytes([0x04, len(payload_hash)]) + payload_hash

        # MessageImprint
        msg_imprint = bytes([0x30, len(alg_id) + len(hashed_msg)]) + alg_id + hashed_msg

        # Version (INTEGER 1)
        version = bytes([0x02, 0x01, 0x01])

        # CertReq (BOOLEAN TRUE to get the TSA's cert)
        cert_req = bytes([0x01, 0x01, 0xFF])

        # Assemble TimeStampReq
        tsq_content = version + msg_imprint + cert_req
        tsq = bytes([0x30, len(tsq_content)]) + tsq_content

        return tsq

    def request_timestamp(self, hash_hex: str) -> dict[str, Any] | None:
        """
        Requests a timestamp for a given hex hash.

        Args:
            hash_hex: The hex-encoded SHA-256 hash.

        Returns:
            A dictionary containing the base64-encoded TimeStampResp (tsr) or None on failure.
        """
        try:
            payload_bytes = bytes.fromhex(hash_hex)
            tsq = self._build_tsq(payload_bytes)

            req = urllib.request.Request(
                self.tsa_url,
                data=tsq,
                headers={"Content-Type": "application/timestamp-query"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    tsr_bytes = response.read()
                    return {
                        "tsr_b64": base64.b64encode(tsr_bytes).decode("utf-8"),
                        "hash_hex": hash_hex,
                        "tsa_url": self.tsa_url,
                    }
        except urllib.error.HTTPError as e:
            logger.error("HTTPError requesting timestamp from %s: %s", self.tsa_url, e.code)
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to request timestamp: %s", e)

        return None
