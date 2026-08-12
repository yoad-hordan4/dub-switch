@echo off
REM Build DubSwitch.exe for Windows distribution.
REM Run this on a Windows machine inside the project directory.
REM Output: dist\DubSwitch\DubSwitch.exe

echo === DubSwitch - Windows Build ===

REM Create venv if needed
if not exist .venv (
    python -m venv .venv
)

.venv\Scripts\pip install --quiet --upgrade pip
.venv\Scripts\pip install --quiet -r requirements.txt
.venv\Scripts\pip install --quiet pyinstaller

echo Building .exe...
.venv\Scripts\pyinstaller ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --name "DubSwitch" ^
    --add-data "layout.py;." ^
    --add-data "input_source.py;." ^
    --hidden-import "pynput.keyboard._win32" ^
    --hidden-import "pynput.mouse._win32" ^
    --hidden-import "pystray" ^
    --hidden-import "PIL" ^
    app.py

echo.
echo Done! App is at: dist\DubSwitch\DubSwitch.exe
echo.
echo To distribute: zip the dist\DubSwitch folder and share it.
