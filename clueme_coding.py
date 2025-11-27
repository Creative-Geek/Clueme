"""
Clueme Coding - AI assistant for coding questions using OneOCR.
This version uses Windows native OCR (OneOCR) and provides markdown-formatted responses.
"""
import sys
import ctypes
import os
import datetime
import platform
from dotenv import load_dotenv
from PIL import ImageGrab

import oneocr_wrapper
from coding_ai_processor import CodingAIProcessor

# Import from PySide6
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QSizePolicy,
    QMessageBox, QTextEdit, QScrollArea
)
from PySide6.QtCore import Qt, QObject, Signal, QThread, Slot
from PySide6.QtGui import QFont, QTextCursor
from global_hotkeys import register_hotkeys, start_checking_hotkeys, stop_checking_hotkeys

# Markdown rendering
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound


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


def is_win10_2004_or_higher():
    """Check if Windows 10 version 2004 or higher (build 19041+) or Windows 11"""
    ver = get_windows_version()
    if not ver:
        return False
    
    if ver[0] >= 11:
        return True
    
    if ver[0] == 10 and ver[2] >= 22631:
        return True
    
    return False


def is_frozen():
    """Check if running as a compiled executable (Nuitka)"""
    return getattr(sys, 'frozen', False)


def get_base_dir():
    """Get the base directory depending on frozen status"""
    if is_frozen():
        return os.path.dirname(sys.executable)
    else:
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
        show_error_dialog(
            "Configuration Error",
            f"Required configuration file not found:\n{env_path}",
            "Please create a .env file with your API keys and settings.",
            "The .env file should contain:\nSOLVING_MODEL_API_KEY=your_api_key_here\nSOLVING_MODEL_BASE_URL=optional_base_url\nSOLVING_MODEL=gpt-4 (or another model)"
        )
        sys.exit(1)


def show_error_dialog(title: str, text: str, info: str = "", details: str = ""):
    """Show an error dialog box"""
    app = QApplication.instance()
    needs_temp_app = False
    
    if app is None:
        temp_app = QApplication(sys.argv)
        needs_temp_app = True
    
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    if info:
        msg_box.setInformativeText(info)
    if details:
        msg_box.setDetailedText(details)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()
    
    if needs_temp_app:
        del temp_app


def check_oneocr_setup():
    """Check if OneOCR is properly set up and warn the user if not"""
    all_present, missing_files = oneocr_wrapper.check_oneocr_requirements()
    
    if not all_present:
        message = oneocr_wrapper.get_missing_files_message(missing_files)
        show_error_dialog(
            "OneOCR Setup Required",
            "OneOCR is not properly configured.",
            "The application requires OneOCR DLL files to function.",
            message
        )
        sys.exit(1)


# Custom code block renderer for syntax highlighting
class MarkdownRenderer:
    """Renders markdown to HTML with syntax-highlighted code blocks"""
    
    def __init__(self):
        self.md = MarkdownIt()
        self.formatter = HtmlFormatter(style='monokai', noclasses=True)
    
    def highlight_code(self, code: str, lang: str | None) -> str:
        """Highlight code block with pygments"""
        try:
            if lang:
                lexer = get_lexer_by_name(lang, stripall=True)
            else:
                lexer = guess_lexer(code)
        except ClassNotFound:
            # Fall back to plain text
            return f'<pre style="background-color: #272822; color: #f8f8f2; padding: 10px; border-radius: 5px; overflow-x: auto;"><code>{code}</code></pre>'
        
        highlighted = highlight(code, lexer, self.formatter)
        return highlighted
    
    def render(self, text: str) -> str:
        """
        Render markdown text to HTML with syntax highlighting.
        
        Args:
            text: Markdown formatted text
        
        Returns:
            HTML string with syntax highlighting
        """
        # First, extract and highlight code blocks manually
        import re
        
        # Pattern for fenced code blocks
        code_block_pattern = r'```(\w*)\n(.*?)```'
        
        def replace_code_block(match):
            lang = match.group(1) or None
            code = match.group(2)
            return self.highlight_code(code, lang)
        
        # Replace code blocks with highlighted versions
        text_with_code = re.sub(code_block_pattern, replace_code_block, text, flags=re.DOTALL)
        
        # Now render the rest as markdown (but code blocks are already processed)
        # Simple rendering for remaining markdown
        html = self.simple_markdown_to_html(text_with_code)
        
        return html
    
    def simple_markdown_to_html(self, text: str) -> str:
        """Simple markdown to HTML conversion for non-code content"""
        import re
        
        # Inline code
        text = re.sub(r'`([^`]+)`', r'<code style="background-color: #3a3a3a; color: #f8f8f2; padding: 2px 5px; border-radius: 3px;">\1</code>', text)
        
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
        
        # Italic
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
        
        # Headers
        text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        
        # Line breaks
        text = text.replace('\n', '<br>')
        
        return text


