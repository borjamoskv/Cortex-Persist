import ast
import operator
from collections.abc import Callable
from typing import Any

from cortex.utils.errors import PearlError

try:
    import cortex_rust
except ImportError:
    cortex_rust = None


class PearlEngine:
    """
    PeARL (Program-Aided Reasoner over Logic) Primitive Induction Engine.
    Implements AX-043: Structural Common Sense via logical primitives.
    """

    def __init__(self):
        # Core ARC primitives (subset of the 77 mentioned in AX-043)
        self.primitives: dict[str, Callable[..., Any]] = {
            # Geometry & Transformation
            "move": self._move,
            "rotate": self._rotate,
            "reflect": self._reflect,
            "scale": self._scale,
            # Matrix Ops
            "crop": self._crop,
            "fill": self._fill,
            "get_pixel": self._get_pixel,
            "set_pixel": self._set_pixel,
            # Logic & Search
            "count": self._count,
            "exists": self._exists,
            "get_objects": self._get_objects,
            "color": self._color,
        }

        # Vector 1 Extension: Rust Performance Injection (AX-051)
        if cortex_rust:
            self.primitives.update({
                "move": cortex_rust.move_grid,
                "rotate": cortex_rust.rotate_grid,
                "reflect": cortex_rust.reflect_grid,
                "scale": cortex_rust.scale_grid,
                "get_objects": cortex_rust.get_objects,
            })

    def register_primitive(self, name: str, func: Callable[..., Any]):
        """Registers a new JIT-formed primitive (AX-046)."""
        if name in self.primitives:
            raise PearlError(f"Primitive '{name}' already exists.")
        self.primitives[name] = func

    def evaluate(self, expression: str, context: dict[str, Any] | None = None) -> Any:
        """
        Safely evaluate a PeARL expression string using Python AST.
        """
        if context is None:
            context = {}

        try:
            tree = ast.parse(expression, mode="eval")
            return self._eval(tree.body, context)
        except Exception as err:
            raise PearlError(f"Evaluation error: {err}") from err

    def sandbox_execute(self, code: str, inputs: dict[str, Any]) -> Any:
        """
        Executes a block of Python/PeARL code in a restricted environment.
        """
        safe_builtins = {
            "range": range,
            "len": len,
            "list": list,
            "dict": dict,
            "sum": sum,
            "min": min,
            "max": max,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
        }

        exec_globals = {**self.primitives, "__builtins__": safe_builtins}
        locals_dict = {**inputs}

        try:
            exec(code, exec_globals, locals_dict)
            return locals_dict.get("output") or locals_dict.get("result")
        except Exception as err:
            raise PearlError(f"Sandbox execution error: {err}") from err

    async def induction_v2(
        self, bridge: Any, task_description: str, examples: list[dict[str, Any]]
    ) -> Any:
        """
        Induces a PeARL program using the provided LLMBridge (AX-046).
        """
        return await bridge.induce_program(task_description, examples)

    def _eval(self, node: ast.AST, context: dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in context:
                return context[node.id]
            if node.id in self.primitives:
                return self.primitives[node.id]
            raise PearlError(f"Unknown name: {node.id}")
        elif isinstance(node, ast.Call):
            func = self._eval(node.func, context)
            args = [self._eval(arg, context) for arg in node.args]
            return func(*args)
        elif isinstance(node, ast.BinOp):
            left = self._eval(node.left, context)
            right = self._eval(node.right, context)
            op_map: dict[type[ast.AST], Any] = { # type: ignore
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
            }
            op_func = op_map.get(type(node.op))
            if op_func:
                return op_func(left, right)
            raise PearlError(f"Unsupported operator: {type(node.op)}")
        raise PearlError(f"Unsupported node type: {type(node)}")

    # Primitive implementations (AX-043)
    def _move(self, grid: Any, dx: int, dy: int) -> Any:
        rows, cols = len(grid), len(grid[0])
        new_grid = [[0] * cols for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] != 0:
                    nr, nc = r + dy, c + dx
                    if 0 <= nr < rows and 0 <= nc < cols:
                        new_grid[nr][nc] = grid[r][c]
        return new_grid

    def _rotate(self, grid: Any, angle: int) -> Any:
        if angle == 90:
            rotated = []
            for row_tuple in zip(*grid[::-1]):
                rotated.append(list(row_tuple))
            return rotated
        if angle == 180:
            return [row[::-1] for row in grid[::-1]]
        if angle == 270:
            rotated_270 = []
            for row_tuple in zip(*grid):
                rotated_270.append(list(row_tuple)[::-1])
            return rotated_270
        return grid

    def _reflect(self, grid: Any, axis: str) -> Any:
        if axis == "x":
            return grid[::-1]
        if axis == "y":
            return [row[::-1] for row in grid]
        raise PearlError("Reflection axis must be 'x' or 'y'.")

    def _scale(self, grid: Any, factor: int) -> Any:
        new_grid = []
        for row in grid:
            new_row = []
            for val in row:
                new_row.extend([val] * factor)
            for _ in range(factor):
                new_grid.append(new_row[:])
        return new_grid

    def _get_pixel(self, grid: Any, x: int, y: int) -> int:
        return grid[y][x]

    def _set_pixel(self, grid: Any, x: int, y: int, value: int) -> Any:
        new_grid = [row[:] for row in grid]
        new_grid[y][x] = value
        return new_grid

    def _crop(self, grid: Any, x: int, y: int, w: int, h: int) -> Any:
        return [row[x : x + w] for row in grid[y : y + h]]

    def _fill(self, grid: Any, value: int) -> Any:
        return [[value for _ in row] for row in grid]

    def _color(self, grid: Any, old: int, new: int) -> Any:
        return [[new if val == old else val for val in row] for row in grid]

    def _count(self, grid: Any, color: int) -> int:
        return sum(row.count(color) for row in grid)

    def _exists(self, grid: Any, color: int) -> bool:
        return any(color in row for row in grid)

    def _get_objects(self, grid: Any) -> list[dict[str, Any]]:
        rows, cols = len(grid), len(grid[0])
        visited = set()
        objects = []
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] != 0 and (r, c) not in visited:
                    color = grid[r][c]
                    pixels = []
                    queue = [(r, c)]
                    visited.add((r, c))
                    min_r, max_r = r, r
                    min_c, max_c = c, c
                    while queue:
                        curr_r, curr_c = queue.pop(0)
                        pixels.append((curr_r, curr_c))
                        min_r, max_r = min(min_r, curr_r), max(max_r, curr_r)
                        min_c, max_c = min(min_c, curr_c), max(max_c, curr_c)
                        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            nr, nc = curr_r + dr, curr_c + dc
                            if (
                                0 <= nr < rows
                                and 0 <= nc < cols
                                and grid[nr][nc] == color
                                and (nr, nc) not in visited
                            ):
                                visited.add((nr, nc))
                                queue.append((nr, nc))
                    objects.append(
                        {
                            "color": color,
                            "pixels": pixels,
                            "bounds": (min_c, min_r, max_c - min_c + 1, max_r - min_r + 1),
                        }
                    )
        return objects
