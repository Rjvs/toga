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
    Orientation,
    RowDefinition,
    StackPanel,
    TextBlock,
    TreeView,
    TreeViewNode,
    TreeViewSelectionMode,
)
from win32more.Microsoft.UI.Xaml.Media import Stretch

from toga.handlers import WeakrefCallable

from .base import Widget


class Tree(Widget):
    def create(self):
        self.native = Grid()

        # Header row definition (Auto height).
        rd_header = RowDefinition()
        rd_header.Height = GridLength(0, GridUnitType.Auto)
        self.native.RowDefinitions.Append(rd_header)

        # TreeView row definition (Star — fills remaining space).
        rd_tree = RowDefinition()
        rd_tree.Height = GridLength(1, GridUnitType.Star)
        self.native.RowDefinitions.Append(rd_tree)

        # Column header grid.
        self._header = Grid()
        self._header.Padding = Thickness(36, 4, 0, 4)  # indent to match tree indent
        Grid.SetRow(self._header, 0)
        self.native.Children.Append(self._header)

        # Native TreeView.
        self._tree_view = TreeView()
        self._tree_view.SelectionMode = (
            TreeViewSelectionMode.Multiple
            if getattr(self.interface, "multiple_select", False)
            else TreeViewSelectionMode.Single
        )
        self._tree_view.add_SelectionChanged(
            WeakrefCallable(self.winui3_selection_changed)
        )
        self._tree_view.add_ItemInvoked(WeakrefCallable(self.winui3_item_invoked))
        Grid.SetRow(self._tree_view, 1)
        self.native.Children.Append(self._tree_view)

        # Bidirectional map: id(toga_node) -> TreeViewNode
        self._node_map = {}
        # Reverse map: TreeViewNode.value (COM ptr addr) -> toga_node
        self._reverse_map = {}

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
        """Build a Grid with one cell per column for a tree node."""
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

    def _build_tree_node(self, node):
        """Build a TreeViewNode from a toga Node, recursively building children."""
        tree_node = TreeViewNode()
        tree_node.Content = self._build_row_content(node)

        # Register in maps.
        self._node_map[id(node)] = tree_node
        self._reverse_map[tree_node.value] = node

        # Recursively add children if this node can have them.
        if node.can_have_children():
            for child in node:
                tree_node.Children.Append(self._build_tree_node(child))

        return tree_node

    def _unregister_node(self, node):
        """Remove a node (and its descendants) from the maps."""
        native = self._node_map.pop(id(node), None)
        if native is not None:
            self._reverse_map.pop(native.value, None)
        if node.can_have_children():
            for child in node:
                self._unregister_node(child)

    def _toga_node_from_native(self, tree_view_node):
        """Look up the toga Node for a native TreeViewNode."""
        return self._reverse_map.get(tree_view_node.value)

    ######################################################################
    # Source notifications
    ######################################################################

    def change_source(self, source):
        self._tree_view.RootNodes.Clear()
        self._node_map.clear()
        self._reverse_map.clear()
        if source is not None:
            for root in source:
                self._tree_view.RootNodes.Append(self._build_tree_node(root))

    def source_insert(self, *, index, item, parent=None):
        tree_node = self._build_tree_node(item)
        if parent is None:
            self._tree_view.RootNodes.InsertAt(index, tree_node)
        else:
            parent_native = self._node_map.get(id(parent))
            if parent_native:
                parent_native.Children.InsertAt(index, tree_node)

    def source_change(self, *, item):
        native_node = self._node_map.get(id(item))
        if native_node:
            native_node.Content = self._build_row_content(item)

    def source_remove(self, *, index, item, parent=None):
        self._unregister_node(item)
        if parent is None:
            self._tree_view.RootNodes.RemoveAt(index)
        else:
            parent_native = self._node_map.get(id(parent))
            if parent_native:
                parent_native.Children.RemoveAt(index)

    def source_clear(self):
        self._tree_view.RootNodes.Clear()
        self._node_map.clear()
        self._reverse_map.clear()

    # Alias for backwards compatibility:
    # March 2026: In 0.5.3 and earlier, notification methods
    # didn't start with 'source_'
    def insert(self, parent, index, item):
        import warnings

        warnings.warn(
            "The insert() method is deprecated. Use source_insert() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.source_insert(index=index, item=item, parent=parent)

    def change(self, item):
        import warnings

        warnings.warn(
            "The change() method is deprecated. Use source_change() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.source_change(item=item)

    def remove(self, item, index, parent):
        import warnings

        warnings.warn(
            "The remove() method is deprecated. Use source_remove() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.source_remove(index=index, item=item, parent=parent)

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

    def winui3_item_invoked(self, sender, args):
        # args.InvokedItem returns the Content (Grid), not the TreeViewNode.
        # Use SelectedNode which is updated before ItemInvoked fires.
        selected = self._tree_view.SelectedNode
        if selected is not None:
            node = self._toga_node_from_native(selected)
            if node is not None:
                self.interface.on_activate(node=node)

    def get_selection(self):
        if getattr(self.interface, "multiple_select", False):
            result = []
            selected = self._tree_view.SelectedNodes
            for i in range(selected.Size):
                node = self._toga_node_from_native(selected.GetAt(i))
                if node is not None:
                    result.append(node)
            return result
        else:
            selected = self._tree_view.SelectedNode
            if selected is None:
                return None
            return self._toga_node_from_native(selected)

    def set_selection(self, selection):
        # Clear current selection first.
        self._tree_view.SelectedNodes.Clear()

        if selection is None or selection == []:
            return

        if not isinstance(selection, list):
            selection = [selection]

        for node in selection:
            native = self._node_map.get(id(node))
            if native:
                self._tree_view.SelectedNodes.Append(native)

    ######################################################################
    # Expand / Collapse
    ######################################################################

    def expand_node(self, node):
        native = self._node_map.get(id(node))
        if native:
            native.IsExpanded = True

    def expand_all(self):
        self._set_expanded_recursive(self._tree_view.RootNodes, True)

    def collapse_node(self, node):
        native = self._node_map.get(id(node))
        if native:
            native.IsExpanded = False

    def collapse_all(self):
        self._set_expanded_recursive(self._tree_view.RootNodes, False)

    def _set_expanded_recursive(self, nodes, expanded):
        for i in range(nodes.Size):
            node = nodes.GetAt(i)
            node.IsExpanded = expanded
            if node.Children.Size > 0:
                self._set_expanded_recursive(node.Children, expanded)

    ######################################################################
    # Column management
    ######################################################################

    def insert_column(self, index, column):
        self._build_header()
        self._rebuild_all_content()

    def remove_column(self, index):
        self._build_header()
        self._rebuild_all_content()

    # Legacy aliases
    def add_column(self, heading, accessor):
        pass  # insert_column is the active API

    def _rebuild_all_content(self):
        """Rebuild all node content grids after column changes."""
        for _toga_id, native_node in self._node_map.items():
            toga_node = self._reverse_map.get(native_node.value)
            if toga_node:
                native_node.Content = self._build_row_content(toga_node)

    ######################################################################
    # Scroll
    ######################################################################

    def scroll_to_node(self, node):
        native = self._node_map.get(id(node))
        if native:
            # Expand ancestors so the node is visible.
            parent = node._parent
            while parent is not None and hasattr(parent, "_parent"):
                parent_native = self._node_map.get(id(parent))
                if parent_native:
                    parent_native.IsExpanded = True
                parent = getattr(parent, "_parent", None)

            # Force layout so containers are realized after expansion.
            self._tree_view.UpdateLayout()

            # Get the realized TreeViewItem and scroll it into view.
            container = self._tree_view.ContainerFromNode(native)
            if container is not None:
                container.StartBringIntoView()

    ######################################################################
    # Layout
    ######################################################################

    def rehint(self):
        pass
