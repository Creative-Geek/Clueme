# ocr.py
import os
import sys
import numpy as np
from PIL import Image
import time # For timing OCR
import base64 # For Gemini image encoding
import io # For Gemini image encoding
from openai import OpenAI # Reused for Gemini

# --- Function to check if running as frozen executable ---
def is_frozen():
    return getattr(sys, 'frozen', False)

# --- Get base directory depending on frozen status ---
if is_frozen():
    # Path when running from compiled executable (Nuitka)
    # sys.executable is the path to the executable itself
    _base_dir = os.path.dirname(sys.executable)
    print(f"Running frozen. Base directory: {_base_dir}")
else:
    # Path when running as a normal script
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Running as script. Base directory: {_base_dir}")

# --- Engine Selection ---
OCR_ENGINE = os.getenv("OCR_ENGINE", "easyocr").lower()

# --- Tesseract Specific Paths ---
_bundled_tesseract_path = None
_bundled_tessdata_path = None
_pytesseract_initialized = False # Reset flag

# --- Conditional Imports and Initialization ---
ocr_reader = None
gemini_client = None
_easyocr_initialized = False
_gemini_initialized = False # Note: _pytesseract_initialized moved down

# --- Environment Variable Checks (Keep others as before) ---
gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_base_url = os.getenv("GEMINI_BASE_URL")
gemini_ocr_model = os.getenv("GEMINI_OCR_MODEL", "gemini-pro-vision")
# TESSERACT_CMD is now primarily a fallback for non-frozen execution
tesseract_cmd_from_env = os.getenv("TESSERACT_CMD")

# --- Engine Initialization Logic ---

# --- Pytesseract Initialization (Moved Up and Modified) ---
# We need pytesseract imported before we try to set its command path
try:
    import pytesseract
    _pytesseract_imported = True
except ImportError:
    _pytesseract_imported = False
    if OCR_ENGINE == "pytesseract":
        print("WARNING: Pytesseract selected but library not found. Install (`pip install pytesseract`).")
        # Attempt fallback if Pytesseract was the primary choice
        OCR_ENGINE = "easyocr" # Or gemini, depending on preference
        print(f"Attempting fallback to {OCR_ENGINE}...")

