import ast
import logging
import re
from typing import Any

logger = logging.getLogger("cortex.extensions.security.t_cell")


class BabestuTCell:
    """
    LENTE 4: CERO CONFIANZA.
    Escáner estático (AST-level) y heurístico O(1).
    Filtra la inyección antes de que alcance al sistema vascular (PULMONES/Haiku).
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

    # Expresiones para ofuscación y esteganografía
    B64_HEURISTIC = re.compile(r"([A-Za-z0-9+/]{200,}={0,2})")
    HEX_HEURISTIC = re.compile(r"(\\x[0-9a-fA-F]{2}){15,}")

    @classmethod
    def analyze_python_ast(cls, code: str) -> tuple[bool, str]:
        """Convierte en AST y busca vectores letales en O(N) de los nodos."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Si ni siquiera es Python válido, lo dejamos pasar por el AST.
            # El analizador semántico del LLM se encargará si es basura.
            return True, ""

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in cls.FORBIDDEN_CALLS:
                    return (
                        False,
                        f"Llamada a ejecución dinámica o sistema prohibida: {node.func.id}()",
                    )
                elif isinstance(node.func, ast.Attribute) and node.func.attr in cls.FORBIDDEN_CALLS:
                    return False, f"Invocación de atributo prohibida: {node.func.attr}()"

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in cls.FORBIDDEN_IMPORTS:
                        return False, f"Importación bélica/red prohibida: {alias.name}"

            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in cls.FORBIDDEN_IMPORTS:
                    return False, f"Importación relativa/bélica prohibida: {node.module}"

        return True, ""

    @classmethod
    def scan_payload(cls, raw_text: str, source_url: str = "") -> dict[str, Any]:
        """
        Punto de entrada O(1).
        1. Busca ofuscaciones superficiales (Base64, Hex).
        2. Extrae bloques de código (Python).
        3. Realiza la autopsia del AST.
        """
        is_youtube = "youtube.com" in source_url or "youtu.be" in source_url

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
                    "CONTAMINADO", 100, "AST_Static_Lethal_Vector", f"Bloque {idx}: {reason}"
                )

        return cls._veredicto(
            "LIMPIO", 0, None, "AST estático y heurísticas O(1) superadas", raw_text
        )

    @staticmethod
    def _veredicto(
        estado: str, nivel: int, firma: str | None, razon: str, contenido_saneado: str | None = None
    ) -> dict[str, Any]:
        return {
            "estado": estado,
            "nivel_amenaza": nivel,
            "firma_ataque": firma,
            "razon": razon,
            "contenido_saneado": contenido_saneado if estado == "LIMPIO" else None,
        }
