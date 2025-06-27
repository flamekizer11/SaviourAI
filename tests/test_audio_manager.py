import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import patch, MagicMock
import numpy as np
from audio_manager import AudioManager

@pytest.fixture
def audio_manager():
    return AudioManager()

@patch('audio_manager.pyaudio.PyAudio')
def test_find_virtual_audio_device(mock_pyaudio, audio_manager):
    mock_instance = mock_pyaudio.return_value
    mock_instance.get_device_count.return_value = 4
    mock_instance.get_device_info_by_index.side_effect = [
        {"name": "Other Device", "maxInputChannels": 1},
        {"name": "Other Device", "maxInputChannels": 1},
        {"name": "Other Device", "maxInputChannels": 1},
        {"name": "CABLE Output (VB-Audio Virtual)", "maxInputChannels": 1}
    ]
    device_index = audio_manager.find_virtual_audio_device()
    assert device_index == 3

@patch('audio_manager.pyaudio.PyAudio')
def test_start_and_stop_recording(mock_pyaudio, audio_manager):
    mock_instance = mock_pyaudio.return_value
    mock_instance.get_device_count.return_value = 1
    mock_instance.get_device_info_by_index.return_value = {"name": "Device", "maxInputChannels": 1}
    mock_instance.open.return_value = MagicMock()
    audio_manager.device_index = 0

    def dummy_callback(data):
        pass

    result = audio_manager.start_recording(dummy_callback)
    assert result is True
    audio_manager.stop_recording()
    assert audio_manager.is_recording is False

def test_get_audio_chunk_returns_none_for_silence(audio_manager):
    audio_manager.audio_buffer.extend([0]*10000)
    chunk = audio_manager.get_audio_chunk(0.1)
    assert chunk is None

def test_get_audio_chunk_returns_chunk(audio_manager):
    samples = np.random.randint(-1000, 1000, size=1600)
    audio_manager.audio_buffer.extend(samples)
    chunk = audio_manager.get_audio_chunk(0.1)
    assert chunk is not None
    assert isinstance(chunk, np.ndarray)
