from typing import Any

import sympy
from sympy.logic.boolalg import And, Boolean, Implies, Not, Or
from sympy.logic.inference import satisfiable

# ==============================================================================
# C5-REAL: AUTODIDACT LOGIC & FOUNDATIONS PRIMITIVES
# ==============================================================================
# This module implements the foundational concepts of set theory and propositional
# logic as deterministic, high-exergy functions within the MOSKV-1 APEX framework.
# ==============================================================================

# ------------------------------------------------------------------------------
# PRIMITIVES 1-6: SET THEORY (Teoría de Conjuntos)
# ------------------------------------------------------------------------------

def create_set(elements: tuple) -> frozenset:
    """
    1. CONJUNTO (Set)
    Initializes a mathematical boundary of unique, immutable elements.
    """
    return frozenset(elements)

def is_element(element: Any, target_set: frozenset) -> bool:
    """
    2. ELEMENTO (Element)
    Deterministic inclusion assertion: evaluates if element ∈ target_set.
    """
    return element in target_set

def compute_union(set_a: frozenset, set_b: frozenset) -> frozenset:
    """
    3. UNIÓN (Union)
    Logical OR across set boundaries: A ∪ B.
    """
    return set_a | set_b

def compute_intersection(set_a: frozenset, set_b: frozenset) -> frozenset:
    """
    4. INTERSECCIÓN (Intersection)
    Logical AND across set boundaries: A ∩ B.
    """
    return set_a & set_b

def is_subset(subset: frozenset, superset: frozenset) -> bool:
    """
    5. SUBCONJUNTO (Subset)
    Directional inclusion relation: evaluates if A ⊆ B.
    """
    return subset.issubset(superset)

def empty_set() -> frozenset:
    """
    6. CONJUNTO VACÍO (Empty Set)
    The absolute zero boundary: ∅.
    """
    return frozenset()

# ------------------------------------------------------------------------------
# PRIMITIVES 7-10: PROPOSITIONAL LOGIC & EPISTEMOLOGY
# ------------------------------------------------------------------------------

class PropositionalLogic:
    """
    7. LÓGICA PROPOSICIONAL (Propositional Logic)
    Interface for computable Boolean algebra nodes.
    """
    @staticmethod
    def symbol(name: str) -> sympy.Symbol:
        return sympy.symbols(name)
        
    @staticmethod
    def logical_and(p: Boolean, q: Boolean) -> Boolean:
        return And(p, q)
        
    @staticmethod
    def logical_or(p: Boolean, q: Boolean) -> Boolean:
        return Or(p, q)
        
    @staticmethod
    def implies(p: Boolean, q: Boolean) -> Boolean:
        return Implies(p, q)
        
    @staticmethod
    def not_(p: Boolean) -> Boolean:
        return Not(p)

def define_axiom(expression: Boolean) -> Boolean:
    """
    8. AXIOMA (Axiom)
    A structural invariant assumed to be unequivocally True within the system.
    """
    return expression

def define_theorem(expression: Boolean) -> Boolean:
    """
    9. TEOREMA (Theorem)
    An expression pending deterministic verification against the axiom graph.
    """
    return expression

def formal_proof(axioms: list[Boolean], theorem: Boolean) -> bool:
    """
    10. DEMOSTRACIÓN (Proof)
    Executes a deterministic verification of (Axioms => Theorem).
    If the implication is a tautology (its negation is unsatisfiable), the proof is valid.
    """
    if not axioms:
        # If no axioms, the theorem must be an inherent tautology
        premise = sympy.true
    else:
        # Combine all axioms with AND
        premise = And(*axioms)
    
    # Implication: (A1 ∧ A2 ... ∧ An) => Theorem
    implication = Implies(premise, theorem)
    
    # A statement is a tautology if its negation is unsatisfiable.
    negated_implication = Not(implication)
    is_satisfiable = satisfiable(negated_implication)
    
    # If satisfiable is False, the negation is impossible, thus implication is True
    return is_satisfiable is False


# ==============================================================================
# EXECUTION & DIAGNOSTICS (C5-REAL VALIDATION)
# ==============================================================================
if __name__ == "__main__":
    print(">> MOSKV-1 APEX: INITIALIZING C5-REAL LOGIC & FOUNDATION PRIMITIVES <<\n")

    # --- SET THEORY VALIDATION ---
    print("--- 1. SET THEORY ---")
    A = create_set((1, 2, 3))
    B = create_set((3, 4, 5))
    E = empty_set()
    
    print(f"[1] Conjunto A: {set(A)}")
    print(f"[2] Elemento (¿2 ∈ A?): {is_element(2, A)}")
    print(f"[3] Unión (A ∪ B): {set(compute_union(A, B))}")
    print(f"[4] Intersección (A ∩ B): {set(compute_intersection(A, B))}")
    print(f"[5] Subconjunto (¿{{1,2}} ⊆ A?): {is_subset(create_set((1,2)), A)}")
    print(f"[6] Conjunto vacío (∅): {set(E)} (¿∅ ⊆ A? {is_subset(E, A)})\n")

    # --- PROPOSITIONAL LOGIC VALIDATION ---
    print("--- 2. PROPOSITIONAL LOGIC & EPISTEMOLOGY ---")
    
    P = PropositionalLogic.symbol('P')
    Q = PropositionalLogic.symbol('Q')
    
    # Modus Ponens Simulation
    print("[7] Lógica Proposicional: Símbolos P, Q")
    
    # Axioms
    ax1 = define_axiom(P)                    # Axiom 1: P is True
    ax2 = define_axiom(Implies(P, Q))        # Axiom 2: P implies Q
    
    # Theorem
    thm = define_theorem(Q)                  # Theorem: Therefore, Q is True
    
    # Proof
    is_proven = formal_proof([ax1, ax2], thm)
    
    print(f"[8] Axiomas: A1: {ax1}, A2: {ax2}")
    print(f"[9] Teorema: {thm}")
    print(f"[10] Demostración (¿A1 ∧ A2 => Teorema?): {'VÁLIDA (C5-REAL)' if is_proven else 'INVÁLIDA'}\n")

    # Modus Tollens Simulation
    ax3 = define_axiom(Not(Q))
    thm2 = define_theorem(Not(P))
    is_proven2 = formal_proof([ax2, ax3], thm2)
    print(f"Demostración Modus Tollens (¿(P=>Q) ∧ ~Q => ~P?): {'VÁLIDA (C5-REAL)' if is_proven2 else 'INVÁLIDA'}\n")

    print(">> C5-REAL DIAGNOSTICS COMPLETE: ZERO ANERGIA. <<")
