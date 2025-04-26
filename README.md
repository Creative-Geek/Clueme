# Stealth AI Assistant

A Windows application that provides AI assistance through keyboard shortcuts, designed to be invisible to screen recording software.

## Features
- Screen OCR using Tesseract
- AI integration with OpenAI (or compatible endpoints)
- Global keyboard shortcuts
- Stealth mode (invisible to screen recording)

## Setup
1. Install Python 3.8 or higher
2. Install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your configuration:
   ```
   OPENAI_API_KEY=your_api_key_here
   OPENAI_API_BASE=your_custom_endpoint_url  # Optional, defaults to OpenAI's endpoint
   OPENAI_MODEL=your_model_name  # Optional, defaults to gpt-3.5-turbo
   CAPTURE_HOTKEY=Ctrl+Alt+R  # Optional, defaults to Ctrl+Alt+R
   QUIT_HOTKEY=Ctrl+Alt+Q  # Optional, defaults to Ctrl+Alt+Q
   ```

## Usage
- Press the configured capture hotkey (default: `Ctrl+Alt+R`) to capture screen and get AI assistance
- Press the configured quit hotkey (default: `Ctrl+Alt+Q`) to close the application

## Hotkey Configuration
You can configure the hotkeys in the `.env` file using the following format:
- Modifiers: `Ctrl`, `Alt`, `Win`, `Shift`
- Keys: Any single key (e.g., `R`, `Q`, `F22`)
- Format: `Modifier1+Modifier2+Key` (e.g., `Ctrl+Alt+R`, `Win+Shift+F22`)

## Note
Make sure Tesseract OCR is installed and added to your system PATH. 