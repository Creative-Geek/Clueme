import sys
import ctypes
import os
from dotenv import load_dotenv
from openai import OpenAI
from PIL import ImageGrab
import pytesseract
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, QTimer, QObject, pyqtSignal
from PyQt6.QtGui import QColor
# from pynput import keyboard # No longer needed for debugging
from global_hotkeys import *
pytesseract.pytesseract.tesseract_cmd=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# --- Custom Signal Emitter ---
class SignalEmitter(QObject):
    quit_signal = pyqtSignal()

emitter = SignalEmitter()
# -----------------------------

# Load environment variables
load_dotenv()

# Configure OpenAI
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_API_BASE")  # base_url replaces api_base
MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Log configuration (masking the API key for security)
print(f"OpenAI API Key: {'*' * 4 + api_key[-4:] if api_key else 'Not set'}")
print(f"OpenAI Base URL: {base_url if base_url else 'Default (https://api.openai.com/v1)'}")
print(f"OpenAI Model: {MODEL}")

# Initialize the client
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

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
        # Log the base_url being used
        print(f"Using OpenAI base_url: {client.base_url}")
        print(f"Using model: {MODEL}")
        print(f"Sending request to OpenAI with text: {text[:100]}..." if len(text) > 100 else f"Sending request to OpenAI with text: {text}")
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant. Provide concise and accurate responses."},
                {"role": "user", "content": text}
            ]
        )
        content = response.choices[0].message.content
        print(f"OpenAI response: {content[:100]}..." if len(content) > 100 else f"OpenAI response: {content}")

        # Log additional response information
        print(f"Model used: {response.model}")
        print(f"Completion tokens: {response.usage.completion_tokens}")
        print(f"Prompt tokens: {response.usage.prompt_tokens}")
        print(f"Total tokens: {response.usage.total_tokens}")

        return content
    except Exception as e:
        error_message = f"Error: {str(e)}"
        print(f"OpenAI API error: {error_message}")
        return error_message

def process_screen_callback():
    print("Hotkey Ctrl+Alt+R pressed!")
    text = capture_screen()
    print(f"Captured text from screen: {text[:100]}..." if len(text) > 100 else f"Captured text from screen: {text}")
    response = get_ai_response(text)
    label.setText(response)

# This function is called by the hotkey thread
def trigger_quit_from_hotkey():
    print("Hotkey Ctrl+Alt+Q pressed! Emitting signal...")
    emitter.quit_signal.emit() # Emit the signal

# This slot runs in the main thread
def perform_quit():
    print("Quit signal received in main thread. Stopping listeners and quitting...")
    try:
        stop_checking_hotkeys()
    except Exception as e:
        print(f"Error stopping global_hotkeys: {e}")
    QApplication.quit()

# Connect the signal to the slot
emitter.quit_signal.connect(perform_quit)

# Debug logging for all key presses using pynput - REMOVED
# def on_press_debug(key):
#     try:
#         print(f"Key pressed: {key.char}")
#     except AttributeError:
#         print(f"Special key pressed: {key}")

# Start pynput listener for debugging - REMOVED
# debug_listener = keyboard.Listener(on_press=on_press_debug)
# debug_listener.start()

# Define and register global hotkeys
hotkeys = [
    # Format: [ ["modifier", "key"], key_down_callback, key_up_callback (optional) ], ...
    [ ["control", "alt", "r"], process_screen_callback, None ],
    [ ["control", "alt", "q"], trigger_quit_from_hotkey, None ]
]
register_hotkeys(hotkeys)

# Start listening for hotkeys
start_checking_hotkeys()

widget.show()
hwnd = widget.winId()
hwnd_int = int(hwnd)  # Convert sip.voidptr to an integer
ctypes.windll.user32.SetWindowDisplayAffinity(hwnd_int, 17)
sys.exit(app.exec())