import re
from pathlib import Path


def detect_routers(files: list):
    routers = []

    for file in files:
        try:
            content = Path(file).read_text(errors="ignore")

            # FastAPI
            fastapi_routes = re.findall(
                r'@(?:router|app)\.(get|post|put|delete|patch)\(["\'](.+?)["\']\)',
                content
            )
            for method, path in fastapi_routes:
                routers.append({
                    "type": "FastAPI",
                    "method": method.upper(),
                    "path": path,
                    "file": file
                })

            # Express
            express_routes = re.findall(
                r'(?:router|app)\.(get|post|put|delete|patch)\(["\'](.+?)["\']\)',
                content
            )
            for method, path in express_routes:
                routers.append({
                    "type": "Express",
                    "method": method.upper(),
                    "path": path,
                    "file": file
                })

        except Exception:
            continue

    return routers
