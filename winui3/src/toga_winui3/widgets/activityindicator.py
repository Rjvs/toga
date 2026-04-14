from win32more.Microsoft.UI.Xaml.Controls import ProgressRing

from ._utils import unbounded_size
from .base import Widget


class ActivityIndicator(Widget):
    native: ProgressRing

    def create(self):
        self.native = ProgressRing()
        self.native.IsActive = False
        self._running = False
        self._hidden = False

    def is_running(self):
        return self._running

    def start(self):
        self._running = True
        self.native.IsActive = True
        if not self._hidden:
            from win32more.Microsoft.UI.Xaml import Visibility

            self.native.Visibility = Visibility.Visible

    def stop(self):
        self._running = False
        self.native.IsActive = False
        from win32more.Microsoft.UI.Xaml import Visibility

        self.native.Visibility = Visibility.Collapsed

    def set_hidden(self, hidden):
        from win32more.Microsoft.UI.Xaml import Visibility

        self._hidden = hidden
        # Only visible when running AND not hidden.
        if self._running and not hidden:
            self.native.Visibility = Visibility.Visible
        else:
            self.native.Visibility = Visibility.Collapsed

    def rehint(self):
        self.native.Measure(unbounded_size())
        desired = self.native.DesiredSize
        self.interface.intrinsic.width = desired.Width
        self.interface.intrinsic.height = desired.Height
