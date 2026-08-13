#!/bin/bash
# Build DubSwitch.app for macOS distribution.
# Run this on a Mac inside the project directory.
# Output: dist/DubSwitch.app and DubSwitch.dmg
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

echo "=== DubSwitch — Mac Build ==="

# Create venv and install deps if needed
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"
"$VENV/bin/pip" install --quiet pyinstaller

echo "Building .app bundle..."
"$VENV/bin/pyinstaller" \
    --noconfirm \
    --onedir \
    --windowed \
    --name "DubSwitch" \
    --hidden-import "pynput.keyboard._darwin" \
    --hidden-import "pynput.mouse._darwin" \
    --hidden-import "rumps" \
    --icon "$SCRIPT_DIR/icon.icns" \
    "$SCRIPT_DIR/app.py"

echo "Signing app (ad-hoc)..."
codesign --force --deep --sign - "$SCRIPT_DIR/dist/DubSwitch.app"

echo "Creating DMG..."
# Clean up old DMG if it exists
rm -f "$SCRIPT_DIR/DubSwitch.dmg"

# Create a temporary directory for DMG contents
DMG_TMP="$SCRIPT_DIR/dist/dmg_tmp"
rm -rf "$DMG_TMP"
mkdir -p "$DMG_TMP"
cp -R "$SCRIPT_DIR/dist/DubSwitch.app" "$DMG_TMP/"
ln -s /Applications "$DMG_TMP/Applications"

# Create DMG
hdiutil create -volname "DubSwitch" \
    -srcfolder "$DMG_TMP" \
    -ov -format UDZO \
    "$SCRIPT_DIR/DubSwitch.dmg"

rm -rf "$DMG_TMP"

# Also create a zip with Install.command for users who prefer that
echo "Creating zip fallback..."
cp "$SCRIPT_DIR/Install.command" "$SCRIPT_DIR/dist/Install.command"
chmod +x "$SCRIPT_DIR/dist/Install.command"
cd "$SCRIPT_DIR/dist"
zip -r "$SCRIPT_DIR/DubSwitch-mac.zip" \
    DubSwitch.app \
    Install.command

echo ""
echo "Done!"
echo "  DMG: DubSwitch.dmg (drag to Applications)"
echo "  ZIP: DubSwitch-mac.zip (fallback)"
