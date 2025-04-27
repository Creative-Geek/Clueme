import sys
import ctypes
import os
import datetime
import json
import platform
from dotenv import load_dotenv
from PIL import ImageGrab

import ocr
from ai_processor import AIProcessor

# Import from PySide6 instead of PyQt6
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QObject, Signal, QThread, Slot
from global_hotkeys import register_hotkeys, start_checking_hotkeys, stop_checking_hotkeys

# Windows version detection
def get_windows_version():
    """Get Windows major and minor version numbers"""
    if platform.system() != 'Windows':
        return None
    
    win_ver = platform.win32_ver()[1].split('.')
    try:
        major = int(win_ver[0])
        minor = int(win_ver[1]) if len(win_ver) > 1 else 0
        build = int(win_ver[2]) if len(win_ver) > 2 else 0
        return (major, minor, build)
    except (IndexError, ValueError):
        return None

# Check if Windows 10 version 2004 or higher (build 19041+) or Windows 11
def is_win10_2004_or_higher():
    ver = get_windows_version()
    if not ver:
        return False
    
    # Windows 11 or higher
    if ver[0] >= 11:
        return True
    
    # Windows 11 build 22631 or higher
    if ver[0] == 10 and ver[2] >= 22631:
        return True
    
    return False

def is_frozen():
    """Check if running as a compiled executable (Nuitka)"""
    return getattr(sys, 'frozen', False)

def get_base_dir():
    """Get the base directory depending on frozen status"""
    if is_frozen():
        # Path when running from compiled executable (Nuitka)
        return os.path.dirname(sys.executable)
    else:
        # Path when running as a normal script
        return os.path.dirname(os.path.abspath(__file__))

def load_env_settings():
    """Load environment settings from .env file"""
    base_dir = get_base_dir()
    env_path = os.path.join(base_dir, '.env')
    
    if os.path.exists(env_path):
        print(f"Loading settings from: {env_path}")
        load_dotenv(env_path)
    else:
        print(f"Error: .env file not found at {env_path}")
        
        # Check if QApplication exists already or create a temporary one
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance()
        if app is None:
            # Create a temporary QApplication
            temp_app = QApplication(sys.argv)
            needs_temp_app = True
        else:
            needs_temp_app = False
        
        # Create a message box that will be visible even if no console is present
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Configuration Error")
        msg_box.setText(f"Required configuration file not found:\n{env_path}\n\nThe application cannot start without proper configuration.")
        msg_box.setInformativeText("Please create a .env file with your API keys and settings.")
        msg_box.setDetailedText("The .env file should contain:\nSOLVING_MODEL_API_KEY=your_api_key_here\nSOLVING_MODEL_BASE_URL=optional_base_url\nSOLVING_MODEL=gpt-4 (or another model)")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
        
        # If we created a temporary app, clean it up
        if needs_temp_app:
            del temp_app
        
        # Exit the application
        sys.exit(1)

# Load environment variables
load_env_settings()

# --- Display Selected OCR Engine ---
print(f"Using OCR Engine: GEMINI")

# Configure OpenAI
SOLVING_MODEL_API_KEY = os.getenv("SOLVING_MODEL_API_KEY")
SOLVING_MODEL_BASE_URL = os.getenv("SOLVING_MODEL_BASE_URL")
SOLVING_MODEL = os.getenv("SOLVING_MODEL", "gpt-4")

# Configure hotkeys
CAPTURE_HOTKEY = os.getenv("CAPTURE_HOTKEY", "Alt+Enter")
QUIT_HOTKEY = os.getenv("QUIT_HOTKEY", "Ctrl+Alt+Q")
RESET_HOTKEY = os.getenv("RESET_HOTKEY", "Ctrl+Alt+R")

