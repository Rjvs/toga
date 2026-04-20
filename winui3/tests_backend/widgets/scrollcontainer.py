from win32more.Microsoft.UI.Xaml.Controls import ScrollViewer

from .base import SimpleProbe


class ScrollContainerProbe(SimpleProbe):
    native_class = ScrollViewer
    # WinUI 3 uses overlay scrollbars, so the inset is smaller.
    scrollbar_inset = 0
    frame_inset = 0

    def __init__(self, widget):
        super().__init__(widget)
        self.native_content = self.impl._content_canvas

    @property
    def has_content(self):
        return self.native_content.Children.Size > 0

    @property
    def document_height(self):
        return round(self.native_content.ActualHeight / self.scale_factor)

    @property
    def document_width(self):
        return round(self.native_content.ActualWidth / self.scale_factor)

    async def scroll(self):
        if self.document_height > self.height:
            self.native.ChangeView(None, 100, None)

    async def wait_for_scroll_completion(self):
        pass
