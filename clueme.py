import sys
import ctypes
import os
import datetime
import json
from dotenv import load_dotenv
from openai import OpenAI
from PIL import ImageGrab

import ocr

# Import from PySide6 instead of PyQt6
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QObject, Signal, QThread, Slot
from global_hotkeys import *

# Load environment variables
load_dotenv()

# --- Display Selected OCR Engine ---
print(f"Using OCR Engine: GEMINI")

# Configure OpenAI
API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_API_BASE")
SMARTER_MODEL_API_BASE = os.getenv("SMARTER_MODEL_API_BASE")
SMARTER_MODEL = os.getenv("SMARTER_MODEL", "gpt-4")

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
print(f"OpenAI API Key: {'*' * 4 + API_KEY[-4:] if API_KEY else 'Not set'}")
print(f"OpenAI Base URL (Default): {BASE_URL if BASE_URL else 'Default (https://api.openai.com/v1)'}")
print(f"Smarter Model API Base: {SMARTER_MODEL_API_BASE if SMARTER_MODEL_API_BASE else 'Same as default'}")
print(f"Answering Model: {SMARTER_MODEL}")
print(f"Capture Hotkey: {CAPTURE_HOTKEY}")
print(f"Quit Hotkey: {QUIT_HOTKEY}")
print(f"Reset Hotkey: {RESET_HOTKEY}")

# Initialize the client
if not API_KEY:
    print("Error: OPENAI_API_KEY environment variable not set.")
    sys.exit(1)

# Create client for the smarter model
client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

# Create a separate client for the smarter model if a different API base is specified
smarter_client = None
if SMARTER_MODEL_API_BASE and SMARTER_MODEL_API_BASE != BASE_URL:
    print("Using separate client for smarter model with different API base")
    smarter_client = OpenAI(
        api_key=API_KEY,
        base_url=SMARTER_MODEL_API_BASE
    )
else:
    smarter_client = client

# --- Signal Emitter ---
class SignalEmitter(QObject):
    # Changed: pyqtSignal to Signal
    quit_signal = Signal()
    response_chunk_received = Signal(str)
    response_finished = Signal()
    error_occurred = Signal(str)
    processing_started = Signal()
    extraction_complete = Signal(dict)

emitter = SignalEmitter()

# --- Worker Thread for AI Calls ---
class AIWorker(QObject):
    @Slot(dict)
    def run_answering(self, extracted_data):
        """Runs the AI step (answering) if a question was found."""
        if not extracted_data.get("question_found"):
            print("No question found. Skipping answering step.")
            emitter.response_chunk_received.emit("Didn't find any questions.")
            emitter.response_finished.emit()
            return
        if not extracted_data.get("question") or not extracted_data.get("choices"):
            print("Question found but question/choices missing. Skipping answering step.")
            emitter.response_chunk_received.emit("Found question but couldn't extract details.")
            emitter.response_finished.emit()
            return

        question = extracted_data["question"]
        choices = extracted_data["choices"]

        print(f"\n--- Answering MCQ using {SMARTER_MODEL} ---")
        print(f"Question: {question}")
        print(f"Choices: {choices}")

        try:
            # --- Get Answer and Explanation ---
            answering_prompt = f"""
            You are an expert AI assistant. Answer the following multiple-choice question and provide a brief explanation for your choice.
            Limit your total response (answer + explanation) to approximately 700 characters.
            Be concise and clear. State the correct choice first, then the explanation.

            Question:
            {question}

            Choices:
            {chr(10).join(f'- {choice}' for choice in choices)}

            Your Answer (Correct Choice + Brief Explanation):
            """

            context_content = f"Context from extraction:\nQuestion: {question}\nChoices:\n" + "\n".join(f"- {choice}" for choice in choices)

            stream = smarter_client.chat.completions.create(
                model=SMARTER_MODEL,
                messages=[
                    {"role": "system", "content": context_content},
                    {"role": "system", "content": "You are a helpful AI assistant specializing in answering MCQs concisely."},
                    {"role": "user", "content": answering_prompt}
                ],
                stream=True,
                max_tokens=200
            )

            full_response_content = ""
            for chunk in stream:
                content_chunk = chunk.choices[0].delta.content
                if content_chunk is not None:
                    full_response_content += content_chunk
                    emitter.response_chunk_received.emit(content_chunk)

            emitter.response_finished.emit()

            with open('openai_logs.txt', 'a', encoding='utf-8') as f:
                f.write(f"\n\n=== {datetime.datetime.now().isoformat()} ===\n")
                f.write(f"Extracted Question:\n{question}\n")
                f.write(f"Extracted Choices:\n{choices}\n\n")
                f.write(f"Answering Prompt (User):\n{answering_prompt}\n\n")
                f.write(f"Response (Smarter Model):\n{full_response_content}\n")

            print(f"Full OpenAI response logged. Length: {len(full_response_content)}")

        except Exception as e:
            error_message = f"Error during answering: {str(e)}"
            print(error_message)
            emitter.response_chunk_received.emit(error_message)
            emitter.response_finished.emit()

# --- PySide6 UI Setup ---
app = QApplication(sys.argv)
widget = QWidget()

# Window Styling
widget.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput)
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
            emitter.error_occurred.emit(f"OCR process failed with Gemini Vision. Check logs.")
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
        emitter.error_occurred.emit(f"Error capturing screen: {e}")
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
    emitter.processing_started.emit()
    
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
            emitter.extraction_complete.emit(extracted_data)  # Emit result directly to answering step

        except json.JSONDecodeError:
            print("Error: Gemini did not return valid JSON for extraction.")
            emitter.error_occurred.emit("Error: Failed to parse extraction result.")
            is_processing = False
        except ValueError as ve:
            print(f"Error: Invalid JSON structure received: {ve}")
            emitter.error_occurred.emit(f"Error: Invalid extraction structure ({ve}).")
            is_processing = False
    else:
        # Handle OCR failure immediately (error signal already emitted)
        is_processing = False  # Reset processing flag

def trigger_quit_from_hotkey():
    print("Quit Hotkey pressed!")
    emitter.quit_signal.emit()

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
emitter.processing_started.connect(show_thinking)
emitter.response_chunk_received.connect(update_label_chunk)
emitter.response_finished.connect(handle_response_finished)
emitter.error_occurred.connect(handle_error)
emitter.quit_signal.connect(perform_quit)

# --- Setup Worker Thread ---
thread = QThread()
worker = AIWorker()
worker.moveToThread(thread)

emitter.extraction_complete.connect(worker.run_answering)

thread.started.connect(lambda: print("Worker thread started."))
thread.finished.connect(lambda: print("Worker thread finished."))
emitter.quit_signal.connect(thread.quit)
emitter.quit_signal.connect(worker.deleteLater)

# Use wait() for proper thread termination before app exit
emitter.quit_signal.connect(thread.wait)

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
    ctypes.windll.user32.SetWindowDisplayAffinity(int(hwnd), 0x00000011)
    print("Window display affinity set to exclude from capture.")
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