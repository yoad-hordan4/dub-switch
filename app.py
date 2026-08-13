#!qודרqנןמqקמה פטאיםמ3
#!/usr/bin/env python3
"""
Hebrew-English keyboard switcher.
Listens globally for keystrokes, buffers them, and on Ctrl+1
converts the last typed word/phrase between Hebrew and English layouts.

Mac:     requires Accessibility permission (System Settings > Privacy > Accessibility).
Windows: run as administrator (or grant Accessibility via UAC prompt).
"""

import sys
import time
import threading
import multiprocessing
import subprocess
from pynput import keyboard
from pynput.keyboard import Key, KeyCode, Controller as _Controller
from layout import convert_text, detect_language
from input_source import detect_hebrew_and_english, switch_to

_IS_MAC = sys.platform == 'darwin'

if _IS_MAC:
    from Quartz import (kCGEventKeyDown, CGEventGetFlags,
                        CGEventGetIntegerValueField, kCGKeyboardEventKeycode)

# ── Trigger key ────────────────────────────────────────────────────────────────
# Ctrl+; mapped to the US-English semicolon key on the physical keyboard.
# This is deliberately detected by physical keycode/virtual key rather than the
# visible character, so it works the same in Hebrew and English layouts.
# On Mac we intercept and SUPPRESS this combo so it never reaches the active
# text field.  On Windows Ctrl+; usually doesn't produce visible characters in
# most apps, so suppression is not needed.
_TRIGGER_KEYCODE = 41       # ';' key hardware keycode on a US Mac keyboard
_TRIGGER_VK = 186           # VK for ';' on a US Windows keyboard
_CTRL_MASK  = 0x40000       # kCGEventFlagMaskControl (Mac)

if _IS_MAC:
    def _trigger_intercept(event_type, event):
        """Suppress Ctrl+; so it doesn't reach the focused app (Mac only)."""
        if event_type == kCGEventKeyDown:
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            flags   = CGEventGetFlags(event)
            if keycode == _TRIGGER_KEYCODE and (flags & _CTRL_MASK):
                return None   # suppress
        return event

# How long a pause (seconds) resets the buffer
IDLE_RESET_SECONDS = 5

# ── Input source IDs (auto-detected at startup) ───────────────────────────────
_hebrew_source, _english_source = detect_hebrew_and_english()

# ── Buffer state ──────────────────────────────────────────────────────────────
is_typing = False
buffer = []
buffer_lock = threading.Lock()
_conversion_lock = threading.Lock()
pressed_keys = set()
_reset_timer = None
_caps_lock_pending = False   # True if last reset was caps_lock with no typing since


def reset_buffer():
    global buffer
    with buffer_lock:
        buffer = []


def schedule_idle_reset():
    global _reset_timer
    if _reset_timer:
        _reset_timer.cancel()
    _reset_timer = threading.Timer(IDLE_RESET_SECONDS, reset_buffer)
    _reset_timer.daemon = True
    _reset_timer.start()


# ── Injection worker ──────────────────────────────────────────────────────────
# Deletes the last n characters and pastes the converted text.
# On Mac: uses osascript (System Events) which bypasses CGEventTap.
# On Windows: uses pynput Controller; is_typing flag prevents re-buffering.
def _inject_worker(n, converted):
    """Delete n chars then paste the converted text."""
    import time as t

    if _IS_MAC:
        # Use osascript + pbcopy/pbpaste — reliable across all Mac app types.
        # The forked child has no CGEventTap, so events flow cleanly.
        old_clip = subprocess.run(['pbpaste'], capture_output=True).stdout
        proc = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        proc.communicate(converted.encode('utf-8'))

        # Select n chars left (Shift+Left Arrow) then paste over selection.
        # This avoids field-hopping that can happen when backspace empties a field.
        select_script = '\n'.join(['    key code 123 using shift down', '    delay 0.02'] * n)
        script = f'''tell application "System Events"
    delay 0.05
{select_script}
    delay 0.05
    key code 9 using command down
    delay 0.1
end tell'''
        subprocess.run(['osascript', '-e', script])

        proc2 = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        proc2.communicate(old_clip)
    else:
        # Windows: pynput Controller (no CGEventTap on Windows)
        import pyperclip
        from pynput.keyboard import Controller as Ctrl, Key as K
        ctrl = Ctrl()
        old_clip = pyperclip.paste()
        pyperclip.copy(converted)
        t.sleep(0.05)
        for _ in range(n):
            ctrl.press(K.shift)
            ctrl.press(K.left)
            ctrl.release(K.left)
            ctrl.release(K.shift)
            t.sleep(0.02)
        t.sleep(0.05)
        ctrl.press(K.ctrl_l)
        ctrl.press('v')
        ctrl.release('v')
        ctrl.release(K.ctrl_l)
        t.sleep(0.1)
        pyperclip.copy(old_clip)


