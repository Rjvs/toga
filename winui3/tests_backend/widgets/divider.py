from win32more.Microsoft.UI.Xaml.Controls import Border

from .base import SimpleProbe


class DividerProbe(SimpleProbe):
    native_class = Border
