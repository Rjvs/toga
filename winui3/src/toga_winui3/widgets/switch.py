from travertino.size import at_least
from win32more.Microsoft.UI.Xaml.Controls import ToggleSwitch

from toga.handlers import WeakrefCallable

from ._utils import unbounded_size
from .base import Widget


class Switch(Widget):
    def create(self):
        self.native = ToggleSwitch()
        self.native.add_Toggled(WeakrefCallable(self.winui3_toggled))

    def get_text(self):
        return self.native.Header or ""

    def set_text(self, text):
        # Zero-width space prevents ToggleSwitch layout collapse with empty Header.
        self.native.Header = text or "\u200b"

    def get_value(self):
        return self.native.IsOn

    def set_value(self, value):
        self.native.IsOn = bool(value)

    def rehint(self):
        self.native.Measure(unbounded_size())
        desired = self.native.DesiredSize
        self.interface.intrinsic.width = at_least(desired.Width)
        self.interface.intrinsic.height = desired.Height

    def winui3_toggled(self, sender, event):
        self.interface.on_change()
