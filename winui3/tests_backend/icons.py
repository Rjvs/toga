from pathlib import Path

import PIL.Image
import pytest
import toga_winui3

from .probe import BaseProbe


class IconProbe(BaseProbe):
    alternate_resource = "resources/icons/blue"

    def __init__(self, app, icon):
        super().__init__()
        self.app = app
        self.icon = icon
        # WinUI 3 icons store their native as a pathlib.Path.
        assert isinstance(self.icon._impl.native, Path)

    def assert_icon_content(self, path):
        if path == "resources/icons/green":
            assert (
                self.icon._impl.path == self.app.paths.app / "resources/icons/green.ico"
            )
        elif path == "resources/icons/blue":
            assert (
                self.icon._impl.path == self.app.paths.app / "resources/icons/blue.png"
            )
        else:
            pytest.fail("Unknown icon resource")

    def assert_default_icon_content(self):
        assert (
            self.icon._impl.path
            == Path(toga_winui3.__file__).parent / "resources/toga.ico"
        )

    def assert_platform_icon_content(self):
        assert self.icon._impl.path == self.app.paths.app / "resources/logo-windows.ico"

    def assert_app_icon_content(self):
        # Load the icon file directly with PIL and pixel-peep.
        img = PIL.Image.open(self.icon._impl.path)

        # The default icon is transparent background, and brown in the center.
        assert img.getpixel((5, 5))[3] == 0
        mid_color = img.getpixel((img.size[0] // 2, img.size[1] // 2))
        assert mid_color == (130, 100, 57, 255)
