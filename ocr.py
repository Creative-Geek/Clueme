import os
import sys
import time
import base64
import io
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

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
        print(f"Warning: .env file not found at {env_path}")
        print("Using default settings or environment variables")

# Load environment variables
load_env_settings()

# Engine Setting - Only Gemini supported in this version
OCR_ENGINE = "gemini"

# OCR Configuration
OCR_API_KEY = os.getenv("OCR_API_KEY")
OCR_BASE_URL = os.getenv("OCR_BASE_URL")
OCR_MODEL = os.getenv("OCR_MODEL", "gemini-2.5-flash")

# Log configuration
print(f"Base Directory: {get_base_dir()}")
print(f"OCR API Key: {'*' * 4 + OCR_API_KEY[-4:] if OCR_API_KEY else 'Not set'}")
print(f"OCR Base URL: {OCR_BASE_URL if OCR_BASE_URL else 'Not set'}")
print(f"OCR Model: {OCR_MODEL}")

# Client initialization
gemini_client = None
_gemini_initialized = False

def _initialize_gemini():
    """Initializes the Gemini client using OpenAI SDK if not already done."""
    global gemini_client, _gemini_initialized
    
    if _gemini_initialized:
        return _gemini_initialized
        
    if not OCR_API_KEY or not OCR_BASE_URL:
        print("ERROR: Cannot initialize Gemini client. Missing API Key or Base URL.")
        return False
        
    print(f"Initializing Gemini client for model {OCR_MODEL}...")
    try:
        gemini_client = OpenAI(
            api_key=OCR_API_KEY,
            base_url=OCR_BASE_URL,
        )
        _gemini_initialized = True
        print("Gemini client initialized.")
    except Exception as e:
        print(f"ERROR: Failed to initialize Gemini client: {e}")
        gemini_client = None
        _gemini_initialized = False
        
    return _gemini_initialized

def _pil_to_base64(image_pil: Image.Image, format="WEBP") -> str:
    """Converts a PIL image to a Base64 encoded string."""
    buffered = io.BytesIO()
    image_pil.save(buffered, format=format)
    img_byte = buffered.getvalue()
    img_base64 = base64.b64encode(img_byte).decode('utf-8')
    return img_base64

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
        
        print("Encoding image for Gemini (WEBP)...")
        base64_image = _pil_to_base64(image_pil, format="WEBP")
        image_url = f"data:image/webp;base64,{base64_image}"
        
        ocr_prompt = """
        Analyze the following image and determine if it contains a multiple-choice question (MCQ).
        Output a JSON object with the following structure:
        {
          "question_found": boolean, // true if an MCQ is found, false otherwise
          "question": "The extracted question text." | null, // null if question_found is false
          "choices": ["A) Choice A text with its number", "B) Choice B text with its number", ...] | null // null if question_found is false or choices aren't clear
        }
        The text is extracted via OCR so it may contain errors, fix those errors in the output.
        If there is code, include it in the question text.
        Only output the JSON object. Do not include any other text or explanations.
        Focus on identifying a clear question stem and distinct answer options (often labeled A, B, C, D or 1, 2, 3, 4).
        If no clear MCQ is present, set "question_found" to false.
        If there are multiple questions present, only return the first one.
        """
        
        print(f"Sending request to Gemini model: {OCR_MODEL}...")
        response = gemini_client.chat.completions.create(
            model=OCR_MODEL,
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
            response_format={"type": "json_object"}
        )
        text = response.choices[0].message.content
        end_time = time.time()
        print(f"Gemini OCR completed in {end_time - start_time:.2f} seconds.")
        
        if text is None: 
            return None  # Handle case where model returns nothing
            
        # Clean up any markdown code blocks the model might add
        text = text.strip().removeprefix("```").removesuffix("```").strip()
        text = text.strip().removeprefix("```text").removesuffix("```").strip()
        text = text.strip().removeprefix("```json").removesuffix("```").strip()
        return text
        
    except Exception as e:
        print(f"Error during Gemini OCR processing: {e}")
        return None

def perform_ocr(image_pil: Image.Image) -> str | None:
    """
    Performs OCR on the given PIL Image using Gemini Vision.
    """
    print(f"--- Performing OCR using Gemini Vision API ---")
    
    result = _ocr_with_gemini(image_pil)
    
    if result is None:
        print(f"OCR failed with Gemini Vision API.")
    
    return result

# Example usage (for testing ocr.py directly)
if __name__ == "__main__":
    print(f"\nTesting OCR module with Gemini Vision API")
    
    if not OCR_API_KEY or not OCR_BASE_URL:
        print("Skipping Gemini test due to missing API Key or Base URL in environment.")
    else:
        try:
            from PIL import ImageGrab
            print("Grabbing test image (top-left 400x100)...")
            test_image = ImageGrab.grab(bbox=(0, 0, 400, 100))
            print("Running perform_ocr...")
            extracted_text = perform_ocr(test_image)
            if extracted_text:
                print("\n--- Test OCR Result ---")
                print(extracted_text[:300])  # Print first 300 chars
                print("-----------------------\n")
            else:
                print("\nTest OCR failed.\n")
        except ImportError:
            print("Could not import ImageGrab for test. Skipping test grab.")
        except Exception as e:
            print(f"Error during test: {e}")