# Hebrew ↔ English Keyboard Switcher

Typed something in the wrong language? Press **Ctrl + 1** and it fixes itself — instantly, in any app.

---

## Download

👉 **[Go to Releases](https://github.com/yoad-hordan4/dub-switch/releases)** and download the file for your platform:

| Platform | File |
|----------|------|
| Mac | `HebrewEnglishSwitcher-mac.zip` |
| Windows | `HebrewEnglishSwitcher-windows.zip` |

---

## Install

### Mac
1. Unzip the downloaded file
2. Right-click `HebrewEnglishSwitcher.app` → **Open**
3. If macOS asks to confirm, click **Open** in the dialog that appears
4. Go to **System Settings → Privacy & Security → Accessibility** → click **+** → add `HebrewEnglishSwitcher`
5. The switcher is now running in the background

> To run automatically on login, drag the app to **System Settings → General → Login Items**.

### Windows
1. Unzip the downloaded folder
2. Right-click `HebrewEnglishSwitcher.exe` → **Run as administrator**
3. Windows may show a security prompt — click **Run anyway**
4. The switcher is now running in the background

---

## How to Use

Just type normally. When you realize you typed in the wrong language:

1. **Press Ctrl + 1**
2. The last word (or phrase) you typed is converted and replaced in-place
3. The keyboard language switches automatically

**Examples:**
- Typed `שלום` with English layout active? → press Ctrl+1 → becomes `shalom` ✓
- Typed `svmo` with Hebrew layout active? → press Ctrl+1 → becomes `שלום` ✓

**Notes:**
- Works in any app: browsers, Word, Notes, Slack, etc.
- The buffer resets after **5 seconds** of no typing (so only recent text is converted)
- Spaces are included, so full multi-word phrases can be converted at once

---

## How It Works

The app runs silently in the background, keeping a rolling buffer of your recent keystrokes. When you press Ctrl+1, it detects whether the buffered text is Hebrew or English, maps each character through a Hebrew↔QWERTY layout table, deletes the original text, and pastes the converted version. It then switches the OS keyboard input language automatically so your next keystroke is in the right layout.

---

## Build from Source

Requires Python 3.10+.

```bash
git clone https://github.com/yoad-hordan4/dub-switch.git
cd dub-switch/hebrew-english

# Mac
./build_mac.sh

# Windows
build_windows.bat
```

Output is in the `dist/` folder.

---

## Files

| File | Description |
|------|-------------|
| `app.py` | Main app — keyboard listener, buffer, conversion trigger |
| `layout.py` | Hebrew↔English character mapping table |
| `input_source.py` | OS language switching (Mac TIS API / Windows user32) |
| `build_mac.sh` | PyInstaller build script for Mac |
| `build_windows.bat` | PyInstaller build script for Windows |
