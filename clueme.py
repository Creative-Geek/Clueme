import sys
import ctypes
import os
from dotenv import load_dotenv
import openai
from PIL import ImageGrab
import pytesseract
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QColor
from pynput import keyboard

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = os.getenv("OPENAI_API_BASE")
MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

app = QApplication(sys.argv)
widget = QWidget()

# Set window flags for borderless and click-through
widget.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput)
widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
widget.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation)

# Set minimum size
widget.setMinimumSize(650, 100)

# Set semi-transparency
widget.setWindowOpacity(0.5)

# Set black background
widget.setStyleSheet("background-color: black;")

# Add a label with white text
label = QLabel("Test Window")
label.setStyleSheet("color: white; font-size: 24px;")
label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
label = QLabel("Press Ctrl+Alt+R to capture screen and get AI response\nPress Ctrl+Alt+Q to quit")
label.setStyleSheet("color: white; font-size: 16px;")
layout = QVBoxLayout()
layout.addWidget(label)
widget.setLayout(layout)

# Position window at top with 30px margin
screen = app.primaryScreen().geometry()
x = (screen.width() - widget.width()) // 2
y = 30
widget.move(x, y)

def capture_screen():
    # Capture the screen
    screenshot = ImageGrab.grab()
    # Perform OCR
    text = pytesseract.image_to_string(screenshot)
    return text

def get_ai_response(text):
    try:
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant. Provide concise and accurate responses."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def process_screen():
    text = capture_screen()
    response = get_ai_response(text)
    label.setText(response)

def quit_app():
    app.quit()

# Global keyboard monitoring
current_keys = set()

def on_press(key):
    try:
        current_keys.add(key)
        # Check for Ctrl+Alt+R
        if keyboard.Key.ctrl in current_keys and keyboard.Key.alt in current_keys and key == keyboard.KeyCode.from_char('r'):
            process_screen()
        # Check for Ctrl+Alt+Q
        elif keyboard.Key.ctrl in current_keys and keyboard.Key.alt in current_keys and key == keyboard.KeyCode.from_char('q'):
            quit_app()
    except AttributeError:
        pass

def on_release(key):
    try:
        current_keys.remove(key)
    except KeyError:
        pass

# Start keyboard listener
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

widget.show()
hwnd = widget.winId()
hwnd_int = int(hwnd)  # Convert sip.voidptr to an integer
ctypes.windll.user32.SetWindowDisplayAffinity(hwnd_int, 17)
sys.exit(app.exec())