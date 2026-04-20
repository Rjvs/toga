from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage
from win32more.Microsoft.UI.Xaml.Media.Imaging import BitmapImage
from win32more.Windows.Storage.Streams import (
    DataWriter,
    InMemoryRandomAccessStream,
)

from toga.images import ImageLoadError


class Image:
    RAW_TYPE = BitmapImage

    def __init__(self, interface, data=None, raw=None):
        self.interface = interface
        self._data = None

        if data is not None:
            self._data = bytes(data)
            try:
                self.native = _bitmap_image_from_bytes(self._data)
            except Exception as exc:
                raise ImageLoadError from exc
        elif raw is not None:
            self.native = raw
        else:
            self.native = BitmapImage()

    def get_width(self):
        return self.native.PixelWidth

    def get_height(self):
        return self.native.PixelHeight

    def get_data(self):
        """Return image data in PNG format, as required by the Toga contract."""
        raw = self._get_raw_bytes()
        if not raw:
            return b""
        buf = BytesIO()
        PILImage.open(BytesIO(raw)).save(buf, format="PNG")
        return buf.getvalue()

    def _get_raw_bytes(self):
        """Return the original image bytes (any format), or empty bytes."""
        if self._data is not None:
            return self._data
        uri = self.native.UriSource
        if uri is not None:
            try:
                local_path = uri.LocalPath
                if local_path:
                    return Path(local_path).read_bytes()
            except Exception:
                pass
        return b""

    def save(self, path):
        path = Path(path)
        FORMAT_MAP = {
            ".png": "PNG",
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".gif": "GIF",
            ".bmp": "BMP",
            ".tiff": "TIFF",
        }
        fmt = FORMAT_MAP.get(path.suffix.lower())
        if fmt is None:
            raise ValueError(f"Don't know how to save image of type {path.suffix!r}")

        raw = self._get_raw_bytes()
        if not raw:
            raise RuntimeError("No image data available to save")

        PILImage.open(BytesIO(raw)).save(path, format=fmt)


def _bitmap_image_from_bytes(data):
    """Create a BitmapImage from raw image bytes (synchronous).

    Uses .GetResults() to synchronously complete WinRT async operations
    (StoreAsync/FlushAsync) before seeking the stream.
    """
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.WriteBytes(data)
    writer.StoreAsync().GetResults()
    writer.FlushAsync().GetResults()
    stream.Seek(0)

    bmp = BitmapImage()
    bmp.SetSource(stream)
    return bmp
