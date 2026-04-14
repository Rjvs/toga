from win32more.Microsoft.UI.Xaml.Controls import Image as WinUIImage
from win32more.Microsoft.UI.Xaml.Media import Stretch

from toga.widgets.imageview import rehint_imageview

from .base import Widget


class ImageView(Widget):
    native: WinUIImage

    def create(self):
        self.native = WinUIImage()
        self.native.Stretch = Stretch.Uniform

    def set_image(self, image):
        if image:
            self.native.Source = image._impl.native
        else:
            self.native.Source = None

    def rehint(self):
        # WinUI 3 handles DPI scaling natively, so scale=1.
        width, height, aspect_ratio = rehint_imageview(
            self.interface.image, self.interface.style
        )
        self.interface.intrinsic.width = width
        self.interface.intrinsic.height = height
        if aspect_ratio is not None:
            self.native.Stretch = Stretch.Uniform
        else:
            self.native.Stretch = Stretch.Fill
