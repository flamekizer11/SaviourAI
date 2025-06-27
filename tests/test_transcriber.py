import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import patch, MagicMock
import numpy as np
from transcriber import WhisperTranscriber

@pytest.fixture
def transcriber():
    return WhisperTranscriber()

@patch('transcriber.whisper.load_model')
def test_initialize_whisper_python_success(mock_load_model, transcriber):
    mock_load_model.return_value = MagicMock()
    transcriber._initialize_whisper()
    assert transcriber.model_loaded is True

@patch('transcriber.subprocess.run')
def test_transcribe_with_whisper_cpp_success(mock_run, transcriber):
    mock_run.return_value = MagicMock(returncode=0, stdout="Test transcript", stderr="")
    transcriber.whisper_cpp_path = "whisper-cpp"
    audio_data = np.random.rand(16000).astype(np.float32)
    transcript, confidence = transcriber._transcribe_with_whisper_cpp(audio_data, 0)
    assert transcript == "Test transcript"
    assert confidence == 0.8

@patch('transcriber.whisper.load_model')
def test_transcribe_with_whisper_python_success(mock_load_model, transcriber):
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "text": "Test transcript",
        "segments": [{"avg_logprob": -0.5}]
    }
    mock_load_model.return_value = mock_model
    transcriber.model = mock_model
    transcriber.model_loaded = True
    audio_data = np.random.rand(16000).astype(np.float32)
    transcript, confidence = transcriber._transcribe_with_whisper_python(audio_data, 0)
    assert transcript == "Test transcript"
    assert confidence > 0

def test_is_ready(transcriber):
    transcriber.model_loaded = True
    assert transcriber.is_ready() is True
    transcriber.model_loaded = False
    transcriber.whisper_cpp_path = "whisper-cpp"
    assert transcriber.is_ready() is True
