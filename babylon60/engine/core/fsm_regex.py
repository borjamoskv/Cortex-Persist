from __future__ import annotations

import string
from dataclasses import dataclass
from typing import Optional

# [C5-REAL] Exergy-Maximized
"""
Finite State Machine (FSM) Compiler for Regex.

Converts a restricted regular expression into a Deterministic Finite Automaton (DFA)
for exact, deterministic control of logit generation.
"""


@dataclass(frozen=True)
class CharSet:
    chars: frozenset[str]
    invert: bool = False

    def matches(self, c: str) -> bool:
        if self.invert:
            return c not in self.chars
        return c in self.chars

    def __repr__(self) -> str:
        if self.invert:
            return f"[^{''.join(sorted(self.chars))}]"
        return f"[{''.join(sorted(self.chars))}]"


class NFAState:
    _id_counter = 0

    def __init__(self, is_final: bool = False):
        self.id = NFAState._id_counter
        NFAState._id_counter += 1
        self.is_final = is_final
        # transitions: CharSet -> list of states
        self.transitions: dict[CharSet, list[NFAState]] = {}
        # epsilon transitions
        self.epsilon_transitions: list[NFAState] = []

    def add_transition(self, charset: CharSet, state: NFAState):
        if charset not in self.transitions:
            self.transitions[charset] = []
        self.transitions[charset].append(state)

    def add_epsilon(self, state: NFAState):
        self.epsilon_transitions.append(state)


@dataclass
class NFA:
    start: NFAState
    end: NFAState


# --- AST Nodes ---
class RegexNode:
    pass


@dataclass
class LiteralNode(RegexNode):
    charset: CharSet


@dataclass
class ConcatNode(RegexNode):
    left: RegexNode
    right: RegexNode


@dataclass
class UnionNode(RegexNode):
    left: RegexNode
    right: RegexNode


@dataclass
class StarNode(RegexNode):
    child: RegexNode


@dataclass
class PlusNode(RegexNode):
    child: RegexNode


@dataclass
class OptionalNode(RegexNode):
    child: RegexNode


# --- Parser ---
class RegexParser:
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.pos = 0

    def peek(self) -> Optional[str]:
        if self.pos < len(self.pattern):
            return self.pattern[self.pos]
        return None

    def consume(self) -> str:
        c = self.pattern[self.pos]
        self.pos += 1
        return c

    def parse(self) -> RegexNode:
        node = self._parse_union()
        if self.pos < len(self.pattern):
            raise ValueError(f"Unexpected character at {self.pos}: {self.peek()}")
        return node

    def _parse_union(self) -> RegexNode:
        node = self._parse_concat()
        while self.peek() == "|":
            self.consume()
            right = self._parse_concat()
            node = UnionNode(node, right)
        return node

    def _parse_concat(self) -> RegexNode:
        nodes = []
        while self.peek() is not None and self.peek() not in (")", "|"):
            nodes.append(self._parse_quantifier())

        if not nodes:
            return LiteralNode(CharSet(frozenset([""])))  # Epsilon

        node = nodes[0]
        for right in nodes[1:]:
            node = ConcatNode(node, right)
        return node

    def _parse_quantifier(self) -> RegexNode:
        node = self._parse_base()
        while True:
            if self.peek() == "*":
                self.consume()
                node = StarNode(node)
            elif self.peek() == "+":
                self.consume()
                node = PlusNode(node)
            elif self.peek() == "?":
                self.consume()
                node = OptionalNode(node)
            else:
                break
        return node

    def _parse_base(self) -> RegexNode:
        c = self.peek()
        if c == "(":
            self.consume()
            node = self._parse_union()
            if self.consume() != ")":
                raise ValueError("Expected ')'")
            return node
        elif c == "[":
            return self._parse_class()
        elif c == "\\":
            self.consume()
            esc = self.consume()
            # Simple escape support
            if esc == "d":
                return LiteralNode(CharSet(frozenset(string.digits)))
            elif esc == "w":
                return LiteralNode(CharSet(frozenset(string.ascii_letters + string.digits + "_")))
            elif esc == "s":
                return LiteralNode(CharSet(frozenset(string.whitespace)))
            return LiteralNode(CharSet(frozenset([esc])))
        elif c == ".":
            self.consume()
            return LiteralNode(CharSet(frozenset(), invert=True))  # Match anything
        else:
            self.consume()
            return LiteralNode(CharSet(frozenset([c])))

    def _parse_class(self) -> RegexNode:
        self.consume()  # '['
        invert = False
        if self.peek() == "^":
            self.consume()
            invert = True

        chars = set()
        while self.peek() is not None and self.peek() != "]":
            c = self.consume()
            if c == "\\":
                c = self.consume()
            # Note: Ranges like a-z are omitted for simplicity in this baseline,
            # but can be added. For this primitive, literal parsing inside brackets.
            chars.add(c)

        if self.consume() != "]":
            raise ValueError("Expected ']'")

        return LiteralNode(CharSet(frozenset(chars), invert=invert))


