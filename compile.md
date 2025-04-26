# Clueme Compilation Guide

## PyInstaller Compilation Command

```bash
pyinstaller --onefile --noconsole --icon=clueme.ico --name=clueme --add-data ".env;." --exclude-module PyQt5 --exclude-module PyQt6 clueme.py
```

## Command Breakdown

- `--onefile`: Creates a single executable file
- `--noconsole`: Creates a windowed application (no console window)
- `--icon=clueme.ico`: Uses the application icon
- `--name=clueme`: Names the output executable
- `--add-data ".env;."`: Includes the .env file (Windows path separator)
- `--exclude-module PyQt5`: Excludes PyQt5 to avoid conflicts
- `--exclude-module PyQt6`: Excludes PyQt6 to avoid conflicts

## Prerequisites

1. Install PyInstaller:
```bash
pip install pyinstaller
```

2. Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

## Notes

- The compilation process may take several minutes
- The resulting executable will be in the `dist` directory
- The executable will be self-contained and ready to distribute
- The application will run without a console window 