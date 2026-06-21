#!/usr/bin/env python3
"""
cortex/nodes/goat_math_nodes.py
═══════════════════════════════════════════════════════════════
GOAT-MATH: 100 Primitivas Matemáticas para IA
Motor de inyección en el DAG epistémico C5-REAL (Cortex-Persist)
═══════════════════════════════════════════════════════════════
Protocolo: C5-REAL | AX-041 Trazabilidad Criptográfica
Restricción: Zero stochastic floats | BFT-compliant
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime, timezone


# ═══════════════════════════════════════════════════════════════
# ENUMS Y TIPOS
# ═══════════════════════════════════════════════════════════════

class Criticality(Enum):
    CRITICAL = "CRÍTICO"
    HIGH = "ALTO"
    MASTERY = "MAESTRÍA"


class ValidationStatus(Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    FAILED = "FAILED"


class Block(Enum):
    B1_LINEAR_ALGEBRA = "B1"
    B2_CALCULUS = "B2"
    B3_PROBABILITY = "B3"
    B4_OPTIMIZATION = "B4"
    B5_INFORMATION_THEORY = "B5"
    B6_DIFFERENTIAL_GEOMETRY = "B6"
    B7_STATISTICAL_LEARNING = "B7"
    B8_MODERN_ARCHITECTURES = "B8"
    B9_ABSOLUTE_FOUNDATIONS = "B9"


BLOCK_METADATA = {
    Block.B1_LINEAR_ALGEBRA: {
        "name": "Álgebra Lineal Avanzada",
        "criticality": Criticality.CRITICAL,
        "range": (1, 10)
    },
    Block.B2_CALCULUS: {
        "name": "Cálculo Multivariable y Diferencial",
        "criticality": Criticality.CRITICAL,
        "range": (11, 20)
    },
    Block.B3_PROBABILITY: {
        "name": "Probabilidad Profunda",
        "criticality": Criticality.CRITICAL,
        "range": (21, 35)
    },
    Block.B4_OPTIMIZATION: {
        "name": "Optimización GOAT",
        "criticality": Criticality.CRITICAL,
        "range": (36, 50)
    },
    Block.B5_INFORMATION_THEORY: {
        "name": "Teoría de Información",
        "criticality": Criticality.HIGH,
        "range": (51, 60)
    },
    Block.B6_DIFFERENTIAL_GEOMETRY: {
        "name": "Geometría Diferencial y Topología",
        "criticality": Criticality.HIGH,
        "range": (61, 70)
    },
    Block.B7_STATISTICAL_LEARNING: {
        "name": "Teoría de Aprendizaje Estadístico",
        "criticality": Criticality.HIGH,
        "range": (71, 80)
    },
    Block.B8_MODERN_ARCHITECTURES: {
        "name": "Arquitecturas Modernas",
        "criticality": Criticality.CRITICAL,
        "range": (81, 90)
    },
    Block.B9_ABSOLUTE_FOUNDATIONS: {
        "name": "Fundamentos Matemáticos Absolutos",
        "criticality": Criticality.MASTERY,
        "range": (91, 100)
    },
}


# ═══════════════════════════════════════════════════════════════
# NODO EPISTÉMICO
# ═══════════════════════════════════════════════════════════════

@dataclass
class GOATMathNode:
    """Nodo epistémico para una primitiva matemática GOAT."""
    id: str                              # GOAT-MATH-001
    index: int                           # 1
    name: str                            # "Descomposición SVD"
    block: str                           # "B1"
    block_name: str                      # "Álgebra Lineal Avanzada"
    criticality: str                     # "CRÍTICO"
    dependencies: List[str] = field(default_factory=list)  # ["GOAT-MATH-004"]
    verification_method: str = ""        # "torch.linalg.svd()"
    validation_status: str = "PENDING"
    hash: str = ""
    injected_at: str = ""

    def compute_hash(self) -> str:
        """Hash determinista BFT-compliant (AX-041)."""
        payload = f"{self.id}|{self.name}|{self.block}|{','.join(sorted(self.dependencies))}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def __post_init__(self):
        self.hash = self.compute_hash()
        if not self.injected_at:
            self.injected_at = datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════
# REGISTRO DE LAS 100 PRIMITIVAS
# ═══════════════════════════════════════════════════════════════

def _id(n: int) -> str:
    return f"GOAT-MATH-{n:03d}"


def _deps(*indices: int) -> List[str]:
    return [_id(i) for i in indices]


def build_all_nodes() -> List[GOATMathNode]:
    """Construye las 100 primitivas GOAT como nodos epistémicos."""

    raw = [
        # ═══ B1: ÁLGEBRA LINEAL AVANZADA ═══
        (1,   "Descomposición SVD",              "B1", [],       "torch.linalg.svd()"),
        (2,   "Descomposición LU",               "B1", [],       "scipy.linalg.lu()"),
        (3,   "Descomposición QR",               "B1", [],       "torch.linalg.qr()"),
        (4,   "Eigendecomposición",              "B1", [],       "torch.linalg.eigh()"),
        (5,   "Pseudoinversa Moore-Penrose",     "B1", [1],      "torch.linalg.pinv()"),
        (6,   "Producto de Kronecker",           "B1", [],       "torch.kron()"),
        (7,   "Norma Frobenius",                 "B1", [],       "torch.norm(M,'fro')"),
        (8,   "Matriz semidefinida positiva",     "B1", [4],      "eigenvalues >= 0"),
        (9,   "Traza de una matriz",             "B1", [],       "torch.trace()"),
        (10,  "Rango numérico",                  "B1", [1],      "torch.linalg.matrix_rank()"),

        # ═══ B2: CÁLCULO MULTIVARIABLE ═══
        (11,  "Gradiente",                       "B2", [],       "torch.autograd.grad()"),
        (12,  "Jacobiano",                       "B2", [11],     "torch.autograd.functional.jacobian()"),
        (13,  "Hessiano",                        "B2", [11,12],  "torch.autograd.functional.hessian()"),
        (14,  "Regla de la cadena generalizada", "B2", [11],     "backprop_test()"),
        (15,  "Derivada direccional",            "B2", [11],     "grad_dot_v_test()"),
        (16,  "Operador Laplaciano",             "B2", [11,13],  "trace_hessian_test()"),
        (17,  "Diferenciación automática",       "B2", [14],     "jax.grad()"),
        (18,  "Serie de Taylor multivariable",   "B2", [11,13],  "taylor_expansion_test()"),
        (19,  "Integral de línea",               "B2", [11],     "numerical_line_integral_test()"),
        (20,  "Transformada de Fourier",         "B2", [],       "torch.fft.fft()"),

        # ═══ B3: PROBABILIDAD PROFUNDA ═══
        (21,  "Inferencia bayesiana",            "B3", [],       "posterior_test()"),
        (22,  "Distribución de Dirichlet",       "B3", [],       "torch.distributions.Dirichlet()"),
        (23,  "Proceso gaussiano",               "B3", [8],      "gpytorch_test()"),
        (24,  "Cadenas de Markov",               "B3", [],       "transition_matrix_test()"),
        (25,  "MCMC (Monte Carlo)",              "B3", [21,24],  "pymc_sampling_test()"),
        (26,  "Divergencia KL",                  "B3", [],       "F.kl_div()"),
        (27,  "Información mutua",               "B3", [26],     "MI_estimation_test()"),
        (28,  "Entropía de Shannon",             "B3", [],       "entropy_computation_test()"),
        (29,  "Distribución de Laplace",         "B3", [],       "torch.distributions.Laplace()"),
        (30,  "Función de partición",            "B3", [28],     "Z_computation_test()"),
        (31,  "Estimación máxima verosimilitud", "B3", [],       "MLE_test()"),
        (32,  "Estimación MAP",                  "B3", [21,31],  "MAP_test()"),
        (33,  "Variables latentes",              "B3", [],       "VAE_latent_test()"),
        (34,  "Algoritmo EM",                    "B3", [31,33],  "EM_convergence_test()"),
        (35,  "Teorema de Bayes jerárquico",     "B3", [21,32],  "hierarchical_model_test()"),

        # ═══ B4: OPTIMIZACIÓN GOAT ═══
        (36,  "Condiciones KKT",                 "B4", [11],     "KKT_solver_test()"),
        (37,  "Método de Newton",                "B4", [11,13],  "newton_convergence_test()"),
        (38,  "Quasi-Newton (L-BFGS)",           "B4", [37],     "torch.optim.LBFGS()"),
        (39,  "Descenso gradiente estocástico",  "B4", [11],     "torch.optim.SGD()"),
        (40,  "Adam optimizer",                  "B4", [39],     "torch.optim.Adam()"),
        (41,  "Adagrad / RMSProp",              "B4", [39],     "torch.optim.RMSprop()"),
        (42,  "Funciones convexas",              "B4", [13],     "convexity_check_test()"),
        (43,  "Funciones no convexas",           "B4", [42],     "saddle_point_test()"),
        (44,  "Paisaje de pérdida",              "B4", [11,43],  "loss_landscape_viz_test()"),
        (45,  "Programación lineal",             "B4", [],       "scipy.optimize.linprog()"),
        (46,  "Programación cuadrática",         "B4", [45],     "cvxpy_QP_test()"),
        (47,  "Multiplicadores de Lagrange",     "B4", [11,36],  "lagrange_test()"),
        (48,  "Gradiente natural",               "B4", [11,57],  "natural_grad_test()"),
        (49,  "Dualidad de Lagrange",            "B4", [47],     "dual_formulation_test()"),
        (50,  "Optim. estocástica variacional",  "B4", [26,39],  "VI_ELBO_test()"),

        # ═══ B5: TEORÍA DE INFORMACIÓN ═══
        (51,  "Entropía cruzada",                "B5", [28],     "F.cross_entropy()"),
        (52,  "Divergencia Jensen-Shannon",      "B5", [26],     "JSD_computation_test()"),
        (53,  "Distancia de Wasserstein",        "B5", [],       "scipy.stats.wasserstein_distance()"),
        (54,  "Capacidad de canal",              "B5", [28],     "channel_capacity_test()"),
        (55,  "Codificación aritmética",         "B5", [28],     "arithmetic_coding_test()"),
        (56,  "Longitud descripción mínima",     "B5", [28,31],  "MDL_test()"),
        (57,  "Información de Fisher",           "B5", [12,31],  "fisher_info_matrix_test()"),
        (58,  "Entropía condicional",            "B5", [28],     "H_Y_given_X_test()"),
        (59,  "Coeficiente de Gini",             "B5", [],       "gini_impurity_test()"),
        (60,  "Ganancia de información",         "B5", [28,58],  "info_gain_test()"),

        # ═══ B6: GEOMETRÍA DIFERENCIAL ═══
        (61,  "Variedad diferenciable",          "B6", [11],     "manifold_chart_test()"),
        (62,  "Espacio de Riemannian",           "B6", [61,8],   "riemannian_metric_test()"),
        (63,  "Curvatura",                       "B6", [13,62],  "curvature_tensor_test()"),
        (64,  "Geodésica",                       "B6", [62],     "geodesic_solver_test()"),
        (65,  "Homeomorfismo",                   "B6", [],       "topological_equiv_test()"),
        (66,  "Análisis topológico (TDA)",       "B6", [65],     "ripser_persistence_test()"),
        (67,  "Flujo de gradiente",              "B6", [11,61],  "gradient_flow_ODE_test()"),
        (68,  "Métrica Riemanniana",             "B6", [62],     "metric_tensor_test()"),
        (69,  "Diffeomorfismo",                  "B6", [65],     "normalizing_flow_bijection_test()"),
        (70,  "Fibrado vectorial",               "B6", [61],     "gauge_equivariant_test()"),

        # ═══ B7: TEORÍA APRENDIZAJE ESTADÍSTICO ═══
        (71,  "Dimensión VC",                    "B7", [],       "VC_bound_test()"),
        (72,  "Complejidad de Rademacher",       "B7", [71],     "rademacher_test()"),
        (73,  "Desigualdad de Hoeffding",        "B7", [],       "hoeffding_bound_test()"),
        (74,  "PAC Learning",                    "B7", [71,73],  "PAC_bound_test()"),
        (75,  "Bias-Variance Tradeoff",          "B7", [],       "bias_variance_decomp_test()"),
        (76,  "Regularización de Tikhonov",      "B7", [5],      "ridge_regression_test()"),
        (77,  "Kernels y RKHS",                  "B7", [8,91],   "kernel_trick_test()"),
        (78,  "Teorema de representación",       "B7", [77],     "representer_theorem_test()"),
        (79,  "Margen en clasificación",         "B7", [77],     "SVM_margin_test()"),
        (80,  "No Free Lunch Theorem",           "B7", [],       "NFL_demonstration()"),

        # ═══ B8: ARQUITECTURAS MODERNAS ═══
        (81,  "Mecanismo de atención",           "B8", [11,82],  "attention_forward_test()"),
        (82,  "Producto escalar escalado",       "B8", [],       "scaled_dot_product_test()"),
        (83,  "Softmax temperature",             "B8", [],       "softmax_temp_test()"),
        (84,  "Convolución discreta",            "B8", [],       "F.conv2d() test"),
        (85,  "FFT",                             "B8", [20],     "torch.fft.fft() perf_test"),
        (86,  "Teoría espectral de grafos",      "B8", [4,16],   "graph_spectrum_test()"),
        (87,  "Laplaciano de grafo",             "B8", [16,86],  "graph_laplacian_test()"),
        (88,  "Ecuaciones diferenciales estoc.", "B8", [11,25],  "SDE_solver_test()"),
        (89,  "Score matching",                  "B8", [11,88],  "score_function_test()"),
        (90,  "Flujos normalizadores",           "B8", [69,26],  "normalizing_flow_nll_test()"),

        # ═══ B9: FUNDAMENTOS ABSOLUTOS ═══
        (91,  "Espacios de Hilbert",             "B9", [],       "inner_product_test()"),
        (92,  "Espacios de Banach",              "B9", [91],     "completeness_test()"),
        (93,  "Teorema de punto fijo",           "B9", [],       "banach_fixed_point_test()"),
        (94,  "Análisis funcional",              "B9", [91,92],  "operator_norm_test()"),
        (95,  "Teoría de medida",                "B9", [],       "sigma_algebra_test()"),
        (96,  "Integral de Lebesgue",            "B9", [95],     "lebesgue_vs_riemann_test()"),
        (97,  "Convergencia en distribución",    "B9", [95],     "CLT_convergence_test()"),
        (98,  "Lema de Fatou",                   "B9", [95,96],  "fatou_inequality_test()"),
        (99,  "Teorema de Radon-Nikodym",        "B9", [95,96],  "density_existence_test()"),
        (100, "Teorema representación Riesz",    "B9", [91,94],  "riesz_functional_test()"),
    ]

    nodes = []
    for idx, name, block_id, deps, verif in raw:
        block_enum = [b for b in Block if b.value == block_id][0]
        meta = BLOCK_METADATA[block_enum]
        node = GOATMathNode(
            id=_id(idx),
            index=idx,
            name=name,
            block=block_id,
            block_name=meta["name"],
            criticality=meta["criticality"].value,
            dependencies=_deps(*deps),
            verification_method=verif,
        )
        nodes.append(node)

    return nodes


# ═══════════════════════════════════════════════════════════════
# VALIDADOR DAG (DETECCIÓN DE CICLOS)
# ═══════════════════════════════════════════════════════════════

class DAGValidator:
    """Valida que el grafo de dependencias sea un DAG acíclico."""

    @staticmethod
    def validate(nodes: List[GOATMathNode]) -> Dict:
        """Topological sort con detección de ciclos."""
        node_map = {n.id: n for n in nodes}
        in_degree = {n.id: 0 for n in nodes}
        adjacency = {n.id: [] for n in nodes}

        for node in nodes:
            for dep in node.dependencies:
                if dep in adjacency:
                    adjacency[dep].append(node.id)
                    in_degree[node.id] += 1

        # Kahn's algorithm
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        sorted_order = []

        while queue:
            current = queue.pop(0)
            sorted_order.append(current)
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        is_dag = len(sorted_order) == len(nodes)
        orphan_deps = []
        for node in nodes:
            for dep in node.dependencies:
                if dep not in node_map:
                    orphan_deps.append((node.id, dep))

        return {
            "is_valid_dag": is_dag,
            "topological_order": sorted_order if is_dag else [],
            "total_nodes": len(nodes),
            "total_edges": sum(len(n.dependencies) for n in nodes),
            "orphan_dependencies": orphan_deps,
            "root_nodes": [n.id for n in nodes if not n.dependencies],
            "leaf_nodes": [
                n.id for n in nodes
                if not any(n.id in other.dependencies for other in nodes)
            ],
        }


# ═══════════════════════════════════════════════════════════════
# PERSISTENCIA SQLite (cortex.db)
# ═══════════════════════════════════════════════════════════════

class CortexPersist:
    """Persistencia BFT-compliant en SQLite."""

    def __init__(self, db_path: str = "cortex.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS goat_math_nodes (
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

            CREATE TABLE IF NOT EXISTS goat_math_dag_validation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                validated_at TEXT NOT NULL,
                is_valid_dag INTEGER NOT NULL,
                total_nodes INTEGER NOT NULL,
                total_edges INTEGER NOT NULL,
                root_nodes TEXT NOT NULL,
                leaf_nodes TEXT NOT NULL,
                orphan_deps TEXT NOT NULL,
                manifest_hash TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_goat_block
                ON goat_math_nodes(block);
            CREATE INDEX IF NOT EXISTS idx_goat_status
                ON goat_math_nodes(validation_status);
        """)
        self.conn.commit()

    def inject_nodes(self, nodes: List[GOATMathNode]) -> Dict:
        """Inyecta nodos con upsert atómico."""
        injected = 0
        updated = 0

        for node in nodes:
            existing = self.conn.execute(
                "SELECT hash FROM goat_math_nodes WHERE id = ?",
                (node.id,)
            ).fetchone()

            if existing is None:
                self.conn.execute("""
                    INSERT INTO goat_math_nodes
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
                    UPDATE goat_math_nodes
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

    def record_dag_validation(self, result: Dict):
        """Registra validación del DAG."""
        manifest_hash = hashlib.sha256(
            json.dumps(result, sort_keys=True).encode()
        ).hexdigest()[:16]

        self.conn.execute("""
            INSERT INTO goat_math_dag_validation
            (validated_at, is_valid_dag, total_nodes, total_edges,
             root_nodes, leaf_nodes, orphan_deps, manifest_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            int(result["is_valid_dag"]),
            result["total_nodes"],
            result["total_edges"],
            json.dumps(result["root_nodes"]),
            json.dumps(result["leaf_nodes"]),
            json.dumps(result["orphan_dependencies"]),
            manifest_hash
        ))
        self.conn.commit()
        return manifest_hash

    def get_status_report(self) -> Dict:
        """Genera reporte de estado del sistema."""
        cursor = self.conn.execute("""
            SELECT
                block,
                block_name,
                criticality,
                COUNT(*) as total,
                SUM(CASE WHEN validation_status='VALIDATED' THEN 1 ELSE 0 END)
                    as validated,
                SUM(CASE WHEN validation_status='PENDING' THEN 1 ELSE 0 END)
                    as pending,
                SUM(CASE WHEN validation_status='FAILED' THEN 1 ELSE 0 END)
                    as failed
            FROM goat_math_nodes
            GROUP BY block
            ORDER BY MIN(idx)
        """)

        blocks = []
        for row in cursor:
            blocks.append({
                "block": row[0],
                "name": row[1],
                "criticality": row[2],
                "total": row[3],
                "validated": row[4],
                "pending": row[5],
                "failed": row[6],
                "progress": f"{row[4]}/{row[3]}"
                            f" ({100*row[4]//row[3] if row[3] else 0}%)"
            })

        total = self.conn.execute(
            "SELECT COUNT(*) FROM goat_math_nodes"
        ).fetchone()[0]
        validated = self.conn.execute(
            "SELECT COUNT(*) FROM goat_math_nodes "
            "WHERE validation_status='VALIDATED'"
        ).fetchone()[0]

        return {
            "blocks": blocks,
            "total_nodes": total,
            "total_validated": validated,
            "global_progress": f"{validated}/{total}"
                               f" ({100*validated//total if total else 0}%)"
        }

    def close(self):
        self.conn.close()


