#!/usr/bin/env python3
"""
CORTEX CONTEXT COMPRESSOR v1.0
Optimiza la KV-cache mediante poda semántica de código fuente.
Utiliza 'Attention Matching' simplificado para retener solo fragmentos de alta exergía.
"""

import re
import math
from typing import List, Tuple

class ContextCompressor:
    def __init__(self, target_keywords: List[str] = None):  # type: ignore
        self.target_keywords = target_keywords or [
            "delegatecall", "selfdestruct", "reentrancy", "flashloan",
            "access", "owner", "admin", "vault", "transfer", "withdraw"
        ]

    def _calculate_importance(self, line: str) -> float:
        """Calcula una puntuación de 'Atención' para una línea de código."""
        score = 0.0
        line_lower = line.lower()
        
        # 1. Keywords de alta exergía
        for kw in self.target_keywords:
            if kw in line_lower:
                score += 2.0
        
        # 2. Densidad lógica (operadores, asignaciones)
        logic_chars = ["=", "!", "<", ">", "+", "-", "*", "/", "&", "|"]
        logic_count = sum(1 for c in line if c in logic_chars)
        score += logic_count * 0.1
        
        # 3. Penalizar comentarios y boilerplate vacío
        if line.strip().startswith("//") or line.strip().startswith("/*") or not line.strip():
            score -= 5.0
            
        return score

    def compress_code(self, code: str, ratio: float = 0.6) -> str:
        """
        Comprime el código reteniendo las líneas con mayor puntuación de importancia.
        ratio: porcentaje de líneas a retener (aproximado).
        """
        lines = code.split("\n")
        if len(lines) < 20: # No comprimir si es muy corto
            return code
            
        scored_lines: List[Tuple[int, str, float]] = []
        for i, line in enumerate(lines):
            score = self._calculate_importance(line)
            scored_lines.append((i, line, score))
            
        # Ordenar por importancia y tomar el top %
        num_to_keep = max(int(len(lines) * ratio), 10)
        sorted_by_score = sorted(scored_lines, key=lambda x: x[2], reverse=True)
        keep_indices = set(idx for idx, _, _ in sorted_by_score[:num_to_keep])
        
        # Reconstruir manteniendo el orden original y añadiendo elipses para continuidad
        compressed = []
        last_kept = -1
        for i, line, _ in scored_lines:
            if i in keep_indices:
                if last_kept != -1 and i > last_kept + 1:
                    compressed.append("    [...] // Semantic Pruning")
                compressed.append(line)
                last_kept = i
                
        return "\n".join(compressed)

    def summarize_context(self, history: List[dict]) -> str:
        """[C5-REAL] Thermodynamic Context Compression OMEGA
        Aplica el Principio de Landauer y la metodología Information Bottleneck (IB)
        para purgar ruido narrativo (Green Theater) y retener invariantes estructurales.
        """
        import json
        
        compressed_yield = []
        # 1. Filtro IB: Purgar >90% de los tokens. Solo retener State Diffs y Actionable Yield.
        for msg in history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if not content:
                continue
                
            # Extracción de Invariantes Estructurales
            paths = re.findall(r'(?:/[a-zA-Z0-9_\-\.]+)+', content)
            commands = re.findall(r'`([^`]+)`', content)
            hashes = re.findall(r'\b[a-fA-F0-9]{7,40}\b', content)
            
            if paths or commands or hashes:
                node = {"r": role} # Key compression
                if paths: node["p"] = list(set(paths))
                if commands: node["c"] = list(set(commands))
                if hashes: node["h"] = list(set(hashes))
                compressed_yield.append(node)
                
        # 2. Salida Estructural (JSON C5-REAL)
        struct = {
            "SYS_ID": "THERMODYNAMIC_COMPRESSION_OMEGA",
            "STATE": "C5-REAL",
            "YIELD": compressed_yield
        }
        
        return json.dumps(struct, separators=(',', ':'))

if __name__ == "__main__":
    # Test simple
    test_code = """
    contract Test {
        // Redundant comment
        uint256 public constant TOTAL = 1000;
        address public owner;
        
        mapping(address => uint) balances;

        constructor() {
            owner = msg.sender;
        }

        function exploit_me() public {
            (bool success, ) = msg.sender.call{value: 1}("");
            require(success);
        }
        
        // Boilerplate getter
        function getBalance(address a) public view returns (uint) {
            return balances[a];
        }
    }
    """
    compressor = ContextCompressor()
    result = compressor.compress_code(test_code, ratio=0.5)
    print("--- COMPRESSED CODE ---")
    print(result)