# ── Selection injection worker (Mac) ─────────────────────────────────────────
def _inject_selection_worker(converted, old_clip_bytes):
    """Paste converted text over the current selection (Mac only)."""
    proc = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    proc.communicate(converted.encode('utf-8'))
    script = '''tell application "System Events"
    delay 0.05
    key code 9 using command down
    delay 0.1
end tell'''
    subprocess.run(['osascript', '-e', script])
    proc2 = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    proc2.communicate(old_clip_bytes)


# ── Trigger logic ─────────────────────────────────────────────────────────────
def do_conversion():
    global buffer, is_typing
    if not _conversion_lock.acquire(blocking=False):
        return  # another conversion is already running
    try:
        is_typing = True  # block buffering of Cmd+C / Ctrl+C keystrokes

        # Wait for Ctrl to be physically released before injecting
        deadline = time.time() + 2.0
        while time.time() < deadline:
            if not (Key.ctrl_l in pressed_keys or Key.ctrl_r in pressed_keys):
                break
            time.sleep(0.02)
        time.sleep(0.08)

        # ── Try selection-based conversion (Mac only) ──────────────────────
        selected_text  = None
        old_clip_bytes = b''

        if _IS_MAC:
            old_clip_bytes = subprocess.run(['pbpaste'], capture_output=True).stdout
            from pynput.keyboard import KeyCode as _KC
            _kc = _Controller()
            _kc.press(Key.cmd)
            _kc.press(_KC(vk=8))
            _kc.release(_KC(vk=8))
            _kc.release(Key.cmd)
            time.sleep(0.20)
            new_clip_bytes = subprocess.run(['pbpaste'], capture_output=True).stdout
            if new_clip_bytes != old_clip_bytes:
                selected_text = new_clip_bytes.decode('utf-8', errors='replace')

        if selected_text is not None and selected_text.strip():
            # ── Selection mode ─────────────────────────────────────────────
            converted     = convert_text(selected_text)
            original_lang = detect_language(selected_text)
            print(f"[selection] {repr(selected_text)}")
            if converted == selected_text:
                print(f"[skip]    no change needed")
                subprocess.run(['pbcopy'], input=old_clip_bytes)
                return
            print(f"[convert] ({original_lang}) → {repr(converted)}")
            # Call directly — CGEventTap is passive and is_typing=True blocks on_press
            _inject_selection_worker(converted, old_clip_bytes)

        else:
            # ── Buffer mode ────────────────────────────────────────────────
            with buffer_lock:
                text = ''.join(buffer)
                n    = len(buffer)
                buffer = []

            if not text.strip():
                return

            converted     = convert_text(text)
            original_lang = detect_language(text)
            print(f"[buffer]  {repr(text)}")
            if converted == text:
                print(f"[skip]    no change needed")
                return
            print(f"[convert] ({original_lang}) → {repr(converted)}")
            _inject_worker(n, converted)

        time.sleep(0.1)

        # Switch input source to the language we just converted to
        target = _english_source if original_lang == 'hebrew' else _hebrew_source
        if target:
            switch_to(target)
            print(f"[switch]  → {target}")

    finally:
        time.sleep(0.1)
        with buffer_lock:
            buffer = []   # discard anything that leaked in during injection
        is_typing = False
        _conversion_lock.release()


