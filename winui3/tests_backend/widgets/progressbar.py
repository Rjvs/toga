from win32more.Microsoft.UI.Xaml.Controls import ProgressBar

from .base import SimpleProbe


class ProgressBarProbe(SimpleProbe):
    native_class = ProgressBar

    @property
    def is_determinate(self):
        return not self.native.IsIndeterminate

    @property
    def is_animating_indeterminate(self):
        return self.native.IsIndeterminate

    @property
    def position(self):
        return self.native.Value / self.native.Maximum

    async def wait_for_animation(self):
        # WinUI 3 ProgressBar handles animation natively; no special handling.
        pass