def parse_hotkey(hotkey_str):
    """Parse a hotkey string like 'Ctrl+Alt+R' into a list of modifiers and key."""
    parts = hotkey_str.lower().split('+')
    modifiers = []
    key = parts[-1]
    for part in parts[:-1]:
        if part in ['ctrl', 'control']: modifiers.append('control')
        elif part in ['alt']: modifiers.append('alt')
        elif part in ['win', 'windows']: modifiers.append('win')
        elif part in ['shift']: modifiers.append('shift')
    if key == 'enter': key = 'enter'
    return [modifiers, key]

# Log configuration
print(f"Base Directory: {get_base_dir()}")
print(f"Solving Model API Key: {'*' * 4 + SOLVING_MODEL_API_KEY[-4:] if SOLVING_MODEL_API_KEY else 'Not set'}")
print(f"Solving Model Base URL: {SOLVING_MODEL_BASE_URL if SOLVING_MODEL_BASE_URL else 'Default (https://api.openai.com/v1)'}")
print(f"Answering Model: {SOLVING_MODEL}")
print(f"Capture Hotkey: {CAPTURE_HOTKEY}")
print(f"Quit Hotkey: {QUIT_HOTKEY}")
print(f"Reset Hotkey: {RESET_HOTKEY}")

# Initialize the client
if not SOLVING_MODEL_API_KEY:
    print("Error: SOLVING_MODEL_API_KEY environment variable not set.")
    sys.exit(1)

# Create AI processor
ai_processor = AIProcessor(
    api_key=SOLVING_MODEL_API_KEY,
    base_url=SOLVING_MODEL_BASE_URL,
    smarter_model=SOLVING_MODEL
)

# --- Worker Thread for AI Calls ---
class AIWorker(QObject):
    @Slot(dict)
    def run_answering(self, extracted_data):
        """Runs the AI step (answering) if a question was found."""
        ai_processor.process_question(extracted_data)

# --- PySide6 UI Setup ---
app = QApplication(sys.argv)
widget = QWidget()

# Window Styling - Different approach based on Windows version
windows_version = get_windows_version()
print(f"Detected Windows version: {windows_version if windows_version else 'Non-Windows OS'}")

# Use different window flags depending on Windows version
if is_win10_2004_or_higher():
    # For Windows 10 version 2004+ and Windows 11, we can use FramelessWindowHint safely
    print("Using FramelessWindowHint (Windows 10 v2004+ or Windows 11 detected)")
    widget.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput)
else:
    # For older Windows versions, avoid FramelessWindowHint to ensure SetWindowDisplayAffinity works
    print("Avoiding FramelessWindowHint (older Windows version detected)")
    widget.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput)
    
widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
widget.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation)
widget.setMinimumSize(650, 100)
widget.setWindowOpacity(0.6)
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

label = QLabel("Press " + CAPTURE_HOTKEY + " to capture screen and get AI response\nPress " + QUIT_HOTKEY + " to quit")
label.setWordWrap(True)
label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
label.setMinimumWidth(600)
label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

layout = QVBoxLayout()
layout.setContentsMargins(15, 15, 15, 15)
layout.addWidget(label)
widget.setLayout(layout)

# --- UI Positioning ---
def position_widget():
    screen = app.primaryScreen().geometry()
    widget.adjustSize()
    max_height = screen.height() * 0.6
    if widget.height() > max_height:
        widget.setFixedHeight(int(max_height))
    
    x = (screen.width() - widget.width()) // 2
    y = 30
    widget.move(x, y)

position_widget()  # Initial position

