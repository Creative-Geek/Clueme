# ocr.py
import os
import sys
import numpy as np
from PIL import Image
import time # For timing OCR
import base64 # For Gemini image encoding
import io # For Gemini image encoding
from openai import OpenAI # Reused for Gemini

# --- Engine Selection ---
# Default to 'easyocr' if the env var is not set or invalid
OCR_ENGINE = os.getenv("OCR_ENGINE", "easyocr").lower()

# --- Conditional Imports and Initialization ---
ocr_reader = None
pytesseract_path_set = False
gemini_client = None # Client instance for Gemini

# --- Flags to track initialization status ---
_easyocr_initialized = False
_pytesseract_initialized = False
_gemini_initialized = False

# --- Environment Variable Checks ---
gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_base_url = os.getenv("GEMINI_BASE_URL")
# Default to gemini-pro-vision as it's known to be multimodal
gemini_ocr_model = os.getenv("GEMINI_OCR_MODEL", "gemini-pro-vision")
tesseract_cmd_path = os.getenv("TESSERACT_CMD", r'C:\Program Files\Tesseract-OCR\tesseract.exe')


# --- Engine Initialization Logic ---

# EasyOCR
if OCR_ENGINE == "easyocr":
    try:
        import easyocr
        print("OCR Engine: EasyOCR selected.")
    except ImportError:
        print("WARNING: EasyOCR library not found. Please install it (`pip install easyocr`).")
        print("Skipping EasyOCR initialization.")
        if OCR_ENGINE == "easyocr": # If it was the explicit choice, try others
             OCR_ENGINE = "pytesseract" # Try Pytesseract next
             print("Attempting fallback to Pytesseract...")
    except Exception as e:
        print(f"ERROR: Unknown error importing EasyOCR: {e}")
        if OCR_ENGINE == "easyocr":
             OCR_ENGINE = "pytesseract"
             print("Attempting fallback to Pytesseract...")

# Pytesseract
if OCR_ENGINE == "pytesseract":
    try:
        import pytesseract
        print(f"OCR Engine: Pytesseract selected (or fallback).")
        try:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_path
            pytesseract.get_tesseract_version() # Check if Tesseract is working
            _pytesseract_initialized = True
            print(f"Pytesseract command set to: {tesseract_cmd_path}")
        except FileNotFoundError:
            print(f"ERROR: Tesseract executable not found at '{tesseract_cmd_path}'.")
            print("Ensure Tesseract is installed and the path is correct or set TESSERACT_CMD env var.")
            if OCR_ENGINE == "pytesseract": # If it was the explicit choice or first fallback
                OCR_ENGINE = "gemini" # Try Gemini next
                print("Attempting fallback to Gemini...")
        except pytesseract.TesseractNotFoundError:
             print(f"ERROR: Tesseract is not installed or not in your PATH, or TESSERACT_CMD ('{tesseract_cmd_path}') is incorrect.")
             if OCR_ENGINE == "pytesseract":
                OCR_ENGINE = "gemini"
                print("Attempting fallback to Gemini...")
        except Exception as e:
             print(f"ERROR: Error initializing Pytesseract: {e}")
             if OCR_ENGINE == "pytesseract":
                OCR_ENGINE = "gemini"
                print("Attempting fallback to Gemini...")

    except ImportError:
        print("WARNING: Pytesseract library not found. Please install it (`pip install pytesseract`).")
        if OCR_ENGINE == "pytesseract": # If it was the explicit choice or first fallback
            OCR_ENGINE = "gemini" # Try Gemini next
            print("Attempting fallback to Gemini...")

# Gemini (Check happens here, initialization happens on first use)
if OCR_ENGINE == "gemini":
    print(f"OCR Engine: Gemini selected (or fallback). Model: {gemini_ocr_model}")
    if not gemini_api_key:
        print("ERROR: GEMINI_API_KEY environment variable not set. Cannot use Gemini.")
        # Decide on final fallback. If others failed, we might have no engine.
        # For simplicity, we'll let perform_ocr handle the final failure.
        # If you want to exit here if ALL fail: check if easyocr/pytesseract are usable.
    elif not gemini_base_url:
        print("ERROR: GEMINI_BASE_URL environment variable not set. Cannot use Gemini.")
    else:
        # We will initialize the client inside _ocr_with_gemini to avoid
        # unnecessary client creation if Gemini isn't actually used.
        print(f"Gemini configured with Base URL: {gemini_base_url}")


