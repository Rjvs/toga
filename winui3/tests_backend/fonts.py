from toga_winui3.fonts import DEFAULT_FONT_SIZE, FONT_FAMILY_MAP
from win32more.Microsoft.UI.Xaml import FontStyle as WinUIFontStyle

from toga.fonts import (
    BOLD,
    ITALIC,
    NORMAL,
    OBLIQUE,
    SMALL_CAPS,
    SYSTEM_DEFAULT_FONT_SIZE,
)


class FontMixin:
    supports_custom_fonts = True
    supports_custom_variable_fonts = True

    def preinstalled_font(self):
        return "Times New Roman"

    def assert_font_options(self, weight=NORMAL, style=NORMAL, variant=NORMAL):
        # WinUI 3 stores font weight as an integer (400=Normal, 700=Bold).
        native_weight = self.native.FontWeight.Weight
        assert weight == (BOLD if native_weight >= 600 else NORMAL)

        native_style = self.native.FontStyle
        if style == OBLIQUE:
            print("Interpreting OBLIQUE font as ITALIC")
            assert native_style == WinUIFontStyle.Italic
        else:
            assert style == (
                ITALIC if native_style == WinUIFontStyle.Italic else NORMAL
            )

        if variant == SMALL_CAPS:
            print("Ignoring SMALL CAPS font test")
        else:
            assert variant == NORMAL

    @property
    def font_size(self):
        return self.native.FontSize

    def assert_font_size(self, expected):
        if expected == SYSTEM_DEFAULT_FONT_SIZE:
            expected = DEFAULT_FONT_SIZE
        assert self.font_size == expected

    def assert_font_family(self, expected):
        actual = self.native.FontFamily.Source
        expected_name = FONT_FAMILY_MAP.get(expected, expected)
        assert actual == expected_name
