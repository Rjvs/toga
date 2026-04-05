from win32more.Microsoft.UI.Xaml.Controls import (
    TabView,
    TabViewItem,
)

from toga.handlers import WeakrefCallable

from ..container import Container
from .base import Widget

# Default height of the TabView tab strip in DIPs.
TAB_STRIP_HEIGHT = 40


class OptionContainer(Widget):
    uses_icons = True

    def create(self):
        self.native = TabView()
        self.native.IsAddTabButtonVisible = False
        self.native.add_SelectionChanged(WeakrefCallable(self.winui3_selection_changed))
        self.panels = []
        self._icons = []

    def add_option(self, index, text, widget, icon):
        item = TabViewItem()
        item.Header = text
        item.IsClosable = False
        if icon is not None:
            item.IconSource = icon._impl._as_bitmap_icon_source()
        self.native.TabItems.InsertAt(index, item)
        self._icons.insert(index, icon)

        panel = Container(item)
        self.panels.insert(index, panel)
        panel.set_content(widget)

    def remove_option(self, index):
        panel = self.panels.pop(index)
        self._icons.pop(index)
        panel.clear_content()
        self.native.TabItems.RemoveAt(index)

    def set_option_enabled(self, index, enabled):
        self.native.TabItems.GetAt(index).IsEnabled = enabled

    def is_option_enabled(self, index):
        return self.native.TabItems.GetAt(index).IsEnabled

    def set_option_text(self, index, value):
        self.native.TabItems.GetAt(index).Header = value

    def get_option_text(self, index):
        return self.native.TabItems.GetAt(index).Header

    def set_option_icon(self, index, icon):
        self._icons[index] = icon
        tab_item = self.native.TabItems.GetAt(index)
        if icon is not None:
            tab_item.IconSource = icon._impl._as_bitmap_icon_source()
        else:
            tab_item.IconSource = None

    def get_option_icon(self, index):
        return self._icons[index]

    def set_current_tab_index(self, current_tab_index):
        self.native.SelectedIndex = current_tab_index

    def get_current_tab_index(self):
        return self.native.SelectedIndex

    def winui3_selection_changed(self, sender, args):
        self.interface.on_select()
        index = self.native.SelectedIndex
        if 0 <= index < len(self.panels):
            self._resize_panel(self.panels[index])

    def set_bounds(self, x, y, width, height):
        super().set_bounds(x, y, width, height)
        for panel in self.panels:
            self._resize_panel(panel)

    def _resize_panel(self, panel):
        width = self.native.ActualWidth
        height = self.native.ActualHeight
        if width > 0 and height > 0:
            content_height = max(0, height - TAB_STRIP_HEIGHT)
            panel.resize_content(width, content_height)

    def rehint(self):
        pass
