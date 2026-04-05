from datetime import timedelta

from toga_winui3.widgets.dateinput import _py_date
from win32more.Microsoft.UI.Xaml.Controls import CalendarDatePicker

from .base import SimpleProbe


class DateInputProbe(SimpleProbe):
    native_class = CalendarDatePicker
    supports_limits = True

    @property
    def value(self):
        native_date = self.native.Date
        if native_date is None:
            return None
        return _py_date(native_date)

    @property
    def min_value(self):
        return _py_date(self.native.MinDate)

    @property
    def max_value(self):
        return _py_date(self.native.MaxDate)

    async def change(self, delta):
        current = self.value
        if current is not None:
            new_date = current + timedelta(days=delta)
            self.widget.value = new_date
        await self.redraw(f"Change value by {delta} days")
