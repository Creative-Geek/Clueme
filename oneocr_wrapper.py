"""
OneOCR wrapper module for Windows native OCR.
Uses the oneocr library from https://github.com/AuroraWright/oneocr
"""
import os
import sys
from PIL import Image

# Required DLL files for OneOCR
REQUIRED_FILES = [
    "oneocr.dll",
    "oneocr.onemodel",
    "onnxruntime.dll"
]

# OneOCR config directory
CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.config', 'oneocr')


def check_oneocr_requirements() -> tuple[bool, list[str]]:
    """
    Check if all required DLL files for OneOCR are present.
    
    Returns:
        Tuple of (all_present: bool, missing_files: list[str])
    """
    missing_files = []
    
    if not os.path.exists(CONFIG_DIR):
        return False, REQUIRED_FILES
    
    for file in REQUIRED_FILES:
        file_path = os.path.join(CONFIG_DIR, file)
        if not os.path.exists(file_path):
            missing_files.append(file)
    
    return len(missing_files) == 0, missing_files


def get_missing_files_message(missing_files: list[str]) -> str:
    """
    Generate a user-friendly message about missing OneOCR files.
    
    Args:
        missing_files: List of missing file names
    
    Returns:
        Formatted error message with instructions
    """
    config_dir = CONFIG_DIR.replace(os.path.expanduser('~'), '%USERPROFILE%')
    
    message = f"""OneOCR is not properly configured.

The following required files are missing from {config_dir}:
{chr(10).join(f'  - {f}' for f in missing_files)}

To set up OneOCR:
1. Create the directory: {config_dir}
2. Download the required DLL files from the OneOCR releases
3. Place all three files in the directory above

Required files:
  - oneocr.dll (OneOCR library)
  - oneocr.onemodel (OCR model file)
  - onnxruntime.dll (ONNX Runtime library)

For more information, visit: https://github.com/AuroraWright/oneocr"""
    
    return message


# Global OCR engine instance
_ocr_engine = None
_initialization_error = None


def _initialize_ocr():
    """Initialize the OneOCR engine."""
    global _ocr_engine, _initialization_error
    
    if _ocr_engine is not None:
        return True
    
    if _initialization_error is not None:
        return False
    
    # Check for required files first
    all_present, missing_files = check_oneocr_requirements()
    if not all_present:
        _initialization_error = get_missing_files_message(missing_files)
        return False
    
    try:
        from oneocr import OcrEngine
        _ocr_engine = OcrEngine()
        return True
    except Exception as e:
        _initialization_error = f"Failed to initialize OneOCR: {str(e)}"
        return False


def get_initialization_error() -> str | None:
    """
    Get the initialization error message if OneOCR failed to initialize.
    
    Returns:
        Error message string or None if no error
    """
    return _initialization_error


def perform_ocr(image: Image.Image) -> str | None:
    """
    Perform OCR on a PIL Image using OneOCR.
    
    Args:
        image: PIL Image object to process
    
    Returns:
        Extracted text as string, or None if OCR failed
    """
    if not _initialize_ocr():
        print(f"OneOCR initialization failed: {_initialization_error}")
        return None
    
    try:
        result = _ocr_engine.recognize_pil(image)
        
        if 'error' in result:
            print(f"OneOCR error: {result['error']}")
            return None
        
        text = result.get('text', '')
        if not text:
            print("OneOCR returned empty text")
            return None
        
        return text
    except Exception as e:
        print(f"Error during OneOCR processing: {e}")
        return None


def is_available() -> bool:
    """
    Check if OneOCR is available and properly configured.
    
    Returns:
        True if OneOCR can be used, False otherwise
    """
    all_present, _ = check_oneocr_requirements()
    return all_present


# For testing
if __name__ == "__main__":
    print("Checking OneOCR requirements...")
    all_present, missing = check_oneocr_requirements()
    
    if all_present:
        print("All required files are present!")
        print(f"Config directory: {CONFIG_DIR}")
    else:
        print(get_missing_files_message(missing))
