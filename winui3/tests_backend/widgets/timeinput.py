from datetime import time, timedelta

from toga_winui3.widgets.timeinput import _py_time
from win32more.Microsoft.UI.Xaml.Controls import TimePicker

from .base import SimpleProbe


class TimeInputProbe(SimpleProbe):
    native_class = TimePicker
    supports_limits = False
    supports_seconds = False

    @property
    def value(self):
        return _py_time(self.native.Time)

    @property
    def min_value(self):
        # TimePicker doesn't support min/max.
        return None

    @property
    def max_value(self):
        # TimePicker doesn't support min/max.
        return None

    async def change(self, delta):
        current = self.value
        # Create a timedelta from the current time and add delta minutes.
        dt = timedelta(hours=current.hour, minutes=current.minute + delta)
        total_seconds = int(dt.total_seconds()) % 86400
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        self.widget.value = time(h, m, s)
        await self.redraw(f"Change value by {delta} minutes")
