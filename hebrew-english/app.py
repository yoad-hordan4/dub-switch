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
from pynput.keyboard import Key, Controller as _Controller
from layout import convert_text, detect_language
from input_source import detect_hebrew_and_english, switch_to

_IS_MAC = sys.platform == 'darwin'

if _IS_MAC:
    from Quartz import (kCGEventKeyDown, CGEventGetFlags,
                        CGEventGetIntegerValueField, kCGKeyboardEventKeycode)

# ── Trigger key ────────────────────────────────────────────────────────────────
# Ctrl+1.  On Mac we intercept and SUPPRESS this combo so it never reaches
# the active text field.  On Windows Ctrl+1 doesn't produce visible characters
# in most apps so suppression is not needed.
_TRIGGER_KEYCODE = 18       # '1' key hardware keycode (Mac)
_CTRL_MASK  = 0x40000       # kCGEventFlagMaskControl (Mac)

if _IS_MAC:
    def _trigger_intercept(event_type, event):
        """Suppress Ctrl+1 so it doesn't reach the focused app (Mac only)."""
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


# ── Injection worker (runs in a child process) ─────────────────────────────────
# A child process has no CGEventTap, so its injected keystrokes flow directly
# to the focused app without being swallowed or double-processed.
# Works on both Mac and Windows.
def _inject_worker(n, converted):
    """Delete n chars then paste the converted text."""
    import subprocess, time as t

    if _IS_MAC:
        # Use osascript + pbcopy/pbpaste — reliable across all Mac app types.
        # The forked child has no CGEventTap, so events flow cleanly.
        old_clip = subprocess.run(['pbpaste'], capture_output=True).stdout
        proc = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        proc.communicate(converted.encode('utf-8'))

        backspace_script = '\n'.join(['    key code 51', '    delay 0.02'] * n)
        script = f'''tell application "System Events"
    delay 0.05
{backspace_script}
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
            ctrl.press(K.backspace)
            ctrl.release(K.backspace)
            t.sleep(0.02)
        t.sleep(0.05)
        ctrl.press(K.ctrl_l)
        ctrl.press('v')
        ctrl.release('v')
        ctrl.release(K.ctrl_l)
        t.sleep(0.1)
        pyperclip.copy(old_clip)


# ── Selection injection worker (Mac — child process) ──────────────────────────
def _inject_selection_worker(converted, old_clip_bytes):
    """Paste converted text over a selection (Mac — child process)."""
    import subprocess, time as t
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

    if ctrl and hasattr(key, 'char') and key.char == '1':
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


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    print("Hebrew-English switcher running.")
    print("Shortcut: Ctrl + 1")
    print(f"Hebrew input source : {_hebrew_source or 'NOT FOUND'}")
    print(f"English input source: {_english_source or 'NOT FOUND'}")
    print("Press Ctrl+C to stop.\n")

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        if _IS_MAC:
            listener._intercept = _trigger_intercept
        try:
            listener.join()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == '__main__':
    if _IS_MAC:
        multiprocessing.set_start_method('fork')   # near-instant child startup
    multiprocessing.freeze_support()               # required for PyInstaller on Windows
    main()
