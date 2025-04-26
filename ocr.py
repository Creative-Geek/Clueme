# ocr.py
import os
import sys
import numpy as np
from PIL import Image
import time # For timing OCR

# --- Engine Selection ---
# Default to 'easyocr' if the env var is not set or invalid
OCR_ENGINE = os.getenv("OCR_ENGINE", "easyocr").lower()

# --- Conditional Imports and Initialization ---
ocr_reader = None
pytesseract_path_set = False
_easyocr_initialized = False
_pytesseract_initialized = False

# Only import and initialize the selected engine to save resources
if OCR_ENGINE == "easyocr":
    try:
        import easyocr
        print("OCR Engine: EasyOCR selected.")
    except ImportError:
        print("ERROR: EasyOCR library not found. Please install it (`pip install easyocr`).")
        print("Falling back to Pytesseract if available.")
        OCR_ENGINE = "pytesseract" # Fallback
    except Exception as e:
        print(f"ERROR: Unknown error importing EasyOCR: {e}")
        print("Falling back to Pytesseract if available.")
        OCR_ENGINE = "pytesseract" # Fallback

if OCR_ENGINE == "pytesseract":
    try:
        import pytesseract
        print(f"OCR Engine: Pytesseract selected (or fallback).")
        # Attempt to set the command path immediately if using pytesseract
        tesseract_cmd_path = os.getenv("TESSERACT_CMD", r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        try:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_path
            # Check if Tesseract is actually working
            pytesseract.get_tesseract_version()
            pytesseract_path_set = True
            _pytesseract_initialized = True # Mark as initialized
            print(f"Pytesseract command set to: {tesseract_cmd_path}")
        except FileNotFoundError:
            print(f"ERROR: Tesseract executable not found at '{tesseract_cmd_path}'.")
            print("Ensure Tesseract is installed and the path is correct or set TESSERACT_CMD env var.")
            if 'easyocr' not in sys.modules: # If EasyOCR also failed
                 print("FATAL: No usable OCR engine found.")
                 # sys.exit(1) # Or handle this more gracefully in the main app
        except pytesseract.TesseractNotFoundError:
             print(f"ERROR: Tesseract is not installed or not in your PATH, or TESSERACT_CMD ('{tesseract_cmd_path}') is incorrect.")
             if 'easyocr' not in sys.modules:
                 print("FATAL: No usable OCR engine found.")
                 # sys.exit(1)
        except Exception as e:
             print(f"ERROR: Error initializing Pytesseract: {e}")
             if 'easyocr' not in sys.modules:
                 print("FATAL: No usable OCR engine found.")
                 # sys.exit(1)

    except ImportError:
        print("ERROR: Pytesseract library not found. Please install it (`pip install pytesseract`).")
        if OCR_ENGINE == "pytesseract": # Only fatal if it was the primary choice or only fallback
             print("FATAL: Pytesseract selected/fallback but not installed.")
             # sys.exit(1)


def _initialize_easyocr():
    """Initializes the EasyOCR reader."""
    global ocr_reader, _easyocr_initialized
    if _easyocr_initialized:
        return True

    if 'easyocr' not in sys.modules:
        print("ERROR: Cannot initialize EasyOCR, library not imported.")
        return False

    print("Initializing EasyOCR Reader (this may take a moment)...")
    try:
        # Try with GPU first
        ocr_reader = easyocr.Reader(['en'], gpu=True)
        print("EasyOCR Reader initialized with GPU.")
        _easyocr_initialized = True
        return True
    except Exception as e_gpu:
        print(f"EasyOCR GPU initialization failed ({e_gpu}), falling back to CPU...")
        try:
            ocr_reader = easyocr.Reader(['en'], gpu=False)
            print("EasyOCR Reader initialized with CPU.")
            _easyocr_initialized = True
            return True
        except Exception as e_cpu:
            print(f"FATAL: Failed to initialize EasyOCR Reader on CPU: {e_cpu}")
            ocr_reader = None # Ensure reader is None if failed
            return False

def _ocr_with_easyocr(image_pil: Image.Image) -> str | None:
    """Performs OCR using EasyOCR."""
    global ocr_reader
    if not _initialize_easyocr(): # Initialize on first use if needed
         return None
    if ocr_reader is None:
        print("ERROR: EasyOCR reader is not available.")
        return None

    try:
        start_time = time.time()
        # Convert PIL Image to NumPy array
        image_np = np.array(image_pil)
        # Perform OCR
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
    if not _pytesseract_initialized: # Check if initialized correctly earlier
        print("ERROR: Pytesseract not properly initialized.")
        return None
    try:
        start_time = time.time()
        text = pytesseract.image_to_string(image_pil)
        end_time = time.time()
        print(f"Pytesseract completed in {end_time - start_time:.2f} seconds.")
        return text
    except pytesseract.TesseractNotFoundError:
         # This error *should* have been caught during init, but check again
         print(f"ERROR: Tesseract not found during OCR. Path: {pytesseract.pytesseract.tesseract_cmd}")
         return None
    except Exception as e:
        print(f"Error during Pytesseract processing: {e}")
        return None

def perform_ocr(image_pil: Image.Image) -> str | None:
    """
    Performs OCR on the given PIL Image using the engine specified by OCR_ENGINE.

    Args:
        image_pil: A PIL Image object.

    Returns:
        The extracted text as a string, or None if OCR fails.
    """
    print(f"--- Performing OCR using {OCR_ENGINE} ---")
    if OCR_ENGINE == "easyocr":
        return _ocr_with_easyocr(image_pil)
    elif OCR_ENGINE == "pytesseract":
        return _ocr_with_pytesseract(image_pil)
    else:
        print(f"ERROR: Invalid OCR_ENGINE '{OCR_ENGINE}' specified.")
        # Maybe default to one? Or just fail.
        # Let's try easyocr as a last resort if available
        if 'easyocr' in sys.modules:
             print("Attempting fallback to EasyOCR...")
             return _ocr_with_easyocr(image_pil)
        elif 'pytesseract' in sys.modules and _pytesseract_initialized:
             print("Attempting fallback to Pytesseract...")
             return _ocr_with_pytesseract(image_pil)
        else:
             print("ERROR: No valid OCR engine available.")
             return None

# Example usage (optional, for testing ocr.py directly)
if __name__ == "__main__":
    print(f"Testing OCR module with engine: {OCR_ENGINE}")
    # Try grabbing a small part of the screen for a quick test
    try:
        from PIL import ImageGrab
        # Grab a small top-left region
        test_image = ImageGrab.grab(bbox=(0, 0, 400, 100))
        print("Grabbed test image.")
        extracted_text = perform_ocr(test_image)
        if extracted_text:
            print("\n--- Test OCR Result ---")
            print(extracted_text[:300]) # Print first 300 chars
            print("-----------------------\n")
        else:
            print("\nTest OCR failed.\n")
    except Exception as e:
        print(f"Error during test: {e}")