# [C5-REAL] Exergy-Maximized
"""
CLI entrypoint para el motor FSM de despliegue.
Erradicación de bash probabilístico. Orquestación 100% Python.
"""
import click

from babylon60.engine.core.fsm_deploy_engine import FSMDeployEngine


@click.group(name="deploy")
def deploy_group():
    """Comandos de despliegue determinista (FSM)."""
    pass

@deploy_group.command("run-fsm")
def run_fsm():
    """Ejecuta la máquina de estados de despliegue."""
    click.echo("[C5-REAL] Inicializando FSM Deploy Engine...")
    engine = FSMDeployEngine()
    engine.run()
