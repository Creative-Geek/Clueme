# Clueme Compilation Guide

## Optimized Nuitka Compilation Command

```bash
python -m nuitka --onefile --windows-icon-from-ico=clueme.ico --windows-company-name="Clueme" --windows-product-name="Clueme" --windows-file-version="1.0.0" --windows-product-version="1.0.0" --enable-plugin=pyside6 --include-module=PIL.Image --include-module=PIL.ImageGrab --include-package=dotenv --include-package=openai --include-package=global_hotkeys --include-data-file=.env=.env clueme.py
```

## Command Breakdown

- `--onefile`: Creates a single executable file
- `--windows-icon-from-ico=clueme.ico`: Uses the application icon
- `--windows-company-name="Clueme"`: Sets company name in file properties
- `--windows-product-name="Clueme"`: Sets product name in file properties
- `--windows-file-version="1.0.0"`: Sets file version
- `--windows-product-version="1.0.0"`: Sets product version
- `--enable-plugin=pyside6`: Enables PySide6 support
- `--include-module=PIL.Image`: Includes only the PIL Image module
- `--include-module=PIL.ImageGrab`: Includes only the PIL ImageGrab module
- `--include-package=dotenv`: Includes python-dotenv for .env loading
- `--include-package=openai`: Includes OpenAI package
- `--include-package=global_hotkeys`: Includes global_hotkeys package
- `--include-data-file=.env=.env`: Includes the .env file in the executable
- `clueme.py`: The main script to compile

## Prerequisites

1. Install Nuitka:
```bash
pip install nuitka
```

2. Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

## Notes

- The compilation process may take several minutes
- The resulting executable will be in the same directory
- The executable will be self-contained and ready to distribute
- Using `--include-module` instead of `--include-package` for PIL significantly reduces the final size
- Only the necessary PIL components (Image and ImageGrab) are included 