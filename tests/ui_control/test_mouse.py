"""Tests para MouseEngine — control de ratón vía CoreGraphics."""

from unittest.mock import MagicMock, patch

import pytest

from cortex.ui_control.mouse import MouseEngine


@pytest.fixture
def mouse():
    return MouseEngine()


class TestMouseClick:
    """Tests de MouseEngine.click()."""

    def test_click_left(self, mouse):
        """Click izquierdo en coordenadas."""
        with patch("cortex.ui_control.mouse.CG") as mock_cg:
            mock_cg.kCGMouseButtonLeft = 0
            mock_cg.kCGEventLeftMouseDown = 1
            mock_cg.kCGEventLeftMouseUp = 2
            mock_cg.kCGHIDEventTap = 0
            mock_cg.CGEventCreateMouseEvent.return_value = MagicMock()
            result = mouse.click(100, 200)
            assert result.success

    def test_click_right(self, mouse):
        """Click derecho en coordenadas."""
        with patch("cortex.ui_control.mouse.CG") as mock_cg:
            mock_cg.kCGMouseButtonRight = 1
            mock_cg.kCGEventRightMouseDown = 3
            mock_cg.kCGEventRightMouseUp = 4
            mock_cg.kCGHIDEventTap = 0
            mock_cg.CGEventCreateMouseEvent.return_value = MagicMock()
            result = mouse.click(100, 200, button="right")
            assert result.success

    def test_click_without_cg(self, mouse):
        """Sin CoreGraphics devuelve error."""
        with patch("cortex.ui_control.mouse.CG", None):
            result = mouse.click(0, 0)
            assert not result.success


class TestMouseDoubleClick:
    """Tests de MouseEngine.double_click()."""

    def test_double_click(self, mouse):
        """Doble click nativo con clickCount."""
        with patch("cortex.ui_control.mouse.CG") as mock_cg:
            mock_cg.kCGMouseButtonLeft = 0
            mock_cg.kCGEventLeftMouseDown = 1
            mock_cg.kCGEventLeftMouseUp = 2
            mock_cg.kCGHIDEventTap = 0
            mock_cg.kCGMouseEventClickState = 1
            mock_cg.CGEventCreateMouseEvent.return_value = MagicMock()
            result = mouse.double_click(300, 400)
            assert result.success
            # 4 eventos: down1, up1, down2, up2
            assert mock_cg.CGEventCreateMouseEvent.call_count == 4


class TestMouseDrag:
    """Tests de MouseEngine.drag()."""

    def test_drag(self, mouse):
        """Drag-and-drop con interpolación."""
        with patch("cortex.ui_control.mouse.CG") as mock_cg:
            mock_cg.kCGMouseButtonLeft = 0
            mock_cg.kCGEventLeftMouseDown = 1
            mock_cg.kCGEventLeftMouseUp = 2
            mock_cg.kCGEventLeftMouseDragged = 6
            mock_cg.kCGHIDEventTap = 0
            mock_cg.CGEventCreateMouseEvent.return_value = MagicMock()
            result = mouse.drag(0, 0, 100, 100, duration=0.01, steps=2)
            assert result.success
            # 1 down + 2 drags + 1 up = 4 eventos
            assert mock_cg.CGEventCreateMouseEvent.call_count == 4


class TestMouseScroll:
    """Tests de MouseEngine.scroll()."""

    def test_scroll_up(self, mouse):
        """Scroll hacia arriba."""
        with patch("cortex.ui_control.mouse.CG") as mock_cg:
            mock_cg.kCGScrollEventUnitLine = 0
            mock_cg.kCGHIDEventTap = 0
            mock_cg.CGEventCreateScrollWheelEvent.return_value = MagicMock()
            result = mouse.scroll(3)
            assert result.success

    def test_scroll_down(self, mouse):
        """Scroll hacia abajo."""
        with patch("cortex.ui_control.mouse.CG") as mock_cg:
            mock_cg.kCGScrollEventUnitLine = 0
            mock_cg.kCGHIDEventTap = 0
            mock_cg.CGEventCreateScrollWheelEvent.return_value = MagicMock()
            result = mouse.scroll(-5)
            assert result.success


class TestMouseRightClick:
    """Tests de MouseEngine.right_click()."""

    def test_right_click_delegates(self, mouse):
        """right_click delega a click(button='right')."""
        with patch.object(mouse, "click") as mock_click:
            from cortex.ui_control.models import InteractionResult

            mock_click.return_value = InteractionResult(success=True)
            result = mouse.right_click(50, 60)
            assert result.success
            mock_click.assert_called_once_with(50, 60, button="right")
