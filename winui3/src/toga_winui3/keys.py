import re
from string import ascii_lowercase

from win32more.Windows.System import VirtualKey

from toga.keys import Key

WINUI3_MODIFIERS = {
    Key.MOD_1: VirtualKey.Control,
    Key.MOD_2: VirtualKey.Menu,  # Alt key
    Key.SHIFT: VirtualKey.Shift,
}

WINUI3_KEYS = {
    Key.ESCAPE.value: VirtualKey.Escape,
    Key.MINUS.value: VirtualKey(189),  # VK_OEM_MINUS
    Key.CAPSLOCK.value: VirtualKey.CapitalLock,
    Key.TAB.value: VirtualKey.Tab,
    Key.SPACE.value: VirtualKey.Space,
    Key.PAGE_UP.value: VirtualKey.PageUp,
    Key.PAGE_DOWN.value: VirtualKey.PageDown,
    Key.INSERT.value: VirtualKey.Insert,
    Key.DELETE.value: VirtualKey.Delete,
    Key.HOME.value: VirtualKey.Home,
    Key.END.value: VirtualKey.End,
    Key.UP.value: VirtualKey.Up,
    Key.DOWN.value: VirtualKey.Down,
    Key.LEFT.value: VirtualKey.Left,
    Key.RIGHT.value: VirtualKey.Right,
    Key.NUMLOCK.value: VirtualKey.NumberKeyLock,
    Key.NUMPAD_DECIMAL_POINT.value: VirtualKey.Decimal,
    Key.SCROLLLOCK.value: VirtualKey.Scroll,
    Key.MENU.value: VirtualKey.Application,
    # OEM keys — VirtualKey enum lacks named members for these,
    # so we use the raw Win32 virtual-key codes.
    Key.SEMICOLON.value: VirtualKey(186),  # VK_OEM_1
    Key.EQUAL.value: VirtualKey(187),  # VK_OEM_PLUS (unshifted: =)
    Key.COMMA.value: VirtualKey(188),  # VK_OEM_COMMA
    Key.FULL_STOP.value: VirtualKey(190),  # VK_OEM_PERIOD
    Key.SLASH.value: VirtualKey(191),  # VK_OEM_2
    Key.OPEN_BRACKET.value: VirtualKey(219),  # VK_OEM_4
    Key.BACKSLASH.value: VirtualKey(220),  # VK_OEM_5
    Key.CLOSE_BRACKET.value: VirtualKey(221),  # VK_OEM_6
    Key.QUOTE.value: VirtualKey(222),  # VK_OEM_7
}
WINUI3_KEYS.update(
    {str(digit): getattr(VirtualKey, f"Number{digit}") for digit in range(10)}
)
WINUI3_KEYS.update(
    {
        getattr(Key, f"NUMPAD_{digit}").value: getattr(VirtualKey, f"NumberPad{digit}")
        for digit in range(10)
    }
)

SHIFTED_KEYS = dict(zip("!@#$%^&*()", "1234567890", strict=False))
SHIFTED_KEYS.update(
    {lower.upper(): lower for lower in ascii_lowercase},
)
SHIFTED_KEYS.update(
    {
        "~": "`",
        "_": "-",
        "+": "=",
        "{": "[",
        "}": "]",
        "|": "\\",
        ":": ";",
        '"': "'",
        "<": ",",
        ">": ".",
        "?": "/",
    }
)

# Reverse mapping: VirtualKey -> toga key string value.
WINUI3_KEYS_REVERSE = {v: k for k, v in WINUI3_KEYS.items()}


def toga_to_winui3_key(key):
    """Convert a Toga Key to a WinUI 3 VirtualKey."""
    try:
        key = key.value
    except AttributeError:
        pass

    codes = []
    for modifier, modifier_code in WINUI3_MODIFIERS.items():
        if modifier.value in key:
            codes.append(modifier_code)
            key = key.replace(modifier.value, "")

    if lower := SHIFTED_KEYS.get(key):
        key = lower
        codes.append(VirtualKey.Shift)

    try:
        codes.append(WINUI3_KEYS[key])
    except KeyError:
        if match := re.fullmatch(r"<(.+)>", key):
            key = match[1]
        try:
            codes.append(getattr(VirtualKey, key.title()))
        except AttributeError:  # pragma: no cover
            raise ValueError(f"unknown key: {key!r}") from None

    return codes


def toga_to_winui3_shortcut(key):
    """Convert a Toga Key to a human-readable shortcut string."""
    try:
        key = key.value
    except AttributeError:
        key = key

    display = []
    for toga_keyval, display_text in [
        (Key.MOD_1.value, "Ctrl"),
        (Key.MOD_2.value, "Alt"),
        (Key.SHIFT.value, "Shift"),
    ]:
        if toga_keyval in key:
            display.append(display_text)
            key = key.replace(toga_keyval, "")

    if key == " ":
        display.append("Space")
    else:
        if match := re.fullmatch(r"<(.+)>", key):
            key = match[1]
        display.append(key.title())

    return "+".join(display)


def winui3_to_toga_key(virtual_key, modifier_flags=0):
    """Convert a WinUI 3 VirtualKey and modifier flags to a Toga Key dict.

    Args:
        virtual_key: A VirtualKey enum value (the primary key).
        modifier_flags: Bitwise combination of VirtualKeyModifiers values.

    Returns:
        A dict with ``"key"`` (toga Key) and ``"modifiers"`` (set of toga
        modifier Keys), or ``None`` if the key cannot be mapped.
    """
    from win32more.Windows.System import VirtualKeyModifiers

    modifiers = set()
    if modifier_flags & VirtualKeyModifiers.Control:
        modifiers.add(Key.MOD_1)
    if modifier_flags & VirtualKeyModifiers.Menu:
        modifiers.add(Key.MOD_2)
    if modifier_flags & VirtualKeyModifiers.Shift:
        modifiers.add(Key.SHIFT)

    # Look up the virtual key in the reverse mapping.
    toga_value = WINUI3_KEYS_REVERSE.get(virtual_key)

    if toga_value is None:
        # Try letter keys (A-Z) which map to VirtualKey.A through VirtualKey.Z.
        for letter in ascii_lowercase:
            try:
                if virtual_key == getattr(VirtualKey, letter.upper()):
                    toga_value = letter
                    break
            except AttributeError:
                continue

    if toga_value is None:
        # Try F-keys (F1-F24).
        for n in range(1, 25):
            try:
                if virtual_key == getattr(VirtualKey, f"F{n}"):
                    toga_value = f"<F{n}>"
                    break
            except AttributeError:
                continue

    if toga_value is None:
        return None

    # Handle shifted keys: if Shift is held and the base key has a shifted form,
    # use the shifted character and remove Shift from modifiers.
    if Key.SHIFT in modifiers:
        for symbol, base in SHIFTED_KEYS.items():
            if base == toga_value:
                toga_value = symbol
                modifiers.discard(Key.SHIFT)
                break

    return {"key": Key(toga_value), "modifiers": modifiers}
