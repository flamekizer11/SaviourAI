import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class AudioConfig:
    """Audio processing configuration"""
    SAMPLE_RATE: int = 16000
    CHUNK_SIZE: int = 1024
    CHANNELS: int = 1
    FORMAT: int = 16  # pyaudio.paInt16
    CHUNK_DURATION: float = 3.0  # Reduced for lower latency
    SILENCE_THRESHOLD: float = 0.01
    MIN_AUDIO_LENGTH: float = 1.0

@dataclass
class AIConfig:
    """AI model configuration"""
    OPENROUTER_API_KEY: str = "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"
    OPENROUTER_ENDPOINT: str = "https://openrouter.ai/api/v1/chat/completions"
    PRIMARY_MODEL: str = "openai/gpt-4-turbo"
    FALLBACK_MODEL: str = "openai/gpt-3.5-turbo"
    MAX_TOKENS: int = 300
    TEMPERATURE: float = 0.7
    TIMEOUT: int = 10
    MAX_RETRIES: int = 3

@dataclass
class WhisperConfig:
    """Whisper transcription configuration"""
    MODEL_SIZE: str = "base.en"  # Faster for English-only
    DEVICE: str = "cpu"  # Change to "cuda" if available
    FP16: bool = False
    LANGUAGE: str = "en"
    INITIAL_PROMPT: str = "This is a technical interview about data science, machine learning, and programming."

@dataclass
class UIConfig:
    """UI configuration"""
    OVERLAY_WIDTH: int = 800
    OVERLAY_HEIGHT: int = 120
    FONT_SIZE: int = 16
    OPACITY: float = 0.9
    POSITION_X: int = 100
    POSITION_Y: int = 100

@dataclass
class AppConfig:
    """Main application configuration"""
    audio: AudioConfig = AudioConfig()
    ai: AIConfig = AIConfig()
    whisper: WhisperConfig = WhisperConfig()
    ui: UIConfig = UIConfig()
    
    # Paths
    WHISPER_MODEL_PATH: str = "./models"
    LOG_PATH: str = "./logs"
    TEMP_AUDIO_PATH: str = "./temp"
    
    # Features
    ENABLE_TTS: bool = True
    ENABLE_LOGGING: bool = True
    ENABLE_CLIPBOARD: bool = True
    ENABLE_HOTKEYS: bool = True
    
    # Virtual audio device names to search for
    VIRTUAL_AUDIO_DEVICES: list = None
    
    def __post_init__(self):
        if self.VIRTUAL_AUDIO_DEVICES is None:
            self.VIRTUAL_AUDIO_DEVICES = [
                "VB-Audio", "CABLE", "Stereo Mix", "What U Hear",
                "Virtual Audio Cable", "VoiceMeeter"
            ]
        
        # Create directories
        os.makedirs(self.WHISPER_MODEL_PATH, exist_ok=True)
        os.makedirs(self.LOG_PATH, exist_ok=True)
        os.makedirs(self.TEMP_AUDIO_PATH, exist_ok=True)

# Global config instance
CONFIG = AppConfig()