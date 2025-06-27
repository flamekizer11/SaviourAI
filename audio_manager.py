import pyaudio
import numpy as np
import wave
import os
import threading
from collections import deque
from typing import Optional, Callable, Tuple
from config import CONFIG
from logger import interview_logger

class AudioManager:
    """Manages audio capture with optimized buffering and device detection"""
    
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.device_index = None
        self.is_recording = False
        self.audio_buffer = deque(maxlen=int(CONFIG.audio.SAMPLE_RATE * 30))  # 30 seconds buffer
        self.callbacks = []
        
    def find_virtual_audio_device(self) -> Optional[int]:
        """Find virtual audio cable device"""
        try:
            for i in range(self.audio.get_device_count()):
                info = self.audio.get_device_info_by_index(i)
                device_name = info.get("name", "").upper()
                
                for virtual_device in CONFIG.VIRTUAL_AUDIO_DEVICES:
                    if virtual_device.upper() in device_name:
                        if info.get("maxInputChannels", 0) > 0:
                            interview_logger.log_info(f"Found virtual audio device: {info['name']}")
                            return i
                            
        except Exception as e:
            interview_logger.log_error(f"Error finding virtual audio device: {e}")
            
        # Fallback to default input device
        try:
            default_device = self.audio.get_default_input_device_info()
            interview_logger.log_warning(f"Using default audio device: {default_device['name']}")
            return default_device['index']
        except:
            interview_logger.log_error("No audio input device found")
            return None
    
    def start_recording(self, callback: Callable[[np.ndarray], None]):
        """Start continuous audio recording"""
        if self.is_recording:
            return False
            
        self.device_index = self.find_virtual_audio_device()
        if self.device_index is None:
            interview_logger.log_error("Cannot start recording: No audio device found")
            return False
        
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=CONFIG.audio.CHANNELS,
                rate=CONFIG.audio.SAMPLE_RATE,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=CONFIG.audio.CHUNK_SIZE,
                stream_callback=self._audio_callback
            )
            
            self.callbacks.append(callback)
            self.is_recording = True
            self.stream.start_stream()
            
            interview_logger.log_info("Audio recording started")
            return True
            
        except Exception as e:
            interview_logger.log_error(f"Failed to start audio recording: {e}")
            return False
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Internal audio callback"""
        if status:
            interview_logger.log_warning(f"Audio callback status: {status}")
            
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        self.audio_buffer.extend(audio_data)
        
        return (None, pyaudio.paContinue)
    
    def get_audio_chunk(self, duration: float) -> Optional[np.ndarray]:
        """Get audio chunk of specified duration"""
        samples_needed = int(CONFIG.audio.SAMPLE_RATE * duration)
        
        if len(self.audio_buffer) < samples_needed:
            return None
            
        # Extract samples from buffer
        chunk = np.array(list(self.audio_buffer)[-samples_needed:])
        
        # Check if audio has meaningful content (above silence threshold)
        rms = np.sqrt(np.mean(chunk**2))
        if rms < CONFIG.audio.SILENCE_THRESHOLD:
            return None
            
        # Normalize audio
        chunk_float = chunk.astype(np.float32) / 32768.0
        return chunk_float
    
    def save_audio_chunk(self, audio_data: np.ndarray, filename: str) -> bool:
        """Save audio chunk to file"""
        try:
            filepath = os.path.join(CONFIG.TEMP_AUDIO_PATH, filename)
            
            # Convert back to int16 for saving
            audio_int16 = (audio_data * 32768.0).astype(np.int16)
            
            with wave.open(filepath, 'wb') as wf:
                wf.setnchannels(CONFIG.audio.CHANNELS)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(CONFIG.audio.SAMPLE_RATE)
                wf.writeframes(audio_int16.tobytes())
                
            return True
            
        except Exception as e:
            interview_logger.log_error(f"Failed to save audio: {e}")
            return False
    
    def stop_recording(self):
        """Stop audio recording"""
        if not self.is_recording:
            return
            
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                
            self.is_recording = False
            self.callbacks.clear()
            interview_logger.log_info("Audio recording stopped")
            
        except Exception as e:
            interview_logger.log_error(f"Error stopping recording: {e}")
    
    def get_device_info(self) -> dict:
        """Get current device information"""
        if self.device_index is not None:
            try:
                return self.audio.get_device_info_by_index(self.device_index)
            except:
                pass
        return {}
    
    def __del__(self):
        """Cleanup"""
        self.stop_recording()
        if hasattr(self, 'audio'):
            self.audio.terminate()