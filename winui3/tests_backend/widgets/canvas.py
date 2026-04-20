from io import BytesIO

from PIL import Image
from win32more.Microsoft.Graphics.Canvas.UI.Xaml import CanvasControl

from ..probe import (
    MOUSEEVENTF_LEFTDOWN,
    MOUSEEVENTF_LEFTUP,
    MOUSEEVENTF_MOVE,
    MOUSEEVENTF_RIGHTDOWN,
    MOUSEEVENTF_RIGHTUP,
)
from .base import SimpleProbe


class CanvasProbe(SimpleProbe):
    native_class = CanvasControl

    def reference_variant(self, reference):
        if reference in {
            "multiline_text",
            "write_text",
            "write_text_and_path",
            "miter_join",
        }:
            return f"{reference}-winui3"
        return reference

    def get_image(self):
        return Image.open(BytesIO(self.impl.get_image_data()))

    async def mouse_press(self, x, y, **kwargs):
        await self._send_mouse_event(self.native, x, y, MOUSEEVENTF_LEFTDOWN)
        await self._send_mouse_event(self.native, x, y, MOUSEEVENTF_LEFTUP)

    async def mouse_activate(self, x, y, **kwargs):
        # First click
        await self._send_mouse_event(self.native, x, y, MOUSEEVENTF_LEFTDOWN)
        await self._send_mouse_event(self.native, x, y, MOUSEEVENTF_LEFTUP)
        # Second click triggers DoubleTapped
        await self._send_mouse_event(self.native, x, y, MOUSEEVENTF_LEFTDOWN)
        await self._send_mouse_event(self.native, x, y, MOUSEEVENTF_LEFTUP)

    async def mouse_drag(self, x1, y1, x2, y2, **kwargs):
        mid_x, mid_y = (x1 + x2) // 2, (y1 + y2) // 2

        # Move without a button pressed should be ignored.
        await self._send_mouse_event(self.native, mid_x, mid_y, MOUSEEVENTF_MOVE)

        # Press, drag, release.
        await self._send_mouse_event(self.native, x1, y1, MOUSEEVENTF_LEFTDOWN)
        await self._send_mouse_event(self.native, mid_x, mid_y, MOUSEEVENTF_MOVE)
        await self._send_mouse_event(self.native, x2, y2, MOUSEEVENTF_LEFTUP)

    async def alt_mouse_press(self, x, y):
        await self._send_mouse_event(self.native, x, y, MOUSEEVENTF_RIGHTDOWN)
        await self._send_mouse_event(self.native, x, y, MOUSEEVENTF_RIGHTUP)

    async def alt_mouse_drag(self, x1, y1, x2, y2):
        mid_x, mid_y = (x1 + x2) // 2, (y1 + y2) // 2

        # Move without a button pressed should be ignored.
        await self._send_mouse_event(self.native, mid_x, mid_y, MOUSEEVENTF_MOVE)

        # Press, drag, release.
        await self._send_mouse_event(self.native, x1, y1, MOUSEEVENTF_RIGHTDOWN)
        await self._send_mouse_event(self.native, mid_x, mid_y, MOUSEEVENTF_MOVE)
        await self._send_mouse_event(self.native, x2, y2, MOUSEEVENTF_RIGHTUP)
