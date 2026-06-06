#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
import logging

logger = logging.getLogger("script")
import logging

logger = logging.getLogger("campaign")
import ast
import subprocess
import sys
from pathlib import Path

import yaml


class Mutator(ast.NodeTransformer):
    def __init__(self):
        self.mutations_applied = 0
        self.target_mutation = 0
        self.current_index = 0
        self.last_mutation_type = None
        self.last_mutation_lineno = -1

    def try_mutate(self, node, mutation_type, action_fn):
        if self.current_index == self.target_mutation:
            action_fn()
            self.mutations_applied += 1
            self.last_mutation_type = mutation_type
            self.last_mutation_lineno = getattr(node, "lineno", -1)
        self.current_index += 1

    def visit_Compare(self, node):
        self.generic_visit(node)

        def action():
            for i, op in enumerate(node.ops):
                if isinstance(op, ast.Eq):
                    node.ops[i] = ast.NotEq()
                elif isinstance(op, ast.NotEq):
                    node.ops[i] = ast.Eq()
                elif isinstance(op, ast.Is):
                    node.ops[i] = ast.IsNot()
                elif isinstance(op, ast.IsNot):
                    node.ops[i] = ast.Is()
                elif isinstance(op, ast.In):
                    node.ops[i] = ast.NotIn()
                elif isinstance(op, ast.NotIn):
                    node.ops[i] = ast.In()
                elif isinstance(op, ast.Lt):
                    node.ops[i] = ast.GtE()
                elif isinstance(op, ast.LtE):
                    node.ops[i] = ast.Gt()
                elif isinstance(op, ast.Gt):
                    node.ops[i] = ast.LtE()
                elif isinstance(op, ast.GtE):
                    node.ops[i] = ast.Lt()

        # We only consider mutable if the operator is in our list
        mutable = any(
            isinstance(
                op,
                (
                    ast.Eq,
                    ast.NotEq,
                    ast.Is,
                    ast.IsNot,
                    ast.In,
                    ast.NotIn,
                    ast.Lt,
                    ast.LtE,
                    ast.Gt,
                    ast.GtE,
                ),
            )
            for op in node.ops
        )
        if mutable:
            self.try_mutate(node, "CompareFlip", action)
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)

        def action():
            if isinstance(node.op, ast.And):
                node.op = ast.Or()
            elif isinstance(node.op, ast.Or):
                node.op = ast.And()

        if isinstance(node.op, (ast.And, ast.Or)):
            self.try_mutate(node, "BooleanFlip", action)
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)

        def action():
            if isinstance(node.op, ast.Add):
                node.op = ast.Sub()
            elif isinstance(node.op, ast.Sub):
                node.op = ast.Add()
            elif isinstance(node.op, ast.Mult):
                node.op = ast.Div()
            elif isinstance(node.op, ast.Div):
                node.op = ast.Mult()

        if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            self.try_mutate(node, "BinOpFlip", action)
        return node

    def visit_If(self, node):
        self.generic_visit(node)

        def action():
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)

        self.try_mutate(node, "BranchInversion", action)
        return node

    def visit_Constant(self, node):
        self.generic_visit(node)

        def action():
            if isinstance(node.value, bool):
                node.value = not node.value
            elif isinstance(node.value, int) and not isinstance(node.value, bool):
                node.value = node.value + 1

        if isinstance(node.value, (bool, int)) and not isinstance(node.value, str):
            self.try_mutate(node, "ConstantReplacement", action)
        return node

    def visit_Return(self, node):
        self.generic_visit(node)

        def action():
            if (
                node.value
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, bool)
            ):
                node.value.value = not node.value.value
            else:
                # Return None as fallback mutation if it's returning something else
                node.value = ast.Constant(value=None)

        if node.value:
            self.try_mutate(node, "ReturnValueMutation", action)
        return node


