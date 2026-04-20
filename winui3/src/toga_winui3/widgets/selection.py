from contextlib import contextmanager

from win32more.Microsoft.UI.Xaml.Controls import ComboBox, ComboBoxItem

from toga.handlers import WeakrefCallable

from ._utils import unbounded_size
from .base import Widget


class Selection(Widget):
    native: ComboBox

    def create(self):
        self.native = ComboBox()
        self._items = []
        self._send_notifications = True
        self.native.add_SelectionChanged(WeakrefCallable(self.winui3_selection_changed))

    @contextmanager
    def suspend_notifications(self):
        self._send_notifications = False
        yield
        self._send_notifications = True

    def winui3_selection_changed(self, sender, event):
        if self._send_notifications:
            self.interface.on_change()

    ######################################################################
    # Source notifications (new listener API)
    ######################################################################

    def change_source(self, source):
        self.native.Items.Clear()
        self._items = []
        for i, item in enumerate(source):
            self._add_native_item(i, item)

    def source_insert(self, *, index, item):
        self._add_native_item(index, item)
        # Auto-select the first item if nothing is selected.
        if self.native.SelectedIndex == -1:
            self.native.SelectedIndex = 0

    def source_change(self, *, item):
        index = self.interface._items.index(item)
        with self.suspend_notifications():
            self.source_insert(index=index, item=item)
            self.source_remove(index=index + 1, item=item)
        # Changing the item text can change the layout size.
        self.interface.refresh()

    def source_remove(self, *, index, item):
        selection_change = self.get_selected_index() == index
        self.native.Items.RemoveAt(index)
        del self._items[index]

        # Removing the selected item: select an adjacent item if there is one.
        if selection_change:
            if self.native.Items.Size == 0:
                self.winui3_selection_changed(None, None)
            else:
                self.native.SelectedIndex = max(0, index - 1)

    def source_clear(self):
        self.native.Items.Clear()
        self._items = []
        self.winui3_selection_changed(None, None)

    ######################################################################
    # Selection
    ######################################################################

    def get_selected_index(self):
        index = self.native.SelectedIndex
        return None if index == -1 else index

    def select_item(self, index, item):
        self.native.SelectedIndex = index

    ######################################################################
    # Value access (legacy, used by some paths)
    ######################################################################

    def get_value(self):
        index = self.native.SelectedIndex
        if index < 0:
            return None
        return self._items[index]

    def set_value(self, value):
        if value is None:
            self.native.SelectedIndex = -1
        else:
            try:
                index = self._items.index(value)
                self.native.SelectedIndex = index
            except ValueError:
                self.native.SelectedIndex = -1

    ######################################################################
    # Layout
    ######################################################################

    def rehint(self):
        self.native.Measure(unbounded_size())
        self.interface.intrinsic.height = self.native.DesiredSize.Height

    ######################################################################
    # Helpers
    ######################################################################

    def _add_native_item(self, index, item):
        text = self.interface._title_for_item(item)
        native_item = ComboBoxItem()
        native_item.Content = text
        self.native.Items.InsertAt(index, native_item)
        self._items.insert(index, item)

    # Alias for backwards compatibility:
    # March 2026: In 0.5.3 and earlier, notification methods
    # didn't start with 'source_'
    def clear(self):
        import warnings

        warnings.warn(
            "The clear() method is deprecated. Use source_clear() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.source_clear()

    def insert(self, index, item):
        import warnings

        warnings.warn(
            "The insert() method is deprecated. Use source_insert() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.source_insert(index=index, item=item)

    def remove(self, index, item):
        import warnings

        warnings.warn(
            "The remove() method is deprecated. Use source_remove() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.source_remove(index=index, item=item)
