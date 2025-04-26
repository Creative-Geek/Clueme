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
from global_hotkeys import *

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

def process_screen_callback():
    print("Hotkey Ctrl+Alt+R pressed!")
    text = capture_screen()
    response = get_ai_response(text)
    label.setText(response)

def quit_app_callback():
    print("Hotkey Ctrl+Alt+Q pressed!")
    app.quit()

# Debug logging for all key presses using pynput
def on_press_debug(key):
    try:
        print(f"Key pressed: {key.char}")
    except AttributeError:
        print(f"Special key pressed: {key}")

# Start pynput listener for debugging
debug_listener = keyboard.Listener(on_press=on_press_debug)
debug_listener.start()

# Define and register global hotkeys
hotkeys = [
    # Format: [ ["modifier", "key"], key_down_callback, key_up_callback (optional) ], ...
    [ ["control", "alt", "r"], process_screen_callback, None ],
    [ ["control", "alt", "q"], quit_app_callback, None ]
]
register_hotkeys(hotkeys)

# Start listening for hotkeys
start_checking_hotkeys()

widget.show()
hwnd = widget.winId()
hwnd_int = int(hwnd)  # Convert sip.voidptr to an integer
ctypes.windll.user32.SetWindowDisplayAffinity(hwnd_int, 17)
sys.exit(app.exec())