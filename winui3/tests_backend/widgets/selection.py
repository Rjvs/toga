from pytest import xfail
from win32more.Microsoft.UI.Xaml.Controls import ComboBox

from .base import SimpleProbe


class SelectionProbe(SimpleProbe):
    native_class = ComboBox

    def assert_resizes_on_content_change(self):
        xfail("Selection doesn't resize on content changes on this backend")

    @property
    def text_align(self):
        xfail("Can't change the text alignment of Selection on this backend")

    @property
    def titles(self):
        items = self.native.Items
        return [items.GetAt(i).Content for i in range(items.Size)]

    @property
    def selected_title(self):
        item = self.native.SelectedItem
        if item is None:
            return None
        return item.Content

    async def select_item(self):
        self.native.SelectedIndex = 1