# ═══════════════════════════════════════════════════════════════
# IMPLEMENTACIONES DE EJEMPLO (PyTorch / JAX)
# ═══════════════════════════════════════════════════════════════

PYTORCH_EXAMPLES = {
    "GOAT-MATH-001": '''
# SVD - Descomposición en Valores Singulares
import torch
A = torch.randn(5, 3)
U, S, Vh = torch.linalg.svd(A, full_matrices=False)
# Reconstrucción: A ≈ U @ diag(S) @ Vh
A_reconstructed = U @ torch.diag(S) @ Vh
error = torch.norm(A - A_reconstructed).item()
assert error < 1e-5, f"SVD reconstruction error: {error}"
print(f"✅ SVD: error={error:.2e}, rank={len(S)}")
''',

    "GOAT-MATH-011": '''
# Gradiente con autograd
import torch
x = torch.tensor([2.0, 3.0], requires_grad=True)
y = x[0]**2 + 3*x[1]**3
y.backward()
# ∂y/∂x₀ = 2x₀ = 4, ∂y/∂x₁ = 9x₁² = 81
assert torch.allclose(x.grad, torch.tensor([4.0, 81.0]))
print(f"✅ Gradiente: {x.grad}")
''',

    "GOAT-MATH-081": '''
# Mecanismo de Atención (Scaled Dot-Product)
import torch
import torch.nn.functional as F
import math

d_k = 64
Q = torch.randn(1, 8, 10, d_k)   # (batch, heads, seq, d_k)
K = torch.randn(1, 8, 10, d_k)
V = torch.randn(1, 8, 10, d_k)

scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(d_k)
attn_weights = F.softmax(scores, dim=-1)
output = torch.matmul(attn_weights, V)
print(f"✅ Atención: output shape={output.shape}")
print(f"   Weights sum per query: {attn_weights.sum(-1)[0,0,:3]}")
''',

    "GOAT-MATH-089": '''
# Score Matching (Denoising Score Matching simplificado)
import torch
import torch.nn as nn

class ScoreNet(nn.Module):
    def __init__(self, dim=2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim + 1, 128), nn.SiLU(),
            nn.Linear(128, 128), nn.SiLU(),
            nn.Linear(128, dim)
        )
    def forward(self, x, sigma):
        return self.net(torch.cat([x, sigma.unsqueeze(-1)], dim=-1))

# Denoising score matching loss
def dsm_loss(model, x_clean, sigma=0.1):
    noise = torch.randn_like(x_clean) * sigma
    x_noisy = x_clean + noise
    sigma_t = torch.full((x_clean.shape[0],), sigma)
    score_pred = model(x_noisy, sigma_t)
    target = -noise / (sigma**2)  # ∇log p(x̃|x)
    return ((score_pred - target)**2).mean()

model = ScoreNet()
x = torch.randn(256, 2)  # datos de ejemplo
loss = dsm_loss(model, x)
print(f"✅ Score Matching Loss: {loss.item():.4f}")
''',
}


