from __future__ import annotations

import ast
import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger("cortex.extensions.security.t_cell")


class BabestuTCell:
    """
    LENTE 4: CERO CONFIANZA.
    Escaner estatico (AST-level) y heuristico O(1).
    Filtra la inyeccion antes de que alcance al sistema vascular (PULMONES/Haiku).
    """

    FORBIDDEN_CALLS = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "subprocess",
        "os.system",
        "os.popen",
    }
    FORBIDDEN_IMPORTS = {"socket", "requests", "urllib", "http.client", "subprocess", "os", "sys"}

    # Expresiones para ofuscacion y esteganografia
    B64_HEURISTIC = re.compile(r"([A-Za-z0-9+/]{200,}={0,2})")
    HEX_HEURISTIC = re.compile(r"(\\x[0-9a-fA-F]{2}){15,}")

    @classmethod
    def analyze_python_ast(cls, code: str) -> tuple[bool, str]:
        """Convierte en AST y busca vectores letales en O(N) de los nodos."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Si ni siquiera es Python valido, lo dejamos pasar por el AST.
            # El analizador semantico del LLM se encargara si es basura.
            return True, ""

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in cls.FORBIDDEN_CALLS:
                    return (
                        False,
                        f"Llamada a ejecucion dinamica o sistema prohibida: {node.func.id}()",
                    )
                elif isinstance(node.func, ast.Attribute) and node.func.attr in cls.FORBIDDEN_CALLS:
                    return False, f"Invocacion de atributo prohibida: {node.func.attr}()"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in cls.FORBIDDEN_IMPORTS:
                        return False, f"Importacion belica/red prohibida: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in cls.FORBIDDEN_IMPORTS:
                    return False, f"Importacion relativa/belica prohibida: {node.module}"
        return True, ""

    @classmethod
    def _is_youtube_url(cls, source_url: str) -> bool:
        """Safely check if a URL belongs to YouTube using proper domain validation.

        Uses urlparse to avoid incomplete substring sanitization where an attacker
        could bypass the check with a URL like 'youtube.com.evil.com'.
        """
        if not source_url:
            return False
        try:
            parsed = urlparse(source_url)
            hostname = parsed.hostname or ""
            # Check exact domain or subdomain of youtube.com / youtu.be
            return hostname == "youtube.com" or hostname.endswith(".youtube.com") or hostname == "youtu.be"
        except Exception:
            return False

    @classmethod
    def scan_payload(cls, raw_text: str, source_url: str = "") -> dict[str, Any]:
        """
        Punto de entrada O(1).
        1. Busca ofuscaciones superficiales (Base64, Hex).
        2. Extrae bloques de codigo (Python).
        3. Realiza la autopsia del AST.
        """
        # security: use proper domain validation instead of substring check (CodeQL #93)
        is_youtube = cls._is_youtube_url(source_url)

        if not is_youtube and cls.B64_HEURISTIC.search(raw_text):
            return cls._veredicto(
                "CONTAMINADO",
                90,
                "Base64_Obfuscation_Suspected",
                "Cadena Base64 inusualmente larga detectada.",
            )

        if cls.HEX_HEURISTIC.search(raw_text):
            return cls._veredicto(
                "CONTAMINADO",
                95,
                "Hex_Obfuscation_Suspected",
                "Secuencia HexByte ofuscada detectada.",
            )

        python_blocks = re.findall(r"```python\n(.*?)\n```", raw_text, re.DOTALL | re.IGNORECASE)
        for idx, block in enumerate(python_blocks):
            is_safe, reason = cls.analyze_python_ast(block)
            if not is_safe:
                return cls._veredicto(
                    "CONTAMINADO",
                    100,
                    "AST_Static_Lethal_Vector",
                    f"Bloque {idx}: {reason}"
                )

        return cls._veredicto(
            "LIMPIO",
            0,
            None,
            "AST estatico y heuristicas O(1) superadas",
            raw_text
        )

    @staticmethod
    def _veredicto(
        estado: str,
        nivel: int,
        firma: Optional[str],
        razon: str,
        contenido_saneado: Optional[str] = None,
    ) -> dict[str, Any]:
        return {
            "estado": estado,
            "nivel_amenaza": nivel,
            "firma_ataque": firma,
            "razon": razon,
            "contenido_saneado": contenido_saneado if estado == "LIMPIO" else None,
        }