def _initialize_easyocr():
    """Initializes the EasyOCR reader if not already done."""
    global ocr_reader, _easyocr_initialized
    if _easyocr_initialized or OCR_ENGINE != "easyocr":
        return _easyocr_initialized

    if 'easyocr' not in sys.modules:
        print("ERROR: Cannot initialize EasyOCR, library not imported.")
        return False

    print("Initializing EasyOCR Reader (this may take a moment)...")
    try:
        ocr_reader = easyocr.Reader(['en'], gpu=True)
        print("EasyOCR Reader initialized with GPU.")
        _easyocr_initialized = True
    except Exception as e_gpu:
        print(f"EasyOCR GPU initialization failed ({e_gpu}), falling back to CPU...")
        try:
            ocr_reader = easyocr.Reader(['en'], gpu=False)
            print("EasyOCR Reader initialized with CPU.")
            _easyocr_initialized = True
        except Exception as e_cpu:
            print(f"FATAL: Failed to initialize EasyOCR Reader on CPU: {e_cpu}")
            ocr_reader = None
            _easyocr_initialized = False # Mark as failed

    return _easyocr_initialized

def _initialize_gemini():
    """Initializes the Gemini client using OpenAI SDK if not already done."""
    global gemini_client, _gemini_initialized
    if _gemini_initialized or OCR_ENGINE != "gemini":
        return _gemini_initialized

    if not gemini_api_key or not gemini_base_url:
         print("ERROR: Cannot initialize Gemini client. Missing API Key or Base URL.")
         return False

    print(f"Initializing Gemini client for model {gemini_ocr_model}...")
    try:
        gemini_client = OpenAI(
            api_key=gemini_api_key,
            base_url=gemini_base_url,
            # Add timeout configuration if needed
            # timeout=30.0,
            # max_retries=2,
        )
        # Optional: Perform a quick test call? (Could be slow/costly)
        # Maybe just assume it's okay for now.
        _gemini_initialized = True
        print("Gemini client initialized.")
    except Exception as e:
        print(f"ERROR: Failed to initialize Gemini client: {e}")
        gemini_client = None
        _gemini_initialized = False

    return _gemini_initialized


def _pil_to_base64(image_pil: Image.Image, format="PNG") -> str:
    """Converts a PIL image to a Base64 encoded string."""
    buffered = io.BytesIO()
    image_pil.save(buffered, format=format)
    img_byte = buffered.getvalue()
    img_base64 = base64.b64encode(img_byte).decode('utf-8')
    return img_base64


def _ocr_with_easyocr(image_pil: Image.Image) -> str | None:
    """Performs OCR using EasyOCR."""
    if not _initialize_easyocr():
         print("ERROR: EasyOCR not initialized.")
         return None
    if ocr_reader is None:
        print("ERROR: EasyOCR reader is not available.")
        return None

    try:
        start_time = time.time()
        image_np = np.array(image_pil)
        results = ocr_reader.readtext(image_np, detail=0, paragraph=True)
        text = "\n".join(results)
        end_time = time.time()
        print(f"EasyOCR completed in {end_time - start_time:.2f} seconds.")
        return text
    except Exception as e:
        print(f"Error during EasyOCR processing: {e}")
        return None

def _ocr_with_pytesseract(image_pil: Image.Image) -> str | None:
    """Performs OCR using Pytesseract."""
    if not _pytesseract_initialized:
        print("ERROR: Pytesseract not properly initialized.")
        return None
    try:
        start_time = time.time()
        text = pytesseract.image_to_string(image_pil)
        end_time = time.time()
        print(f"Pytesseract completed in {end_time - start_time:.2f} seconds.")
        return text
    except pytesseract.TesseractNotFoundError:
         print(f"ERROR: Tesseract not found during OCR. Path: {pytesseract.pytesseract.tesseract_cmd}")
         return None
    except Exception as e:
        print(f"Error during Pytesseract processing: {e}")
        return None