class NFACompiler:
    def compile(self, node: RegexNode) -> NFA:
        if isinstance(node, LiteralNode):
            start = NFAState()
            end = NFAState(is_final=True)
            if node.charset.chars == frozenset([""]) and not node.charset.invert:
                start.add_epsilon(end)
            else:
                start.add_transition(node.charset, end)
            return NFA(start, end)

        elif isinstance(node, ConcatNode):
            nfa1 = self.compile(node.left)
            nfa2 = self.compile(node.right)
            nfa1.end.is_final = False
            nfa1.end.add_epsilon(nfa2.start)
            return NFA(nfa1.start, nfa2.end)

        elif isinstance(node, UnionNode):
            nfa1 = self.compile(node.left)
            nfa2 = self.compile(node.right)
            start = NFAState()
            end = NFAState(is_final=True)
            start.add_epsilon(nfa1.start)
            start.add_epsilon(nfa2.start)
            nfa1.end.is_final = False
            nfa2.end.is_final = False
            nfa1.end.add_epsilon(end)
            nfa2.end.add_epsilon(end)
            return NFA(start, end)

        elif isinstance(node, StarNode):
            nfa = self.compile(node.child)
            start = NFAState()
            end = NFAState(is_final=True)
            start.add_epsilon(nfa.start)
            start.add_epsilon(end)
            nfa.end.is_final = False
            nfa.end.add_epsilon(nfa.start)
            nfa.end.add_epsilon(end)
            return NFA(start, end)

        elif isinstance(node, PlusNode):
            nfa = self.compile(node.child)
            start = NFAState()
            end = NFAState(is_final=True)
            start.add_epsilon(nfa.start)
            nfa.end.is_final = False
            nfa.end.add_epsilon(nfa.start)
            nfa.end.add_epsilon(end)
            return NFA(start, end)

        elif isinstance(node, OptionalNode):
            nfa = self.compile(node.child)
            start = NFAState()
            end = NFAState(is_final=True)
            start.add_epsilon(nfa.start)
            start.add_epsilon(end)
            nfa.end.is_final = False
            nfa.end.add_epsilon(end)
            return NFA(start, end)

        raise ValueError(f"Unknown node type {type(node)}")


# --- DFA ---
@dataclass(frozen=True)
class DFAState:
    id: int
    nfa_states: frozenset[int]
    is_final: bool


class DFA:
    def __init__(self):
        self.states: dict[int, DFAState] = {}
        # current_state_id -> character -> next_state_id
        self.transitions: dict[int, dict[str, int]] = {}
        self.start_state: int = 0

    def matches(self, string: str) -> bool:
        current = self.start_state
        for c in string:
            if c in self.transitions.get(current, {}):
                current = self.transitions[current][c]
            else:
                # Need to handle fallback logic for CharSets properly
                # This simple matches() is just for exact character dict lookups.
                return False
        return self.states[current].is_final


def epsilon_closure(states: set[NFAState]) -> set[NFAState]:
    stack = list(states)
    closure = set(states)
    while stack:
        state = stack.pop()
        for next_state in state.epsilon_transitions:
            if next_state not in closure:
                closure.add(next_state)
                stack.append(next_state)
    return closure


def get_alphabet(nfa_states: set[NFAState]) -> set[str]:
    # We collect all distinct single characters.
    # For actual broad FSM mapping over tokens, we need a complete character set
    # mapped against the vocabulary.
    # For the generic DFA conversion here, we build transitions based on explicit chars.
    alphabet = set()
    for state in nfa_states:
        for charset in state.transitions.keys():
            if not charset.invert:
                alphabet.update(charset.chars)
    return alphabet


def build_dfa(nfa: NFA, vocab_chars: set[str]) -> DFA:
    """
    Builds a DFA evaluated explicitly over a set of possible characters (vocab_chars)
    to handle inversions and dot (.) properly.
    """
    dfa = DFA()

    start_closure = epsilon_closure({nfa.start})
    start_nfa_ids = frozenset(s.id for s in start_closure)

    start_dfa_state = DFAState(
        id=0, nfa_states=start_nfa_ids, is_final=any(s.is_final for s in start_closure)
    )

    dfa.states[0] = start_dfa_state
    dfa.start_state = 0

    unmarked = [start_dfa_state]
    nfa_id_map = {s.id: s for s in _get_all_nfa_states(nfa.start)}
    state_cache = {start_nfa_ids: 0}
    state_counter = 1

    while unmarked:
        current_dfa = unmarked.pop(0)
        current_nfa_states = {nfa_id_map[sid] for sid in current_dfa.nfa_states}

        dfa.transitions[current_dfa.id] = {}

        for char in vocab_chars:
            next_nfa = set()
            for s in current_nfa_states:
                for charset, targets in s.transitions.items():
                    if charset.matches(char):
                        next_nfa.update(targets)

            if next_nfa:
                closure = epsilon_closure(next_nfa)
                closure_ids = frozenset(s.id for s in closure)

                if closure_ids not in state_cache:
                    new_dfa_state = DFAState(
                        id=state_counter,
                        nfa_states=closure_ids,
                        is_final=any(s.is_final for s in closure),
                    )
                    state_cache[closure_ids] = state_counter
                    dfa.states[state_counter] = new_dfa_state
                    unmarked.append(new_dfa_state)
                    state_counter += 1

                dfa.transitions[current_dfa.id][char] = state_cache[closure_ids]

    return dfa


def _get_all_nfa_states(start: NFAState) -> set[NFAState]:
    visited = set()
    stack = [start]
    while stack:
        s = stack.pop()
        if s not in visited:
            visited.add(s)
            for t in s.epsilon_transitions:
                stack.append(t)
            for targets in s.transitions.values():
                for t in targets:
                    stack.append(t)
    return visited


def compile_regex(pattern: str, vocab_chars: set[str]) -> DFA:
    parser = RegexParser(pattern)
    ast = parser.parse()
    compiler = NFACompiler()
    nfa = compiler.compile(ast)
    return build_dfa(nfa, vocab_chars)
