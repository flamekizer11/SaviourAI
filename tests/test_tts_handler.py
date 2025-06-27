import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import patch, MagicMock
from tts_handler import TTSHandler

@pytest.fixture
def tts_handler():
    return TTSHandler()

@patch('tts_handler.pyttsx3.init')
def test_initialize_tts_success(mock_init, tts_handler):
    mock_engine = MagicMock()
    mock_init.return_value = mock_engine
    tts_handler._initialize_tts()
    assert tts_handler.engine is not None

@patch('tts_handler.pyttsx3.init')
def test_speak_adds_to_queue(mock_init, tts_handler):
    mock_engine = MagicMock()
    mock_init.return_value = mock_engine
    tts_handler.engine = mock_engine
    tts_handler.running = True
    tts_handler.speak("Hello world")
    assert not tts_handler.tts_queue.empty()

def test_clear_queue(tts_handler):
    tts_handler.tts_queue.put("Test")
    tts_handler.clear_queue()
    assert tts_handler.tts_queue.empty()

@patch('tts_handler.pyttsx3.init')
def test_stop_speaking_calls_engine_stop(mock_init, tts_handler):
    mock_engine = MagicMock()
    mock_init.return_value = mock_engine
    tts_handler.engine = mock_engine
    tts_handler.is_speaking = True
    tts_handler.stop_speaking()
    mock_engine.stop.assert_called_once()
