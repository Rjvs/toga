import ctypes
from pathlib import Path

from win32more.Microsoft.UI.Xaml import FontStyle as WinUIFontStyle
from win32more.Microsoft.UI.Xaml.Media import FontFamily
from win32more.Windows.UI.Text import FontWeights

from toga.fonts import (
    _IMPL_CACHE,
    _REGISTERED_FONT_CACHE,
    CURSIVE,
    FANTASY,
    MESSAGE,
    MONOSPACE,
    SANS_SERIF,
    SERIF,
    SYSTEM,
    SYSTEM_DEFAULT_FONT_SIZE,
    UnknownFontError,
)

# WinUI 3 default font is Segoe UI Variable (or Segoe UI on older Windows)
DEFAULT_FONT_FAMILY = "Segoe UI Variable"
DEFAULT_FONT_SIZE = 14  # WinUI 3 default body text size


# Map Toga generic font families to WinUI 3 font family names
FONT_FAMILY_MAP = {
    SYSTEM: DEFAULT_FONT_FAMILY,
    MESSAGE: DEFAULT_FONT_FAMILY,
    SERIF: "Times New Roman",
    SANS_SERIF: DEFAULT_FONT_FAMILY,
    CURSIVE: "Comic Sans MS",
    FANTASY: "Impact",
    MONOSPACE: "Consolas",
}


class Font:
    def __init__(self, interface):
        self.interface = interface

    def load_predefined_system_font(self):
        """Use one of the system font names Toga predefines."""
        try:
            family_name = FONT_FAMILY_MAP[self.interface.family]
        except KeyError as exc:
            msg = f"{self.interface} not a predefined system font"
            raise UnknownFontError(msg) from exc

        self._assign_native(family_name)

    def load_user_registered_font(self):
        """Use a font that the user has registered in their code."""
        font_key = self.interface._registered_font_key(
            self.interface.family,
            weight=self.interface.weight,
            style=self.interface.style,
            variant=self.interface.variant,
        )
        try:
            font_path = _REGISTERED_FONT_CACHE[font_key]
        except KeyError as exc:
            msg = f"{self.interface} not a user-registered font"
            raise UnknownFontError(msg) from exc

        # WinUI 3 FontFamily supports file:// URIs with a #FamilyName fragment.
        path = Path(font_path)
        font_uri = f"{path.as_uri()}#{self.interface.family}"
        self._assign_native(font_uri)

    def load_arbitrary_system_font(self):
        """Use a font available on the system."""
        family_name = self.interface.family
        if not _font_family_exists(family_name):
            raise UnknownFontError(family_name)
        self._assign_native(family_name)

    def _assign_native(self, family_name):
        self.native_family = FontFamily(family_name)

        # Font weight
        if self.interface.weight == "bold":
            self.native_weight = FontWeights.Bold
        else:
            self.native_weight = FontWeights.Normal

        # Font style
        if self.interface.style in {"italic", "oblique"}:
            self.native_style = WinUIFontStyle.Italic
        else:
            self.native_style = WinUIFontStyle.Normal

        # Font size (in DIPs - device independent pixels, same as CSS pixels)
        if self.interface.size == SYSTEM_DEFAULT_FONT_SIZE:
            self.native_size = DEFAULT_FONT_SIZE
        else:
            self.native_size = self.interface.size

        _IMPL_CACHE[self.interface] = self

    def apply(self, control):
        """Apply this font to a WinUI 3 control."""
        control.FontFamily = self.native_family
        control.FontSize = self.native_size
        control.FontWeight = self.native_weight
        control.FontStyle = self.native_style

    def metric(self, name):
        """Return the given metric, measured in CSS pixels.

        Uses GDI GetTextMetrics for accurate font measurements. Falls back to
        standard typography ratios if GDI fails.
        """
        if not hasattr(self, "_metrics"):
            self._metrics = _get_text_metrics(self)

        if self._metrics:
            tm = self._metrics
            match name:
                case "CellAscent":
                    return tm["ascent"]
                case "CellDescent":
                    return tm["descent"]
                case "LineSpacing":
                    return tm["height"]
                case _:
                    return tm["height"]
        else:
            # Fallback: approximate from font size using standard ratios.
            em_height = self.native_size
            match name:
                case "CellAscent":
                    return em_height * 0.8
                case "CellDescent":
                    return em_height * 0.2
                case "LineSpacing":
                    return em_height * 1.2
                case _:
                    return em_height


######################################################################
# GDI font validation and metrics
######################################################################


