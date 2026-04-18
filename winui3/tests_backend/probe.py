import asyncio
import ctypes
import ctypes.wintypes as wintypes

from pytest import approx
from win32more.Microsoft.UI.Xaml.Controls import Canvas

import toga

from .fonts import FontMixin

# Win32 Virtual Key codes for special keys
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_UP = 0x26
VK_DOWN = 0x28
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_HOME = 0x24
VK_END = 0x23
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt

KEY_CODES = {
    "\n": VK_RETURN,
    "<esc>": VK_ESCAPE,
    "<up>": VK_UP,
    "<down>": VK_DOWN,
    "<left>": VK_LEFT,
    "<right>": VK_RIGHT,
    "<home>": VK_HOME,
    "<end>": VK_END,
}

# Win32 SendInput structures
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

# Mouse event flags for MOUSEINPUT.dwFlags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [
            ("ki", KEYBDINPUT),
            ("mi", MOUSEINPUT),
        ]

    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


def _make_key_input(vk, down=True):
    """Create an INPUT structure for a key press or release."""
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = 0
    inp.union.ki.dwFlags = 0 if down else KEYEVENTF_KEYUP
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = None
    return inp


def _make_mouse_input(screen_x, screen_y, flags):
    """Create an INPUT structure for a mouse action at absolute screen coords.

    SendInput with MOUSEEVENTF_ABSOLUTE expects coordinates in the range
    [0, 65535] mapped to the full virtual screen.
    """
    # Map pixel coordinates to the normalised [0, 65535] range.
    sm_cx = ctypes.windll.user32.GetSystemMetrics(0)  # SM_CXSCREEN
    sm_cy = ctypes.windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
    abs_x = int(screen_x * 65536 / sm_cx)
    abs_y = int(screen_y * 65536 / sm_cy)

    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.union.mi.dx = abs_x
    inp.union.mi.dy = abs_y
    inp.union.mi.mouseData = 0
    inp.union.mi.dwFlags = flags | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE
    inp.union.mi.time = 0
    inp.union.mi.dwExtraInfo = None
    return inp


def _send_inputs(*inputs):
    """Send a sequence of INPUT structures via Win32 SendInput."""
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    ctypes.windll.user32.SendInput(n, arr, ctypes.sizeof(INPUT))


class BaseProbe(FontMixin):
    fixed_height = None

    def __init__(self, native=None):
        self.native = native

    async def redraw(self, message=None, delay=0, wait_for=None):
        """Request a redraw of the app, waiting until that redraw has completed."""
        # WinUI 3 style changes take effect on the next composition frame.

        # If we're running slow, or we have a wait condition,
        # wait for at least a second
        if toga.App.app.run_slow or wait_for:
            delay = max(1, delay)

        if delay or wait_for:
            print("Waiting for redraw" if message is None else message)
            if toga.App.app.run_slow or wait_for is None:
                await asyncio.sleep(delay)
            else:
                delta = 0.1
                interval = 0.0
                while not wait_for() and interval < delay:
                    await asyncio.sleep(delta)
                    interval += delta
        else:
            # Sleep even if the delay is zero: this allows any pending callbacks on the
            # event loop to run.
            await asyncio.sleep(0)

    @property
    def x(self):
        return round(Canvas.GetLeft(self.native) / self.scale_factor)

    @property
    def y(self):
        return round(Canvas.GetTop(self.native) / self.scale_factor)

    @property
    def width(self):
        return round(self.native.ActualWidth / self.scale_factor)

    @property
    def height(self):
        return round(self.native.ActualHeight / self.scale_factor)

    def assert_width(self, min_width, max_width):
        assert min_width <= self.width <= max_width

    def assert_height(self, min_height, max_height):
        if self.fixed_height is not None:
            assert self.height == approx(self.fixed_height, rel=0.1)
        else:
            assert min_height <= self.height <= max_height

    @property
    def scale_factor(self):
        # WinUI 3 works in DIPs, so for layout purposes scale_factor is 1.
        # But for image assertions we need the actual DPI scale. Use the primary
        # screen's scale factor as a reasonable default.
        return self._get_primary_scale_factor()

    def _get_primary_scale_factor(self):
        """Get the DPI scale factor for the primary monitor."""
        try:
            # MONITOR_DEFAULTTOPRIMARY = 1
            hMonitor = ctypes.windll.user32.MonitorFromPoint(wintypes.POINT(0, 0), 1)
            pScale = wintypes.UINT()
            ctypes.windll.shcore.GetScaleFactorForMonitor(
                hMonitor, ctypes.byref(pScale)
            )
            return pScale.value / 100
        except Exception:
            return 1.0

    async def type_character(self, char, *, shift=False, ctrl=False, alt=False):
        try:
            vk = KEY_CODES[char]
        except KeyError:
            assert len(char) == 1, char
            # Use VkKeyScanW to determine the VK code and shift state for a character
            result = ctypes.windll.user32.VkKeyScanW(ord(char))
            vk = result & 0xFF
            # High byte contains shift state: bit 0 = Shift
            if result & 0x100:
                shift = True

        inputs = []
        # Press modifiers
        if ctrl:
            inputs.append(_make_key_input(VK_CONTROL, down=True))
        if alt:
            inputs.append(_make_key_input(VK_MENU, down=True))
        if shift:
            inputs.append(_make_key_input(VK_SHIFT, down=True))

        # Press and release the key
        inputs.append(_make_key_input(vk, down=True))
        inputs.append(_make_key_input(vk, down=False))

        # Release modifiers (reverse order)
        if shift:
            inputs.append(_make_key_input(VK_SHIFT, down=False))
        if alt:
            inputs.append(_make_key_input(VK_MENU, down=False))
        if ctrl:
            inputs.append(_make_key_input(VK_CONTROL, down=False))

        _send_inputs(*inputs)

        # Give the WinUI 3 message pump time to process the input.
        await asyncio.sleep(0.05)

    def _widget_screen_position(self, native):
        """Get the top-left corner of a native element in screen coordinates."""
        from win32more.Windows.Foundation import Point

        # TransformToVisual(None) gives us a transform from the element to the
        # root visual. Combined with the window position this gives screen coords.
        transform = native.TransformToVisual(None)
        origin = transform.TransformPoint(Point(X=0, Y=0))

        # Use AppWindow.Position for the window's screen offset.
        app_window = toga.App.app.main_window._impl.native.AppWindow
        win_x = app_window.Position.X
        win_y = app_window.Position.Y

        # AppWindow.Position is the outer frame; the client area is offset by
        # the title bar height. We approximate with GetSystemMetrics.
        caption_h = ctypes.windll.user32.GetSystemMetrics(4)  # SM_CYCAPTION
        frame_w = ctypes.windll.user32.GetSystemMetrics(7)  # SM_CXFRAME
        frame_h = ctypes.windll.user32.GetSystemMetrics(8)  # SM_CYFRAME

        screen_x = win_x + frame_w + origin.X
        screen_y = win_y + caption_h + frame_h + origin.Y
        return screen_x, screen_y

    async def _send_mouse_event(self, native, x, y, flags):
        """Send a mouse event at widget-local (x, y) via Win32 SendInput."""
        sx, sy = self._widget_screen_position(native)
        _send_inputs(_make_mouse_input(sx + x, sy + y, flags))
        await asyncio.sleep(0.05)

    def assert_image_size(self, image_size, size, screen, window=None):
        scale_factor = screen._impl._scale_factor
        assert image_size == (
            round(size[0] * scale_factor),
            round(size[1] * scale_factor),
        )
