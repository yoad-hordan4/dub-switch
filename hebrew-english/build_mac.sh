#!/bin/bash
# Build HebrewEnglishSwitcher.app for macOS distribution.
# Run this on a Mac inside the project directory.
# Output: dist/HebrewEnglishSwitcher.app
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

echo "=== Hebrew-English Switcher — Mac Build ==="

# Create venv and install deps if needed
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"
# pyobjc-framework-Quartz is required for Mac event suppression
"$VENV/bin/pip" install --quiet pyobjc-framework-Quartz

echo "Building .app bundle..."
"$VENV/bin/pyinstaller" \
    --noconfirm \
    --onedir \
    --windowed \
    --name "HebrewEnglishSwitcher" \
    --add-data "layout.py:." \
    --add-data "input_source.py:." \
    --hidden-import "pynput.keyboard._darwin" \
    --hidden-import "pynput.mouse._darwin" \
    "$SCRIPT_DIR/app.py"

echo "Signing app (ad-hoc)..."
codesign --force --deep --sign - "$SCRIPT_DIR/dist/HebrewEnglishSwitcher.app"

echo ""
echo "Done! App is at: dist/HebrewEnglishSwitcher.app"
echo ""
echo "To distribute: zip the .app and share it."
echo "Users must grant Accessibility permission on first run:"
echo "  System Settings → Privacy & Security → Accessibility"
