from win32more.Microsoft.UI.Input import InputSystemCursor, InputSystemCursorShape
from win32more.Microsoft.UI.Xaml import GridLength, GridUnitType
from win32more.Microsoft.UI.Xaml.Controls import (
    Border,
    Canvas,
    ColumnDefinition,
    Grid,
    RowDefinition,
)

from toga.constants import Direction
from toga.handlers import WeakrefCallable

from ._utils import theme_brush
from .base import Widget

# Width of the draggable splitter bar in DIPs.
SPLITTER_WIDTH = 5


class _PanelContainer:
    """A Container that lives inside a Grid cell instead of using .Content."""

    def __init__(self, grid, cell_index):
        self.grid = grid
        self.cell_index = cell_index
        self.native_width = self.native_height = 0
        self.content = None

        self.native_content = Canvas()
        grid.Children.Append(self.native_content)

    def place_in_column(self, col):
        """Position this panel's canvas in a Grid column (vertical split)."""
        self.cell_index = col
        Grid.SetColumn(self.native_content, col)
        Grid.SetRow(self.native_content, 0)

    def place_in_row(self, row):
        """Position this panel's canvas in a Grid row (horizontal split)."""
        self.cell_index = row
        Grid.SetRow(self.native_content, row)
        Grid.SetColumn(self.native_content, 0)

    @property
    def width(self):
        return self.native_width

    @property
    def height(self):
        return self.native_height

    def set_content(self, widget):
        self.clear_content()
        if widget:
            widget.container = self
            self.content = widget

    def clear_content(self):
        if self.content:
            self.content.container = None
            self.content = None

    def resize_content(self, width, height, *, force_refresh=False):
        if (self.native_width, self.native_height) != (width, height):
            self.native_width, self.native_height = (width, height)
            force_refresh = True

        if force_refresh and self.content:
            self.content.interface.refresh()

    def refreshed(self):
        layout = self.content.interface.layout
        self.apply_layout(layout.width, layout.height)

    def apply_layout(self, layout_width, layout_height):
        self.native_content.Width = max(self.width, layout_width)
        self.native_content.Height = max(self.height, layout_height)

    def add_content(self, widget):
        # Remove first to prevent duplicates and ensure top-Z positioning.
        self.remove_content(widget)
        self.native_content.Children.Append(widget.native)

    def remove_content(self, widget):
        children = self.native_content.Children
        for i in range(children.Size):
            if children.GetAt(i) == widget.native:
                children.RemoveAt(i)
                break