# Load environment variables
load_env_settings()

# Check OneOCR setup
print("Checking OneOCR setup...")
check_oneocr_setup()
print("OneOCR is properly configured.")

# Display configuration
print(f"Using OCR Engine: OneOCR (Windows Native)")

# Configure model settings
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
        if part in ['ctrl', 'control']:
            modifiers.append('control')
        elif part in ['alt']:
            modifiers.append('alt')
        elif part in ['win', 'windows']:
            modifiers.append('win')
        elif part in ['shift']:
            modifiers.append('shift')
    if key == 'enter':
        key = 'enter'
    return [modifiers, key]


# Log configuration
print(f"Base Directory: {get_base_dir()}")
print(f"Solving Model API Key: {'*' * 4 + SOLVING_MODEL_API_KEY[-4:] if SOLVING_MODEL_API_KEY else 'Not set'}")
print(f"Solving Model Base URL: {SOLVING_MODEL_BASE_URL if SOLVING_MODEL_BASE_URL else 'Default (https://api.openai.com/v1)'}")
print(f"Answering Model: {SOLVING_MODEL}")
print(f"Capture Hotkey: {CAPTURE_HOTKEY}")
print(f"Quit Hotkey: {QUIT_HOTKEY}")
print(f"Reset Hotkey: {RESET_HOTKEY}")

# Initialize API key
if not SOLVING_MODEL_API_KEY:
    print("Error: SOLVING_MODEL_API_KEY environment variable not set.")
    show_error_dialog(
        "Configuration Error",
        "No API Key provided in the .env file.",
        "Please add SOLVING_MODEL_API_KEY to your .env file.",
        "The .env file should contain:\nSOLVING_MODEL_API_KEY=your_api_key_here\nSOLVING_MODEL_BASE_URL=optional_base_url\nSOLVING_MODEL=gpt-4 (or another model)"
    )
    sys.exit(1)

# Create AI processor
ai_processor = CodingAIProcessor(
    api_key=SOLVING_MODEL_API_KEY,
    base_url=SOLVING_MODEL_BASE_URL,
    model=SOLVING_MODEL
)

# Create markdown renderer
markdown_renderer = MarkdownRenderer()


# --- Worker Thread for AI Calls ---
class AIWorker(QObject):
    @Slot(str)
    def run_processing(self, text):
        """Runs the AI processing for coding questions."""
        ai_processor.process_coding_question(text)


# --- PySide6 UI Setup ---
app = QApplication(sys.argv)
widget = QWidget()

# Window Styling - Different approach based on Windows version
windows_version = get_windows_version()
print(f"Detected Windows version: {windows_version if windows_version else 'Non-Windows OS'}")

# Use different window flags depending on Windows version
if is_win10_2004_or_higher():
    print("Using FramelessWindowHint (Windows 10 v2004+ or Windows 11 detected)")
    widget.setWindowFlags(
        Qt.WindowType.FramelessWindowHint |
        Qt.WindowType.WindowStaysOnTopHint |
        Qt.WindowType.Tool |
        Qt.WindowType.WindowTransparentForInput
    )
else:
    print("Avoiding FramelessWindowHint (older Windows version detected)")
    widget.setWindowFlags(
        Qt.WindowType.WindowStaysOnTopHint |
        Qt.WindowType.Tool |
        Qt.WindowType.WindowTransparentForInput
    )

widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
widget.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation)
widget.setMinimumSize(700, 150)
widget.setWindowOpacity(0.85)

# Main stylesheet for the widget
widget.setStyleSheet("""
QWidget {
    background-color: #1e1e1e;
    border-radius: 15px;
}
""")

# Create text display widget (QTextEdit for rich text/HTML support)
text_display = QTextEdit()
text_display.setReadOnly(True)
text_display.setWordWrapMode(1)  # WordWrap
text_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
text_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
text_display.setMinimumWidth(680)
text_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

# Style the text display
text_display.setStyleSheet("""
QTextEdit {
    background-color: transparent;
    color: #f8f8f2;
    font-size: 14px;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    border: none;
    padding: 15px;
}
QScrollBar:vertical {
    background: #2d2d2d;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #555;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
""")

# Set initial text
initial_message = f"""<div style="color: #f8f8f2; font-size: 14px;">
<p>Press <b style="color: #66d9ef;">{CAPTURE_HOTKEY}</b> to capture screen and get AI response</p>
<p>Press <b style="color: #66d9ef;">{QUIT_HOTKEY}</b> to quit</p>
<p>Press <b style="color: #66d9ef;">{RESET_HOTKEY}</b> to reset</p>
</div>"""
text_display.setHtml(initial_message)

layout = QVBoxLayout()
layout.setContentsMargins(10, 10, 10, 10)
layout.addWidget(text_display)
widget.setLayout(layout)


