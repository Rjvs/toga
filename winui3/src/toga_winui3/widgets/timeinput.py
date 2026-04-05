import datetime

from win32more.Microsoft.UI.Xaml.Controls import TimePicker as WinUITimePicker
from win32more.Windows.Foundation import TimeSpan

from toga.handlers import WeakrefCallable

from ._utils import unbounded_size
from .base import Widget

_TICKS_PER_SECOND = 10_000_000


def _py_time(native_ts):
    """Convert a WinRT TimeSpan to a Python time."""
    total_seconds = native_ts.Duration // _TICKS_PER_SECOND
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return datetime.time(hours, minutes, seconds)


def _native_time(py_time):
    """Convert a Python time to a WinRT TimeSpan."""
    total_seconds = py_time.hour * 3600 + py_time.minute * 60 + py_time.second
    ts = TimeSpan()
    ts.Duration = total_seconds * _TICKS_PER_SECOND
    return ts


class TimeInput(Widget):
    def create(self):
        self.native = WinUITimePicker()
        self.native.add_TimeChanged(WeakrefCallable(self.winui3_time_changed))
        self._min_time = datetime.time(0, 0, 0)
        self._max_time = datetime.time(23, 59, 59)

    def get_value(self):
        return _py_time(self.native.Time)

    def set_value(self, value):
        if value is not None:
            self.native.Time = _native_time(value)

    def get_min_time(self):
        return self._min_time

    def set_min_time(self, value):
        if value is not None:
            self._min_time = value

    def get_max_time(self):
        return self._max_time

    def set_max_time(self, value):
        if value is not None:
            self._max_time = value

    def rehint(self):
        self.native.Measure(unbounded_size())
        self.interface.intrinsic.height = self.native.DesiredSize.Height

    def winui3_time_changed(self, sender, args):
        # Clamp value to min/max range since WinUI3 TimePicker has no
        # native min/max constraint.  Setting self.native.Time re-triggers
        # TimeChanged, so return after clamping to avoid double-firing.
        current = _py_time(self.native.Time)
        if current < self._min_time:
            self.native.Time = _native_time(self._min_time)
            return
        elif current > self._max_time:
            self.native.Time = _native_time(self._max_time)
            return
        self.interface.on_change()