# --- Screen Capture ---
def capture_screen():
    """Captures the screen and performs OCR using Gemini Vision."""
    try:
        screenshot_pil = ImageGrab.grab()
        print("Screenshot grabbed. Performing OCR with Gemini Vision...")
        
        # Call the perform_ocr function from the ocr module
        text = ocr.perform_ocr(screenshot_pil)
        
        if text is None:
            print("OCR failed.")
            ai_processor.emitter.error_occurred.emit(f"OCR process failed with Gemini Vision. Check logs.")
            return None
        
        print("OCR successful.")
        
        # Log the captured text
        print(f"Captured text (first 200 chars): {text[:200]}")
        # Log full OCR text to file
        with open('openai_logs.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n\n=== OCR TEXT (GEMINI) {datetime.datetime.now().isoformat()} ===\n")
            f.write(text)
            f.write("\n=== END OCR TEXT ===\n")
        
        return text
        
    except Exception as e:
        # Catch errors during ImageGrab itself or other unexpected issues here
        print(f"Error during screen capture phase: {e}")
        ai_processor.emitter.error_occurred.emit(f"Error capturing screen: {e}")
        return None

# --- Global State ---
is_processing = False  # Flag to prevent concurrent processing
is_first_chunk = True  # Flag for clearing label on first chunk of Step 2

# --- UI Update Slots ---
@Slot(str)
def update_label_chunk(chunk):
    global is_first_chunk
    if is_first_chunk:
        label.setText("")
        is_first_chunk = False
    
    current_text = label.text()
    label.setText(current_text + chunk)
    position_widget()

@Slot()
def handle_response_finished():
    global is_processing
    print("Processing finished.")
    is_processing = False
    position_widget()

@Slot(str)
def handle_error(error_message):
    global is_processing
    print(f"Displaying error: {error_message}")
    label.setText(f"Error:\n{error_message}")
    is_processing = False
    position_widget()

@Slot()
def show_thinking():
    global is_first_chunk
    is_first_chunk = True
    label.setText("Thinking...")
    position_widget()

# --- Hotkey Callbacks ---
def process_screen_callback():
    global is_processing
    if is_processing:
        print("Already processing, ignoring hotkey press.")
        return
    
    print("Capture Hotkey pressed!")
    is_processing = True
    ai_processor.emitter.processing_started.emit()
    
    # Perform screen capture and OCR
    text = capture_screen()
    
    if text:
        try:
            # Parse the JSON response from Gemini
            extracted_data = json.loads(text)
            # Basic validation
            if not isinstance(extracted_data.get("question_found"), bool):
                raise ValueError("Invalid 'question_found' field")
            if extracted_data.get("question_found"):
                if not isinstance(extracted_data.get("question"), str) or not isinstance(extracted_data.get("choices"), list):
                    raise ValueError("Missing or invalid 'question' or 'choices' when question_found is true")
                # Further validation: ensure choices are strings
                if not all(isinstance(item, str) for item in extracted_data.get("choices", [])):
                    raise ValueError("Not all items in 'choices' are strings")

            print(f"Parsed Extraction Data: {extracted_data}")
            ai_processor.emitter.extraction_complete.emit(extracted_data)  # Emit result directly to answering step

        except json.JSONDecodeError:
            print("Error: Gemini did not return valid JSON for extraction.")
            ai_processor.emitter.error_occurred.emit("Error: Failed to parse extraction result.")
            is_processing = False
        except ValueError as ve:
            print(f"Error: Invalid JSON structure received: {ve}")
            ai_processor.emitter.error_occurred.emit(f"Error: Invalid extraction structure ({ve}).")
            is_processing = False
    else:
        # Handle OCR failure immediately (error signal already emitted)
        is_processing = False  # Reset processing flag

def trigger_quit_from_hotkey():
    print("Quit Hotkey pressed!")
    ai_processor.emitter.quit_signal.emit()

@Slot()
def perform_quit():
    print("Quit signal received. Stopping listeners and quitting...")
    try:
        stop_checking_hotkeys()
    except Exception as e:
        print(f"Error stopping global_hotkeys: {e}")
    
    # Ensure thread is properly cleaned up
    if thread.isRunning():
        print("Waiting for worker thread to finish...")
        thread.quit()
        thread.wait()  # Wait for thread to finish
        print("Worker thread finished.")
    
    app.quit()

def reset_program():
    global is_processing, is_first_chunk
    if is_processing:
        print("Cannot reset while processing.")
        return
    
    print("Reset Hotkey pressed!")
    is_first_chunk = True
    is_processing = False
    label.setText("Press " + CAPTURE_HOTKEY + " to capture screen and get AI response\nPress " + QUIT_HOTKEY + " to quit")
    position_widget()

# --- Signal/Slot Connections ---
ai_processor.emitter.processing_started.connect(show_thinking)
ai_processor.emitter.response_chunk_received.connect(update_label_chunk)
ai_processor.emitter.response_finished.connect(handle_response_finished)
ai_processor.emitter.error_occurred.connect(handle_error)
ai_processor.emitter.quit_signal.connect(perform_quit)

# --- Setup Worker Thread ---
thread = QThread()
worker = AIWorker()
worker.moveToThread(thread)

ai_processor.emitter.extraction_complete.connect(worker.run_answering)

thread.started.connect(lambda: print("Worker thread started."))
thread.finished.connect(lambda: print("Worker thread finished."))
ai_processor.emitter.quit_signal.connect(thread.quit)
ai_processor.emitter.quit_signal.connect(worker.deleteLater)

# Use wait() for proper thread termination before app exit
ai_processor.emitter.quit_signal.connect(thread.wait)

thread.start()  # Start the thread event loop

# --- Register Hotkeys ---
hotkeys_bindings = [
    { "key": CAPTURE_HOTKEY, "callback": process_screen_callback },
    { "key": QUIT_HOTKEY, "callback": trigger_quit_from_hotkey },
    { "key": RESET_HOTKEY, "callback": reset_program }
]

registered_hotkeys = []
for binding in hotkeys_bindings:
    try:
        parsed = parse_hotkey(binding["key"])
        hotkey_definition = parsed[0] + [parsed[1]]
        registered_hotkeys.append([hotkey_definition, binding["callback"], None])
        print(f"Registering hotkey: {binding['key']} -> {hotkey_definition}")
    except Exception as e:
        print(f"Error parsing or registering hotkey '{binding['key']}': {e}")

if registered_hotkeys:
    try:
        register_hotkeys(registered_hotkeys)
        start_checking_hotkeys()
        print("Hotkey listener started.")
    except Exception as e:
        print(f"Failed to start hotkey listener: {e}")
        sys.exit(1)  # Consider exiting if hotkeys fail
else:
    print("No valid hotkeys registered. Exiting.")
    sys.exit(1)

# --- Show Window and Run App ---
widget.show()
try:
    hwnd = widget.winId()
    # Make sure we get a valid window handle
    if hwnd:
        # Apply SetWindowDisplayAffinity with proper error handling
        try:
            result = ctypes.windll.user32.SetWindowDisplayAffinity(int(hwnd), 0x00000011)  # DWMWA_EXCLUDED_FROM_CAPTURE
            if result:
                print("Window display affinity set to exclude from capture.")
            else:
                error_code = ctypes.windll.kernel32.GetLastError()
                print(f"Failed to set window display affinity. Error code: {error_code}")
                
                # Try an alternative approach if the current Windows version needs it
                if not is_win10_2004_or_higher():
                    print("Trying alternative approach for older Windows versions...")
                    # For older Windows versions, we may need to recreate the window
                    # or use a different attribute
        except Exception as e:
            print(f"Error in SetWindowDisplayAffinity: {e}")
    else:
        print("Could not get window handle (winId)")
except Exception as e:
    print(f"Could not set window display affinity (might be normal on non-Windows): {e}")

exit_code = app.exec()
print("Application exiting.")
if registered_hotkeys:
    try:
        print("Stopping hotkey listener...")
        stop_checking_hotkeys()
        print("Hotkey listener stopped.")
    except Exception as e:
        print(f"Error stopping global_hotkeys on exit: {e}")

sys.exit(exit_code)