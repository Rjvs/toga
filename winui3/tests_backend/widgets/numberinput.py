import math

import pytest
from win32more.Microsoft.UI.Xaml.Controls import NumberBox

from .base import SimpleProbe
from .properties import toga_x_text_align


class NumberInputProbe(SimpleProbe):
    native_class = NumberBox
    allows_invalid_value = False
    allows_empty_value = True
    allows_extra_digits = True
    allows_unchanged_updates = True

    @property
    def value(self):
        v = self.native.Value
        if math.isnan(v):
            return ""
        return str(v)

    @property
    def readonly(self):
        return not self.native.IsHitTestVisible

    def clear_input(self):
        self.native.Value = float("nan")

    async def increment(self):
        self.widget.focus()
        await self.type_character("<up>")

    async def decrement(self):
        self.widget.focus()
        await self.type_character("<down>")

    @property
    def text_align(self):
        inner = self.impl._inner_textbox
        if inner is None:
            from toga_winui3.widgets.numberinput import _find_inner_textbox

            inner = _find_inner_textbox(self.native)
        if inner is None:
            pytest.skip("Inner TextBox not available in NumberBox visual tree")
        return toga_x_text_align(inner.TextAlignment)

    def assert_vertical_text_align(self, expected):
        # Vertical text alignment isn't configurable in this native widget.
        pass

    def set_cursor_at_end(self):
        pytest.skip("Cursor positioning not supported on this platform")
