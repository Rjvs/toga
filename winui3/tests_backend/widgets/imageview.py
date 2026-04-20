from win32more.Microsoft.UI.Xaml.Controls import Image
from win32more.Microsoft.UI.Xaml.Media import Stretch

from .base import SimpleProbe


class ImageViewProbe(SimpleProbe):
    native_class = Image

    @property
    def preserve_aspect_ratio(self):
        return self.native.Stretch == Stretch.Uniform

    def assert_image_size(self, width, height):
        # WinUI 3 internally scales the image to the container,
        # so there's no image size check required.
        pass
