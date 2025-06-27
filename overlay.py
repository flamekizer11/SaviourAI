import sys
import ctypes
import pyperclip
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QFrame, QApplication)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QFont, QPalette, QColor, QCursor
from config import CONFIG
from logger import interview_logger

class OverlayWidget(QWidget):
    """Enhanced overlay widget with animations and controls"""
    
    def __init__(self):
        super().__init__()
        self.is_visible = True
        self.last_answer = ""
        self.fade_animation = None
        self.setup_ui()
        self.setup_window_properties()
        
    def setup_ui(self):
        """Setup the UI components"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # Header with controls
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        # Status indicator
        self.status_label = QLabel("●")
        self.status_label.setStyleSheet("color: #00ff00; font-size: 12px; font-weight: bold;")
        self.status_label.setToolTip("Status: Ready")
        
        # Title
        title_label = QLabel("StealthAI")
        title_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold;")
        
        # Control buttons
        self.copy_btn = QPushButton("📋")
        self.copy_btn.setFixedSize(25, 25)
        self.copy_btn.setStyleSheet(self._get_button_style())
        self.copy_btn.setToolTip("Copy to clipboard (Ctrl+Shift+C)")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        
        self.clear_btn = QPushButton("🗑")
        self.clear_btn.setFixedSize(25, 25)
        self.clear_btn.setStyleSheet(self._get_button_style())
        self.clear_btn.setToolTip("Clear text (Ctrl+Shift+X)")
        self.clear_btn.clicked.connect(self.clear_text)
        
        self.hide_btn = QPushButton("👁")
        self.hide_btn.setFixedSize(25, 25)
        self.hide_btn.setStyleSheet(self._get_button_style())
        self.hide_btn.setToolTip("Toggle visibility (Ctrl+Shift+H)")
        self.hide_btn.clicked.connect(self.toggle_visibility)
        
        # Add to header layout
        header_layout.addWidget(self.status_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.copy_btn)
        header_layout.addWidget(self.clear_btn)
        header_layout.addWidget(self.hide_btn)
        
        # Header frame
        header_frame = QFrame()
        header_frame.setLayout(header_layout)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 200);
                border-radius: 5px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
        # Main text area
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                border: none;
                padding: 15px;
                border-radius: 5px;
                line-height: 1.4;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
            }
        """)
        
        # Set initial text
        self.text_display.setText("AI: Waiting for input...")
        
        # Add components to main layout
        main_layout.addWidget(header_frame)
        main_layout.addWidget(self.text_display)
        
        self.setLayout(main_layout)
        
    def setup_window_properties(self):
        """Setup window properties for stealth mode"""
        # Window flags for overlay behavior
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool |
            Qt.BypassWindowManagerHint
        )
        
        # Transparent background
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Set geometry
        self.setGeometry(
            CONFIG.ui.POSITION_X, 
            CONFIG.ui.POSITION_Y,
            CONFIG.ui.OVERLAY_WIDTH, 
            CONFIG.ui.OVERLAY_HEIGHT
        )
        
        # Hide from screen sharing (Windows specific)
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                # WDA_EXCLUDEFROMCAPTURE = 0x11
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
                interview_logger.log_info("Overlay hidden from screen capture")
            except Exception as e:
                interview_logger.log_warning(f"Could not hide from screen capture: {e}")
    
    def _get_button_style(self) -> str:
        """Get consistent button styling"""
        return """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 12px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.4);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """
    
    def update_text(self, text: str, animated: bool = True):
        """Update overlay text with optional animation"""
        self.last_answer = text
        
        # Format text nicely
        formatted_text = self._format_text(text)
        
        if animated:
            self._animate_text_change(formatted_text)
        else:
            self.text_display.setText(formatted_text)
        
        # Auto-scroll to top
        cursor = self.text_display.textCursor()
        cursor.movePosition(cursor.Start)
        self.text_display.setTextCursor(cursor)
        
        interview_logger.log_info(f"Overlay updated with {len(text)} characters")
    
    def _format_text(self, text: str) -> str:
        """Format text for better display"""
        if not text.strip():
            return "AI: Waiting for input..."
        
        # Add AI prefix if not present
        if not text.startswith("AI:"):
            text = f"AI: {text}"
        
        # Basic markdown-style formatting
        formatted = text
        
        # Bold text
        formatted = formatted.replace("**", "")  # Remove markdown bold
        
        # Code blocks (simple handling)
        formatted = formatted.replace("`", "'")
        
        # Ensure reasonable length
        if len(formatted) > 1000:
            formatted = formatted[:997] + "..."
        
        return formatted
    
    def _animate_text_change(self, new_text: str):
        """Animate text change with fade effect"""
        if self.fade_animation and self.fade_animation.state() == self.fade_animation.Running:
            self.fade_animation.stop()
        
        # Create fade out animation
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(150)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.7)
        self.fade_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Update text when fade out completes
        self.fade_animation.finished.connect(lambda: self._complete_text_animation(new_text))
        self.fade_animation.start()
    
    def _complete_text_animation(self, text: str):
        """Complete text animation by fading back in"""
        self.text_display.setText(text)
        
        # Fade back in
        fade_in = QPropertyAnimation(self, b"windowOpacity")
        fade_in.setDuration(150)
        fade_in.setStartValue(0.7)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.InCubic)
        fade_in.start()
    
    def set_status(self, status: str, color: str = "#00ff00"):
        """Update status indicator"""
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        self.status_label.setToolTip(f"Status: {status}")
        
        status_colors = {
            "ready": "#00ff00",
            "listening": "#ffff00", 
            "processing": "#ff8800",
            "error": "#ff0000",
            "disabled": "#888888"
        }
        
        if status.lower() in status_colors:
            color = status_colors[status.lower()]
            self.status_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
    
    def copy_to_clipboard(self):
        """Copy current text to clipboard"""
        if self.last_answer:
            try:
                # Remove AI prefix for cleaner copy
                text_to_copy = self.last_answer
                if text_to_copy.startswith("AI: "):
                    text_to_copy = text_to_copy[4:]
                
                pyperclip.copy(text_to_copy)
                interview_logger.log_info("Text copied to clipboard")
                
                # Visual feedback
                original_text = self.copy_btn.text()
                self.copy_btn.setText("✓")
                QTimer.singleShot(1000, lambda: self.copy_btn.setText(original_text))
                
            except Exception as e:
                interview_logger.log_error(f"Failed to copy to clipboard: {e}")
    
    def clear_text(self):
        """Clear overlay text"""
        self.update_text("", animated=True)
        self.last_answer = ""
        interview_logger.log_info("Overlay text cleared")
    
    def toggle_visibility(self):
        """Toggle overlay visibility"""
        if self.is_visible:
            self.hide()
            self.is_visible = False
            interview_logger.log_info("Overlay hidden")
        else:
            self.show()
            self.is_visible = True
            interview_logger.log_info("Overlay shown")
    
    def emergency_hide(self):
        """Emergency hide function"""
        self.hide()
        self.is_visible = False
        interview_logger.log_info("Emergency hide activated")
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.globalPos()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_start_position'):
            diff = event.globalPos() - self.drag_start_position
            self.move(self.pos() + diff)
            self.drag_start_position = event.globalPos()
    
    def get_current_text(self) -> str:
        """Get current display text"""
        return self.last_answer
    
    @pyqtProperty(float)
    def windowOpacity(self):
        """Property for animation"""
        return super().windowOpacity()
    
    @windowOpacity.setter
    def windowOpacity(self, opacity):
        """Property setter for animation"""
        super().setWindowOpacity(opacity)