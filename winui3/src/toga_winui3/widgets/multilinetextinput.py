from win32more.Microsoft.UI.Xaml import TextAlignment, TextWrapping
from win32more.Microsoft.UI.Xaml.Controls import ScrollBarVisibility, TextBox

from toga.handlers import WeakrefCallable

from .base import Widget


class MultilineTextInput(Widget):
    native: TextBox

    def create(self):
        self.native = TextBox()
        self.native.AcceptsReturn = True
        self.native.TextWrapping = TextWrapping.Wrap
        self.native.VerticalScrollBarVisibility = ScrollBarVisibility.Auto
        self.native.add_TextChanged(WeakrefCallable(self.winui3_text_changed))

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

    def scroll_to_bottom(self):
        text = self.native.Text or ""
        self.native.SelectionStart = len(text)
        self.native.SelectionLength = 0

    def scroll_to_top(self):
        self.native.SelectionStart = 0
        self.native.SelectionLength = 0

    def set_text_align(self, value):
        self.native.TextAlignment = {
            "left": TextAlignment.Left,
            "right": TextAlignment.Right,
            "center": TextAlignment.Center,
        }.get(str(value), TextAlignment.Left)

    def rehint(self):
        pass  # Multiline text inputs don't have an intrinsic height

    def winui3_text_changed(self, sender, event):
        self.interface.on_change()
