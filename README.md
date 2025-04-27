# Clueme

<div align="center">
  
<img src="clueme.png" alt="Clueme Logo" width="500px">

</div>

------

A Windows application that provides AI assistance through keyboard shortcuts, designed to be invisible to screen recording software.

## Features

- Screen OCR using Gemini Vision (because tesseract and EasyOCR are not good enough)
- AI integration with OpenAI (or the many free compatible endpoints)
- Global keyboard shortcuts
- Stealth mode (invisible to screen recording)
- Modular architecture with separate AI processing component
- Could work on macOS but you'll need to edit some lines
-----

⚠️⚠️⚠️ Danger: this program is for research purposes only!

It was made as a response to the following post on X:
<div align="center">
<img src="https://github.com/user-attachments/assets/ea695b17-fa31-49c8-96b1-750a5c1cd981" alt="Clueme Logo" width="500px">
</div>

Do not missuse it, I'm not responsible for the use of this program.

## Setup

1. Install Python 3.8 or higher
2. Install dependencies:
   ```
   uv pip install -r requirements.txt
   ```
3. Create a `.env` file with your configuration (please do not include any comments in the file):
   ```
   # Solving Model Configuration
   SOLVING_MODEL_API_KEY=your_api_key_here
   SOLVING_MODEL_BASE_URL=your_custom_endpoint_url
   SOLVING_MODEL=your_model_name

   # OCR Model Configuration
   OCR_API_KEY=your_ocr_api_key_here
   OCR_BASE_URL=your_ocr_endpoint_url
   OCR_MODEL=your_ocr_model_name

   # Hotkey Configuration
   CAPTURE_HOTKEY=Alt+Enter  # Optional, defaults to Alt+Enter
   QUIT_HOTKEY=Ctrl+Alt+Q  # Optional, defaults to Ctrl+Alt+Q
   RESET_HOTKEY=Ctrl+Alt+R  # Optional, defaults to Ctrl+Alt+R
   ```

## Usage

- Press the configured capture hotkey (default: `Alt+Enter`) to capture screen and get AI assistance
- Press the configured quit hotkey (default: `Ctrl+Alt+Q`) to close the application
- Press the configured reset hotkey (default: `Ctrl+Alt+R`) to reset the application state

## Hotkey Configuration

You can configure the hotkeys in the `.env` file using the following format:

- Modifiers: `Ctrl`, `Alt`, `Win`, `Shift`
- Keys: Any single key (e.g., `R`, `Q`, `Enter`)
- Format: `Modifier1+Modifier2+Key` (e.g., `Ctrl+Alt+R`, `Alt+Enter`)

## PyInstaller Compilation Command

```bash
pyinstaller --onefile --noconsole --icon=clueme.ico --name=clueme --add-data ".env;." --exclude-module PyQt5 --exclude-module PyQt6 clueme.py
```

## Architecture

The application is built with a modular architecture:
- `clueme.py`: Main application file handling UI and hotkey management
- `ai_processor.py`: Dedicated module for AI processing and OpenAI integration
- `ocr.py`: OCR functionality using Gemini Vision

# Notes:
## Can work offline:
If you have ollama with a vision model you can specify it to be the endpoint for both OCR and Solving models (specify the models too).

## Requires Windows 10 version 2004 or higher:
I only tested it on Windows 11 24H2 but the flag for screen capture exclusion might not work on older versions.

## Make the AI hear:
You can intergrate whisper, adding the generated STT as context for each message, but it's not implemented, you're welcome to put in a pr.
