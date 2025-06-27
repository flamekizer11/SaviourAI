import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from PyQt5.QtWidgets import QApplication
from overlay import OverlayWidget

@pytest.fixture(scope="module")
def app():
    app = QApplication([])
    yield app
    app.quit()

@pytest.fixture
def overlay(app):
    return OverlayWidget()

def test_initial_text(overlay):
    assert "AI: Waiting for input" in overlay.text_display.toPlainText()

def test_update_text(overlay):
    overlay.update_text("Test update", animated=False)
    assert "Test update" in overlay.text_display.toPlainText()

def test_clear_text(overlay):
    overlay.clear_text()
    assert "AI: Waiting for input" in overlay.text_display.toPlainText()

def test_toggle_visibility(overlay):
    initial_visibility = overlay.is_visible
    overlay.toggle_visibility()
    assert overlay.is_visible != initial_visibility
    overlay.toggle_visibility()
    assert overlay.is_visible == initial_visibility

def test_copy_to_clipboard(overlay, monkeypatch):
    copied = {}
    def fake_copy(text):
        copied['text'] = text
    monkeypatch.setattr("pyperclip.copy", fake_copy)
    overlay.last_answer = "AI: Test copy"
    overlay.copy_to_clipboard()
    assert copied['text'] == "Test copy"
