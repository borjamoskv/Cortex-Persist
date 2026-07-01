import hashlib
import json
import sys
from dataclasses import dataclass
from enum import Enum


# LL-AC-01 · Invariante de Tipado Estricto
class Componente(str, Enum):
    AST = "AST"
    CTX = "CTX"
    DOM = "DOM"
    LED = "LED"
    MEM = "MEM"
    NET = "NET"
    PRM = "PRM"
    SWR = "SWR"
    THR = "THR"
    VEC = "VEC"

class Accion(str, Enum):
    Colapso = "Colapso"
    Composicion = "Composicion"
    Aislamiento = "Aislamiento"
    Acotamiento = "Acotamiento"
    Mapeo = "Mapeo"
    Preservacion = "Preservacion"

@dataclass(frozen=True)
class PrimitivaBFT:
    accion: Accion
    componente: Componente

    @property
    def identifier(self) -> str:
        # e.g. PRIM-BFT-COL-AST
        return f"PRIM-BFT-{self.accion.name[:3].upper()}-{self.componente.value}"

    @property
    def sha3_256_hash(self) -> str:
        # CORTEX-TAINT compliant hashing (SHA3-256)
        return hashlib.sha3_256(self.identifier.encode()).hexdigest()

class OntologiaParser:
    @staticmethod
    def parse_file(filepath: str) -> list[PrimitivaBFT]:
        try:
            with open(filepath) as f:
                data = json.load(f)
            
            primitivas = []
            for item in data.get("primitives", []):
                # Extraemos de item["operation"] e item["target"] si existe, o usamos fallbacks
                op = item.get("operation", "Colapso")
                tgt = item.get("target", "AST")
                
                # Mapeo crudo (heurística simple para C5-REAL)
                accion_enum = Accion.Colapso
                for a in Accion:
                    if a.value.lower() in op.lower():
                        accion_enum = a
                        break
                        
                comp_enum = Componente.AST
                for _c in Componente:
                    # Mapeo simple de siglas
                    if tgt == "Árbol de Sintaxis Abstracta": comp_enum = Componente.AST
                    elif tgt == "Memoria Persistente (SQLite)": comp_enum = Componente.MEM
                    elif tgt == "Ventana de Contexto": comp_enum = Componente.CTX
                    elif tgt == "Espacio Vectorial": comp_enum = Componente.VEC
                    elif tgt == "Hilo de Ejecución": comp_enum = Componente.THR
                    elif tgt == "Enjambre de Agentes": comp_enum = Componente.SWR
                    elif tgt == "Ledger Criptográfico": comp_enum = Componente.LED
                    elif tgt == "Prompt / Inyección Causal": comp_enum = Componente.PRM
                    elif tgt == "Grafo DOM / Interfaz": comp_enum = Componente.DOM
                    elif tgt == "Topología de Red": comp_enum = Componente.NET

                prim = PrimitivaBFT(accion=accion_enum, componente=comp_enum)
                primitivas.append(prim)
            return primitivas
        except Exception as e:
            # LL-AC-03 Error Containment / Fail Fast
            print(f"[P0 ABORT] Fractura Termodinámica en Parseo JSON: {e}")
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python parse_primitives_c5.py <ruta_al_json>")
        sys.exit(1)
        
    filepath = sys.argv[1]
    print(f"[*] C5-REAL Init: Colapsando entropía de {filepath}...")
    
    primitivas = OntologiaParser.parse_file(filepath)
    print(f"[*] Exergía pura: {len(primitivas)} primitivas matriciales inmutables generadas en memoria.")
    
    print("\n[!] Muestra Estructural (Primeros 5 nodos):")
    for prim in primitivas[:5]:
        print(f" -> {prim.identifier:<20} | SHA3-256: {prim.sha3_256_hash[:16]}")
