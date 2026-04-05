import pytest
from win32more.Microsoft.UI.Xaml.Controls import TabView

from .base import SimpleProbe


class OptionContainerProbe(SimpleProbe):
    native_class = TabView
    max_tabs = None
    disabled_tab_selectable = True

    def assert_supports_content_based_rehint(self):
        pytest.skip("Content-based rehinting not yet supported on this platform")

    def select_tab(self, index):
        self.native.SelectedIndex = index

    async def wait_for_tab(self, message):
        await self.redraw(message)

    def tab_enabled(self, index):
        return self.native.TabItems.GetAt(index).IsEnabled

    def assert_tab_icon(self, index, expected):
        actual = self.impl.get_option_icon(index)
        if expected is None:
            assert actual is None
        else:
            assert actual is not None
