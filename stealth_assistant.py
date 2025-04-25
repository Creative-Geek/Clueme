import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QWindow
import pytesseract
from PIL import ImageGrab
import openai
from dotenv import load_dotenv
from pynput import keyboard
import threading

# Load environment variables
load_dotenv()

class StealthWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stealth Assistant")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        
        # Make window transparent to screen recording
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create text display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 0, 0, 0.8);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.text_display)
        
        # Initialize OpenAI client with custom endpoint if specified
        api_base = os.getenv('OPENAI_API_BASE')
        self.client = openai.OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=api_base if api_base else None
        )
        
        # Get model from environment variable or use default
        self.model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        
        # Set up keyboard listener
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()
        
        # Hide window initially
        self.hide()
        
    def on_key_press(self, key):
        try:
            # Ctrl+Alt+A to capture screen and get AI assistance
            if key == keyboard.KeyCode.from_char('a') and keyboard.Key.ctrl in self.listener.current_keys and keyboard.Key.alt in self.listener.current_keys:
                self.capture_and_process()
            # Esc to close the application
            elif key == keyboard.Key.esc:
                QApplication.quit()
        except AttributeError:
            pass
            
    def capture_and_process(self):
        # Capture screen
        screenshot = ImageGrab.grab()
        
        # Perform OCR
        text = pytesseract.image_to_string(screenshot)
        
        # Get AI response
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant. Provide concise and relevant responses."},
                {"role": "user", "content": f"Here's the text from my screen: {text}\n\nPlease analyze and provide insights:"}
            ]
        )
        
        # Display result
        self.text_display.setText(response.choices[0].message.content)
        self.show()
        
        # Hide after 5 seconds
        QTimer.singleShot(5000, self.hide)

def main():
    app = QApplication(sys.argv)
    window = StealthWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 