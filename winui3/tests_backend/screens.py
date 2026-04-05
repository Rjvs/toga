from toga_winui3.screens import Screen as WinUI3Screen

from toga.images import Image as TogaImage

from .probe import BaseProbe


class ScreenProbe(BaseProbe):
    def __init__(self, screen):
        super().__init__()
        self.screen = screen
        self._impl = screen._impl
        assert isinstance(self._impl, WinUI3Screen)

    def get_screenshot(self, format=TogaImage):
        return self.screen.as_image(format=format)
