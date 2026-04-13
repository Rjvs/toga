from win32more.Microsoft.UI.Text import FontWeights
from win32more.Microsoft.UI.Xaml import Thickness
from win32more.Microsoft.UI.Xaml.Controls import (
    Image,
    ListView,
    ListViewSelectionMode,
    MenuFlyout,
    MenuFlyoutItem,
    Orientation,
    StackPanel,
    TextBlock,
)
from win32more.Microsoft.UI.Xaml.Media import Stretch

import toga
from toga.handlers import WeakrefCallable

from .base import Widget


class DetailedList(Widget):
    def create(self):
        self.native = ListView()
        self.native.SelectionMode = ListViewSelectionMode.Single
        self.native.add_SelectionChanged(WeakrefCallable(self.winui3_selection_changed))
        self.native.add_DoubleTapped(WeakrefCallable(self.winui3_double_tapped))

        # Context menu for primary/secondary actions.
        self._flyout = MenuFlyout()
        self._primary_action_item = MenuFlyoutItem()
        self._primary_action_item.Text = self.interface._primary_action or "Delete"
        self._primary_action_item.add_Click(WeakrefCallable(self.winui3_primary_action))
        self._secondary_action_item = MenuFlyoutItem()
        self._secondary_action_item.Text = self.interface._secondary_action or "Action"
        self._secondary_action_item.add_Click(
            WeakrefCallable(self.winui3_secondary_action)
        )
        self._flyout.Items.Append(self._primary_action_item)
        self._flyout.Items.Append(self._secondary_action_item)
        self.native.ContextFlyout = self._flyout

        self._primary_action_enabled = False
        self._secondary_action_enabled = False

    ######################################################################
    # Row building
    ######################################################################

    def _get_row_data(self, item):
        title = getattr(item, self.interface.accessors[0], None)
        subtitle = getattr(item, self.interface.accessors[1], None)
        icon = getattr(item, self.interface.accessors[2], None)
        title = str(title) if title is not None else self.interface.missing_value
        subtitle = (
            str(subtitle) if subtitle is not None else self.interface.missing_value
        )
        return title, subtitle, icon

    def _build_row(self, item):
        title_text, subtitle_text, icon = self._get_row_data(item)

        title = TextBlock()
        title.Text = title_text
        title.FontWeight = FontWeights.SemiBold

        subtitle = TextBlock()
        subtitle.Text = subtitle_text
        subtitle.FontSize = 12
        subtitle.Opacity = 0.6

        text_stack = StackPanel()
        text_stack.Orientation = Orientation.Vertical
        text_stack.Children.Append(title)
        text_stack.Children.Append(subtitle)

        row_panel = StackPanel()
        row_panel.Orientation = Orientation.Horizontal
        row_panel.Padding = Thickness(0, 4, 0, 4)

        if icon is not None:
            icon = toga.Icon(icon) if not isinstance(icon, toga.Icon) else icon
            img = Image()
            img.Source = icon._impl._as_bitmap_image()
            img.Width = 40
            img.Height = 40
            img.Stretch = Stretch.Uniform
            img.Margin = Thickness(0, 0, 8, 0)
            row_panel.Children.Append(img)

        row_panel.Children.Append(text_stack)

        return row_panel

    ######################################################################
    # Source notifications
    ######################################################################

    def change_source(self, source):
        self.native.Items.Clear()
        for item in source:
            self.native.Items.Append(self._build_row(item))

    def source_insert(self, *, index, item):
        self.native.Items.InsertAt(index, self._build_row(item))

    def source_change(self, *, item):
        index = self.interface.data.index(item)
        self.native.Items.SetAt(index, self._build_row(item))

    def source_remove(self, *, index, item):
        self.native.Items.RemoveAt(index)

    def source_clear(self):
        self.native.Items.Clear()

    # Alias for backwards compatibility:
    # March 2026: In 0.5.3 and earlier, notification methods
    # didn't start with 'source_'
    def insert(self, index, item):
        import warnings

        warnings.warn(
            "The insert() method is deprecated. Use source_insert() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.source_insert(index=index, item=item)

    def change(self, item):
        import warnings

        warnings.warn(
            "The change() method is deprecated. Use source_change() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.source_change(item=item)

    def remove(self, index, item):
        import warnings

        warnings.warn(
            "The remove() method is deprecated. Use source_remove() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.source_remove(index=index, item=item)

    def clear(self):
        import warnings

        warnings.warn(
            "The clear() method is deprecated. Use source_clear() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.source_clear()

    ######################################################################
    # Selection
    ######################################################################

    def winui3_selection_changed(self, sender, args):
        self.interface.on_select()

    def winui3_double_tapped(self, sender, args):
        index = self.native.SelectedIndex
        if index >= 0:
            self.interface.on_activate(row=self.interface.data[index])

    def get_selection(self):
        index = self.native.SelectedIndex
        return None if index < 0 else index

    def set_selection(self, selection):
        self.native.SelectedIndex = selection if selection is not None else -1

    ######################################################################
    # Actions
    ######################################################################

    def winui3_primary_action(self, sender, args):
        index = self.native.SelectedIndex
        if index >= 0:
            self.interface.on_primary_action(row=self.interface.data[index])

    def winui3_secondary_action(self, sender, args):
        index = self.native.SelectedIndex
        if index >= 0:
            self.interface.on_secondary_action(row=self.interface.data[index])

    def set_primary_action_enabled(self, enabled):
        self._primary_action_enabled = enabled
        from win32more.Microsoft.UI.Xaml import Visibility

        self._primary_action_item.Visibility = (
            Visibility.Visible if enabled else Visibility.Collapsed
        )

    def set_secondary_action_enabled(self, enabled):
        self._secondary_action_enabled = enabled
        from win32more.Microsoft.UI.Xaml import Visibility

        self._secondary_action_item.Visibility = (
            Visibility.Visible if enabled else Visibility.Collapsed
        )

    def set_refresh_enabled(self, enabled):
        # No native pull-to-refresh on desktop Windows.
        pass

    after_on_refresh = None

    ######################################################################
    # Scroll
    ######################################################################

    def scroll_to_row(self, row):
        if 0 <= row < self.native.Items.Size:
            item = self.native.Items.GetAt(row)
            self.native.ScrollIntoView(item)

    ######################################################################
    # Layout
    ######################################################################

    def rehint(self):
        pass
