# [C5-REAL] Exergy-Maximized
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from babylon60.extensions.bci.maestro_bridge import BCIMaestroBridge, get_bci_maestro_handlers
from babylon60.extensions.ui_control.bootstrapper import PermsBootstrapper
from babylon60.extensions.ui_control.feedback_loop import UIFeedbackLoop
from babylon60.extensions.ui_control.models import AppTarget, InteractionResult, Point


# ─── BCI Maestro Bridge Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_bci_maestro_bridge_app_activation():
    mock_maestro = MagicMock()
    mock_maestro.activate_app = AsyncMock(return_value=InteractionResult(success=True))

    bridge = BCIMaestroBridge(maestro=mock_maestro)

    # Invoke desktop action for activate_app
    payload = '{"app": "Finder"}'
    result = await bridge.handle_desktop_action("activate_app", payload)

    assert result.success is True
    # Verify app was correctly converted to AppTarget
    mock_maestro.activate_app.assert_called_once_with(target=AppTarget(name="Finder"))


@pytest.mark.asyncio
async def test_bci_maestro_bridge_mouse_click():
    mock_maestro = MagicMock()
    # Click could be synchronous or async depending on wrapper, make mock handle both
    mock_maestro.click = MagicMock(return_value=InteractionResult(success=True))

    bridge = BCIMaestroBridge(maestro=mock_maestro)

    payload = '{"x": 100, "y": 200, "button": "left"}'
    result = await bridge.handle_desktop_action("click", payload)

    assert result.success is True
    mock_maestro.click.assert_called_once_with(point=Point(x=100, y=200), button="left")


@pytest.mark.asyncio
async def test_bci_maestro_bridge_invalid_method():
    mock_maestro = MagicMock()
    # Remove any mock attributes to simulate missing method
    if hasattr(mock_maestro, "nonexistent"):
        delattr(mock_maestro, "nonexistent")

    bridge = BCIMaestroBridge(maestro=mock_maestro)

    result = await bridge.handle_desktop_action("nonexistent", "{}")
    assert result["success"] is False
    assert "has no attribute" in result["error"]


def test_get_bci_maestro_handlers():
    handlers = get_bci_maestro_handlers()
    assert 5 in handlers
    assert callable(handlers[5])


# ─── UIFeedbackLoop Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_feedback_loop_success():
    mock_maestro = MagicMock()
    mock_maestro.screenshot = MagicMock(
        return_value=InteractionResult(success=True, output="/tmp/test.png")
    )

    loop = UIFeedbackLoop(maestro=mock_maestro)

    # Mock native OCR so we don't call actual macOS Vision APIs during test
    loop.perform_native_ocr = MagicMock(
        return_value=[
            {"text": "Goal Found", "confidence": 1.0, "x": 0, "y": 0, "width": 1, "height": 1}
        ]
    )

    # Verification function checks if 'Goal Found' is in full text
    def verify_fn(state):
        return "Goal Found" in state["full_text"]

    decide_fn = MagicMock(return_value=[])

    result = await loop.execute_perception_action_loop(
        goal="Find the goal",
        verify_fn=verify_fn,
        decide_fn=decide_fn,
        max_iterations=3,
        step_delay=0.01,
    )

    assert result.success is True
    assert "verified" in result.output
    # Verification was checked immediately on first iteration, no decisions/actions needed
    decide_fn.assert_not_called()


@pytest.mark.asyncio
async def test_feedback_loop_action_execution():
    mock_maestro = MagicMock()
    mock_maestro.screenshot = MagicMock(
        return_value=InteractionResult(success=True, output="/tmp/test.png")
    )
    mock_maestro.activate_app = AsyncMock(return_value=InteractionResult(success=True))

    loop = UIFeedbackLoop(maestro=mock_maestro)
    loop.perform_native_ocr = MagicMock(
        side_effect=[
            [{"text": "Not yet", "confidence": 1.0, "x": 0, "y": 0, "width": 1, "height": 1}],
            [{"text": "Goal Found", "confidence": 1.0, "x": 0, "y": 0, "width": 1, "height": 1}],
        ]
    )

    def verify_fn(state):
        return "Goal Found" in state["full_text"]

    # Decide to run an action on the first step
    def decide_fn(state, goal):
        return [{"action": "activate_app", "args": {"app": "Safari"}}]

    result = await loop.execute_perception_action_loop(
        goal="Find the goal",
        verify_fn=verify_fn,
        decide_fn=decide_fn,
        max_iterations=3,
        step_delay=0.01,
    )

    assert result.success is True
    # Verify that the decided action was executed
    mock_maestro.activate_app.assert_called_once_with(target=AppTarget(name="Safari"))


# ─── Permissions Bootstrapper Tests ───────────────────────────────────


def test_perms_bootstrapper_non_mac():
    with patch("sys.platform", "linux"):
        res = PermsBootstrapper.verify_and_prompt_permissions()
        # Should skip and return false flags
        assert res["accessibility"] is False
        assert res["screen_recording"] is False


def test_perms_bootstrapper_check():
    # Mock ApplicationServices and Quartz
    mock_app_services = MagicMock()
    mock_app_services.AXIsProcessTrustedWithOptions = MagicMock(return_value=True)

    mock_quartz = MagicMock()
    mock_quartz.CGPreflightScreenCaptureAccess = MagicMock(return_value=True)

    with (
        patch("sys.platform", "darwin"),
        patch("cortex_extensions.ui_control.bootstrapper.ApplicationServices", mock_app_services),
        patch("cortex_extensions.ui_control.bootstrapper.Quartz", mock_quartz),
    ):
        res = PermsBootstrapper.verify_and_prompt_permissions()
        assert res["accessibility"] is True
        assert res["screen_recording"] is True

        mock_app_services.AXIsProcessTrustedWithOptions.assert_called_once()
        mock_quartz.CGPreflightScreenCaptureAccess.assert_called_once()
