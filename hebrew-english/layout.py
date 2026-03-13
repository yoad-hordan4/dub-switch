# Hebrew keyboard layout mapping
# Each entry: English key -> Hebrew character (what you get when Hebrew layout is active)

EN_TO_HE = {
    'q': '/', 'w': "׳", 'e': 'ק', 'r': 'ר', 't': 'א', 'y': 'ט', 'u': 'ו',
    'i': 'ן', 'o': 'ם', 'p': 'פ',
    'a': 'ש', 's': 'ד', 'd': 'ג', 'f': 'כ', 'g': 'ע', 'h': 'י', 'j': 'ח',
    'k': 'ל', 'l': 'ך', ';': 'ף',
    'z': 'ז', 'x': 'ס', 'c': 'ב', 'v': 'ה', 'b': 'נ', 'n': 'מ', 'm': 'צ',
    ',': 'ת', '.': 'ץ',
    # Uppercase (shift held)
    'Q': '/', 'W': "׳", 'E': 'ק', 'R': 'ר', 'T': 'א', 'Y': 'ט', 'U': 'ו',
    'I': 'ן', 'O': 'ם', 'P': 'פ',
    'A': 'ש', 'S': 'ד', 'D': 'ג', 'F': 'כ', 'G': 'ע', 'H': 'י', 'J': 'ח',
    'K': 'ל', 'L': 'ך',
    'Z': 'ז', 'X': 'ס', 'C': 'ב', 'V': 'ה', 'B': 'נ', 'N': 'מ', 'M': 'צ',
    # numbers
    '1': '1', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7','8': '8', '9': '9', '0': '0',
}

# Reverse: Hebrew char -> English key
HE_TO_EN = {v: k for k, v in EN_TO_HE.items() if k.islower() or k.isdigit() or k in ",./;׳"}

# Hebrew characters set for detection
HEBREW_CHARS = set(EN_TO_HE.values())


def detect_language(text):
    """Returns 'hebrew', 'english', or 'mixed'."""
    has_hebrew = any(c in HEBREW_CHARS for c in text)
    has_english = any(c.isascii() and c.isalpha() for c in text)
    if has_hebrew and not has_english:
        return 'hebrew'
    if has_english and not has_hebrew:
        return 'english'
    return 'mixed'


def convert_text(text):
    """Convert Hebrew -> English or English -> Hebrew based on detected language."""
    lang = detect_language(text)
    result = []

    if lang == 'hebrew':
        for ch in text:
            result.append(HE_TO_EN.get(ch, ch))
    elif lang == 'english':
        for ch in text:
            lower = ch.lower()
            converted = EN_TO_HE.get(lower, ch)
            result.append(converted)
    else:
        # Mixed: try character by character
        for ch in text:
            if ch in HEBREW_CHARS:
                result.append(HE_TO_EN.get(ch, ch))
            elif ch.isascii() and ch.isalpha():
                result.append(EN_TO_HE.get(ch.lower(), ch))
            else:
                result.append(ch)

    return ''.join(result)
