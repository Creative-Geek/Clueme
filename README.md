# Clueme

<div align="center">
  
<img src="clueme.png" alt="Clueme Logo" width="500px">

</div>

A Windows application that provides AI assistance through keyboard shortcuts, designed to be invisible to screen recording software.

## Features

- Screen OCR using Gemini Vision (because tesseract and EasyOCR are not good enough)
- AI integration with OpenAI (or the many free compatible endpoints)
- Global keyboard shortcuts
- Stealth mode (invisible to screen recording)
- Modular architecture with separate AI processing component

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

## Architecture

The application is built with a modular architecture:
- `clueme.py`: Main application file handling UI and hotkey management
- `ai_processor.py`: Dedicated module for AI processing and OpenAI integration
- `ocr.py`: OCR functionality using Gemini Vision

## Note

The application uses Gemini Vision for OCR, which requires an internet connection to function.
