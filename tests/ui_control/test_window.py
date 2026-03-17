"""Tests para WindowEngine — gestión de ventanas vía AppleScript."""

from unittest.mock import AsyncMock, patch

import pytest

from cortex.extensions.ui_control.models import AppTarget
from cortex.extensions.ui_control.window import WindowEngine


@pytest.fixture
def win():
    return WindowEngine()


class TestListWindows:
    """Tests de WindowEngine.list_windows()."""

    @pytest.mark.asyncio
    async def test_list_windows_parses_output(self, win):
        """Parsea la salida pipe-delimited de System Events."""
        # Formato real: name|||x,y|||w,h|||minimized
        mock_output = "Finder|||100,50|||800,600|||false"
        with patch(
            "cortex.extensions.ui_control.window.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = mock_output
            windows = await win.list_windows("Finder")
            assert len(windows) == 1
            w = windows[0]
            assert w.title == "Finder"
            assert w.x == 100
            assert w.y == 50
            assert w.width == 800
            assert w.height == 600
            assert not w.minimized

    @pytest.mark.asyncio
    async def test_list_windows_empty(self, win):
        """Sin ventanas devuelve lista vacía."""
        with patch(
            "cortex.extensions.ui_control.window.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = None
            windows = await win.list_windows("AppInexistente")
            assert windows == []


class TestGetFrontmost:
    """Tests de WindowEngine.get_frontmost()."""

    @pytest.mark.asyncio
    async def test_get_frontmost_success(self, win):
        """Devuelve la ventana activa con formato pipe."""
        # Formato real: appName|||winName|||x,y|||w,h
        mock_output = "Safari|||Main Window|||0,0|||1440,900"
        with patch(
            "cortex.extensions.ui_control.window.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = mock_output
            result = await win.get_frontmost()
            assert result is not None
            assert result.app_name == "Safari"
            assert result.title == "Main Window"
            assert result.width == 1440

    @pytest.mark.asyncio
    async def test_get_frontmost_no_window(self, win):
        """Sin ventana activa devuelve None."""
        with patch(
            "cortex.extensions.ui_control.window.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = None
            result = await win.get_frontmost()
            assert result is None


class TestWindowOperations:
    """Tests para move, resize, minimize, restore, fullscreen, close."""

    @pytest.mark.asyncio
    async def test_move_window(self, win):
        """Mueve la ventana a coordenadas específicas."""
        with patch(
            "cortex.extensions.ui_control.window.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            target = AppTarget(name="Finder")
            result = await win.move(target, 200, 100)
            assert result.success
            script = mock.call_args[0][0]
            assert "200" in script and "100" in script

    @pytest.mark.asyncio
    async def test_resize_window(self, win):
        """Redimensiona la ventana."""
        with patch(
            "cortex.extensions.ui_control.window.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await win.resize(AppTarget(name="Finder"), 1024, 768)
            assert result.success

    @pytest.mark.asyncio
    async def test_minimize_window(self, win):
        """Minimiza una ventana."""
        with patch(
            "cortex.extensions.ui_control.window.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await win.minimize(AppTarget(name="Finder"))
            assert result.success

    @pytest.mark.asyncio
    async def test_close_window(self, win):
        """Cierra la ventana (Cmd+W)."""
        with patch(
            "cortex.extensions.ui_control.window.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await win.close_window(AppTarget(name="Finder"))
            assert result.success