# ── Keyboard listener callbacks ───────────────────────────────────────────────
def on_press(key):
    pressed_keys.add(key)

    ctrl = Key.ctrl_l in pressed_keys or Key.ctrl_r in pressed_keys

    trigger_pressed = False
    if isinstance(key, KeyCode):
        trigger_pressed = getattr(key, 'vk', None) == _TRIGGER_VK
    if not trigger_pressed and hasattr(key, 'char') and key.char == ';':
        trigger_pressed = True

    if ctrl and trigger_pressed:
        global _caps_lock_pending
        if _caps_lock_pending:
            _caps_lock_pending = False
            c = _Controller()
            c.press(Key.caps_lock)
            c.release(Key.caps_lock)
        if not is_typing:
            threading.Thread(target=do_conversion, daemon=True).start()
        return

    if is_typing:
        return

    if ctrl:
        return

    if key == Key.space:
        with buffer_lock:
            buffer.append(' ')
        schedule_idle_reset()
        return

    if hasattr(key, 'char') and key.char:
        with buffer_lock:
            buffer.append(key.char)
        schedule_idle_reset()
        return

    if key == Key.caps_lock:
        reset_buffer()
        _caps_lock_pending = True
        return

    reset_keys = {Key.enter, Key.tab, Key.esc, Key.left, Key.right,
                  Key.up, Key.down, Key.home, Key.end, Key.page_up, Key.page_down}
    if key in reset_keys:
        reset_buffer()
        return

    if key == Key.backspace:
        with buffer_lock:
            if buffer:
                buffer.pop()
        schedule_idle_reset()


def on_release(key):
    pressed_keys.discard(key)


# ── Keyboard listener ────────────────────────────────────────────────────────
def _start_listener():
    """Start the global keyboard listener (blocking)."""
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        if _IS_MAC:
            listener._intercept = _trigger_intercept
        try:
            listener.join()
        except KeyboardInterrupt:
            pass


# ── System tray / menu bar ───────────────────────────────────────────────────
def _run_tray():
    """Run the app with a system tray icon."""
    if _IS_MAC:
        import rumps

        class DubSwitchApp(rumps.App):
            def __init__(self):
                super().__init__("DubSwitch", title="⌨")
                self.menu = [
                    rumps.MenuItem("DubSwitch is running"),
                    None,  # separator
                    rumps.MenuItem("Shortcut: Ctrl + ;"),
                    None,
                ]
                # Start keyboard listener in background thread
                t = threading.Thread(target=_start_listener, daemon=True)
                t.start()

            @rumps.clicked("Quit DubSwitch")
            def quit_app(self, _):
                rumps.quit_application()

        DubSwitchApp().run()
    else:
        # Windows / Linux: use pystray
        from pystray import Icon, Menu, MenuItem
        from PIL import Image, ImageDraw

        # Generate a simple icon (blue square with "DS" text)
        def _create_icon():
            img = Image.new('RGB', (64, 64), color=(59, 130, 246))
            d = ImageDraw.Draw(img)
            d.text((12, 18), "DS", fill="white")
            return img

        def _on_quit(icon, item):
            icon.stop()

        icon = Icon(
            "DubSwitch",
            _create_icon(),
            "DubSwitch",
            menu=Menu(
                MenuItem("DubSwitch is running", None, enabled=False),
                MenuItem("Shortcut: Ctrl + ;", None, enabled=False),
                Menu.SEPARATOR,
                MenuItem("Quit", _on_quit),
            ),
        )

        # Start keyboard listener in background thread
        t = threading.Thread(target=_start_listener, daemon=True)
        t.start()

        icon.run()


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    print("DubSwitch running.")
    print("Shortcut: Ctrl + ;")
    print(f"Hebrew input source : {_hebrew_source or 'NOT FOUND'}")
    print(f"English input source: {_english_source or 'NOT FOUND'}")

    # If --no-tray is passed (for debugging), run without system tray
    if '--no-tray' in sys.argv:
        print("Press Ctrl+C to stop.\n")
        _start_listener()
    else:
        _run_tray()


if __name__ == '__main__':
    multiprocessing.freeze_support()               # required for PyInstaller on Windows
    main()
