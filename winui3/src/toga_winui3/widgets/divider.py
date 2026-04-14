from win32more.Microsoft.UI.Xaml.Controls import Border

from ._utils import theme_brush
from .base import Widget

# Neutral gray fallback for when no theme resource is available.
_DIVIDER_FALLBACK = (255, 200, 200, 200)


class Divider(Widget):
    native: Border

    HORIZONTAL = 0
    VERTICAL = 1

    def create(self):
        self.native = Border()
        self._direction = self.interface.HORIZONTAL

        # Use a WinUI 3 theme resource so the divider adapts to
        # light/dark theme automatically.
        brush = theme_brush(
            "DividerStrokeColorDefaultBrush",
            fallback_rgba=_DIVIDER_FALLBACK,
        )
        if brush is not None:
            self.native.Background = brush

    def get_direction(self):
        return self._direction

    def set_direction(self, value):
        self._direction = value
        self.interface.refresh()

    def set_background_color(self, value):
        # Divider background color should not be changed by the user.
        pass

    def rehint(self):
        if self._direction == self.HORIZONTAL:
            self.interface.intrinsic.height = 1
        else:
            self.interface.intrinsic.width = 1
