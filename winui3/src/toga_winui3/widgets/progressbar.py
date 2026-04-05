from win32more.Microsoft.UI.Xaml.Controls import ProgressBar as WinUIProgressBar

from ._utils import unbounded_size
from .base import Widget

# Implementation notes
# ====================
#
# WinUI 3's ProgressBar has an IsIndeterminate property that controls the
# marquee animation.  However, Toga treats "running" and "indeterminate"
# as orthogonal concepts:
#   - A bar can be running + determinate  (shows progress + animating)
#   - A bar can be running + indeterminate (marquee animation)
#   - A bar can be stopped + determinate   (shows static progress)
#   - A bar can be stopped + indeterminate (shows empty/static)
#
# WinUI 3's IsIndeterminate only makes sense when both conditions are met
# (indeterminate AND running).  We track both states independently, matching
# the WinForms backend pattern.


class ProgressBar(Widget):
    def create(self):
        self.native = WinUIProgressBar()
        self.native.Minimum = 0
        self.native.Maximum = 1.0

        self._running = False
        self._determinate = True

    def is_running(self):
        return self._running

    def start(self):
        self._running = True
        self._update_style()

    def stop(self):
        self._running = False
        self._update_style()

    def get_max(self):
        if not self._determinate:
            return None
        return self.native.Maximum

    def set_max(self, value):
        if value is None:
            self._determinate = False
        else:
            self.native.Maximum = float(value)
            self._determinate = True
        self._update_style()

    def _update_style(self):
        # Show marquee animation only when both indeterminate AND running.
        self.native.IsIndeterminate = not self._determinate and self._running

    def get_value(self):
        if not self._determinate:
            return None
        return self.native.Value

    def set_value(self, value):
        self.native.Value = float(value)

    def rehint(self):
        self.native.Measure(unbounded_size())
        self.interface.intrinsic.height = self.native.DesiredSize.Height
