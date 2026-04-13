import datetime

from win32more.Microsoft.UI.Xaml.Controls import CalendarDatePicker
from win32more.Windows.Foundation import DateTime

from toga.handlers import WeakrefCallable

from ._utils import unbounded_size
from .base import Widget

# Offset between WinRT epoch (1601-01-01) and Python epoch (1970-01-01)
# in 100-nanosecond ticks.
_EPOCH_OFFSET_TICKS = 116444736000000000
_TICKS_PER_SECOND = 10_000_000
_TICKS_PER_DAY = _TICKS_PER_SECOND * 86400


def _py_date(native_dt):
    """Convert a WinRT DateTime to a Python date."""
    ticks = native_dt.UniversalTime
    # Convert ticks back to days since the WinRT epoch (1601-01-01) and
    # construct the date directly, avoiding timezone-dependent fromtimestamp().
    epoch = datetime.date(1601, 1, 1)
    days = ticks // _TICKS_PER_DAY
    return epoch + datetime.timedelta(days=days)


def _native_date(py_date):
    """Convert a Python date to a WinRT DateTime."""
    # Days from 1601-01-01 to the given date.
    epoch = datetime.date(1601, 1, 1)
    delta = py_date - epoch
    dt = DateTime()
    dt.UniversalTime = delta.days * _TICKS_PER_DAY
    return dt


class DateInput(Widget):
    def create(self):
        self.native = CalendarDatePicker()
        self.native.add_DateChanged(WeakrefCallable(self.winui3_date_changed))

    def get_value(self):
        native_date = self.native.Date
        if native_date is None:
            return None
        return _py_date(native_date)

    def set_value(self, value):
        if value is None:
            self.native.Date = None
        else:
            self.native.Date = _native_date(value)

    def get_min_date(self):
        return _py_date(self.native.MinDate)

    def set_min_date(self, value):
        if value is not None:
            self.native.MinDate = _native_date(value)

    def get_max_date(self):
        return _py_date(self.native.MaxDate)

    def set_max_date(self, value):
        if value is not None:
            self.native.MaxDate = _native_date(value)

    def rehint(self):
        self.native.Measure(unbounded_size())
        self.interface.intrinsic.height = self.native.DesiredSize.Height

    def winui3_date_changed(self, sender, args):
        self.interface.on_change()
