# [C5-REAL] Exergy-Maximized

from unittest.mock import AsyncMock, patch

import pytest

from babylon60.extensions.ui_control.keyboard import KeyboardEngine
from babylon60.extensions.ui_control.models import AppTarget, KeyCombo


@pytest.fixture
def kb():
    return KeyboardEngine()


class TestKeyboardPress:
    """Tests de KeyboardEngine.press()."""

    @pytest.mark.asyncio
    async def test_press_simple_key(self, kb):
        """Pulsa una tecla simple sin modificadores."""
        combo = KeyCombo(key="a")
        with patch(
            "cortex_extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await kb.press(combo)
            assert result.success
            mock.assert_called_once()
            script = mock.call_args[0][0]
            assert 'keystroke "a"' in script

    @pytest.mark.asyncio
    async def test_press_with_modifiers(self, kb):
        """Pulsa Cmd+Shift+S."""
        combo = KeyCombo(key="s", modifiers=["command", "shift"])
        with patch(
            "cortex_extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await kb.press(combo)
            assert result.success
            script = mock.call_args[0][0]
            assert "command down" in script
            assert "shift down" in script

    @pytest.mark.asyncio
    async def test_press_with_target_app(self, kb):
        """Activa una app antes de pulsar."""
        combo = KeyCombo(key="c", modifiers=["command"])
        target = AppTarget(name="Safari")
        with patch(
            "cortex_extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await kb.press(combo, target=target)
            assert result.success
            # Debe haber dos llamadas: activar app + keystroke
            assert mock.call_count >= 1


class TestKeyboardHotkey:
    """Tests de KeyboardEngine.hotkey()."""

    @pytest.mark.asyncio
    async def test_hotkey_cmd_c(self, kb):
        """Atajo Cmd+C."""
        with patch(
            "cortex_extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await kb.hotkey("c", "command")
            assert result.success

    @pytest.mark.asyncio
    async def test_hotkey_no_modifiers(self, kb):
        """Tecla sola sin modificadores."""
        with patch(
            "cortex_extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await kb.hotkey("a")
            assert result.success


class TestKeyboardTypeText:
    """Tests of KeyboardEngine.type_text()."""

    @pytest.mark.asyncio
    async def test_type_short_text(self, kb):
        """Short text uses a single AppleScript script with all keystrokes."""
        with patch(
            "cortex_extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await kb.type_text("abc")
            assert result.success
            # A single script with all embedded keystrokes
            assert mock.call_count == 1
            script = mock.call_args[0][0]
            assert 'keystroke "a"' in script
            assert 'keystroke "c"' in script

    @pytest.mark.asyncio
    async def test_type_long_text_uses_clipboard(self, kb):
        """Long text uses clipboard paste in a single script."""
        long_text = "x" * 200
        with patch(
            "cortex_extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await kb.type_text(long_text)
            assert result.success
            # Clipboard: set + paste in a single script
            assert mock.call_count == 1
            script = mock.call_args[0][0]
            assert "set the clipboard" in script
            assert 'keystroke "v" using command down' in script


class TestKeyboardPressSpecial:
    """Tests of KeyboardEngine.press_special()."""

    @pytest.mark.asyncio
    async def test_press_return(self, kb):
        """Presses Return key."""
        with patch(
            "cortex_extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await kb.press_special("return")
            assert result.success
            script = mock.call_args[0][0]
            assert "key code" in script

    @pytest.mark.asyncio
    async def test_press_unknown_key(self, kb):
        """Unknown key returns error with 'Unknown'."""
        result = await kb.press_special("nonexistent")
        assert not result.success
        assert "Unknown" in result.error
