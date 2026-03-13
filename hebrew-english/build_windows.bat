@echo off
REM Build HebrewEnglishSwitcher.exe for Windows distribution.
REM Run this on a Windows machine inside the project directory.
REM Output: dist\HebrewEnglishSwitcher\HebrewEnglishSwitcher.exe

echo === Hebrew-English Switcher - Windows Build ===

REM Create venv if needed
if not exist .venv (
    python -m venv .venv
)

.venv\Scripts\pip install --quiet --upgrade pip
.venv\Scripts\pip install --quiet -r requirements.txt

echo Building .exe...
.venv\Scripts\pyinstaller ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --name "HebrewEnglishSwitcher" ^
    --add-data "layout.py;." ^
    --add-data "input_source.py;." ^
    --hidden-import "pynput.keyboard._win32" ^
    --hidden-import "pynput.mouse._win32" ^
    app.py

echo.
echo Done! App is at: dist\HebrewEnglishSwitcher\HebrewEnglishSwitcher.exe
echo.
echo To distribute: zip the dist\HebrewEnglishSwitcher folder and share it.
echo Users must run as Administrator on first launch so the keyboard hook works.