def count_mutations(source):
    tree = ast.parse(source)
    mutator = Mutator()
    # By setting target_mutation to an unreachable number, we just count the total indices
    mutator.target_mutation = -1
    mutator.visit(tree)
    return mutator.current_index


def mutate_and_test(target_dir):
    target_path = Path(target_dir)
    if target_path.is_file():
        python_files = [target_path]
    else:
        python_files = list(target_path.rglob("*.py"))

    total_files_tested = 0
    total_killed = 0
    total_survived = 0
    survivors = []

    logger.info(f"Scanning target: {target_dir}")

    for target_file in python_files:
        if target_file.name == "__init__.py":
            continue

        with open(target_file) as f:
            try:
                original_source = f.read()
                num_mutations = count_mutations(original_source)
            except SyntaxError:
                continue

        limit = num_mutations
        file_killed = 0
        file_survived = 0

        total_files_tested += 1

        try:
            for i in range(limit):
                tree = ast.parse(original_source)
                mutator = Mutator()
                mutator.target_mutation = i
                mutated_tree = mutator.visit(tree)

                if mutator.mutations_applied == 0:
                    continue

                mutated_source = ast.unparse(mutated_tree)

                with open(target_file, "w") as f:
                    f.write(mutated_source)

                cmd = f"./.venv/bin/pytest tests/ -k {target_file.stem} -n auto --disable-warnings"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                # Exit code 1 means tests failed (mutant killed)
                # Exit code 0 means tests passed (mutant survived)
                # Exit code 5 means no tests collected (mutant survived)
                if result.returncode == 1:
                    file_killed += 1
                else:
                    file_survived += 1
                    survivors.append(
                        {
                            "file": str(target_file),
                            "mutation_index": i,
                            "mutation_type": mutator.last_mutation_type,
                            "lineno": mutator.last_mutation_lineno,
                            "pytest_exit_code": result.returncode,
                        }
                    )
        except Exception as e:
            print(f"Error processing {target_file}: {e}")
        finally:
            # Restore original source from memory
            with open(target_file, "w") as f:
                f.write(original_source)

        total_killed += file_killed
        total_survived += file_survived

    return total_files_tested, total_killed, total_survived, survivors


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.info(
            "Usage: python h1_ast_mutation_campaign.py <target_directory> [more_targets...]"
        )
        sys.exit(1)

    overall_files = 0
    overall_killed = 0
    overall_survived = 0
    all_survivors = []

    for target in sys.argv[1:]:
        f, k, s, survs = mutate_and_test(target)
        overall_files += f
        overall_killed += k
        overall_survived += s
        all_survivors.extend(survs)

    total_tested = overall_killed + overall_survived
    mutation_score = (overall_killed / total_tested * 100) if total_tested > 0 else 0.0

    # CI/CD Threshold Evaluation
    thresholds = {"Critical": 99.0, "Important": 95.0, "General": 90.0}

    status = "FAIL"
    if mutation_score >= thresholds["General"]:
        status = "PASS_GENERAL"
    if mutation_score >= thresholds["Important"]:
        status = "PASS_IMPORTANT"
    if mutation_score >= thresholds["Critical"]:
        status = "PASS_CRITICAL"

    report = {
        "CI_Mutation_Report": {
            "Metrics": {
                "Total_Files_Scanned": overall_files,
                "Total_Mutants_Generated": total_tested,
                "Mutants_Killed": overall_killed,
                "Mutants_Survived": overall_survived,
                "Mutation_Score": f"{mutation_score:.2f}%",
            },
            "Thresholds": thresholds,
            "Evaluation": {"Status": status, "Passed": mutation_score >= thresholds["General"]},
        }
    }

    with open("mutation_report.yaml", "w") as f:
        yaml.dump(report, f, default_flow_style=False)

    import json

    with open("survivors_matrix.json", "w") as f:
        json.dump(all_survivors, f, indent=2)

    logger.info(yaml.dump(report, default_flow_style=False))
    logger.info(f"Exported {len(all_survivors)} survivor nodes to survivors_matrix.json")