# Now, attempt to configure Pytesseract path if the library was imported
if _pytesseract_imported:
    tesseract_cmd_to_set = None
    tessdata_prefix_to_set = None

    if is_frozen():
        # Construct paths relative to the executable for the bundled version
        _bundled_tesseract_dir = os.path.join(_base_dir, "tesseract_bundle")
        _bundled_tesseract_path = os.path.join(_bundled_tesseract_dir, "tesseract.exe") # Assuming Windows .exe
        _bundled_tessdata_path = os.path.join(_bundled_tesseract_dir, "tessdata")

        print(f"Frozen mode: Attempting to use bundled Tesseract at '{_bundled_tesseract_path}'")
        print(f"Frozen mode: Setting TESSDATA_PREFIX to '{_bundled_tessdata_path}'")

        # Check if the bundled executable actually exists before setting
        if os.path.exists(_bundled_tesseract_path):
            tesseract_cmd_to_set = _bundled_tesseract_path
            # Set TESSDATA_PREFIX ONLY if we found the bundled exe
            tessdata_prefix_to_set = _bundled_tessdata_path
        else:
            print(f"WARNING: Bundled tesseract.exe not found at '{_bundled_tesseract_path}'. Pytesseract might fail.")
            # Optionally fallback to env var even when frozen? Or just let it fail?
            # if tesseract_cmd_from_env:
            #    print("Falling back to TESSERACT_CMD env var even though frozen.")
            #    tesseract_cmd_to_set = tesseract_cmd_from_env
            # else:
            #    print("No fallback Tesseract path found.")

    else:
        # Not frozen: Use environment variable or let Pytesseract search PATH
        if tesseract_cmd_from_env:
            print(f"Script mode: Using Tesseract path from TESSERACT_CMD: '{tesseract_cmd_from_env}'")
            tesseract_cmd_to_set = tesseract_cmd_from_env
        else:
            # If no env var, don't set pytesseract.tesseract_cmd explicitly.
            # Let pytesseract try to find it in PATH. Check will happen later.
            print("Script mode: TESSERACT_CMD not set. Pytesseract will search PATH.")
            # We can still try a default common path as a last resort
            default_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if os.path.exists(default_path):
                 print(f"Script mode: Found Tesseract at default location: {default_path}")
                 tesseract_cmd_to_set = default_path


    # --- Actually set the command and environment variable ---
    initialization_successful = False
    if tesseract_cmd_to_set:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_to_set
        if tessdata_prefix_to_set:
            # Set environment variable for the current process
            os.environ['TESSDATA_PREFIX'] = tessdata_prefix_to_set
            print(f"Runtime TESSDATA_PREFIX set to: {os.environ['TESSDATA_PREFIX']}") # Verify
        try:
            # Check if Tesseract is actually working with the set path/prefix
            version = pytesseract.get_tesseract_version()
            print(f"Pytesseract configured successfully. Path: '{tesseract_cmd_to_set}', Version: {version}")
            initialization_successful = True
        except pytesseract.TesseractNotFoundError:
            print(f"ERROR: Tesseract not found or not working at '{tesseract_cmd_to_set}'. Check path and TESSDATA_PREFIX.")
        except Exception as e:
            print(f"ERROR: Unknown error initializing Pytesseract with path '{tesseract_cmd_to_set}': {e}")
    else:
        # No specific path was set (e.g., not frozen, no env var, no default found)
        # Try checking if Pytesseract can find it in PATH
        print("No explicit Tesseract path set, checking PATH...")
        try:
            version = pytesseract.get_tesseract_version()
            print(f"Pytesseract found Tesseract in PATH. Version: {version}")
            initialization_successful = True
        except pytesseract.TesseractNotFoundError:
            print("ERROR: Tesseract not found in system PATH.")
        except Exception as e:
            print(f"ERROR: Unknown error checking Tesseract in PATH: {e}")

    _pytesseract_initialized = initialization_successful # Set the flag based on success

    # Handle fallback if Pytesseract init failed *and* it was the chosen engine
    if not _pytesseract_initialized and OCR_ENGINE == "pytesseract":
        print("Pytesseract initialization failed.")
        # Decide fallback order (e.g., EasyOCR then Gemini)
        try:
            import easyocr # Check if available for fallback
            OCR_ENGINE = "easyocr"
            print("Attempting fallback to EasyOCR...")
        except ImportError:
            if gemini_api_key and gemini_base_url: # Check if Gemini is possible fallback
                 OCR_ENGINE = "gemini"
                 print("Attempting fallback to Gemini...")
            else:
                 print("ERROR: No usable fallback OCR engine found.")
                 # Potentially exit or raise an error here if OCR is critical

# --- EasyOCR Initialization ---
if OCR_ENGINE == "easyocr":
    try:
        # Check import again in case it wasn't the initial choice
        if 'easyocr' not in sys.modules:
             import easyocr
        print("OCR Engine: EasyOCR selected.")
        # Initialization happens lazily in _initialize_easyocr
    except ImportError:
        print("WARNING: EasyOCR library not found. Cannot use as primary or fallback.")
        if OCR_ENGINE == "easyocr": # If it became the engine choice after fallback
             if _pytesseract_imported and _pytesseract_initialized: # Check if others are usable
                 OCR_ENGINE = "pytesseract"
                 print("EasyOCR failed, falling back to initialized Pytesseract")
             elif gemini_api_key and gemini_base_url:
                 OCR_ENGINE = "gemini"
                 print("EasyOCR failed, falling back to Gemini")
             else:
                 print("ERROR: No usable OCR engine found after EasyOCR failure.")

# --- Gemini Initialization Check ---
if OCR_ENGINE == "gemini":
    print(f"OCR Engine: Gemini selected (or fallback). Model: {gemini_ocr_model}")
    if not gemini_api_key or not gemini_base_url:
        print("ERROR: Gemini selected but requires GEMINI_API_KEY and GEMINI_BASE_URL.")
        if OCR_ENGINE == "gemini": # If it became the engine choice after fallback
             if _pytesseract_imported and _pytesseract_initialized:
                 OCR_ENGINE = "pytesseract"
                 print("Gemini config failed, falling back to initialized Pytesseract")
             elif 'easyocr' in sys.modules: # Check if EasyOCR is importable
                 OCR_ENGINE = "easyocr"
                 print("Gemini config failed, falling back to EasyOCR")
             else:
                 print("ERROR: No usable OCR engine found after Gemini failure.")
    else:
        print(f"Gemini configured. Base URL: {gemini_base_url}")
        # Initialization happens lazily


# --- Lazy Initializer Functions (Keep _initialize_easyocr, _initialize_gemini as before) ---
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
            _easyocr_initialized = False
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
        )
        _gemini_initialized = True
        print("Gemini client initialized.")
    except Exception as e:
        print(f"ERROR: Failed to initialize Gemini client: {e}")
        gemini_client = None
        _gemini_initialized = False
    return _gemini_initialized


