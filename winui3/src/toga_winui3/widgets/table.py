from win32more.Microsoft.UI.Text import FontWeights
from win32more.Microsoft.UI.Xaml import (
    GridLength,
    GridUnitType,
    Thickness,
    Visibility,
)
from win32more.Microsoft.UI.Xaml.Controls import (
    ColumnDefinition,
    Grid,
    Image,
    ListView,
    ListViewSelectionMode,
    Orientation,
    RowDefinition,
    StackPanel,
    TextBlock,
)
from win32more.Microsoft.UI.Xaml.Media import Stretch

from toga.handlers import WeakrefCallable

from .base import Widget


class Table(Widget):
    native: Grid

    def create(self):
        self.native = Grid()

        # Header row definition (Auto height).
        rd_header = RowDefinition()
        rd_header.Height = GridLength(0, GridUnitType.Auto)
        self.native.RowDefinitions.Append(rd_header)

        # ListView row definition (Star — fills remaining space).
        rd_list = RowDefinition()
        rd_list.Height = GridLength(1, GridUnitType.Star)
        self.native.RowDefinitions.Append(rd_list)

        # Column header grid.
        self._header = Grid()
        self._header.Padding = Thickness(4, 4, 0, 4)
        Grid.SetRow(self._header, 0)
        self.native.Children.Append(self._header)

        # Native ListView.
        self._list_view = ListView()
        self._list_view.SelectionMode = (
            ListViewSelectionMode.Multiple
            if getattr(self.interface, "multiple_select", False)
            else ListViewSelectionMode.Single
        )
        self._list_view.add_SelectionChanged(
            WeakrefCallable(self.winui3_selection_changed)
        )
        self._list_view.add_DoubleTapped(WeakrefCallable(self.winui3_double_tapped))
        Grid.SetRow(self._list_view, 1)
        self.native.Children.Append(self._list_view)

        self._build_header()

    ######################################################################
    # Column header
    ######################################################################

    def _build_header(self):
        self._header.ColumnDefinitions.Clear()
        self._header.Children.Clear()

        columns = self.interface.columns
        show = getattr(self.interface, "show_headings", True)
        self._header.Visibility = Visibility.Visible if show else Visibility.Collapsed

        for i, column in enumerate(columns):
            cd = ColumnDefinition()
            cd.Width = GridLength(1, GridUnitType.Star)
            self._header.ColumnDefinitions.Append(cd)

            tb = TextBlock()
            tb.Text = column.heading or ""
            tb.FontWeight = FontWeights.SemiBold
            tb.Margin = Thickness(4, 0, 4, 0)
            Grid.SetColumn(tb, i)
            self._header.Children.Append(tb)

    ######################################################################
    # Row content building
    ######################################################################

    def _build_cell_content(self, column, item, missing):
        """Build cell content for a single column: icon + text or just text."""
        text = column.text(item, default=missing)
        icon = column.icon(item)

        tb = TextBlock()
        tb.Text = str(text) if text is not None else ""

        if icon is None:
            tb.Margin = Thickness(4, 2, 4, 2)
            return tb

        panel = StackPanel()
        panel.Orientation = Orientation.Horizontal
        panel.Margin = Thickness(4, 2, 4, 2)

        img = Image()
        img.Source = icon._impl._as_bitmap_image()
        img.Width = 16
        img.Height = 16
        img.Stretch = Stretch.Uniform
        panel.Children.Append(img)

        tb.Margin = Thickness(4, 0, 0, 0)
        panel.Children.Append(tb)

        return panel

    def _build_row_content(self, item):
        """Build a Grid with one cell per column for a table row."""
        columns = self.interface.columns
        missing = self.interface.missing_value

        row_grid = Grid()
        for i, column in enumerate(columns):
            cd = ColumnDefinition()
            cd.Width = GridLength(1, GridUnitType.Star)
            row_grid.ColumnDefinitions.Append(cd)

            cell = self._build_cell_content(column, item, missing)
            Grid.SetColumn(cell, i)
            row_grid.Children.Append(cell)

        return row_grid

    def _rebuild_all_content(self):
        """Rebuild all row content grids after column changes."""
        for i, item in enumerate(self.interface.data):
            self._list_view.Items.SetAt(i, self._build_row_content(item))

    ######################################################################
    # Source notifications
    ######################################################################

    def change_source(self, source):
        self._list_view.Items.Clear()
        if source is not None:
            for item in source:
                self._list_view.Items.Append(self._build_row_content(item))

    def source_insert(self, *, index, item):
        self._list_view.Items.InsertAt(index, self._build_row_content(item))

    def source_change(self, *, item):
        index = self.interface.data.index(item)
        self._list_view.Items.SetAt(index, self._build_row_content(item))

    def source_remove(self, *, index, item):
        self._list_view.Items.RemoveAt(index)

    def source_clear(self):
        self._list_view.Items.Clear()

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
        index = self._list_view.SelectedIndex
        if index >= 0:
            self.interface.on_activate(row=self.interface.data[index])

    def get_selection(self):
        if getattr(self.interface, "multiple_select", False):
            result = []
            selected = self._list_view.SelectedItems
            items = self._list_view.Items
            for i in range(selected.Size):
                found, index = items.IndexOf(selected.GetAt(i))
                if found:
                    result.append(index)
            return result
        else:
            index = self._list_view.SelectedIndex
            return None if index < 0 else index

    def set_selection(self, selection):
        if selection is None or selection == []:
            self._list_view.SelectedIndex = -1
            return

        if getattr(self.interface, "multiple_select", False):
            from win32more.Microsoft.UI.Xaml.Data import ItemIndexRange

            # Clear current selection using the documented API.
            total = self._list_view.Items.Size
            if total > 0:
                self._list_view.DeselectRange(ItemIndexRange(0, total))
            if not isinstance(selection, list):
                selection = [selection]
            for idx in selection:
                if 0 <= idx < self._list_view.Items.Size:
                    self._list_view.SelectRange(ItemIndexRange(idx, 1))
        else:
            self._list_view.SelectedIndex = (
                selection if isinstance(selection, int) else -1
            )

    ######################################################################
    # Column management
    ######################################################################

    def insert_column(self, index, column):
        self._build_header()
        self._rebuild_all_content()

    def remove_column(self, index):
        self._build_header()
        self._rebuild_all_content()

    # Legacy alias.
    def add_column(self, heading, accessor):
        pass  # insert_column is the active API

    ######################################################################
    # Scroll
    ######################################################################

    def scroll_to_row(self, row):
        if 0 <= row < self._list_view.Items.Size:
            item = self._list_view.Items.GetAt(row)
            self._list_view.ScrollIntoView(item)

    ######################################################################
    # Layout
    ######################################################################

    def rehint(self):
        pass