def _ocr_with_gemini(image_pil: Image.Image) -> str | None:
    """Performs OCR using Gemini via OpenAI-compatible endpoint."""
    if not _initialize_gemini():
        print("ERROR: Gemini client not initialized.")
        return None
    if gemini_client is None:
        print("ERROR: Gemini client is not available.")
        return None

    try:
        start_time = time.time()
        print("Encoding image for Gemini...")
        base64_image = _pil_to_base64(image_pil, format="PNG") # Use PNG or JPEG
        image_url = f"data:image/png;base64,{base64_image}"

        ocr_prompt = "Perform OCR on the following image. Extract all text exactly as it appears, preserving line breaks where possible. Output only the extracted text."

        print(f"Sending request to Gemini model: {gemini_ocr_model}...")
        response = gemini_client.chat.completions.create(
            model=gemini_ocr_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ocr_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        }
                    ]
                }
            ],
            # Add parameters like max_tokens if needed, though OCR might not benefit much
            # max_tokens=1024, # Example
            # temperature=0.1 # Low temp for deterministic OCR
        )

        text = response.choices[0].message.content
        end_time = time.time()
        print(f"Gemini OCR completed in {end_time - start_time:.2f} seconds.")
        # Clean up potential markdown/code blocks if the model adds them
        text = text.strip().removeprefix("```").removesuffix("```").strip()
        text = text.strip().removeprefix("```text").removesuffix("```").strip()
        return text

    except Exception as e:
        print(f"Error during Gemini OCR processing: {e}")
        # You might want more specific error handling here (e.g., for API errors)
        # from openai import APIError # Example
        # if isinstance(e, APIError):
        #     print(f"Gemini API Error: Status={e.status_code}, Message={e.message}")
        return None


def perform_ocr(image_pil: Image.Image) -> str | None:
    """
    Performs OCR on the given PIL Image using the engine specified by OCR_ENGINE.

    Args:
        image_pil: A PIL Image object.

    Returns:
        The extracted text as a string, or None if OCR fails.
    """
    print(f"--- Performing OCR using {OCR_ENGINE.upper()} ---") # Use selected engine
    if OCR_ENGINE == "easyocr":
        result = _ocr_with_easyocr(image_pil)
        if result is not None: return result
        print("EasyOCR failed. No automatic fallback implemented in perform_ocr.")
        # Or implement fallback here if desired
    elif OCR_ENGINE == "pytesseract":
        result = _ocr_with_pytesseract(image_pil)
        if result is not None: return result
        print("Pytesseract failed. No automatic fallback implemented in perform_ocr.")
    elif OCR_ENGINE == "gemini":
        result = _ocr_with_gemini(image_pil)
        if result is not None: return result
        print("Gemini failed. No automatic fallback implemented in perform_ocr.")
    else:
        print(f"ERROR: No valid OCR engine configured or initialized ('{OCR_ENGINE}').")

    # If we reach here, the chosen engine failed or no valid engine was set
    print("OCR failed for the selected engine.")
    return None


# Example usage (optional, for testing ocr.py directly)
if __name__ == "__main__":
    print(f"\nTesting OCR module with engine: {OCR_ENGINE.upper()}")
    if OCR_ENGINE == 'gemini' and (not gemini_api_key or not gemini_base_url):
        print("Skipping Gemini test due to missing API Key or Base URL in environment.")
    elif OCR_ENGINE == 'pytesseract' and not _pytesseract_initialized:
         print("Skipping Pytesseract test as it failed initialization.")
    else:
        try:
            from PIL import ImageGrab
            print("Grabbing test image (top-left 400x100)...")
            test_image = ImageGrab.grab(bbox=(0, 0, 400, 100))
            print("Running perform_ocr...")
            extracted_text = perform_ocr(test_image)
            if extracted_text:
                print("\n--- Test OCR Result ---")
                print(extracted_text[:300]) # Print first 300 chars
                print("-----------------------\n")
            else:
                print("\nTest OCR failed.\n")
        except ImportError:
             print("Could not import ImageGrab for test (maybe not on Windows/macOS with Xlib?). Skipping test grab.")
        except Exception as e:
            print(f"Error during test: {e}")