class SplitContainer(Widget):
    def create(self):
        self.native = Grid()
        self._direction = Direction.VERTICAL
        self._dragging = False
        self.pending_position = None

        # Splitter bar — a thin border with a visible grab area.
        self._splitter = Border()
        brush = theme_brush(
            "ControlStrokeColorDefaultBrush",
            fallback_rgba=(255, 200, 200, 200),
        )
        if brush is not None:
            self._splitter.Background = brush
        self.native.Children.Append(self._splitter)

        # Create two panel containers.
        self.panels = (_PanelContainer(self.native, 0), _PanelContainer(self.native, 2))

        # Build the initial column layout (vertical split).
        self._build_layout()

        # Wire drag events on the splitter.
        self._splitter.add_PointerPressed(WeakrefCallable(self.winui3_pointer_pressed))
        self._splitter.add_PointerMoved(WeakrefCallable(self.winui3_pointer_moved))
        self._splitter.add_PointerReleased(
            WeakrefCallable(self.winui3_pointer_released)
        )

    def _build_layout(self):
        """Rebuild Grid definitions for the current direction."""
        col_defs = self.native.ColumnDefinitions
        row_defs = self.native.RowDefinitions
        col_defs.Clear()
        row_defs.Clear()

        # Set the resize cursor appropriate for the split direction.
        self._splitter.ProtectedCursor = InputSystemCursor.Create(
            InputSystemCursorShape.SizeWestEast
            if self._direction == Direction.VERTICAL
            else InputSystemCursorShape.SizeNorthSouth
        )

        if self._direction == Direction.VERTICAL:
            # 3 columns: panel1 (star) | splitter (fixed) | panel2 (star)
            cd1 = ColumnDefinition()
            cd1.Width = GridLength(1, GridUnitType.Star)
            col_defs.Append(cd1)

            cd_splitter = ColumnDefinition()
            cd_splitter.Width = GridLength(SPLITTER_WIDTH, GridUnitType.Pixel)
            col_defs.Append(cd_splitter)

            cd2 = ColumnDefinition()
            cd2.Width = GridLength(1, GridUnitType.Star)
            col_defs.Append(cd2)

            # Place children in columns.
            self.panels[0].place_in_column(0)
            Grid.SetColumn(self._splitter, 1)
            Grid.SetRow(self._splitter, 0)
            self.panels[1].place_in_column(2)
        else:
            # 3 rows: panel1 (star) | splitter (fixed) | panel2 (star)
            rd1 = RowDefinition()
            rd1.Height = GridLength(1, GridUnitType.Star)
            row_defs.Append(rd1)

            rd_splitter = RowDefinition()
            rd_splitter.Height = GridLength(SPLITTER_WIDTH, GridUnitType.Pixel)
            row_defs.Append(rd_splitter)

            rd2 = RowDefinition()
            rd2.Height = GridLength(1, GridUnitType.Star)
            row_defs.Append(rd2)

            # Place children in rows.
            self.panels[0].place_in_row(0)
            Grid.SetRow(self._splitter, 1)
            Grid.SetColumn(self._splitter, 0)
            self.panels[1].place_in_row(2)

    def set_content(self, content, flex):
        # Clear first to avoid issues when content moves between panels.
        for panel in self.panels:
            panel.clear_content()

        for panel, widget in zip(self.panels, content, strict=False):
            panel.set_content(widget)

        self.pending_position = flex[0] / sum(flex)

    def get_direction(self):
        return self._direction

    def set_direction(self, value):
        if self._direction == value:
            return
        position = self.get_position()
        self._direction = value
        self._build_layout()
        self.set_position(position)

    def get_position(self):
        """Return the split position as a 0-1 proportion."""
        if self._direction == Direction.VERTICAL:
            defs = self.native.ColumnDefinitions
        else:
            defs = self.native.RowDefinitions

        if defs.Size < 3:
            return 0.5

        size_0 = defs.GetAt(0)
        size_2 = defs.GetAt(2)

        if self._direction == Direction.VERTICAL:
            v0 = size_0.Width.Value
            v2 = size_2.Width.Value
        else:
            v0 = size_0.Height.Value
            v2 = size_2.Height.Value

        total = v0 + v2
        if total == 0:
            return 0.5
        return v0 / total

    def set_position(self, position):
        """Set the split position as a 0-1 proportion."""
        position = max(0.01, min(0.99, position))

        if self._direction == Direction.VERTICAL:
            defs = self.native.ColumnDefinitions
            if defs.Size >= 3:
                defs.GetAt(0).Width = GridLength(position, GridUnitType.Star)
                defs.GetAt(2).Width = GridLength(1 - position, GridUnitType.Star)
        else:
            defs = self.native.RowDefinitions
            if defs.Size >= 3:
                defs.GetAt(0).Height = GridLength(position, GridUnitType.Star)
                defs.GetAt(2).Height = GridLength(1 - position, GridUnitType.Star)

    def set_bounds(self, x, y, width, height):
        super().set_bounds(x, y, width, height)

        force_refresh = False
        if self.pending_position and width and height:
            self.set_position(self.pending_position)
            self.pending_position = None
            force_refresh = True

        self.resize_content(force_refresh=force_refresh)

    def resize_content(self, **kwargs):
        for panel in self.panels:
            w = panel.native_content.ActualWidth
            h = panel.native_content.ActualHeight
            panel.resize_content(w, h, **kwargs)

    def rehint(self):
        pass

    # --- Pointer drag handling ---

    def winui3_pointer_pressed(self, sender, args):
        self._dragging = True
        self._splitter.CapturePointer(args.Pointer)
        args.Handled = True

    def winui3_pointer_moved(self, sender, args):
        if not self._dragging:
            return

        # Get the pointer position relative to the Grid.
        pos = args.GetCurrentPoint(self.native)

        if self._direction == Direction.VERTICAL:
            total = self.native.ActualWidth - SPLITTER_WIDTH
            if total > 0:
                proportion = (pos.Position.X - SPLITTER_WIDTH / 2) / total
                self.set_position(proportion)
        else:
            total = self.native.ActualHeight - SPLITTER_WIDTH
            if total > 0:
                proportion = (pos.Position.Y - SPLITTER_WIDTH / 2) / total
                self.set_position(proportion)

        self.resize_content()
        args.Handled = True

    def winui3_pointer_released(self, sender, args):
        if self._dragging:
            self._dragging = False
            self._splitter.ReleasePointerCapture(args.Pointer)
            self.resize_content()
            args.Handled = True
