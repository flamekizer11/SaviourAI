import sys
import signal
import time
import threading
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
import numpy as np

# Import our modules
from config import CONFIG
from logger import interview_logger
from audio_manager import AudioManager
from transcriber import WhisperTranscriber
from ai_handler import AIResponseHandler
from tts_handler import TTSHandler
from hotkey_manager import HotkeyManager
from overlay import OverlayWidget

class AudioProcessingThread(QThread):
    """Thread for handling audio processing pipeline"""
    
    # Signals
    transcription_ready = pyqtSignal(str, float)  # text, confidence
    error_occurred = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.audio_manager = AudioManager()
        self.transcriber = WhisperTranscriber()
        self.running = False
        self.processing = False
        
    def run(self):
        """Main processing loop"""
        self.running = True
        
        # Check if transcriber is ready
        if not self.transcriber.is_ready():
            self.error_occurred.emit("Transcriber not ready")
            return
        
        # Start audio recording
        if not self.audio_manager.start_recording(self._audio_callback):
            self.error_occurred.emit("Failed to start audio recording")
            return
        
        interview_logger.log_info("Audio processing thread started")
        self.status_changed.emit("listening")
        
        # Main processing loop
        while self.running:
            if not self.processing:
                # Get audio chunk
                audio_chunk = self.audio_manager.get_audio_chunk(CONFIG.audio.CHUNK_DURATION)
                
                if audio_chunk is not None and len(audio_chunk) > 0:
                    self.processing = True
                    self.status_changed.emit("processing")
                    
                    try:
                        # Transcribe audio
                        transcript, confidence = self.transcriber.transcribe_audio(audio_chunk)
                        
                        if transcript and len(transcript.strip()) > 3:  # Minimum meaningful length lowered from 10 to 3
                            self.transcription_ready.emit(transcript, confidence)
                        else:
                            self.status_changed.emit("listening")
                            
                    except Exception as e:
                        self.error_occurred.emit(f"Transcription error: {e}")
                    
                    finally:
                        self.processing = False
            
            self.msleep(100)  # Small delay to prevent excessive CPU usage
        
        # Cleanup
        self.audio_manager.stop_recording()
        interview_logger.log_info("Audio processing thread stopped")
    
    def _audio_callback(self, audio_data):
        """Audio callback (currently unused but available for future features)"""
        pass
    
    def stop(self):
        """Stop the processing thread"""
        self.running = False
        self.audio_manager.stop_recording()


