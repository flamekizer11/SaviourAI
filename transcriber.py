import whisper
import numpy as np
import os
import subprocess
import threading
import time
from typing import Optional, Tuple
from config import CONFIG
from logger import interview_logger

class WhisperTranscriber:
    """Optimized Whisper transcription with fallback mechanisms"""
    
    def __init__(self):
        self.model = None
        self.whisper_cpp_path = None
        self.model_loaded = False
        self.lock = threading.Lock()
        self._initialize_whisper()
    
    def _initialize_whisper(self):
        """Initialize Whisper model with fallback"""
        try:
            # Try to load whisper-python first (faster)
            interview_logger.log_info(f"Loading Whisper model: {CONFIG.whisper.MODEL_SIZE}")
            self.model = whisper.load_model(
                CONFIG.whisper.MODEL_SIZE,
                device=CONFIG.whisper.DEVICE,
                download_root=CONFIG.WHISPER_MODEL_PATH
            )
            self.model_loaded = True
            interview_logger.log_info("Whisper model loaded successfully")
            
        except Exception as e:
            interview_logger.log_warning(f"Failed to load whisper-python: {e}")
            # Try whisper.cpp fallback
            self._check_whisper_cpp()
    
    def _check_whisper_cpp(self):
        """Check for whisper.cpp availability"""
        possible_paths = [
            "./whisper.cpp/main.exe",
            "./whisper.cpp/main",
            "whisper-cpp",
            "whisper"
        ]
        
        for path in possible_paths:
            if os.path.exists(path) or self._command_exists(path):
                self.whisper_cpp_path = path
                interview_logger.log_info(f"Found whisper.cpp at: {path}")
                return True
                
        interview_logger.log_error("Neither whisper-python nor whisper.cpp found")
        return False
    
    def _command_exists(self, command: str) -> bool:
        """Check if command exists in PATH"""
        try:
            subprocess.run([command, "--help"], 
                         capture_output=True, 
                         timeout=5)
            return True
        except:
            return False
    
    def transcribe_audio(self, audio_data: np.ndarray) -> Tuple[str, float]:
        """
        Transcribe audio data
        Returns: (transcript, confidence_score)
        """
        with self.lock:
            start_time = time.time()
            
            if self.model_loaded and self.model:
                return self._transcribe_with_whisper_python(audio_data, start_time)
            elif self.whisper_cpp_path:
                return self._transcribe_with_whisper_cpp(audio_data, start_time)
            else:
                interview_logger.log_error("No transcription method available")
                return "", 0.0
    
    def _transcribe_with_whisper_python(self, audio_data: np.ndarray, start_time: float) -> Tuple[str, float]:
        """Transcribe using whisper-python"""
        try:
            # Ensure audio is the right format
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            # Whisper expects float32 audio
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            result = self.model.transcribe(
                audio_data,
                language=CONFIG.whisper.LANGUAGE,
                initial_prompt=CONFIG.whisper.INITIAL_PROMPT,
                fp16=CONFIG.whisper.FP16,
                verbose=False,
                condition_on_previous_text=False  # Faster processing
            )
            
            transcript = result.get("text", "").strip()
            
            # Calculate confidence from segments
            confidence = self._calculate_confidence(result.get("segments", []))
            
            processing_time = time.time() - start_time
            interview_logger.log_info(f"Transcription completed in {processing_time:.2f}s")
            
            return transcript, confidence
            
        except Exception as e:
            interview_logger.log_error(f"Whisper-python transcription failed: {e}")
            return "", 0.0
    
    def _transcribe_with_whisper_cpp(self, audio_data: np.ndarray, start_time: float) -> Tuple[str, float]:
        """Transcribe using whisper.cpp"""
        try:
            # Save audio to temporary file
            temp_file = os.path.join(CONFIG.TEMP_AUDIO_PATH, f"temp_audio_{int(time.time())}.wav")
            
            # Convert to int16 for wav file
            audio_int16 = (audio_data * 32768.0).astype(np.int16)
            
            import wave
            with wave.open(temp_file, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(CONFIG.audio.SAMPLE_RATE)
                wf.writeframes(audio_int16.tobytes())
            
            # Run whisper.cpp
            model_path = f"./whisper.cpp/models/ggml-{CONFIG.whisper.MODEL_SIZE}.bin"
            cmd = [
                self.whisper_cpp_path,
                "-m", model_path,
                "-f", temp_file,
                "-nt",  # No timestamps
                "-l", CONFIG.whisper.LANGUAGE
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Cleanup temp file
            try:
                os.remove(temp_file)
            except:
                pass
            
            if result.returncode == 0:
                transcript = result.stdout.strip()
                processing_time = time.time() - start_time
                interview_logger.log_info(f"Whisper.cpp transcription completed in {processing_time:.2f}s")
                return transcript, 0.8  # Default confidence for whisper.cpp
            else:
                interview_logger.log_error(f"Whisper.cpp error: {result.stderr}")
                return "", 0.0
                
        except subprocess.TimeoutExpired:
            interview_logger.log_error("Whisper.cpp transcription timeout")
            return "", 0.0
        except Exception as e:
            interview_logger.log_error(f"Whisper.cpp transcription failed: {e}")
            return "", 0.0
    
    def _calculate_confidence(self, segments: list) -> float:
        """Calculate average confidence from segments"""
        if not segments:
            return 0.0
        
        confidences = []
        for segment in segments:
            if 'avg_logprob' in segment:
                # Convert log probability to confidence (rough approximation)
                confidence = min(1.0, max(0.0, (segment['avg_logprob'] + 1.0)))
                confidences.append(confidence)
        
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def is_ready(self) -> bool:
        """Check if transcriber is ready"""
        return self.model_loaded or self.whisper_cpp_path is not None