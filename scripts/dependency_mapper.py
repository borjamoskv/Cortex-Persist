import ast
import os
from collections import defaultdict

deps_to_find = [
    "sqlite_vec", "aiosqlite", "click", "rich", "pydantic", 
    "langchain", "langchain_core", "langchain_community", "langchain_ollama", 
    "confluent_kafka", "numpy", "fastapi", "starlette", "uvicorn", "httpx", 
    "mcp", "watchdog", "aiohttp", "neo4j", "stripe", "pytrends", "pandas",
    "sentence_transformers", "onnxruntime", "chromadb"
]

mapping = defaultdict(list)

for root, _, files in os.walk("cortex"):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            try:
                tree = ast.parse(content, filename=path)
            except Exception:
                continue
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        base = alias.name.split('.')[0]
                        if base in deps_to_find:
                            mapping[base].append(path)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        base = node.module.split('.')[0]
                        if base in deps_to_find:
                            mapping[base].append(path)

out_path = "/Users/borjafernandezangulo/.gemini/antigravity/brain/485a969b-d38a-4d5b-afde-2d29ea95d0eb/dependency_map.md"
with open(out_path, "w") as out:
    out.write("# Mapa de Dependencias a Eliminar (UltraThink Blast Radius)\n\n")
    for dep in sorted(deps_to_find):
        files = sorted(list(set(mapping.get(dep, []))))
        out.write(f"### `{dep}` ({len(files)} files)\n")
        if not files:
            out.write("- No usage found via AST imports.\n")
        else:
            for f in files:
                out.write(f"- `{f}`\n")
        out.write("\n")
print(f"Mapping complete. See {out_path}")
