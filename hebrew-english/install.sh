#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PLIST="$HOME/Library/LaunchAgents/com.hebrewenglish.switcher.plist"

echo "=== Hebrew-English Switcher Installer ==="

# 1. Python check
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install it from https://www.python.org or via Homebrew: brew install python3"
    exit 1
fi

# 2. Create virtual environment
echo "Creating virtual environment..."
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"
echo "Dependencies installed."

# 3. Write launchd plist for auto-start on login
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hebrewenglish.switcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV/bin/python3</string>
        <string>$SCRIPT_DIR/app.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/switcher.log</string>
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/switcher.log</string>
</dict>
</plist>
EOF

# 4. Load the agent
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo ""
echo "✓ Installed and running!"
echo ""
echo "IMPORTANT: Grant Accessibility permission:"
echo "  System Settings → Privacy & Security → Accessibility"
echo "  Add Terminal (or the app running this script) to the list."
echo ""
echo "Shortcut: Ctrl + Shift + Space"
echo "  → Converts the last typed word/phrase between Hebrew and English."
echo ""
echo "To uninstall: run ./uninstall.sh"
