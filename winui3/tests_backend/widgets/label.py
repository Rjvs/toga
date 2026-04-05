from win32more.Microsoft.UI.Xaml.Controls import TextBlock

from .base import SimpleProbe
from .properties import toga_x_text_align, toga_y_text_align


class LabelProbe(SimpleProbe):
    native_class = TextBlock

    @property
    def text(self):
        return self.native.Text

    @property
    def text_align(self):
        return toga_x_text_align(self.native.TextAlignment)

    def assert_vertical_text_align(self, expected):
        assert toga_y_text_align(self.native.VerticalAlignment) == expected
