#!/usr/bin/env python3
"""CORTEX Plugin Scaffold Generator.

Creates a complete plugin skeleton with manifest, Dockerfile,
OpenAPI stub, tests, and documentation.

Usage:
    python scripts/create_plugin.py my-plugin
    python scripts/create_plugin.py my-plugin --description "Does something cool"
"""
from __future__ import annotations

import argparse
import textwrap
from pathlib import Path


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")


def _module(name: str) -> str:
    return _slug(name).replace("-", "_")


def create_plugin(name: str, description: str, output_dir: Path) -> Path:
    """Generate a complete plugin scaffold."""
    slug = _slug(name)
    module = _module(name)
    plugin_dir = output_dir / slug
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # --- manifest.yaml ---
    (plugin_dir / "manifest.yaml").write_text(
        textwrap.dedent(f"""\
        name: {slug}
        version: 0.1.0
        description: "{description}"
        author: Your Name <you@example.com>

        runtime:
          type: docker
          image: cortex-plugin-{slug}:latest

        capabilities:
          - name: {module}_action
            description: "Primary action for {name}"
            endpoint: /action
            method: POST

        trust:
          min_cortex_version: "8.0"
          sandbox: true
          network: false
        """)
    )

    # --- openapi.yaml ---
    (plugin_dir / "openapi.yaml").write_text(
        textwrap.dedent(f"""\
        openapi: "3.1.0"
        info:
          title: {name} Plugin API
          version: "0.1.0"
          description: "{description}"
        paths:
          /action:
            post:
              operationId: {module}_action
              summary: Execute the primary action
              requestBody:
                required: true
                content:
                  application/json:
                    schema:
                      type: object
                      properties:
                        input:
                          type: string
                          description: Input for the action
                      required:
                        - input
              responses:
                "200":
                  description: Successful response
                  content:
                    application/json:
                      schema:
                        type: object
                        properties:
                          result:
                            type: string
                          status:
                            type: string
                            enum: [success, error]
          /health:
            get:
              operationId: health
              summary: Health check
              responses:
                "200":
                  description: Plugin is healthy
        """)
    )

    # --- Dockerfile ---
    (plugin_dir / "Dockerfile").write_text(
        textwrap.dedent(f"""\
        FROM python:3.13-slim

        LABEL org.opencontainers.image.source="https://github.com/YOUR_ORG/{slug}"
        LABEL org.opencontainers.image.description="{description}"

        WORKDIR /app

        # Security: run as non-root
        RUN groupadd -r plugin && useradd -r -g plugin plugin

        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt

        COPY {module}/ ./{module}/
        COPY main.py .

        USER plugin
        EXPOSE 8080

        HEALTHCHECK --interval=30s --timeout=5s \\
          CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

        CMD ["python", "main.py"]
        """)
    )

    # --- requirements.txt ---
    (plugin_dir / "requirements.txt").write_text(
        "fastapi>=0.110\nuvicorn[standard]>=0.27\n"
    )

    # --- main.py ---
    (plugin_dir / "main.py").write_text(
        textwrap.dedent(f"""\
        \"\"\"CORTEX Plugin: {name}.\"\"\"
        from __future__ import annotations

        import uvicorn
        from fastapi import FastAPI
        from pydantic import BaseModel

        app = FastAPI(title="{name}", version="0.1.0")


        class ActionRequest(BaseModel):
            input: str


        class ActionResponse(BaseModel):
            result: str
            status: str = "success"


        @app.post("/action")
        async def action(req: ActionRequest) -> ActionResponse:
            # TODO: Implement your plugin logic here
            return ActionResponse(result=f"Processed: {{req.input}}")


        @app.get("/health")
        async def health() -> dict[str, str]:
            return {{"status": "healthy", "plugin": "{slug}"}}


        if __name__ == "__main__":
            uvicorn.run(app, host="0.0.0.0", port=8080)
        """)
    )

    # --- Module directory ---
    module_dir = plugin_dir / module
    module_dir.mkdir(exist_ok=True)
    (module_dir / "__init__.py").write_text(
        f'"""CORTEX Plugin: {name}."""\n\n__version__ = "0.1.0"\n'
    )

    # --- Tests ---
    tests_dir = plugin_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")
    (tests_dir / f"test_{module}.py").write_text(
        textwrap.dedent(f"""\
        \"\"\"Tests for {name} plugin.\"\"\"
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app)


        def test_health():
            resp = client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert data["plugin"] == "{slug}"


        def test_action():
            resp = client.post("/action", json={{"input": "hello"}})
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "hello" in data["result"]
        """)
    )

    # --- README ---
    (plugin_dir / "README.md").write_text(
        textwrap.dedent(f"""\
        # {name}

        > {description}

        ## Quick Start

        ```bash
        # Build
        docker build -t cortex-plugin-{slug}:latest .

        # Run
        docker run -p 8080:8080 cortex-plugin-{slug}:latest

        # Test
        curl http://localhost:8080/health
        curl -X POST http://localhost:8080/action \\
          -H "Content-Type: application/json" \\
          -d '{{"input": "test"}}'
        ```

        ## Install as CORTEX Plugin

        ```bash
        cortex plugin install ./{slug}
        ```

        ## Development

        ```bash
        pip install -r requirements.txt
        python main.py

        # Run tests
        pip install pytest httpx
        pytest tests/ -v
        ```
        """)
    )

    return plugin_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold a new CORTEX plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python scripts/create_plugin.py weather-lookup
              python scripts/create_plugin.py code-reviewer --description "AI code review"
              python scripts/create_plugin.py data-cleaner -o ./plugins
        """),
    )
    parser.add_argument("name", help="Plugin name (e.g. 'weather-lookup')")
    parser.add_argument(
        "--description", "-d",
        default="A CORTEX plugin",
        help="Short description of the plugin",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path.cwd(),
        help="Output directory (default: current directory)",
    )

    args = parser.parse_args()
    plugin_dir = create_plugin(args.name, args.description, args.output)

    print(f"\n✅ Plugin scaffolded at: {plugin_dir}")
    print(f"\n   cd {plugin_dir}")
    print(f"   docker build -t cortex-plugin-{_slug(args.name)} .")
    print(f"   docker run -p 8080:8080 cortex-plugin-{_slug(args.name)}")
    print("\n   Files created:")
    for f in sorted(plugin_dir.rglob("*")):
        if f.is_file():
            print(f"     {f.relative_to(plugin_dir)}")


if __name__ == "__main__":
    main()