def _font_family_exists(family_name):
    """Check if a font family exists on the system using GDI.

    Creates a font with the requested family, selects it into a DC,
    then checks if the actual face name matches the requested name.
    GDI silently substitutes a default font for unknown families.
    """
    gdi32 = ctypes.windll.gdi32
    user32 = ctypes.windll.user32

    try:
        hdc = user32.GetDC(None)
        if not hdc:
            # Can't validate; assume it exists to avoid false negatives.
            return True

        hfont = gdi32.CreateFontW(
            0, 0, 0, 0, FW_NORMAL, 0, 0, 0, 0, 0, 0, 0, 0, family_name
        )
        if not hfont:
            user32.ReleaseDC(None, hdc)
            return True

        old_font = gdi32.SelectObject(hdc, hfont)

        # GetTextFaceW returns the actual face name of the selected font.
        buf = ctypes.create_unicode_buffer(64)
        gdi32.GetTextFaceW(hdc, 64, buf)
        actual_face = buf.value

        gdi32.SelectObject(hdc, old_font)
        gdi32.DeleteObject(hfont)
        user32.ReleaseDC(None, hdc)

        return actual_face.lower() == family_name.lower()
    except Exception:
        # Can't validate; assume it exists.
        return True


class _TEXTMETRICW(ctypes.Structure):
    _fields_ = [
        ("tmHeight", ctypes.c_long),
        ("tmAscent", ctypes.c_long),
        ("tmDescent", ctypes.c_long),
        ("tmInternalLeading", ctypes.c_long),
        ("tmExternalLeading", ctypes.c_long),
        ("tmAveCharWidth", ctypes.c_long),
        ("tmMaxCharWidth", ctypes.c_long),
        ("tmWeight", ctypes.c_long),
        ("tmOverhang", ctypes.c_long),
        ("tmDigitizedAspectX", ctypes.c_long),
        ("tmDigitizedAspectY", ctypes.c_long),
        ("tmFirstChar", ctypes.c_wchar),
        ("tmLastChar", ctypes.c_wchar),
        ("tmDefaultChar", ctypes.c_wchar),
        ("tmBreakChar", ctypes.c_wchar),
        ("tmItalic", ctypes.c_byte),
        ("tmUnderlined", ctypes.c_byte),
        ("tmStruckOut", ctypes.c_byte),
        ("tmPitchAndFamily", ctypes.c_byte),
        ("tmCharSet", ctypes.c_byte),
    ]


# GDI constants
FW_NORMAL = 400
FW_BOLD = 700


def _get_text_metrics(font):
    """Get font metrics via GDI GetTextMetrics. Returns dict or None on failure."""
    gdi32 = ctypes.windll.gdi32
    user32 = ctypes.windll.user32

    try:
        hdc = user32.GetDC(None)
        if not hdc:
            return None

        # Map font properties to GDI CreateFontW parameters.
        # Size is in DIPs (same as points at 96 DPI). GDI expects negative
        # lfHeight for character height (not cell height).
        height = -int(font.native_size * 96 / 72)
        weight = FW_BOLD if font.interface.weight == "bold" else FW_NORMAL
        italic = 1 if font.interface.style in {"italic", "oblique"} else 0

        # Extract the raw family name (strip file:// URI prefix if present).
        family = font.interface.family
        if family in FONT_FAMILY_MAP:
            family = FONT_FAMILY_MAP[family]

        hfont = gdi32.CreateFontW(
            height,  # lfHeight
            0,  # lfWidth
            0,  # lfEscapement
            0,  # lfOrientation
            weight,  # lfWeight
            italic,  # lfItalic
            0,  # lfUnderline
            0,  # lfStrikeOut
            0,  # lfCharSet (DEFAULT_CHARSET)
            0,  # lfOutPrecision
            0,  # lfClipPrecision
            0,  # lfQuality
            0,  # lfPitchAndFamily
            family,  # lfFaceName
        )
        if not hfont:
            user32.ReleaseDC(None, hdc)
            return None

        old_font = gdi32.SelectObject(hdc, hfont)

        tm = _TEXTMETRICW()
        result = gdi32.GetTextMetricsW(hdc, ctypes.byref(tm))

        gdi32.SelectObject(hdc, old_font)
        gdi32.DeleteObject(hfont)
        user32.ReleaseDC(None, hdc)

        if not result:
            return None

        # GDI metrics are in logical units (pixels at screen DPI).
        # Convert to DIPs (CSS pixels). At 96 DPI they're the same;
        # at higher DPI we need to scale down.
        dpi = user32.GetDpiForSystem() if hasattr(user32, "GetDpiForSystem") else 96
        scale = 96.0 / dpi

        return {
            "ascent": tm.tmAscent * scale,
            "descent": tm.tmDescent * scale,
            "height": tm.tmHeight * scale,
        }
    except Exception:
        return None
