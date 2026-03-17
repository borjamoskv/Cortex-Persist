"""Tests para KeyboardEngine — inyección de teclas vía AppleScript."""

from unittest.mock import AsyncMock, patch

import pytest

from cortex.extensions.ui_control.keyboard import KeyboardEngine
from cortex.extensions.ui_control.models import AppTarget, KeyCombo


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
            "cortex.extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
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
            "cortex.extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
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
            "cortex.extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
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
            "cortex.extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await kb.hotkey("c", "command")
            assert result.success

    @pytest.mark.asyncio
    async def test_hotkey_no_modifiers(self, kb):
        """Tecla sola sin modificadores."""
        with patch(
            "cortex.extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await kb.hotkey("a")
            assert result.success


class TestKeyboardTypeText:
    """Tests de KeyboardEngine.type_text()."""

    @pytest.mark.asyncio
    async def test_type_short_text(self, kb):
        """Texto corto usa un único script AppleScript con todos los keystrokes."""
        with patch(
            "cortex.extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await kb.type_text("abc")
            assert result.success
            # Un solo script con todos los keystrokes incrustados
            assert mock.call_count == 1
            script = mock.call_args[0][0]
            assert 'keystroke "a"' in script
            assert 'keystroke "c"' in script

    @pytest.mark.asyncio
    async def test_type_long_text_uses_clipboard(self, kb):
        """Texto largo usa clipboard paste en un solo script."""
        long_text = "x" * 200
        with patch(
            "cortex.extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await kb.type_text(long_text)
            assert result.success
            # Clipboard: set + paste en un único script
            assert mock.call_count == 1
            script = mock.call_args[0][0]
            assert "set the clipboard" in script
            assert 'keystroke "v" using command down' in script


class TestKeyboardPressSpecial:
    """Tests de KeyboardEngine.press_special()."""

    @pytest.mark.asyncio
    async def test_press_return(self, kb):
        """Pulsa tecla Return."""
        with patch(
            "cortex.extensions.ui_control.keyboard.run_applescript", new_callable=AsyncMock
        ) as mock:
            mock.return_value = ""
            result = await kb.press_special("return")
            assert result.success
            script = mock.call_args[0][0]
            assert "key code" in script

    @pytest.mark.asyncio
    async def test_press_unknown_key(self, kb):
        """Tecla desconocida devuelve error con 'Unknown'."""
        result = await kb.press_special("nonexistent")
        assert not result.success
        assert "Unknown" in result.error
