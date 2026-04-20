from win32more.Microsoft.UI.Xaml import TextAlignment
from win32more.Microsoft.UI.Xaml.Controls import (
    NumberBox,
    NumberBoxSpinButtonPlacementMode,
    TextBox,
)
from win32more.Microsoft.UI.Xaml.Media import VisualTreeHelper

from toga.handlers import WeakrefCallable

from ._utils import unbounded_size
from .base import Widget


def _find_inner_textbox(element):
    """Walk the visual tree to find the first TextBox descendant."""
    count = VisualTreeHelper.GetChildrenCount(element)
    for i in range(count):
        child = VisualTreeHelper.GetChild(element, i)
        if isinstance(child, TextBox):
            return child
        result = _find_inner_textbox(child)
        if result is not None:
            return result
    return None


class NumberInput(Widget):
    native: NumberBox

    def create(self):
        self.native = NumberBox()
        self.native.SpinButtonPlacementMode = NumberBoxSpinButtonPlacementMode.Inline
        self.native.add_ValueChanged(WeakrefCallable(self.winui3_value_changed))

        # Text alignment is applied to the inner TextBox, which only exists
        # once the control template is loaded.  Cache the pending value and
        # apply it in _apply_text_alignment after the control is loaded.
        self._pending_text_alignment = None
        self._inner_textbox = None
        self.native.add_Loaded(WeakrefCallable(self._on_loaded))

    def _on_loaded(self, sender, args):
        """Apply deferred text alignment once the visual tree is available."""
        if self._pending_text_alignment is not None:
            self._apply_text_alignment(self._pending_text_alignment)
            self._pending_text_alignment = None

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

    def set_text_align(self, value):
        alignment = {
            "left": TextAlignment.Left,
            "right": TextAlignment.Right,
            "center": TextAlignment.Center,
        }.get(str(value), TextAlignment.Left)

        if self._inner_textbox is not None or _find_inner_textbox(self.native):
            self._apply_text_alignment(alignment)
        else:
            # Control template not yet loaded; defer until Loaded event.
            self._pending_text_alignment = alignment

    def _apply_text_alignment(self, alignment):
        if self._inner_textbox is None:
            self._inner_textbox = _find_inner_textbox(self.native)
        if self._inner_textbox is not None:
            self._inner_textbox.TextAlignment = alignment

    def rehint(self):
        self.native.Measure(unbounded_size())
        self.interface.intrinsic.height = self.native.DesiredSize.Height

    def winui3_value_changed(self, sender, args):
        self.interface.on_change()