class StealthAIApplication:
    """Main application class"""
    
    def __init__(self):
        # Initialize Qt Application
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Initialize components
        self.overlay = OverlayWidget()
        self.ai_handler = AIResponseHandler()
        self.tts_handler = TTSHandler()
        self.hotkey_manager = HotkeyManager()
        self.audio_thread = None
        self.system_tray = None
        
        # State
        self.is_listening = False
        self.last_question = ""
        self.last_answer = ""
        
        # Setup
        self.setup_system_tray()  
        self.setup_hotkeys()
        self.setup_signals()
        
        interview_logger.log_info("StealthAI Application initialized")
    
    def setup_system_tray(self):
        """Setup system tray icon and menu"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            interview_logger.log_warning("System tray not available")
            return
        
        self.system_tray = QSystemTrayIcon(self.app)
        
        # Create tray menu
        tray_menu = QMenu()
        
        # Actions
        show_action = QAction("Show Overlay", self.app)
        show_action.triggered.connect(self.show_overlay)
        
        hide_action = QAction("Hide Overlay", self.app)
        hide_action.triggered.connect(self.hide_overlay)
        
        start_action = QAction("Start Listening", self.app)
        start_action.triggered.connect(self.start_listening)
        
        stop_action = QAction("Stop Listening", self.app)
        stop_action.triggered.connect(self.stop_listening)
        
        separator1 = QAction(self.app)
        separator1.setSeparator(True)
        
        stats_action = QAction("Show Stats", self.app)
        stats_action.triggered.connect(self.show_stats)
        
        separator2 = QAction(self.app)
        separator2.setSeparator(True)
        
        quit_action = QAction("Quit", self.app)
        quit_action.triggered.connect(self.quit_application)
        
        # Add actions to menu
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(separator1)
        tray_menu.addAction(start_action)
        tray_menu.addAction(stop_action)
        tray_menu.addAction(separator2)
        tray_menu.addAction(stats_action)
        tray_menu.addAction(separator2)
        tray_menu.addAction(quit_action)
        
        # Set menu and show tray
        self.system_tray.setContextMenu(tray_menu)
        self.system_tray.setToolTip("StealthAI - Interview Assistant")
        
        # Try to set an icon (will work if you have an icon file)
        try:
            # You can add an icon file or create a simple one
            # self.system_tray.setIcon(QIcon("icon.png"))
            pass
        except:
            pass
            
        self.system_tray.show()
        interview_logger.log_info("System tray initialized")
    
    def setup_hotkeys(self):
        """Setup global hotkeys"""
        # Register hotkey callbacks
        self.hotkey_manager.register_callback('toggle_overlay', self.toggle_overlay)
        self.hotkey_manager.register_callback('toggle_listening', self.toggle_listening)
        self.hotkey_manager.register_callback('copy_last_answer', self.copy_last_answer)
        self.hotkey_manager.register_callback('clear_overlay', self.clear_overlay)
        self.hotkey_manager.register_callback('toggle_tts', self.toggle_tts)
        self.hotkey_manager.register_callback('emergency_hide', self.emergency_hide)
        
        # Start hotkey listening
        self.hotkey_manager.start_listening()
        interview_logger.log_info("Hotkeys initialized")
    
    def setup_signals(self):
        """Setup signal connections"""
        # Connect overlay signals (if any custom ones are added later)
        pass
    
    def start_listening(self):
        """Start audio processing"""
        if self.is_listening:
            interview_logger.log_warning("Already listening")
            return
        
        if self.audio_thread and self.audio_thread.isRunning():
            interview_logger.log_warning("Audio thread already running")
            return
        
        # Create and configure audio thread
        self.audio_thread = AudioProcessingThread()
        
        # Connect signals
        self.audio_thread.transcription_ready.connect(self.handle_transcription)
        self.audio_thread.error_occurred.connect(self.handle_error)
        self.audio_thread.status_changed.connect(self.handle_status_change)
        
        # Start thread
        self.audio_thread.start()
        self.is_listening = True
        
        # Update UI
        self.overlay.set_status("listening", "#ffff00")
        self.overlay.update_text("Listening for questions...")
        
        interview_logger.log_info("Started listening for audio")
    
    def stop_listening(self):
        """Stop audio processing"""
        if not self.is_listening:
            return
        
        if self.audio_thread:
            self.audio_thread.stop()
            self.audio_thread.wait(5000)  # Wait up to 5 seconds
            
            if self.audio_thread.isRunning():
                interview_logger.log_warning("Force terminating audio thread")
                self.audio_thread.terminate()
        
        self.is_listening = False
        
        # Update UI
        self.overlay.set_status("ready", "#00ff00")
        self.overlay.update_text("Stopped listening")
        
        interview_logger.log_info("Stopped listening for audio")
    
    def handle_transcription(self, transcript: str, confidence: float):
        """Handle transcription result"""
        interview_logger.log_info(f"Transcription received: {transcript} (confidence: {confidence:.2f})")
        
        # Store question
        self.last_question = transcript
        
        # Update overlay with question and show transcription immediately
        self.overlay.update_text(f"Q: {transcript}\n\nAI: Processing...")
        self.overlay.set_status("processing", "#ff8800")
        
        # Show a temporary popup notification with transcription (for debug)
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setWindowTitle("Transcription Debug")
        msg.setText(f"Transcribed Text:\n{transcript}\nConfidence: {confidence:.2f}")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.show()
        QTimer.singleShot(3000, msg.accept)  # Auto close after 3 seconds
        
        # Get AI response in separate thread to avoid blocking
        response_thread = threading.Thread(target=self.get_ai_response, args=(transcript,))
        response_thread.daemon = True
        response_thread.start()
    
    def get_ai_response(self, question: str):
        """Get AI response (runs in separate thread)"""
        try:
            # Get response from AI handler
            response, model_used, response_time = self.ai_handler.get_response(question, "data_science")
            
            if response:
                self.last_answer = response
                
                # Update overlay
                display_text = f"Q: {question}\n\nAI: {response}"
                self.overlay.update_text(display_text)
                
                # TTS if enabled
                if CONFIG.ENABLE_TTS:
                    self.tts_handler.speak(response)
                
                # Log Q&A
                interview_logger.log_qa(question, response, model_used, response_time)
                
                # Log stats
                interview_logger.log_info(f"AI response generated in {response_time:.2f}s using {model_used}")
                
            else:
                self.overlay.update_text("AI: Sorry, I couldn't generate a response.")
                
        except Exception as e:
            interview_logger.log_error(f"Error getting AI response: {e}")
            self.overlay.update_text("AI: Error processing your question.")
        
        finally:
            self.overlay.set_status("listening", "#ffff00")
    
    def handle_error(self, error_message: str):
        """Handle processing errors"""
        interview_logger.log_error(f"Processing error: {error_message}")
        self.overlay.set_status("error", "#ff0000")
        self.overlay.update_text(f"Error: {error_message}")
    
    def handle_status_change(self, status: str):
        """Handle status changes"""
        status_colors = {
            "listening": "#ffff00",
            "processing": "#ff8800", 
            "ready": "#00ff00",
            "error": "#ff0000"
        }
        color = status_colors.get(status, "#ffffff")
        self.overlay.set_status(status, color)
    
    # Hotkey callback methods
    def toggle_overlay(self):
        """Toggle overlay visibility"""
        self.overlay.toggle_visibility()
    
    def toggle_listening(self):
        """Toggle listening state"""
        if self.is_listening:
            self.stop_listening()
        else:
            self.start_listening()
    
    def copy_last_answer(self):
        """Copy last answer to clipboard"""
        if self.last_answer:
            self.overlay.copy_to_clipboard(self.last_answer)
            interview_logger.log_info("Last answer copied to clipboard")
        else:
            interview_logger.log_warning("No answer to copy")
    
    def clear_overlay(self):
        """Clear overlay text"""
        self.overlay.clear_text()
        interview_logger.log_info("Overlay cleared")
    
    def toggle_tts(self):
        """Toggle TTS on/off"""
        CONFIG.ENABLE_TTS = not CONFIG.ENABLE_TTS
        status = "enabled" if CONFIG.ENABLE_TTS else "disabled"
        interview_logger.log_info(f"TTS {status}")
        self.overlay.update_text(f"TTS {status}")
    
    def emergency_hide(self):
        """Emergency hide function"""
        self.overlay.emergency_hide()
        self.stop_listening()
        interview_logger.log_info("Emergency hide activated")
    
    # System tray callback methods
    def show_overlay(self):
        """Show overlay"""
        self.overlay.show()
        self.overlay.is_visible = True
        interview_logger.log_info("Overlay shown")
    
    def hide_overlay(self):
        """Hide overlay"""
        self.overlay.hide()
        self.overlay.is_visible = False
        interview_logger.log_info("Overlay hidden")
    
    def show_stats(self):
        """Show performance statistics"""
        try:
            # Get AI handler stats
            ai_stats = self.ai_handler.get_stats()
            
            # Get session stats
            session_stats = interview_logger.get_session_summary()
            
            stats_text = f"""StealthAI Statistics:

