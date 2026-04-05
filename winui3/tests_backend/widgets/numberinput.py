import math

import pytest
from win32more.Microsoft.UI.Xaml.Controls import NumberBox

from .base import SimpleProbe


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
        return not self.native.IsEnabled

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
        # NumberBox doesn't directly expose TextAlignment.
        pytest.skip("Can't read text alignment on NumberBox")

    def assert_vertical_text_align(self, expected):
        # Vertical text alignment isn't configurable in this native widget.
        pass

    def set_cursor_at_end(self):
        pytest.skip("Cursor positioning not supported on this platform")
