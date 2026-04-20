from travertino.size import at_least
from win32more.Microsoft.UI.Xaml import Thickness
from win32more.Microsoft.UI.Xaml.Controls import (
    Button as WinUIButton,
    Image,
    Orientation,
    StackPanel,
    TextBlock,
)
from win32more.Microsoft.UI.Xaml.Media import Stretch

from toga.handlers import WeakrefCallable

from ._utils import unbounded_size
from .base import Widget


class Button(Widget):
    native: WinUIButton

    def create(self):
        self.native = WinUIButton()
        self.native.add_Click(WeakrefCallable(self.winui3_click))
        self._icon = None
        self._text = "\u200b"

    def winui3_click(self, sender, event):
        self.interface.on_press()

    def get_text(self):
        return "" if self._text == "\u200b" else self._text

    def set_text(self, text):
        self._text = text if text else "\u200b"
        # Rebuild the Content to reflect the new text.
        if self._icon:
            self.set_icon(self._icon)
        else:
            self.native.Content = self._text

    def get_icon(self):
        return self._icon

    def set_icon(self, icon):
        self._icon = icon
        if icon:
            panel = StackPanel()
            panel.Orientation = Orientation.Horizontal

            img = Image()
            img.Source = icon._impl._as_bitmap_image()
            img.Width = 16
            img.Height = 16
            img.Stretch = Stretch.Uniform
            panel.Children.Append(img)

            text = self.get_text()
            if text:
                tb = TextBlock()
                tb.Text = text
                tb.Margin = Thickness(4, 0, 0, 0)
                panel.Children.Append(tb)

            self.native.Content = panel
        else:
            # Restore text-only content.
            self.native.Content = self._text

    def rehint(self):
        self.native.Measure(unbounded_size())
        desired = self.native.DesiredSize
        self.interface.intrinsic.width = at_least(desired.Width)
        self.interface.intrinsic.height = desired.Height
