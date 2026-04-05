from win32more.Microsoft.UI.Xaml.Controls import ToggleSwitch

from .base import SimpleProbe


class SwitchProbe(SimpleProbe):
    native_class = ToggleSwitch

    @property
    def text(self):
        header = self.native.Header
        # Normalize the zero width space to the empty string.
        if header == "\u200b":
            return ""
        return header or ""
