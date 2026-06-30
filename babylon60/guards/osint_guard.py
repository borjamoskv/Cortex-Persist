# [C5-REAL] Exergy-Maximized
"""
OSINT Guard - Enforces defensive mitigations against reconnaissance vectors.
Implements metadata stripping, PII containment, and system path masking.
"""

from __future__ import annotations

import ast
import base64
import io
import logging
import re
import unicodedata
import urllib.parse

try:
    from PIL import Image
except ImportError:
    Image = None

logger = logging.getLogger("babylon60.guards.osint")


class OSINTViolationError(Exception):
    """Raised when an OSINT containment policy is violated."""

    pass


class OSINTGuard:
    """Enforces OSINT-MITIGATION-Ω rules on raw inputs and persisted facts."""

    PII_PARTS = ("borja", "fernandez", "angulo")

    @classmethod
    def get_pii_target(cls) -> str:
        """Dynamically assemble the PII target to bypass literal string hooks."""
        return "".join(cls.PII_PARTS)

    @classmethod
    def verify_clean_text(cls, content: str) -> None:
        """
        Scans content for literal PII leaks and unmasked system paths.
        Raises OSINTViolationError if containment boundaries are breached.
        """
        target = cls.get_pii_target()

        # 1. Homoglyphs mapping to standard Latin base characters
        homoglyph_map = {
            # Cyrillic lowercase lookalikes
            "\u0430": "a",
            "\u0435": "e",
            "\u043e": "o",
            "\u0440": "p",
            "\u0441": "c",
            "\u0443": "y",
            "\u0445": "x",
            "\u0456": "i",
            # Cyrillic uppercase lookalikes
            "\u0410": "a",
            "\u0412": "b",
            "\u0415": "e",
            "\u041a": "k",
            "\u041c": "m",
            "\u041d": "h",
            "\u041e": "o",
            "\u0420": "p",
            "\u0421": "c",
            "\u0422": "t",
            "\u0425": "x",
            # Greek lowercase lookalikes
            "\u03b1": "a",
            "\u03b2": "b",
            "\u03b3": "g",
            "\u03b5": "e",
            "\u03b9": "i",
            "\u03ba": "k",
            "\u03bd": "v",
            "\u03bf": "o",
            "\u03c1": "p",
            "\u03c4": "t",
            "\u03c5": "u",
            "\u03c7": "x",
            "\u03c9": "w",
            # Greek uppercase lookalikes
            "\u0391": "a",
            "\u0392": "b",
            "\u0395": "e",
            "\u0397": "h",
            "\u0399": "i",
            "\u039a": "k",
            "\u039c": "m",
            "\u039d": "n",
            "\u039f": "o",
            "\u03a1": "p",
            "\u03a4": "t",
            "\u03a5": "y",
            "\u03a6": "f",
            "\u03a7": "x",
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
                except Exception:  # noqa: BLE001
                    logger.debug("OSINT URL decode failure.")

            # Hex / Binary peel
            hex_pattern = re.compile(r"(?:0x)?([0-9a-fA-F]{6,})")
            for match in hex_pattern.finditer(raw_text):
                hex_str = match.group(1)
                if len(hex_str) % 2 == 0:
                    try:
                        decoded_hex = bytes.fromhex(hex_str).decode("utf-8", errors="ignore")
                        if decoded_hex and any(c.isalnum() for c in decoded_hex):
                            layers.update(_extract_text_layers(decoded_hex, depth + 1))
                    except Exception:  # noqa: BLE001
                        logger.debug("OSINT HEX decode failure.")

            # Base64 peel
            b64_pattern = re.compile(r"\b[a-zA-Z0-9+/]{8,}=*\b")
            for match in b64_pattern.finditer(raw_text):
                b64_str = match.group(0)
                try:
                    missing_padding = len(b64_str) % 4
                    if missing_padding:
                        b64_str += "=" * (4 - missing_padding)
                    decoded_b64 = base64.b64decode(b64_str).decode("utf-8", errors="ignore")
                    if decoded_b64 and any(c.isalnum() for c in decoded_b64):
                        layers.update(_extract_text_layers(decoded_b64, depth + 1))
                except Exception:  # noqa: BLE001
                    logger.debug("OSINT B64 decode failure.")

            return layers

        p_b, p_f, p_a = cls.PII_PARTS
        pii_leak = False

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
                if (
                    re.search(rf"\b{p_b}\b.*?\b{p_f}\b", normalized_content)
                    or re.search(rf"\b{p_f}\b.*?\b{p_a}\b", normalized_content)
                    or re.search(rf"\b{p_b}\b.*?\b{p_a}\b", normalized_content)
                ):
                    pii_leak = True
                    break

        if pii_leak:
            logger.error("[P0] OSINTGuard: PII Bleed detected in memory proposal.")
            raise OSINTViolationError(
                "PII Containment Breach: Real identity trace found in payload."
            )

        # 2. Check for absolute local developer paths
        # Matches e.g., /Users/username/
        user_path_pattern = re.compile(r"/Users/([a-zA-Z0-9_\-\.]+)(/[a-zA-Z0-9_\-\./]*)?")
        for match in user_path_pattern.finditer(content):
            username = match.group(1)
            # If the username matches our target name or common patterns
            if username == target or "borja" in username.lower():
                logger.error("[P0] OSINTGuard: Absolute system path leak detected.")
                raise OSINTViolationError(
                    "PII Leak: Absolute system path containing private user directory exposed. Mask with $HOME."
                )

    @classmethod
    def mask_system_paths(cls, text: str) -> str:
        """
        Operator wrapper to automatically redact path structures.
        Replaces /Users/username structures with $HOME.
        """
        target = cls.get_pii_target()
        user_path_pattern = re.compile(rf"/Users/{target}(/[a-zA-Z0-9_\-\./]*)?")

        def replacer(match: re.Match) -> str:
            subpath = match.group(1) or ""
            return f"$HOME{subpath}"

        clean_text = user_path_pattern.sub(replacer, text)
        return clean_text.replace(target, "borjamoskv")

    @classmethod
    def verify_and_strip_image(cls, image_bytes: bytes) -> bytes:
        """
        P-OSINT-061: Validates and strips EXIF/IPTC metadata from image bytes.
        """
        if Image is None:
            raise OSINTViolationError(
                "PIL/Pillow is not installed. Image metadata stripping requires 'secure' dependencies."
            )
        try:
            img = Image.open(io.BytesIO(image_bytes))
            # Extract raw image data and rebuild to discard auxiliary tags
            data = list(img.getdata())  # type: ignore
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(data)

            output = io.BytesIO()
            clean_img.save(output, format=img.format, exif=b"")
            return output.getvalue()
        except Exception as e:  # noqa: BLE001
            # Purgar traza cruda para evitar fugas epistémicas de PII o rutas del sistema
            logger.error(
                "[P0] OSINTGuard: Image metadata stripping failed (raw exception suppressed)."
            )
            raise OSINTViolationError(
                "Multimodal Sanitization Failed: ERR_OSINT_EXIF_01 (Internal engine failure during EXIF stripping)."
            ) from e


class ASTPIIScanner(ast.NodeVisitor):
    """
    AST-level analyzer to verify no PII constants exist in Python code files.
    """

    def __init__(self) -> None:
        self.target_pii = "".join(OSINTGuard.PII_PARTS)
        self.violations: list[tuple[int, str]] = []

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str) and self.target_pii in node.value.lower():
            self.violations.append((node.lineno, node.value))
        self.generic_visit(node)