# --- Helper Functions (Keep _pil_to_base64 as before) ---
def _pil_to_base64(image_pil: Image.Image, format="WEBP") -> str:
    """Converts a PIL image to a Base64 encoded string."""
    buffered = io.BytesIO()
    image_pil.save(buffered, format=format)
    img_byte = buffered.getvalue()
    img_base64 = base64.b64encode(img_byte).decode('utf-8')
    return img_base64


# --- OCR Implementation Functions (Keep _ocr_with_easyocr, _ocr_with_gemini mostly same) ---
# --- _ocr_with_pytesseract slightly adapted ---

def _ocr_with_easyocr(image_pil: Image.Image) -> str | None:
    """Performs OCR using EasyOCR."""
    if not _initialize_easyocr():
         print("ERROR: EasyOCR not initialized.")
         return None
    # ... (rest of function is same)
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
    # Use the flag set during the initial configuration attempt
    if not _pytesseract_initialized:
        print("ERROR: Pytesseract not properly initialized or available.")
        return None
    # We assume pytesseract.tesseract_cmd and TESSDATA_PREFIX (if needed)
    # have already been set correctly during the initial setup phase.
    try:
        start_time = time.time()
        print(f"Calling pytesseract.image_to_string (using path: {pytesseract.pytesseract.tesseract_cmd})")
        text = pytesseract.image_to_string(image_pil)
        end_time = time.time()
        print(f"Pytesseract completed in {end_time - start_time:.2f} seconds.")
        return text
    # Catch errors *during execution*, init errors were caught earlier
    except pytesseract.TesseractNotFoundError:
         # This might still happen if init said OK but it fails later? Unlikely but possible.
         print(f"ERROR: TesseractNotFoundError during OCR call, despite initialization check. Path: {pytesseract.pytesseract.tesseract_cmd}")
         return None
    except Exception as e:
        print(f"Error during Pytesseract processing: {e}")
        return None

def _ocr_with_gemini(image_pil: Image.Image) -> str | None:
    """Performs OCR using Gemini via OpenAI-compatible endpoint."""
    if not _initialize_gemini():
        print("ERROR: Gemini client not initialized.")
        return None
    # ... (rest of function mostly same, maybe add check for initialized client)
    if gemini_client is None:
        print("ERROR: Gemini client is not available.")
        return None
    try:
        start_time = time.time()
        # Optional: Save input image for debugging Gemini
        # save_path = "gemini_ocr_input.webp"
        # try: image_pil.save(save_path, format="WEBP")
        # except Exception as save_e: print(f"Warning: Could not save review image: {save_e}")

        print("Encoding image for Gemini (WEBP)...")
        base64_image = _pil_to_base64(image_pil, format="WEBP")
        image_url = f"data:image/webp;base64,{base64_image}"

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
            ]
        )
        text = response.choices[0].message.content
        end_time = time.time()
        print(f"Gemini OCR completed in {end_time - start_time:.2f} seconds.")
        if text is None: return None # Handle case where model returns nothing
        text = text.strip().removeprefix("```").removesuffix("```").strip()
        text = text.strip().removeprefix("```text").removesuffix("```").strip()
        return text
    except Exception as e:
        print(f"Error during Gemini OCR processing: {e}")
        return None


# --- Main OCR Function (Keep as before) ---
def perform_ocr(image_pil: Image.Image) -> str | None:
    """
    Performs OCR on the given PIL Image using the engine specified by OCR_ENGINE.
    """
    # Ensure the correct engine determined after fallbacks is used
    effective_engine = OCR_ENGINE.lower()
    print(f"--- Performing OCR using effective engine: {effective_engine.upper()} ---")

    result = None
    if effective_engine == "easyocr":
        result = _ocr_with_easyocr(image_pil)
    elif effective_engine == "pytesseract":
        result = _ocr_with_pytesseract(image_pil)
    elif effective_engine == "gemini":
        result = _ocr_with_gemini(image_pil)
    else:
        print(f"ERROR: No valid OCR engine configured or initialized ('{effective_engine}').")

    if result is None:
        print(f"OCR failed for the selected engine ({effective_engine.upper()}).")
    return result


# Example usage (optional, for testing ocr.py directly)
# Keep __main__ block as it was
if __name__ == "__main__":
    print(f"\nTesting OCR module with effective engine: {OCR_ENGINE.upper()}")
    # ... (rest of test logic) ...
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