import sys
import ctypes
import os,datetime
from dotenv import load_dotenv
from openai import OpenAI
from PIL import ImageGrab
import pytesseract
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt, QPoint, QTimer, QObject, pyqtSignal
from PyQt6.QtGui import QColor
# from pynput import keyboard # No longer needed for debugging
from global_hotkeys import *
pytesseract.pytesseract.tesseract_cmd=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# --- Custom Signal Emitter ---
class SignalEmitter(QObject):
    quit_signal = pyqtSignal()
    response_chunk_received = pyqtSignal(str) # Signal for streaming chunks
    response_finished = pyqtSignal()         # Signal for stream completion

emitter = SignalEmitter()
# -----------------------------

# Load environment variables
load_dotenv()

# Configure OpenAI
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_API_BASE")  # base_url replaces api_base
MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Configure hotkeys
CAPTURE_HOTKEY = os.getenv("CAPTURE_HOTKEY", "Ctrl+Alt+R")
QUIT_HOTKEY = os.getenv("QUIT_HOTKEY", "Ctrl+Alt+Q")

def parse_hotkey(hotkey_str):
    """Parse a hotkey string like 'Ctrl+Alt+R' into a list of modifiers and key."""
    parts = hotkey_str.lower().split('+')
    modifiers = []
    key = parts[-1]  # Last part is the key
    
    # Process modifiers
    for part in parts[:-1]:
        if part in ['ctrl', 'control']:
            modifiers.append('control')
        elif part in ['alt']:
            modifiers.append('alt')
        elif part in ['win', 'windows']:
            modifiers.append('win')
        elif part in ['shift']:
            modifiers.append('shift')
    
    # Handle special keys
    if key == 'enter':
        key = 'enter'  # Keep as 'enter' for global_hotkeys
    
    return [modifiers, key]

# Log configuration (masking the API key for security)
print(f"OpenAI API Key: {'*' * 4 + api_key[-4:] if api_key else 'Not set'}")
print(f"OpenAI Base URL: {base_url if base_url else 'Default (https://api.openai.com/v1)'}")
print(f"OpenAI Model: {MODEL}")
print(f"Capture Hotkey: {CAPTURE_HOTKEY}")
print(f"Quit Hotkey: {QUIT_HOTKEY}")

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

# Set black background with margins
widget.setStyleSheet("""
    QWidget {
        background-color: black;
        border-radius: 15px;
    }
    QLabel {
        padding: 20px;
        color: white;
        font-size: 16px;
    }
""")

# Add a label with white text and word wrapping
label = QLabel("Press Ctrl+Alt+R to capture screen and get AI response\nPress Ctrl+Alt+Q to quit")
label.setWordWrap(True)
label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
label.setMinimumWidth(600)  # Ensure minimum width for text wrapping
label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

# Create layout with margins
layout = QVBoxLayout()
layout.setContentsMargins(20, 20, 20, 20)  # Left, Top, Right, Bottom margins
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

        stream = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant. Provide concise and accurate responses."},
                {"role": "user", "content": text}
            ],
            stream=True
        )

        full_response_content = ""
        for chunk in stream:
            content_chunk = chunk.choices[0].delta.content
            if content_chunk is not None:
                full_response_content += content_chunk
                emitter.response_chunk_received.emit(content_chunk) # Emit chunk

        emitter.response_finished.emit() # Emit finish signal

        # Log full request and response to file AFTER stream completes
        with open('openai_logs.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n\n=== {datetime.datetime.now().isoformat()} ===\n")
            f.write(f"Request text:\n{text}\n\n")
            f.write(f"Response:\n{full_response_content}\n")

        print(f"Full OpenAI response logged. Length: {len(full_response_content)}")
        # Note: Usage info is not typically available directly with streams in the same way.
        # If needed, you might need to estimate or handle it differently.

    except Exception as e:
        error_message = f"Error: {str(e)}"
        print(f"OpenAI API error: {error_message}")
        # Emit the error message as a chunk to display it
        emitter.response_chunk_received.emit(error_message)
        emitter.response_finished.emit() # Still signal finish

# Slot to handle incoming response chunks
is_first_chunk = True
def update_label_chunk(chunk):
    global is_first_chunk
    if is_first_chunk:
        label.setText("")     # Clear "Thinking..."
        is_first_chunk = False

    current_text = label.text()
    label.setText(current_text + chunk)
    # Adjust window size dynamically as text is added
    widget.adjustSize()
    # Ensure window stays within screen bounds and centered
    screen = app.primaryScreen().geometry()
    max_height = screen.height() - 60
    if widget.height() > max_height:
        widget.setFixedHeight(max_height)
    x = (screen.width() - widget.width()) // 2
    y = 30
    widget.move(x, y)

# Slot to handle response finished (optional actions)
def handle_response_finished():
    print("Streaming finished.")
    # Final adjustments or logging if needed

def process_screen_callback():
    global is_first_chunk
    print("Hotkey Ctrl+Alt+R pressed!")

    # Reset window size and position, show "Thinking..."
    is_first_chunk = True # Reset flag for new request
    label.setText("Thinking...")
    widget.adjustSize() # Adjust size for "Thinking..." text initially
    screen = app.primaryScreen().geometry()
    x = (screen.width() - widget.width()) // 2
    y = 30
    widget.move(x, y)

    # Perform OCR and get AI response (runs in background implicitly due to network I/O)
    # Consider running OCR in a separate thread if it's blocking
    print("Performing screen capture and OCR...") # Debug print
    text = capture_screen()
    print(f"Captured text from screen: {text[:100]}..." if len(text) > 100 else f"Captured text from screen: {text}")
    print("Calling get_ai_response...") # Debug print
    get_ai_response(text) # This now emits signals instead of returning directly

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
emitter.response_chunk_received.connect(update_label_chunk) # Connect chunk signal
emitter.response_finished.connect(handle_response_finished) # Connect finish signal

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
    [ parse_hotkey(CAPTURE_HOTKEY)[0] + [parse_hotkey(CAPTURE_HOTKEY)[1]], process_screen_callback, None ],
    [ parse_hotkey(QUIT_HOTKEY)[0] + [parse_hotkey(QUIT_HOTKEY)[1]], trigger_quit_from_hotkey, None ]
]
register_hotkeys(hotkeys)

# Start listening for hotkeys
start_checking_hotkeys()

widget.show()
hwnd = widget.winId()
hwnd_int = int(hwnd)  # Convert sip.voidptr to an integer
ctypes.windll.user32.SetWindowDisplayAffinity(hwnd_int, 17)
sys.exit(app.exec())