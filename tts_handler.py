import pyttsx3
import threading
import queue
import time
from typing import Optional
from config import CONFIG
from logger import interview_logger

class TTSHandler:
    """Text-to-Speech handler for whispering answers back"""
    
    def __init__(self):
        self.engine = None
        self.tts_queue = queue.Queue()
        self.is_speaking = False
        self.worker_thread = None
        self.running = False
        self._initialize_tts()
    
    def _initialize_tts(self):
        """Initialize TTS engine"""
        try:
            self.engine = pyttsx3.init()
            
            # Configure voice settings for whisper-like speech
            voices = self.engine.getProperty('voices')
            if voices:
                # Prefer female voice if available
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
            
            # Set speech rate (slower for whispering effect)
            self.engine.setProperty('rate', 150)  # Default is usually 200
            
            # Set volume (lower for whispering)
            self.engine.setProperty('volume', 0.3)  # Range 0.0-1.0
            
            interview_logger.log_info("TTS engine initialized")
            
        except Exception as e:
            interview_logger.log_error(f"Failed to initialize TTS: {e}")
            self.engine = None
    
    def start_worker(self):
        """Start TTS worker thread"""
        if self.worker_thread and self.worker_thread.is_alive():
            return
            
        self.running = True
        self.worker_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.worker_thread.start()
        interview_logger.log_info("TTS worker started")
    
    def _tts_worker(self):
        """TTS worker thread"""
        while self.running:
            try:
                # Get text from queue with timeout
                text = self.tts_queue.get(timeout=1.0)
                
                if text and self.engine:
                    self.is_speaking = True
                    
                    # Process text for better speech
                    processed_text = self._process_text_for_speech(text)
                    
                    # Speak the text
                    self.engine.say(processed_text)
                    self.engine.runAndWait()
                    
                    self.is_speaking = False
                    interview_logger.log_info("TTS playback completed")
                
                self.tts_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                interview_logger.log_error(f"TTS worker error: {e}")
                self.is_speaking = False
    
    def speak(self, text: str, priority: bool = False):
        """
        Add text to TTS queue
        priority: If True, clear queue and speak immediately
        """
        if not CONFIG.ENABLE_TTS or not self.engine:
            return
            
        if not self.running:
            self.start_worker()
        
        # Clean up text
        text = text.strip()
        if not text:
            return
            
        # Handle priority speech
        if priority:
            # Clear existing queue
            while not self.tts_queue.empty():
                try:
                    self.tts_queue.get_nowait()
                    self.tts_queue.task_done()
                except queue.Empty:
                    break
            
            # Stop current speech if possible
            if self.is_speaking and self.engine:
                try:
                    self.engine.stop()
                except:
                    pass
        
        # Add to queue
        self.tts_queue.put(text)
        interview_logger.log_info(f"Added text to TTS queue: {len(text)} characters")
    
    def _process_text_for_speech(self, text: str) -> str:
        """Process text to make it more suitable for speech"""
        # Remove markdown formatting
        processed = text.replace('**', '').replace('*', '')
        processed = processed.replace('`', '')
        
        # Replace common abbreviations
        replacements = {
            'ML': 'machine learning',
            'AI': 'artificial intelligence',
            'API': 'A P I',
            'SQL': 'sequel',
            'HTTP': 'H T T P',
            'JSON': 'jason',
            'CSV': 'C S V',
            'GPU': 'G P U',
            'CPU': 'C P U',
            'RAM': 'ram',
            'SSD': 'S S D',
            'URL': 'U R L',
            'UI': 'user interface',
            'UX': 'user experience',
            'vs.': 'versus',
            'e.g.': 'for example',
            'i.e.': 'that is',
            'etc.': 'etcetera'
        }
        
        for abbrev, full_form in replacements.items():
            processed = processed.replace(abbrev, full_form)
        
        # Add pauses for better comprehension
        processed = processed.replace('.', '. ')
        processed = processed.replace(',', ', ')
        processed = processed.replace(';', '; ')
        processed = processed.replace(':', ': ')
        
        # Limit length for whisper mode
        if len(processed) > 300:
            sentences = processed.split('.')
            processed = '. '.join(sentences[:3]) + '.'
        
        return processed
    
    def is_available(self) -> bool:
        """Check if TTS is available"""
        return self.engine is not None and CONFIG.ENABLE_TTS
    
    def stop_speaking(self):
        """Stop current speech"""
        if self.engine and self.is_speaking:
            try:
                self.engine.stop()
                self.is_speaking = False
                interview_logger.log_info("TTS stopped")
            except Exception as e:
                interview_logger.log_error(f"Error stopping TTS: {e}")
    
    def clear_queue(self):
        """Clear TTS queue"""
        while not self.tts_queue.empty():
            try:
                self.tts_queue.get_nowait()
                self.tts_queue.task_done()
            except queue.Empty:
                break
        interview_logger.log_info("TTS queue cleared")
    
    def set_voice_settings(self, rate: int = 150, volume: float = 0.3):
        """Adjust voice settings"""
        if self.engine:
            try:
                self.engine.setProperty('rate', rate)
                self.engine.setProperty('volume', volume)
                interview_logger.log_info(f"TTS settings updated: rate={rate}, volume={volume}")
            except Exception as e:
                interview_logger.log_error(f"Error updating TTS settings: {e}")
    
    def shutdown(self):
        """Shutdown TTS handler"""
        self.running = False
        self.clear_queue()
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
        
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass
        
        interview_logger.log_info("TTS handler shutdown")