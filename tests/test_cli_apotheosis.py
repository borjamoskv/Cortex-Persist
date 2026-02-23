import pytest
from click.testing import CliRunner

from cortex.cli.__main__ import cli
from cortex.cli.apotheosis_cmds import apotheosis_cmds


@pytest.fixture
def runner():
    return CliRunner(env={"CORTEX_NO_SLEEP": "1"})


def test_apotheosis_command_registered(runner):
    """Verifica que 'apotheosis' está en el entrypoint principal de cortex."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "apotheosis" in result.output
    # Debe tener la descripción correcta
    assert "El Daemon Autárquico" in result.output


def test_apotheosis_group_help(runner):
    """Verifica la ayuda del comando apotheosis."""
    result = runner.invoke(apotheosis_cmds, ["--help"])
    assert result.exit_code == 0
    assert "manifest" in result.output
    assert "guard" in result.output
    assert "nirvana" in result.output


def test_apotheosis_manifest_help(runner):
    """Verifica la ayuda de apotheosis manifest."""
    result = runner.invoke(apotheosis_cmds, ["manifest", "--help"])
    assert result.exit_code == 0
    assert "Materializa un ecosistema" in result.output


def test_apotheosis_guard_help(runner):
    """Verifica la ayuda de apotheosis guard."""
    result = runner.invoke(apotheosis_cmds, ["guard", "--help"])
    assert result.exit_code == 0
    assert "Sue\u00f1o Demi\u00fargico" in result.output


def test_apotheosis_nirvana_help(runner):
    """Verifica la ayuda de apotheosis nirvana."""
    result = runner.invoke(apotheosis_cmds, ["nirvana", "--help"])
    assert result.exit_code == 0
    assert "Purifica un archivo/dir aniquilando toda complejidad" in result.output
