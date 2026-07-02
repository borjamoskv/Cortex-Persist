# [C5-REAL] Exergy-Maximized
"""
FSM Deploy Engine.

Motor de estados finitos determinista para orquestar el CI/CD, eliminando scripts
probabilísticos de bash. Diseñado bajo las invariantes de tolerancia bizantina
y Fail-Fast Termodinámico (LL-AC-07, L12).
"""

import enum
import os
import subprocess
import sys
from collections.abc import Callable


class DeployState(enum.Enum):
    INIT = "INIT"
    SCOPE_CHECK = "SCOPE_CHECK"
    QUALITY_GATE = "QUALITY_GATE"
    BUILD_CONTAINER = "BUILD_CONTAINER"
    INFRA_TERRAFORM = "INFRA_TERRAFORM"
    DEPLOY_EDGE = "DEPLOY_EDGE"
    SMOKE_TEST = "SMOKE_TEST"
    END = "END"
    ABORT = "ABORT"


class DeployContext:
    def __init__(self):
        self.is_automation_only: bool = False
        self.is_release_only: bool = False
        self.target_env: str = "production"
        self.sha: str = os.getenv("GITHUB_SHA", "unknown")


class FSMDeployEngine:
    def __init__(self):
        self.state: DeployState = DeployState.INIT
        self.context: DeployContext = DeployContext()
        self.transitions: dict[DeployState, Callable[[], DeployState]] = {
            DeployState.INIT: self._handle_init,
            DeployState.SCOPE_CHECK: self._handle_scope_check,
            DeployState.QUALITY_GATE: self._handle_quality_gate,
            DeployState.BUILD_CONTAINER: self._handle_build_container,
            DeployState.INFRA_TERRAFORM: self._handle_infra_terraform,
            DeployState.DEPLOY_EDGE: self._handle_deploy_edge,
            DeployState.SMOKE_TEST: self._handle_smoke_test,
        }

    def run(self) -> None:
        """Bucle FSM."""
        print("[FSM] Iniciando ignición determinista de servicios de despliegue.")
        while self.state not in (DeployState.END, DeployState.ABORT):
            handler = self.transitions.get(self.state)
            if not handler:
                print(f"[FSM] ERROR: Transición indefinida para estado {self.state}")
                self.state = DeployState.ABORT
                break

            print(f"[FSM] Transición a estado: {self.state.value}")
            try:
                next_state = handler()
                self.state = next_state
            except Exception as e:
                # [L12] Fail-Fast Termodinámico: Crashear estrepitosamente.
                print(f"[FSM-CRASH] Fractura termodinámica detectada en estado {self.state.value}: {e}")
                self.state = DeployState.ABORT

        if self.state == DeployState.ABORT:
            print("[FSM] ABORTO CRÍTICO. Apoptosis invocada.")
            sys.exit(1)

        print("[FSM] Despliegue FSM completado (Ontología Cero lograda).")

    def _exec(self, cmd: list[str], cwd: str | None = None) -> None:
        print(f"      > Ejecutando: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"Error executing {' '.join(cmd)}: Exit code {result.returncode}")

    def _handle_init(self) -> DeployState:
        # Validación de asimetrías de estado iniciales.
        if "GITHUB_WORKSPACE" in os.environ:
            os.chdir(os.environ["GITHUB_WORKSPACE"])
        return DeployState.SCOPE_CHECK

    def _handle_scope_check(self) -> DeployState:
        # Determina si solo se han modificado docs/config
        diff_cmd = ["git", "diff", "--name-only", "HEAD~1", "HEAD"]
        try:
            result = subprocess.run(diff_cmd, capture_output=True, text=True, check=True)
            files = result.stdout.strip().split("\n")
            if all(f.endswith(".md") or f.endswith(".json") for f in files if f):
                self.context.is_release_only = True
                print("[FSM] Scope detectado: Release/Docs. Saltando contenedores.")
        except subprocess.CalledProcessError:
            # Fallback seguro si git diff falla (ej. shallow clone parcial)
            pass

        return DeployState.QUALITY_GATE

    def _handle_quality_gate(self) -> DeployState:
        if not self.context.is_release_only:
            self._exec(["ruff", "check", "cortex/", "--output-format=github"])
            self._exec(["pytest", "tests/", "-q", "--tb=short"])
        return DeployState.BUILD_CONTAINER

    def _handle_build_container(self) -> DeployState:
        if self.context.is_release_only:
            return DeployState.INFRA_TERRAFORM
        
        # Simulación C5-REAL Build / Trivy
        image_name = f"cortex-sovereign:{self.context.sha}"
        self._exec(["docker", "build", "-t", image_name, "."])
        # Trivy Scan determinista
        self._exec([
            "docker", "run", "--rm", 
            "-v", "/var/run/docker.sock:/var/run/docker.sock",
            "aquasec/trivy", "image", "--exit-code", "0", "--severity", "CRITICAL,HIGH", image_name
        ])
        return DeployState.INFRA_TERRAFORM

    def _handle_infra_terraform(self) -> DeployState:
        tf_dir = "infra/terraform"
        if os.path.exists(tf_dir):
            self._exec(["terraform", "init"], cwd=tf_dir)
            self._exec(["terraform", "validate"], cwd=tf_dir)
            self._exec(["terraform", "apply", "-auto-approve"], cwd=tf_dir)
        else:
            print("[FSM] Directorio Terraform inexistente. Omitiendo infraestructura base.")
        return DeployState.DEPLOY_EDGE

    def _handle_deploy_edge(self) -> DeployState:
        # Integración de la lógica de deploy.yml (Cloudflare Wrangler) y K8s de sovereign-deploy.yml
        k8s_dir = "infra/k8s/gcp"
        if os.path.exists(k8s_dir):
            self._exec(["kubectl", "apply", "-f", k8s_dir, "--recursive"])
        else:
            print("[FSM] Directorio K8s inexistente. Omitiendo Kubernetes.")
            
        worker_file = "src/worker.js"
        if os.path.exists(worker_file):
            print("[FSM] Despliegue Perimetral Inmediato (Cloudflare Workers)")
            # En FSM no usamos variables bash, construimos el comando determinista.
            self._exec(["npx", "wrangler", "deploy", worker_file, "--name", "ultrathink-edge-ingest"])
            
        return DeployState.SMOKE_TEST

    def _handle_smoke_test(self) -> DeployState:
        # Validación matemática y aserciones en vivo
        endpoints = []
        for v in ["AWS_ENDPOINT", "GCP_ENDPOINT", "AZURE_ENDPOINT"]:
            if val := os.getenv(v):
                endpoints.append(val)
                
        for ep in endpoints:
            self._exec(["curl", "-sf", f"{ep}/health"])
            
        return DeployState.END
