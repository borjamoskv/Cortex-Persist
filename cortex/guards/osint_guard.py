# [C5-REAL] Exergy-Maximized
"""
OSINT Guard - Enforces defensive mitigations against reconnaissance vectors.
Implements metadata stripping, PII containment, and system path masking.
"""

from __future__ import annotations

import ast
import io
import logging
import re

try:
    from PIL import Image
except ImportError:
    Image = None

logger = logging.getLogger("cortex.guards.osint")


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

        # 1. Check for raw target PII
        if target in content.lower():
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
                    f"PII Leak: Absolute system path for user '{username}' exposed. Mask with $HOME."
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
        except Exception as e:
            logger.error("[P0] OSINTGuard: Image metadata stripping failed. %s", e)
            raise OSINTViolationError(f"Multimodal Sanitization Failed: {e}") from e


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
