import ast
import tempfile
import os
import subprocess
import ctypes
import sys
import logging
from typing import Any

logger = logging.getLogger("cortex.autodidact.rust_jit")
logging.basicConfig(level=logging.INFO)


class PythonToRustTranspiler(ast.NodeVisitor):
    def __init__(self):
        self.declared_vars = set()
        self.indent_level = 0
        self.func_name = None
        self.arg_names = []

    def indent(self) -> str:
        return "    " * self.indent_level

    def visit_Module(self, node):
        lines = []
        for item in node.body:
            lines.append(self.visit(item))
        return "\n".join(lines)

    def visit_FunctionDef(self, node):
        self.func_name = node.name
        # Determine arguments
        args = []
        for arg in node.args.args:
            args.append(f"{arg.arg}: f64")
            self.arg_names.append(arg.arg)
            self.declared_vars.add(arg.arg)

        args_str = ", ".join(args)

        lines = []
        lines.append("#[no_mangle]")
        lines.append(f'pub extern "C" fn {node.name}({args_str}) -> f64 {{')
        self.indent_level += 1

        for stmt in node.body:
            stmt_str = self.visit(stmt)
            if stmt_str:
                lines.append(self.indent() + stmt_str)

        self.indent_level -= 1
        lines.append("}")
        return "\n".join(lines)

    def visit_Assign(self, node):
        if len(node.targets) != 1:
            raise NotImplementedError("Multiple assignment targets not supported")

        target = node.targets[0]
        if not isinstance(target, ast.Name):
            raise NotImplementedError("Only basic variable assignments supported")

        var_name = target.id
        val_str = self.visit(node.value)

        if var_name not in self.declared_vars:
            self.declared_vars.add(var_name)
            return f"let mut {var_name} = {val_str};"
        else:
            return f"{var_name} = {val_str};"

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_map = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Mod: "%"}
        op_type = type(node.op)
        if op_type not in op_map:
            raise NotImplementedError(f"Binary operator {op_type.__name__} not supported")
        return f"({left} {op_map[op_type]} {right})"

    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        op_type = type(node.op)
        if op_type == ast.USub:
            return f"(-{operand})"
        elif op_type == ast.UAdd:
            return f"(+{operand})"
        else:
            raise NotImplementedError(f"Unary operator {op_type.__name__} not supported")

    def visit_Name(self, node):
        return node.id

    def visit_Constant(self, node):
        val = node.value
        if isinstance(val, int | float):
            return str(float(val))
        elif isinstance(val, bool):
            return "true" if val else "false"
        else:
            raise NotImplementedError(f"Constant of type {type(val).__name__} not supported")

    def visit_Num(self, node):
        return str(float(node.n))

    def visit_Return(self, node):
        if node.value is None:
            return "return 0.0;"
        val_str = self.visit(node.value)
        return f"return {val_str};"

    def visit_If(self, node):
        test_str = self.visit(node.test)
        lines = []
        lines.append(f"if {test_str} {{")
        self.indent_level += 1
        for stmt in node.body:
            stmt_str = self.visit(stmt)
            if stmt_str:
                lines.append(self.indent() + stmt_str)
        self.indent_level -= 1
        lines.append(self.indent() + "}")

        if node.orelse:
            lines[-1] = self.indent() + "} else {"
            self.indent_level += 1
            for stmt in node.orelse:
                stmt_str = self.visit(stmt)
                if stmt_str:
                    lines.append(self.indent() + stmt_str)
            self.indent_level -= 1
            lines.append(self.indent() + "}")
        return "\n".join(lines)

    def visit_Compare(self, node):
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise NotImplementedError("Chained comparisons not supported")

        left = self.visit(node.left)
        op_type = type(node.ops[0])
        right = self.visit(node.comparators[0])

        op_map = {
            ast.Eq: "==",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
        }
        if op_type not in op_map:
            raise NotImplementedError(f"Comparison operator {op_type.__name__} not supported")
        return f"({left} {op_map[op_type]} {right})"

    def visit_For(self, node):
        if not isinstance(node.target, ast.Name):
            raise NotImplementedError("Only simple range loop targets supported")

        var_name = node.target.id

        if (
            not isinstance(node.iter, ast.Call)
            or not isinstance(node.iter.func, ast.Name)
            or node.iter.func.id != "range"
        ):
            raise NotImplementedError("Only range() loops are currently compiled to JIT-Rust")

        args = node.iter.args
        if len(args) == 1:
            start_str = "0"
            end_str = self.visit(args[0])
        elif len(args) == 2:
            start_str = self.visit(args[0])
            end_str = self.visit(args[1])
        else:
            raise NotImplementedError("Step in range() is not supported")

        lines = []
        loop_var_raw = f"{var_name}_raw"
        lines.append(f"for {loop_var_raw} in ({start_str} as i64)..({end_str} as i64) {{")
        self.indent_level += 1
        lines.append(self.indent() + f"let mut {var_name} = {loop_var_raw} as f64;")
        self.declared_vars.add(var_name)

        for stmt in node.body:
            stmt_str = self.visit(stmt)
            if stmt_str:
                lines.append(self.indent() + stmt_str)

        self.indent_level -= 1
        lines.append(self.indent() + "}")
        return "\n".join(lines)

    def generic_visit(self, node):
        raise NotImplementedError(
            f"Node type {type(node).__name__} is not supported in direct JIT-Rust compilation"
        )


