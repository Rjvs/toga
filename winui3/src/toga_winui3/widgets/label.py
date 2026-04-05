from travertino.size import at_least
from win32more.Microsoft.UI.Xaml import TextAlignment
from win32more.Microsoft.UI.Xaml.Controls import TextBlock, TextWrapping

from ._utils import unbounded_size
from .base import Widget


class Label(Widget):
    def create(self):
        self.native = TextBlock()
        self.native.TextWrapping = TextWrapping.NoWrap

    def set_text_align(self, value):
        self.native.TextAlignment = {
            "left": TextAlignment.Left,
            "right": TextAlignment.Right,
            "center": TextAlignment.Center,
            "justify": TextAlignment.Justify,
        }.get(str(value), TextAlignment.Left)

    def get_text(self):
        return self.native.Text

    def set_text(self, value):
        self.native.Text = value

    def rehint(self):
        # TextBlock measures itself; we can read DesiredSize after Measure().
        self.native.Measure(unbounded_size())
        desired = self.native.DesiredSize
        self.interface.intrinsic.width = at_least(desired.Width)
        self.interface.intrinsic.height = desired.Height
