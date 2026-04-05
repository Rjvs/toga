from win32more.Microsoft.UI.Xaml.Controls import TextBox

from .base import SimpleProbe
from .properties import toga_x_text_align


class TextInputProbe(SimpleProbe):
    native_class = TextBox
    redo_available = True

    @property
    def value(self):
        if self.placeholder_visible:
            return self.native.PlaceholderText
        return self.native.Text

    @property
    def value_hidden(self):
        return False

    @property
    def placeholder_visible(self):
        return not self.native.Text

    @property
    def placeholder_hides_on_focus(self):
        return False

    @property
    def readonly(self):
        return self.native.IsReadOnly

    @property
    def text_align(self):
        return toga_x_text_align(self.native.TextAlignment)

    def assert_vertical_text_align(self, expected):
        # Vertical text alignment isn't configurable in this native widget.
        pass

    def set_cursor_at_end(self):
        self.native.SelectionStart = len(self.native.Text)
        self.native.SelectionLength = 0
