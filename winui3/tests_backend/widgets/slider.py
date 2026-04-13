from win32more.Microsoft.UI.Xaml.Controls import Slider

from .base import SimpleProbe


class SliderProbe(SimpleProbe):
    native_class = Slider

    @property
    def position(self):
        return (self.native.Value - self._min) / (self._max - self._min)

    async def change(self, position):
        self.native.Value = self._min + round(position * (self._max - self._min))

    @property
    def tick_count(self):
        freq = self.native.TickFrequency
        if freq > 0:
            return int((self._max - self._min) / freq) + 1
        return None

    @property
    def _min(self):
        return self.native.Minimum

    @property
    def _max(self):
        return self.native.Maximum

    async def press(self):
        if hasattr(self.impl, "winui3_pointer_pressed"):
            self.impl.winui3_pointer_pressed(self.native, None)

    async def release(self):
        if hasattr(self.impl, "winui3_pointer_released"):
            self.impl.winui3_pointer_released(self.native, None)
