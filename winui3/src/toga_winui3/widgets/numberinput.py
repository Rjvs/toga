from win32more.Microsoft.UI.Xaml.Controls import (
    NumberBox,
    NumberBoxSpinButtonPlacementMode,
)

from toga.handlers import WeakrefCallable

from ._utils import unbounded_size
from .base import Widget


class NumberInput(Widget):
    def create(self):
        self.native = NumberBox()
        self.native.SpinButtonPlacementMode = NumberBoxSpinButtonPlacementMode.Inline
        self.native.add_ValueChanged(WeakrefCallable(self.winui3_value_changed))

    def get_readonly(self):
        # NumberBox has no IsReadOnly property.  We use IsHitTestVisible +
        # IsTabStop to block interaction without graying out the control,
        # preserving the Toga contract of "non-editable but visually active".
        return not self.native.IsHitTestVisible

    def set_readonly(self, value):
        self.native.IsHitTestVisible = not value
        self.native.IsTabStop = not value

    def get_value(self):
        import math
        from decimal import Decimal

        val = self.native.Value
        if math.isnan(val):
            return None
        return Decimal(str(val))

    def set_value(self, value):
        if value is None:
            self.native.Value = float("nan")
        else:
            self.native.Value = float(value)

    def set_step(self, step):
        from decimal import Decimal

        self.native.SmallChange = float(step)
        # Compute the number of decimal places from the step value to
        # control display precision (matching WinForms DecimalPlaces).
        d = Decimal(str(step))
        fraction_digits = max(0, -d.as_tuple().exponent)
        self.native.NumberFormatter.FractionDigits = fraction_digits

    def set_min_value(self, value):
        self.native.Minimum = float(value) if value is not None else float("-inf")

    def set_max_value(self, value):
        self.native.Maximum = float(value) if value is not None else float("inf")

    def rehint(self):
        self.native.Measure(unbounded_size())
        self.interface.intrinsic.height = self.native.DesiredSize.Height

    def winui3_value_changed(self, sender, args):
        self.interface.on_change()
