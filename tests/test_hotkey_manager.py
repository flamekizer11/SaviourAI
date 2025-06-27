import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import patch, MagicMock
from hotkey_manager import HotkeyManager

@pytest.fixture
def hotkey_manager():
    return HotkeyManager()

@patch('hotkey_manager.keyboard.add_hotkey')
def test_start_listening_registers_hotkeys(mock_add_hotkey, hotkey_manager):
    hotkey_manager.start_listening()
    assert hotkey_manager.is_listening is True
    assert mock_add_hotkey.call_count == len(hotkey_manager.hotkeys)

def test_register_callback_and_handle_hotkey(hotkey_manager):
    called = {"flag": False}
    def callback():
        called["flag"] = True
    hotkey_manager.register_callback("toggle_overlay", callback)
    hotkey_manager._handle_hotkey("toggle_overlay")
    assert called["flag"] is True

@patch('hotkey_manager.keyboard.unhook_all_hotkeys')
def test_stop_listening(mock_unhook, hotkey_manager):
    hotkey_manager.is_listening = True
    hotkey_manager.stop_listening()
    assert hotkey_manager.is_listening is False
    mock_unhook.assert_called_once()
