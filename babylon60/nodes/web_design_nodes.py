#!/usr/bin/env python3
"""
cortex/nodes/web_design_nodes.py
═══════════════════════════════════════════════════════════════
WEB-DESIGN-1000: 1000 Primitivas del Diseño Web
Motor de inyección en el DAG epistémico C5-REAL (Cortex-Persist)
═══════════════════════════════════════════════════════════════
Protocolo: C5-REAL | AX-041 Trazabilidad Criptográfica
Restricción: Base-1000 Combinatorial deterministic matrix
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from babylon60.database.core import connect as db_connect


class Criticality(Enum):
    CRITICAL = "CRÍTICO"
    HIGH = "ALTO"
    MASTERY = "MAESTRÍA"

class Block(Enum):
    B1_DOM = "B1"
    B2_LAYOUT = "B2"
    B3_TYPO = "B3"
    B4_COLOR = "B4"
    B5_MOTION = "B5"
    B6_RESPONSIVE = "B6"
    B7_A11Y = "B7"
    B8_WEBGL = "B8"
    B9_CWV = "B9"
    B10_TOKENS = "B10"

BLOCK_METADATA = {
    Block.B1_DOM: {"name": "DOM & Semantics", "crit": Criticality.CRITICAL},
    Block.B2_LAYOUT: {"name": "Box Model & Grid", "crit": Criticality.CRITICAL},
    Block.B3_TYPO: {"name": "Typography & Fonts", "crit": Criticality.HIGH},
    Block.B4_COLOR: {"name": "Color Theory & Theming", "crit": Criticality.HIGH},
    Block.B5_MOTION: {"name": "Micro-Interactions", "crit": Criticality.MASTERY},
    Block.B6_RESPONSIVE: {"name": "Responsive Dynamics", "crit": Criticality.CRITICAL},
    Block.B7_A11Y: {"name": "Accessibility & ARIA", "crit": Criticality.HIGH},
    Block.B8_WEBGL: {"name": "Spatial & Canvas", "crit": Criticality.MASTERY},
    Block.B9_CWV: {"name": "Core Web Vitals", "crit": Criticality.CRITICAL},
    Block.B10_TOKENS: {"name": "Design Tokens", "crit": Criticality.HIGH},
}

@dataclass
class WebDesignNode:
    id: str
    index: int
    name: str
    block: str
    block_name: str
    criticality: str
    dependencies: list[str] = field(default_factory=list)
    verification_method: str = ""
    validation_status: str = "PENDING"
    hash: str = ""
    injected_at: str = ""

    def compute_hash(self) -> str:
        payload = f"{self.id}|{self.name}|{self.block}|{','.join(sorted(self.dependencies))}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def __post_init__(self):
        self.hash = self.compute_hash()
        if not self.injected_at:
            self.injected_at = datetime.now(timezone.utc).isoformat()

def _id(n: int) -> str:
    return f"WEB-DESIGN-{n:04d}"

def _deps(*indices: int) -> list[str]:
    return [_id(i) for i in indices]

def generate_1000_nodes() -> list[WebDesignNode]:
    """Generador combinatorio determinista de 1000 nodos (10 bloques de 100)."""
    nodes = []
    
    # Base dictionary for combinatorial generation
    vocab = {
        Block.B1_DOM: ["<main>", "<article>", "<section>", "<nav>", "<header>", "<footer>", "<dialog>", "<picture>", "<svg>", "Shadow DOM"],
        Block.B2_LAYOUT: ["display: flex", "display: grid", "grid-template-areas", "gap", "align-items", "justify-content", "box-sizing", "position: absolute", "z-index", "inset"],
        Block.B3_TYPO: ["font-family", "font-weight", "line-height", "letter-spacing", "text-transform", "clamp()", "ch units", "rem units", "text-wrap: balance", "font-variant"],
        Block.B4_COLOR: ["oklch()", "hsl()", "color-mix()", "linear-gradient", "radial-gradient", "box-shadow", "mix-blend-mode", "backdrop-filter", "prefers-color-scheme", "currentColor"],
        Block.B5_MOTION: ["transition", "transform: translate", "transform: scale", "transform: rotate", "animation-name", "keyframes", "cubic-bezier", "will-change", "view-timeline", "scroll-timeline"],
        Block.B6_RESPONSIVE: ["@media", "@container", "cqi units", "cqw units", "min-width", "max-width", "aspect-ratio", "object-fit", "flex-wrap", "grid-auto-flow"],
        Block.B7_A11Y: ["aria-label", "aria-hidden", "aria-expanded", "role=", "tabindex", ":focus-visible", ":focus-within", "sr-only class", "prefers-reduced-motion", "contrast ratio"],
        Block.B8_WEBGL: ["Canvas 2D", "WebGL Context", "requestAnimationFrame", "Shader Program", "Uniforms", "Attributes", "Three.js Scene", "Geometry", "Material", "Texture"],
        Block.B9_CWV: ["LCP", "FID", "CLS", "INP", "TTFB", "Rel preload", "Rel preconnect", "Lazy loading", "Async/Defer", "Brotli/Gzip"],
        Block.B10_TOKENS: ["--color-primary", "--color-surface", "--spacing-md", "--radius-lg", "--shadow-elevation", "--z-layer-modal", "--font-body", "--duration-fast", "--ease-out", "--border-subtle"],
    }
    
    actions = ["Initialize", "Validate", "Optimize", "Compose", "Inject", "Bind", "Isolate", "Transform", "Compute", "Paint"]

    global_index = 1
    
    for block in Block:
        meta = BLOCK_METADATA[block]
        bases = vocab[block]
        
        # Generamos 100 nodos por bloque combinando actions y bases
        for action in actions:
            for base in bases:
                node_name = f"{action} {base}"
                
                # Causal dependencies (prev node, except for first node of block)
                deps = []
                if global_index > 1:
                    deps.append(global_index - 1)
                
                # Verif method
                verif = f"Visual/AST assertion for {base}"
                if block == Block.B9_CWV:
                    verif = f"Lighthouse/Chrome DevTools metric for {base}"
                elif block == Block.B7_A11Y:
                    verif = f"Accessibility Tree audit for {base}"
                
                node = WebDesignNode(
                    id=_id(global_index),
                    index=global_index,
                    name=node_name,
                    block=block.value,
                    block_name=meta["name"],
                    criticality=meta["crit"].value,
                    dependencies=_deps(*deps) if deps else [],
                    verification_method=verif,
                )
                nodes.append(node)
                global_index += 1

    return nodes

class CortexPersist:
    def __init__(self, db_path: str = "babylon60.db"):
        self.db_path = Path(db_path)
        self.conn = db_connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS web_design_nodes (
                id TEXT PRIMARY KEY,
                idx INTEGER NOT NULL,
                name TEXT NOT NULL,
                block TEXT NOT NULL,
                block_name TEXT NOT NULL,
                criticality TEXT NOT NULL,
                dependencies TEXT NOT NULL,
                verification_method TEXT NOT NULL,
                validation_status TEXT NOT NULL DEFAULT 'PENDING',
                hash TEXT NOT NULL,
                injected_at TEXT NOT NULL
            );
        """)
        self.conn.commit()

    def inject_nodes(self, nodes: list[WebDesignNode]) -> dict:
        injected, updated = 0, 0
        for node in nodes:
            existing = self.conn.execute(
                "SELECT hash FROM web_design_nodes WHERE id = ?", (node.id,)
            ).fetchone()

            if existing is None:
                self.conn.execute("""
                    INSERT INTO web_design_nodes
                    (id, idx, name, block, block_name, criticality,
                     dependencies, verification_method, validation_status,
                     hash, injected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node.id, node.index, node.name, node.block,
                    node.block_name, node.criticality,
                    json.dumps(node.dependencies),
                    node.verification_method, node.validation_status,
                    node.hash, node.injected_at
                ))
                injected += 1
            elif existing[0] != node.hash:
                self.conn.execute("""
                    UPDATE web_design_nodes
                    SET name=?, block=?, block_name=?, criticality=?,
                        dependencies=?, verification_method=?,
                        hash=?, injected_at=?
                    WHERE id=?
                """, (
                    node.name, node.block, node.block_name,
                    node.criticality, json.dumps(node.dependencies),
                    node.verification_method, node.hash,
                    node.injected_at, node.id
                ))
                updated += 1

        self.conn.commit()
        return {"injected": injected, "updated": updated, "total": len(nodes)}

    def close(self):
        self.conn.close()

def main():
    print("=" * 70)
    print("🕸️  WEB-DESIGN: Inyección de 1000 Primitivas en C5-REAL DAG")
    print("=" * 70)

    nodes = generate_1000_nodes()
    print(f"[1/2] Construidas {len(nodes)} primitivas de Web Design.")

    db = CortexPersist("babylon60.db")
    result = db.inject_nodes(nodes)
    print(f"[2/2] Inyección DB completada: Nuevos={result['injected']} | Actualizados={result['updated']}")
    db.close()
    
    print("✅ MATRIZ ESTRUCTURAL DOM/CSS/CWV PREPARADA")

if __name__ == "__main__":
    main()
