# Clueme

<div align="center">
  
![Clueme Logo](clueme.png)

</div>

A Windows application that provides AI assistance through keyboard shortcuts, designed to be invisible to screen recording software.

## Features

- Screen OCR using Gemini Vision
- AI integration with OpenAI (or compatible endpoints)
- Global keyboard shortcuts
- Stealth mode (invisible to screen recording)
- Modular architecture with separate AI processing component

## Setup

1. Install Python 3.8 or higher
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your configuration:
   ```
   OPENAI_API_KEY=your_api_key_here
   OPENAI_API_BASE=your_custom_endpoint_url  # Optional, defaults to OpenAI's endpoint
   SMARTER_MODEL_API_BASE=your_smarter_model_endpoint_url  # Optional, defaults to same as OPENAI_API_BASE
   SMARTER_MODEL=your_smarter_model_name  # Optional, defaults to gpt-4
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