def compile_rust_code(rust_code: str) -> str:
    """
    Compiles generated Rust source into a dynamic library.
    """
    with tempfile.NamedTemporaryFile(suffix=".rs", delete=False, mode="w") as f:
        f.write(rust_code)
        rust_src = f.name

    ext = ".dylib" if sys.platform == "darwin" else (".dll" if sys.platform == "win32" else ".so")
    output_lib = rust_src.replace(".rs", ext)

    try:
        # Optimization flag -O ensures O(1) direct silicon efficiency
        cmd = ["rustc", "-O", "--crate-type=cdylib", "-o", output_lib, rust_src]
        subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
        return output_lib
    except subprocess.CalledProcessError as e:
        if os.path.exists(rust_src):
            os.unlink(rust_src)
        raise RuntimeError(f"Rust compilation failed: {e.stderr}") from e
    finally:
        if os.path.exists(rust_src):
            os.unlink(rust_src)


def execute_rust_jit(lib_path: str, func_name: str, args: list) -> float:
    """
    Loads dynamically compiled Rust library and executes the critical path.
    """
    try:
        lib = ctypes.CDLL(lib_path)
        func = getattr(lib, func_name)
        func.argtypes = [ctypes.c_double] * len(args)
        func.restype = ctypes.c_double

        c_args = [ctypes.c_double(float(a)) for a in args]
        res = func(*c_args)
        return float(res)
    finally:
        # Clean up dynamic library references and file from disk to avoid entropy leaks
        if sys.platform != "win32":
            import _ctypes

            _ctypes.dlclose(lib._handle)
        if os.path.exists(lib_path):
            try:
                os.unlink(lib_path)
            except Exception:  # noqa: S110
                pass


def compile_and_run_python_ast(source_code: str, global_ctx: dict) -> tuple[bool, Any]:
    """
    Tries to transpile, compile, and run the Python AST inside the dynamic Rust JIT.
    Returns (success, result/error_message).
    """
    try:
        tree = ast.parse(source_code)

        # Check if we have a single function definition
        func_defs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        if len(func_defs) != 1:
            return False, "JIT-Rust requires exactly one function definition as execution path"

        target_func = func_defs[0]
        func_name = target_func.name

        transpiler = PythonToRustTranspiler()
        rust_code = transpiler.visit(tree)

        # Gather inputs from global context
        args_values = []
        for arg in transpiler.arg_names:
            if arg not in global_ctx:
                return False, f"Missing value for argument: {arg} in context"
            val = global_ctx[arg]
            try:
                args_values.append(float(val))
            except (ValueError, TypeError):
                return False, f"Argument {arg} cannot be coerced to float for JIT-Rust"

        # Compile
        lib_path = compile_rust_code(rust_code)

        # Execute
        res = execute_rust_jit(lib_path, func_name, args_values)
        return True, res

    except NotImplementedError as e:
        return False, f"Fallback trigger: {e}"
    except Exception as e:
        return False, f"Unexpected compilation exception: {e}"
