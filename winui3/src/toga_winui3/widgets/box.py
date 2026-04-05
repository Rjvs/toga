from win32more.Microsoft.UI.Xaml.Controls import Canvas

from .base import Widget


class Box(Widget):
    def create(self):
        # Box is a pure container - uses Canvas for absolute positioning
        # just like the window's content container.
        self.native = Canvas()