Session ID: {session_stats.get('session_id', 'N/A')}
Total Questions: {session_stats.get('total_questions', 0)}
Avg Response Time: {session_stats.get('avg_response_time_ms', 0):.0f}ms
Models Used: {', '.join(session_stats.get('models_used', []))}

AI Handler Stats:
Total Requests: {ai_stats.get('total_requests', 0)}
Cache Size: {ai_stats.get('cache_size', 0)}
Average Response Time: {ai_stats.get('avg_response_time', 0):.2f}s

Current Status:
Listening: {'Yes' if self.is_listening else 'No'}
TTS Enabled: {'Yes' if CONFIG.ENABLE_TTS else 'No'}

Last Question: {self.last_question[:100] + '...' if len(self.last_question) > 100 else self.last_question}
"""
            self.overlay.update_text(stats_text)
            interview_logger.log_info("Statistics displayed")
            
        except Exception as e:
            interview_logger.log_error(f"Error displaying stats: {e}")
            self.overlay.update_text("Error retrieving statistics")
    
    def quit_application(self):
        """Quit the application"""
        interview_logger.log_info("Shutting down StealthAI")
        
        # Stop components
        self.stop_listening()
        
        try:
            self.hotkey_manager.stop_listening()
        except Exception as e:
            interview_logger.log_warning(f"Error stopping hotkey manager: {e}")
        
        try:
            self.tts_handler.shutdown()
        except Exception as e:
            interview_logger.log_warning(f"Error shutting down TTS: {e}")
        
        # Hide tray and overlay
        if self.system_tray:
            self.system_tray.hide()
        self.overlay.hide()
        
        # Final log
        session_summary = interview_logger.get_session_summary()
        interview_logger.log_info(f"Session ended. Summary: {session_summary}")
        
        # Quit application
        self.app.quit()
    
    def run(self):
        """Run the application"""
        try:
            # Show overlay initially
            self.overlay.show()
            self.overlay.update_text("StealthAI initialized. Use system tray or Ctrl+Shift+L to start listening.")
            self.overlay.set_status("ready", "#00ff00")
            
            # Handle system signals
            signal.signal(signal.SIGINT, lambda sig, frame: self.quit_application())
            signal.signal(signal.SIGTERM, lambda sig, frame: self.quit_application())
            
            interview_logger.log_info("StealthAI started successfully")
            
            # Run Qt application
            return self.app.exec_()
            
        except KeyboardInterrupt:
            interview_logger.log_info("Keyboard interrupt received")
            self.quit_application()
            return 0
        except Exception as e:
            interview_logger.log_error(f"Fatal error: {e}")
            return 1


def main():
    """Main entry point"""
    try:
        app = StealthAIApplication()
        return app.run()
    except Exception as e:
        print(f"Failed to start StealthAI: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())