import pytest
from win32more.Microsoft.UI.Xaml import Visibility
from win32more.Microsoft.UI.Xaml.Controls import Grid, StackPanel, TextBlock

from .base import SimpleProbe, find_scroll_viewer


class TableProbe(SimpleProbe):
    native_class = Grid
    supports_icons = 2  # All columns
    supports_keyboard_shortcuts = False
    supports_keyboard_boundary_shortcuts = True
    supports_widgets = False

    @property
    def row_count(self):
        return self.impl._list_view.Items.Size

    @property
    def column_count(self):
        return self.impl._header.ColumnDefinitions.Size

    def assert_cell_content(self, row, col, value=None, icon=None, widget=None):
        if widget:
            pytest.skip("This backend doesn't support widgets in Tables")
            return

        row_grid = self.impl._list_view.Items.GetAt(row)
        cell = row_grid.Children.GetAt(col)

        if isinstance(cell, TextBlock):
            # Plain text cell (no icon).
            assert cell.Text == value
            assert icon is None, "Expected icon but cell is a plain TextBlock"
        elif isinstance(cell, StackPanel):
            # Icon + text cell: Image at index 0, TextBlock at index 1.
            text_block = cell.Children.GetAt(cell.Children.Size - 1)
            assert isinstance(text_block, TextBlock)
            assert text_block.Text == value

            if icon is not None:
                img = cell.Children.GetAt(0)
                assert img.Source is not None
        else:
            raise AssertionError(f"Unexpected cell type: {type(cell)}")

    @property
    def max_scroll_position(self):
        sv = find_scroll_viewer(self.impl._list_view)
        if sv is not None:
            return round(sv.ScrollableHeight)
        return round(self.impl._list_view.ActualHeight)

    @property
    def scroll_position(self):
        sv = find_scroll_viewer(self.impl._list_view)
        if sv is not None:
            return round(sv.VerticalOffset)
        return 0

    async def wait_for_scroll_completion(self):
        pass

    @property
    def header_visible(self):
        return self.impl._header.Visibility != Visibility.Collapsed

    @property
    def header_titles(self):
        header = self.impl._header
        titles = []
        for i in range(header.Children.Size):
            child = header.Children.GetAt(i)
            if hasattr(child, "Text"):
                titles.append(child.Text)
        return titles

    def column_width(self, index):
        header = self.impl._header
        child = header.Children.GetAt(index)
        return round(child.ActualWidth / self.scale_factor)

    async def resize_column(self, index, width):
        # Column resizing isn't directly supported in this backend.
        pytest.skip("Column resizing not supported on this backend")

    async def select_row(self, row, add=False):
        lv = self.impl._list_view
        if add:
            # Toggle selection
            item = lv.Items.GetAt(row)
            if item in lv.SelectedItems:
                lv.SelectedItems.Remove(item)
            else:
                lv.SelectedItems.Append(item)
        else:
            lv.SelectedIndex = row

    async def activate_row(self, row):
        await self.select_row(row)
        # Trigger double-tap handler if available.
        if hasattr(self.impl, "winui3_double_tapped"):
            self.impl.winui3_double_tapped(self.impl._list_view, None)

    async def select_first_row_keyboard(self):
        await self.type_character(" ")
