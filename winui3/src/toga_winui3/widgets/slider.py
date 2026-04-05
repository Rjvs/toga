from win32more.Microsoft.UI.Xaml.Controls import (
    Primitives,
    Slider as WinUISlider,
)

from toga.handlers import WeakrefCallable

from ._utils import unbounded_size
from .base import Widget

# WinUI 3's Slider uses doubles natively, so we can use Toga's actual
# min/max values directly without the integer mapping that WinForms requires.
# StepFrequency controls the resolution for continuous mode.
CONTINUOUS_STEP = 0.0001


class Slider(Widget):
    def create(self):
        self.native = WinUISlider()
        self.native.Minimum = 0.0
        self.native.Maximum = 1.0
        self.native.StepFrequency = CONTINUOUS_STEP
        self.native.add_ValueChanged(WeakrefCallable(self.winui3_value_changed))
        self.native.add_PointerPressed(WeakrefCallable(self.winui3_pointer_pressed))
        self.native.add_PointerReleased(WeakrefCallable(self.winui3_pointer_released))
        self.native.add_PointerCaptureLost(
            WeakrefCallable(self.winui3_pointer_released)
        )

    def get_value(self):
        return self.native.Value

    def set_value(self, value):
        self.native.Value = float(value)

    def get_tick_count(self):
        freq = self.native.TickFrequency
        if freq > 0:
            total_range = self.native.Maximum - self.native.Minimum
            return int(round(total_range / freq)) + 1
        return None

    def set_tick_count(self, tick_count):
        total_range = self.native.Maximum - self.native.Minimum
        if tick_count is not None:
            freq = total_range / (tick_count - 1)
            self.native.TickFrequency = freq
            # In discrete mode, step frequency matches tick frequency
            # so the slider snaps to tick positions.
            self.native.StepFrequency = freq
        else:
            self.native.TickFrequency = 0
            self.native.StepFrequency = CONTINUOUS_STEP

    def get_min(self):
        return self.native.Minimum

    def set_min(self, value):
        self.native.Minimum = float(value)

    def get_max(self):
        return self.native.Maximum

    def set_max(self, value):
        self.native.Maximum = float(value)

    def set_ticks_visible(self, visible):
        self.native.TickPlacement = (
            Primitives.TickPlacement.Outside
            if visible
            else Primitives.TickPlacement.None_
        )

    def rehint(self):
        self.native.Measure(unbounded_size())
        self.interface.intrinsic.height = self.native.DesiredSize.Height

    def winui3_value_changed(self, sender, args):
        self.interface.on_change()

    def winui3_pointer_pressed(self, sender, args):
        self.interface.on_press()

    def winui3_pointer_released(self, sender, args):
        self.interface.on_release()
