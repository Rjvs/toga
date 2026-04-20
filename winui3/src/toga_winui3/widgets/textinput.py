from win32more.Microsoft.UI.Xaml import TextAlignment
from win32more.Microsoft.UI.Xaml.Controls import Control, TextBox as WinUITextBox

from toga.handlers import WeakrefCallable

from ._utils import get_error_brush, unbounded_size
from .base import Widget


class TextInput(Widget):
    native: WinUITextBox

    def create(self):
        self.native = WinUITextBox()
        self.native.AcceptsReturn = False
        self._error_message = None
        self.native.add_TextChanged(WeakrefCallable(self.winui3_text_changed))
        self.native.add_KeyDown(WeakrefCallable(self.winui3_key_down))
        self.native.add_GotFocus(WeakrefCallable(self.winui3_got_focus))
        self.native.add_LostFocus(WeakrefCallable(self.winui3_lost_focus))

    def get_readonly(self):
        return self.native.IsReadOnly

    def set_readonly(self, value):
        self.native.IsReadOnly = value

    def get_placeholder(self):
        return self.native.PlaceholderText

    def set_placeholder(self, value):
        self.native.PlaceholderText = value

    def get_value(self):
        return self.native.Text

    def set_value(self, value):
        self.native.Text = value

    def set_text_align(self, value):
        self.native.TextAlignment = {
            "left": TextAlignment.Left,
            "right": TextAlignment.Right,
            "center": TextAlignment.Center,
        }.get(str(value), TextAlignment.Left)

    def rehint(self):
        self.native.Measure(unbounded_size())
        self.interface.intrinsic.height = self.native.DesiredSize.Height

    def winui3_text_changed(self, sender, event):
        self.interface._value_changed()

    def winui3_key_down(self, sender, event):
        from win32more.Windows.System import VirtualKey

        if event.Key == VirtualKey.Enter:
            self.interface.on_confirm()
            event.Handled = True

    def winui3_got_focus(self, sender, event):
        self.interface.on_gain_focus()

    def winui3_lost_focus(self, sender, event):
        self.interface.on_lose_focus()

    def is_valid(self):
        return self._error_message is None

    def clear_error(self):
        self._error_message = None
        self.native.ClearValue(Control.BorderBrushProperty)

    def set_error(self, error_message):
        self._error_message = error_message
        self.native.BorderBrush = get_error_brush()
