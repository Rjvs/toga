from pathlib import Path

from win32more.Microsoft.UI.Xaml.Controls import (
    BitmapIconSource,
)
from win32more.Microsoft.UI.Xaml.Media.Imaging import BitmapImage
from win32more.Windows.Foundation import Uri


class Icon:
    EXTENSIONS = [".ico", ".png", ".bmp"]
    SIZES = None

    def __init__(self, interface, path):
        self.interface = interface
        if path is None:
            # Default app icon — use the bundled toga.ico resource.
            self.path = Path(__file__).parent / "resources" / "toga.ico"
        else:
            self.path = Path(path)

        if not self.path.exists():
            raise ValueError(f"Unable to load icon from {self.path}")

        # Store the path as native; WinUI 3 APIs that need icons accept
        # file paths (AppWindow.SetIcon) or URIs (BitmapIcon).
        self.native = self.path

    def _as_uri(self):
        """Return a file:// URI for this icon."""
        return Uri(self.path.as_uri())

    def _as_bitmap_icon_source(self):
        """Return a BitmapIconSource (for TabViewItem.IconSource etc.)."""
        source = BitmapIconSource()
        source.UriSource = self._as_uri()
        source.ShowAsMonochrome = False
        return source

    def _as_bitmap_image(self):
        """Return a BitmapImage (for Image controls)."""
        bmp = BitmapImage()
        bmp.UriSource = self._as_uri()
        return bmp