# --- UI Positioning ---
def position_widget():
    screen = app.primaryScreen().geometry()
    widget.adjustSize()
    max_height = int(screen.height() * 0.7)
    if widget.height() > max_height:
        widget.setFixedHeight(max_height)
    
    x = (screen.width() - widget.width()) // 2
    y = 30
    widget.move(x, y)


position_widget()


# --- Screen Capture ---
def capture_screen():
    """Captures the screen and performs OCR using OneOCR."""
    try:
        screenshot_pil = ImageGrab.grab()
        print("Screenshot grabbed. Performing OCR with OneOCR...")
        
        # Call the perform_ocr function from oneocr_wrapper
        text = oneocr_wrapper.perform_ocr(screenshot_pil)
        
        if text is None:
            print("OCR failed.")
            ai_processor.emitter.error_occurred.emit("OCR process failed. Check logs.")
            return None
        
        print("OCR successful.")
        print(f"Captured text (first 200 chars): {text[:200]}")
        
        # Log the captured text
        with open('coding_logs.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n\n=== OCR TEXT (OneOCR) {datetime.datetime.now().isoformat()} ===\n")
            f.write(text)
            f.write("\n=== END OCR TEXT ===\n")
        
        return text
        
    except Exception as e:
        print(f"Error during screen capture phase: {e}")
        ai_processor.emitter.error_occurred.emit(f"Error capturing screen: {e}")
        return None


# --- Global State ---
is_processing = False
is_first_chunk = True
accumulated_response = ""


# --- UI Update Slots ---
@Slot(str)
def update_display_chunk(chunk):
    global is_first_chunk, accumulated_response
    
    if is_first_chunk:
        accumulated_response = ""
        is_first_chunk = False
    
    accumulated_response += chunk
    
    # Render markdown to HTML
    html_content = markdown_renderer.render(accumulated_response)
    
    # Wrap in styled container
    styled_html = f"""
    <div style="color: #f8f8f2; font-size: 14px; line-height: 1.5;">
    {html_content}
    </div>
    """
    
    text_display.setHtml(styled_html)
    
    # Scroll to bottom
    cursor = text_display.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    text_display.setTextCursor(cursor)
    
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
    text_display.setHtml(f"""
    <div style="color: #f92672; font-size: 14px;">
    <b>Error:</b><br>{error_message}
    </div>
    """)
    is_processing = False
    position_widget()


@Slot()
def show_thinking():
    global is_first_chunk
    is_first_chunk = True
    text_display.setHtml("""
    <div style="color: #66d9ef; font-size: 14px;">
    <b>Thinking...</b>
    </div>
    """)
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
        # Emit the extracted text for processing
        ai_processor.emitter.text_extracted.emit(text)
    else:
        is_processing = False


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
    
    if thread.isRunning():
        print("Waiting for worker thread to finish...")
        thread.quit()
        thread.wait()
        print("Worker thread finished.")
    
    app.quit()


def reset_program():
    global is_processing, is_first_chunk, accumulated_response
    if is_processing:
        print("Cannot reset while processing.")
        return
    
    print("Reset Hotkey pressed!")
    is_first_chunk = True
    is_processing = False
    accumulated_response = ""
    text_display.setHtml(initial_message)
    position_widget()


# --- Signal/Slot Connections ---
ai_processor.emitter.processing_started.connect(show_thinking)
ai_processor.emitter.response_chunk_received.connect(update_display_chunk)
ai_processor.emitter.response_finished.connect(handle_response_finished)
ai_processor.emitter.error_occurred.connect(handle_error)
ai_processor.emitter.quit_signal.connect(perform_quit)

# --- Setup Worker Thread ---
thread = QThread()
worker = AIWorker()
worker.moveToThread(thread)

ai_processor.emitter.text_extracted.connect(worker.run_processing)

thread.started.connect(lambda: print("Worker thread started."))
thread.finished.connect(lambda: print("Worker thread finished."))
ai_processor.emitter.quit_signal.connect(thread.quit)
ai_processor.emitter.quit_signal.connect(worker.deleteLater)
ai_processor.emitter.quit_signal.connect(thread.wait)

thread.start()

# --- Register Hotkeys ---
hotkeys_bindings = [
    {"key": CAPTURE_HOTKEY, "callback": process_screen_callback},
    {"key": QUIT_HOTKEY, "callback": trigger_quit_from_hotkey},
    {"key": RESET_HOTKEY, "callback": reset_program}
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
        sys.exit(1)
else:
    print("No valid hotkeys registered. Exiting.")
    sys.exit(1)

# --- Show Window and Run App ---
widget.show()
try:
    hwnd = widget.winId()
    if hwnd:
        try:
            result = ctypes.windll.user32.SetWindowDisplayAffinity(int(hwnd), 0x00000011)
            if result:
                print("Window display affinity set to exclude from capture.")
            else:
                error_code = ctypes.windll.kernel32.GetLastError()
                print(f"Failed to set window display affinity. Error code: {error_code}")
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
