import ctypes
from ctypes import wintypes

from toga.screens import Screen as ScreenInterface
from toga.types import Position, Size

# Coordinate system:
#
# Screen._enumerate() uses Win32 EnumDisplayMonitors / GetMonitorInfoW,
# which return rcMonitor in physical pixel coordinates. The public API
# (get_origin / get_size) converts these to DIPs (CSS pixels) by dividing
# by the DPI scale factor, matching Toga's expectation that screen
# coordinates are in logical pixels.
#
# - Origin is scaled by the *primary* screen's DPI (consistent reference
#   frame for multi-monitor coordinate offsets, matching WinForms).
# - Size is scaled by the screen's *own* DPI (consistent with window
#   content scaling).
# - get_image_data() continues to use raw physical pixels for GDI capture.

# Win32 constants
MONITOR_DEFAULTTOPRIMARY = 1
MONITOR_DEFAULTTONEAREST = 2


class Screen:
    _instances = {}
    _all_screens = None

    def __init__(self, hmonitor, name, origin, size, scale_factor):
        self.interface = ScreenInterface(_impl=self)
        self._hmonitor = hmonitor
        self._name = name
        self._origin = origin
        self._size = size
        self._scale_factor = scale_factor

    @classmethod
    def _enumerate(cls):
        """Enumerate all monitors using Win32 API."""
        screens = []

        def _enum_callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
            info = _MONITORINFOEXW()
            info.cbSize = ctypes.sizeof(_MONITORINFOEXW)
            if ctypes.windll.user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
                name = info.szDevice.rstrip("\x00")
                # Get the display name (e.g., "DISPLAY1" from "\\.\DISPLAY1")
                display_name = name.split("\\")[-1] if "\\" in name else name

                rect = info.rcMonitor
                origin = Position(rect.left, rect.top)
                size = Size(rect.right - rect.left, rect.bottom - rect.top)

                # Get DPI scale factor for this monitor.
                scale = _get_scale_factor(hMonitor)

                screen = cls(hMonitor, display_name, origin, size, scale)
                screens.append(screen)
            return True

        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            wintypes.HMONITOR,
            wintypes.HDC,
            ctypes.POINTER(wintypes.RECT),
            wintypes.LPARAM,
        )
        callback = MONITORENUMPROC(_enum_callback)
        ctypes.windll.user32.EnumDisplayMonitors(None, None, callback, 0)

        return screens

    @classmethod
    def _refresh(cls):
        """Refresh the screen list."""
        screens = cls._enumerate()
        cls._all_screens = screens
        cls._instances = {s._hmonitor: s for s in screens}

    @classmethod
    def from_hwnd(cls, hwnd):
        """Find the Screen for the monitor containing the given window handle."""
        hmonitor = ctypes.windll.user32.MonitorFromWindow(
            hwnd, MONITOR_DEFAULTTONEAREST
        )
        if cls._all_screens is None:
            cls._refresh()
        # Match by monitor handle.
        if hmonitor in cls._instances:
            return cls._instances[hmonitor]
        # Monitor handle not found (e.g., new display); refresh and retry.
        cls._refresh()
        if hmonitor in cls._instances:
            return cls._instances[hmonitor]
        return cls.primary()

    @classmethod
    def primary(cls):
        if cls._all_screens is None:
            cls._refresh()
        # The primary monitor has origin (0, 0).
        for screen in cls._all_screens:
            if screen._origin == Position(0, 0):
                return screen
        # Fallback: first screen.
        if cls._all_screens:
            return cls._all_screens[0]
        # Emergency fallback if enumeration failed.
        return cls(None, "DISPLAY1", Position(0, 0), Size(1920, 1080), 1.0)

    @classmethod
    def all_screens(cls):
        if cls._all_screens is None:
            cls._refresh()
        return list(cls._all_screens)

    def get_name(self):
        return self._name

    def get_origin(self) -> Position:
        # Scale by primary screen's DPI for a consistent coordinate frame.
        primary_scale = self.__class__.primary()._scale_factor
        return Position(
            self._origin.x / primary_scale,
            self._origin.y / primary_scale,
        )

    def get_size(self) -> Size:
        # Scale by this screen's own DPI, consistent with window content scaling.
        return Size(
            self._size.width / self._scale_factor,
            self._size.height / self._scale_factor,
        )

    def get_image_data(self):
        """Capture this monitor's contents as BMP image bytes using GDI."""
        from .libs.screenshot import capture_rect

        x = self._origin[0]
        y = self._origin[1]
        w = self._size[0]
        h = self._size[1]
        return capture_rect(int(x), int(y), int(w), int(h))


class _MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", ctypes.c_wchar * 32),
    ]


def _get_scale_factor(hmonitor):
    """Get the DPI scale factor for a monitor."""
    try:
        scale = wintypes.UINT()
        # GetScaleFactorForMonitor returns a percentage (100, 125, 150, etc.)
        hr = ctypes.windll.shcore.GetScaleFactorForMonitor(
            hmonitor, ctypes.byref(scale)
        )
        if hr == 0:  # S_OK
            return scale.value / 100.0
    except Exception:
        pass
    return 1.0
