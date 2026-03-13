from unittest.mock import AsyncMock, patch

import pytest

from cortex.ui_control.maestro import MaestroUI
from cortex.ui_control.models import AppTarget


@pytest.fixture
def maestro():
    return MaestroUI()


@pytest.mark.asyncio
async def test_activate_app_success(maestro):
    with patch("cortex.ui_control.maestro.run_applescript", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = ""
        target = AppTarget(name="Safari")

        result = await maestro.activate_app(target)

        assert result.success is True
        mock_run.assert_called_once()
        script_arg = mock_run.call_args[0][0]
        assert 'tell application "Safari"' in script_arg
        assert "activate" in script_arg


@pytest.mark.asyncio
async def test_activate_app_failure(maestro):
    with patch("cortex.ui_control.maestro.run_applescript", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = Exception("osascript failed")
        target = AppTarget(name="Safari")

        result = await maestro.activate_app(target)

        assert result.success is False
        assert "osascript failed" in result.error


@pytest.mark.asyncio
async def test_inject_keystroke_app_not_running(maestro):
    with patch(
        "cortex.ui_control.maestro.is_app_running", new_callable=AsyncMock
    ) as mock_is_running:
        mock_is_running.return_value = False
        target = AppTarget(name="NonExistentApp")

        result = await maestro.inject_keystroke(target, "v", ["command down"])

        assert result.success is False
        assert "is not running" in result.error


@pytest.mark.asyncio
async def test_inject_keystroke_success(maestro):
    with patch(
        "cortex.ui_control.maestro.is_app_running", new_callable=AsyncMock
    ) as mock_is_running:
        mock_is_running.return_value = True

        with patch("cortex.ui_control.maestro.run_applescript", new_callable=AsyncMock) as mock_run:
            target = AppTarget(name="Safari")

            result = await maestro.inject_keystroke(target, "t", ["command down"])

            assert result.success is True
            mock_run.assert_called_once()
            script_arg = mock_run.call_args[0][0]
            assert 'tell application "Safari" to activate' in script_arg
            assert 'keystroke "t" using {command down}' in script_arg


@pytest.mark.asyncio
async def test_click_menu_invalid_path(maestro):
    target = AppTarget(name="Safari")
    result = await maestro.click_menu_item(target, ["File"])  # Only top level

    assert result.success is False
    assert "must have at least" in result.error


@pytest.mark.asyncio
async def test_click_menu_success(maestro):
    with patch("cortex.ui_control.maestro.run_applescript", new_callable=AsyncMock) as mock_run:
        target = AppTarget(name="Safari")
        result = await maestro.click_menu_item(target, ["File", "Export as PDF..."])

        assert result.success is True
        mock_run.assert_called_once()
        script_arg = mock_run.call_args[0][0]
        assert 'click menu item "Export as PDF..." of menu "File"' in script_arg
