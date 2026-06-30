# [C5-REAL] Exergy-Maximized
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from babylon60.extensions.ui_control.maestro import MaestroUI
from babylon60.extensions.ui_control.models import AppTarget


@pytest.fixture
def maestro():
    return MaestroUI()


@pytest.mark.asyncio
async def test_activate_app_success(maestro):
    with patch(
        "cortex_extensions.ui_control.maestro.run_applescript", new_callable=AsyncMock
    ) as mock_run:
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
    with patch(
        "cortex_extensions.ui_control.maestro.run_applescript", new_callable=AsyncMock
    ) as mock_run:
        mock_run.side_effect = Exception("osascript failed")
        target = AppTarget(name="Safari")

        result = await maestro.activate_app(target)

        assert result.success is False
        assert "osascript failed" in result.error


@pytest.mark.asyncio
async def test_inject_keystroke_app_not_running(maestro):
    with patch(
        "cortex_extensions.ui_control.maestro.is_app_running", new_callable=AsyncMock
    ) as mock_is_running:
        mock_is_running.return_value = False
        target = AppTarget(name="NonExistentApp")

        result = await maestro.inject_keystroke(target, "v", ["command down"])

        assert result.success is False
        assert "is not running" in result.error


@pytest.mark.asyncio
async def test_inject_keystroke_success(maestro):
    with patch(
        "cortex_extensions.ui_control.maestro.is_app_running", new_callable=AsyncMock
    ) as mock_is_running:
        mock_is_running.return_value = True

        with patch(
            "cortex_extensions.ui_control.maestro.run_applescript", new_callable=AsyncMock
        ) as mock_run:
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
    with patch(
        "cortex_extensions.ui_control.maestro.run_applescript", new_callable=AsyncMock
    ) as mock_run:
        target = AppTarget(name="Safari")
        result = await maestro.click_menu_item(target, ["File", "Export as PDF..."])

        assert result.success is True
        mock_run.assert_called_once()
        script_arg = mock_run.call_args[0][0]
        assert 'click menu item "Export as PDF..." of menu "File"' in script_arg


def test_screenshot_region_success(maestro):
    from babylon60.extensions.ui_control.models import InteractionResult
    from unittest.mock import mock_open

    with (
        patch("cortex_extensions.ui_control.vision.CG") as mock_cg,
        patch.object(maestro.vision, "capture_screen") as mock_capture,
    ):
        mock_capture.return_value = InteractionResult(success=True, output="/fake/path.png")

        # Mocking open and os.path.exists
        with (
            patch("builtins.open", mock_open(read_data=b"fake_png_data")),
            patch("os.path.exists", return_value=True),
            patch("os.remove") as mock_remove,
        ):
            data = maestro.screenshot_region(10, 20, 100, 200)
            assert data == b"fake_png_data"
            mock_capture.assert_called_once_with(region=(10, 20, 100, 200))
            mock_remove.assert_called_once_with("/fake/path.png")


@pytest.mark.asyncio
async def test_wait_for_element_by_label_success(maestro):
    from babylon60.extensions.ui_control.models import AXElement

    with patch("cortex_extensions.ui_control.accessibility.NSWorkspace") as mock_ws:
        mock_app = MagicMock()
        mock_app.localizedName.return_value = "Safari"
        mock_ws.sharedWorkspace.return_value.frontmostApplication.return_value = mock_app

        # Mock element lookup
        mock_element = AXElement(role="AXButton", title="Submit")
        with (
            patch.object(maestro.accessibility, "find_element", return_value=None),
            patch.object(maestro.accessibility, "find_element_by_title", return_value=mock_element),
        ):
            found = await maestro.wait_for_element("Submit", timeout_s=1.0)
            assert found is True


@pytest.mark.asyncio
async def test_wait_for_element_by_label_timeout(maestro):
    with patch("cortex_extensions.ui_control.accessibility.NSWorkspace") as mock_ws:
        mock_app = MagicMock()
        mock_app.localizedName.return_value = "Safari"
        mock_ws.sharedWorkspace.return_value.frontmostApplication.return_value = mock_app

        with (
            patch.object(maestro.accessibility, "find_element", return_value=None),
            patch.object(maestro.accessibility, "find_element_by_title", return_value=None),
        ):
            found = await maestro.wait_for_element("NonExistent", timeout_s=0.1)
            assert found is False
