from win32more.Microsoft.UI.Xaml.Controls import TextBox

from .base import SimpleProbe, find_scroll_viewer
from .properties import toga_x_text_align


class MultilineTextInputProbe(SimpleProbe):
    native_class = TextBox
    fixed_height = None
    supports_simulate_mouse_wheel = False

    @property
    def value(self):
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
    def document_height(self):
        sv = find_scroll_viewer(self.native)
        if sv is not None:
            return round(sv.ExtentHeight)
        return round(self.native.ActualHeight)

    @property
    def document_width(self):
        return self.width

    @property
    def vertical_scroll_position(self):
        sv = find_scroll_viewer(self.native)
        if sv is not None:
            return round(sv.VerticalOffset)
        return 0

    async def wait_for_scroll_completion(self):
        pass

    @property
    def text_align(self):
        return toga_x_text_align(self.native.TextAlignment)

    @property
    def redo_available(self):
        return False

    def set_cursor_at_end(self):
        self.native.SelectionStart = len(self.native.Text)
        self.native.SelectionLength = 0