# ═══════════════════════════════════════════════════════════════
# EJECUCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("🐐 GOAT-MATH: Inyección de 100 Primitivas en C5-REAL DAG")
    print("=" * 70)

    # 1. Construir nodos
    print("\n[1/4] Construyendo 100 nodos epistémicos...")
    nodes = build_all_nodes()
    print(f"      ✅ {len(nodes)} nodos construidos")

    # 2. Validar DAG
    print("\n[2/4] Validando integridad del DAG...")
    dag_result = DAGValidator.validate(nodes)
    print(f"      DAG válido: {dag_result['is_valid_dag']}")
    print(f"      Nodos: {dag_result['total_nodes']}")
    print(f"      Aristas: {dag_result['total_edges']}")
    print(f"      Nodos raíz: {len(dag_result['root_nodes'])}")
    print(f"      Nodos hoja: {len(dag_result['leaf_nodes'])}")
    if dag_result['orphan_dependencies']:
        print(f"      ⚠️  Deps huérfanas: {dag_result['orphan_dependencies']}")
    else:
        print(f"      ✅ Sin dependencias huérfanas")

    if not dag_result['is_valid_dag']:
        print("      ❌ CICLO DETECTADO - Abortando inyección")
        return

    # 3. Persistir en SQLite
    print("\n[3/4] Inyectando en cortex.db...")
    db = CortexPersist("../../cortex.db")
    inject_result = db.inject_nodes(nodes)
    print(f"      Nuevos: {inject_result['injected']}")
    print(f"      Actualizados: {inject_result['updated']}")
    print(f"      Total: {inject_result['total']}")

    manifest_hash = db.record_dag_validation(dag_result)
    print(f"      Manifest hash: {manifest_hash}")

    # 4. Reporte de estado
    print("\n[4/4] Reporte de estado:")
    report = db.get_status_report()
    print(f"\n      {'Bloque':<6} {'Nombre':<40} {'Progreso':<12} {'Crit.'}")
    print(f"      {'─'*6} {'─'*40} {'─'*12} {'─'*10}")
    for b in report['blocks']:
        print(f"      {b['block']:<6} {b['name']:<40} "
              f"{b['progress']:<12} {b['criticality']}")

    print(f"\n      📊 PROGRESO GLOBAL: {report['global_progress']}")

    db.close()

    # 5. Exportar JSON para trazabilidad
    export_path = Path("../../goat_math_manifest.json")
    export_data = {
        "version": "1.0",
        "protocol": "C5-REAL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest_hash": manifest_hash,
        "dag_validation": dag_result,
        "nodes": [asdict(n) for n in nodes],
        "pytorch_examples": list(PYTORCH_EXAMPLES.keys()),
    }
    export_path.write_text(json.dumps(export_data, indent=2, ensure_ascii=False))
    print(f"\n      📁 Manifiesto exportado: {export_path.resolve()}")

    print("\n" + "=" * 70)
    print("✅ INYECCIÓN COMPLETADA")
    print(f"   Sentinel commit listo:")
    print(f'   git add . && git commit -m '
          f'"feat(epistemic): inject 100 GOAT math primitives '
          f'into C5-REAL DAG [{manifest_hash}]"')
    print("=" * 70)


if __name__ == "__main__":
    main()
