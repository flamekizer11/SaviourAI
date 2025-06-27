import keyboard
import threading
import time
from typing import Callable, Dict, Any
from config import CONFIG
from logger import interview_logger

class HotkeyManager:
    """Manages global hotkeys for overlay control"""
    
    def __init__(self):
        self.callbacks = {}
        self.is_listening = False
        self.listener_thread = None
        self.last_press_time = {}
        self.debounce_time = 0.5  # Prevent accidental double presses
        
        # Default hotkey bindings
        self.hotkeys = {
            'toggle_overlay': 'ctrl+shift+h',      # Show/hide overlay
            'toggle_listening': 'ctrl+shift+l',    # Start/stop listening
            'copy_last_answer': 'ctrl+shift+c',    # Copy last answer to clipboard
            'clear_overlay': 'ctrl+shift+x',       # Clear overlay text
            'toggle_tts': 'ctrl+shift+t',          # Toggle TTS on/off
            'emergency_hide': 'ctrl+shift+esc'     # Emergency hide (panic button)
        }
    
    def register_callback(self, action: str, callback: Callable):
        """Register callback for hotkey action"""
        self.callbacks[action] = callback
        interview_logger.log_info(f"Registered callback for action: {action}")
    
    def start_listening(self):
        """Start listening for hotkeys"""
        if self.is_listening:
            return
            
        if not CONFIG.ENABLE_HOTKEYS:
            interview_logger.log_info("Hotkeys disabled in config")
            return
        
        try:
            self.is_listening = True
            
            # Register hotkeys
            for action, hotkey in self.hotkeys.items():
                keyboard.add_hotkey(hotkey, self._handle_hotkey, args=[action])
                interview_logger.log_info(f"Registered hotkey {hotkey} for {action}")
            
            interview_logger.log_info("Hotkey listening started")
            
        except Exception as e:
            interview_logger.log_error(f"Failed to start hotkey listening: {e}")
            self.is_listening = False
    
    def _handle_hotkey(self, action: str):
        """Handle hotkey press with debouncing"""
        current_time = time.time()
        
        # Debounce check
        if action in self.last_press_time:
            if current_time - self.last_press_time[action] < self.debounce_time:
                return
        
        self.last_press_time[action] = current_time
        
        # Execute callback
        if action in self.callbacks:
            try:
                interview_logger.log_info(f"Executing hotkey action: {action}")
                self.callbacks[action]()
            except Exception as e:
                interview_logger.log_error(f"Error executing hotkey callback for {action}: {e}")
        else:
            interview_logger.log_warning(f"No callback registered for action: {action}")
    
    def stop_listening(self):
        """Stop listening for hotkeys"""
        if not self.is_listening:
            return
        
        try:
            # Unhook all hotkeys
            keyboard.unhook_all_hotkeys()
            self.is_listening = False
            interview_logger.log_info("Hotkey listening stopped")
            
        except Exception as e:
            interview_logger.log_error(f"Error stopping hotkey listening: {e}")
    
    def update_hotkey(self, action: str, new_hotkey: str):
        """Update hotkey binding"""
        if action not in self.hotkeys:
            interview_logger.log_error(f"Unknown action: {action}")
            return False
        
        try:
            # Remove old hotkey if listening
            if self.is_listening:
                keyboard.remove_hotkey(self.hotkeys[action])
            
            # Update binding
            self.hotkeys[action] = new_hotkey
            
            # Re-register if listening
            if self.is_listening:
                keyboard.add_hotkey(new_hotkey, self._handle_hotkey, args=[action])
            
            interview_logger.log_info(f"Updated hotkey for {action} to {new_hotkey}")
            return True
            
        except Exception as e:
            interview_logger.log_error(f"Failed to update hotkey for {action}: {e}")
            return False
    
    def get_hotkey_info(self) -> Dict[str, str]:
        """Get current hotkey bindings"""
        return self.hotkeys.copy()
    
    def is_hotkey_pressed(self, hotkey: str) -> bool:
        """Check if specific hotkey combination is currently pressed"""
        try:
            keys = hotkey.lower().split('+')
            return all(keyboard.is_pressed(key.strip()) for key in keys)
        except:
            return False
    
    def __del__(self):
        """Cleanup"""
        self.stop_listening()