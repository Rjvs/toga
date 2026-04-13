import asyncio

import pytest
from win32more.Microsoft.UI.Xaml.Controls import Grid, StackPanel, TextBlock

from .base import SimpleProbe


class TreeProbe(SimpleProbe):
    native_class = Grid
    supports_icons = 2  # All columns
    supports_keyboard_shortcuts = False
    supports_keyboard_boundary_shortcuts = True
    supports_widgets = False

    def _toga_node_from_path(self, row_path):
        """Navigate the Toga data source to find the node at row_path."""
        source = self.widget.data
        node = source
        for index in row_path:
            node = node[index]
        return node

    def _native_node(self, row_path):
        """Get the native TreeViewNode for a row path."""
        toga_node = self._toga_node_from_path(row_path)
        return self.impl._node_map.get(id(toga_node))

    @property
    def row_count(self):
        return self.impl._tree_view.RootNodes.Size

    @property
    def column_count(self):
        return self.impl._header.ColumnDefinitions.Size

    def assert_cell_content(self, row_path, col, value=None, icon=None, widget=None):
        if widget:
            pytest.skip("This backend doesn't support widgets in Trees")
            return

        native_node = self._native_node(row_path)
        assert native_node is not None, f"No native node for path {row_path}"

        content_grid = native_node.Content
        cell = content_grid.Children.GetAt(col)

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

    def toggle_node(self, row_path):
        native_node = self._native_node(row_path)
        if native_node is not None:
            native_node.IsExpanded = not native_node.IsExpanded

    async def expand_tree(self):
        if hasattr(self.impl, "expand_all"):
            self.impl.expand_all()
        await asyncio.sleep(0.1)

    def is_expanded(self, node):
        native_node = self.impl._node_map.get(id(node))
        if native_node is None:
            return False
        return native_node.IsExpanded

    def child_count(self, row_path=None):
        if row_path is None:
            return self.impl._tree_view.RootNodes.Size
        native_node = self._native_node(row_path)
        if native_node is None:
            return 0
        return native_node.Children.Size

    async def select_row(self, row_path, add=False):
        native_node = self._native_node(row_path)
        if native_node is None:
            return
        tv = self.impl._tree_view
        if add:
            tv.SelectedNodes.Append(native_node)
        else:
            tv.SelectedNodes.Clear()
            tv.SelectedNodes.Append(native_node)

    async def activate_row(self, row_path):
        await self.select_row(row_path)
        if hasattr(self.impl, "winui3_item_invoked"):
            self.impl.winui3_item_invoked(self.impl._tree_view, None)

    @property
    def header_visible(self):
        from win32more.Microsoft.UI.Xaml import Visibility

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

    async def assert_item_mouse_hover(self, row_path):
        pytest.skip("Native TreeView handles hover internally")

    async def single_click(self, row_path, toggle, on_item):
        pytest.skip("Native TreeView handles click internally")

    async def double_click_state_change_arrow(self, row_path):
        pytest.skip("Native TreeView handles expand/collapse internally")

    async def assert_mouse_leave(self):
        pytest.skip("Native TreeView handles mouse leave internally")
