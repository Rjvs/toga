from win32more.Microsoft.UI.Xaml.Controls import (
    Canvas,
    ScrollBarVisibility,
    ScrollViewer,
)

from toga.handlers import WeakrefCallable

from .base import Widget


class ScrollContainer(Widget):
    def create(self):
        self.native = ScrollViewer()
        self.native.HorizontalScrollBarVisibility = ScrollBarVisibility.Auto
        self.native.VerticalScrollBarVisibility = ScrollBarVisibility.Auto
        self._content_canvas = Canvas()
        self.native.Content = self._content_canvas
        self._content = None

        # Track scrollable directions.
        self.horizontal = True
        self.vertical = True

        # Fire on_scroll when the view changes (covers scrollbar drag,
        # mouse wheel, programmatic position changes, and content resize).
        self.native.add_ViewChanged(WeakrefCallable(self.winui3_view_changed))

    def winui3_view_changed(self, sender, args):
        self.interface.on_scroll()

    ######################################################################
    # Content management — implements Container-like protocol
    ######################################################################

    def set_content(self, widget):
        if self._content:
            self._content.container = None
        self._content = widget
        self._content_canvas.Children.Clear()
        if widget:
            widget.container = self

    def clear_content(self):
        if self._content:
            self._content.container = None
            self._content_canvas.Children.Clear()
            self._content = None

    # Container protocol methods used by Widget.container setter.
    def add_content(self, widget):
        # Remove first to prevent duplicates and ensure top-Z positioning.
        self.remove_content(widget)
        self._content_canvas.Children.Append(widget.native)

    def remove_content(self, widget):
        children = self._content_canvas.Children
        for i in range(children.Size):
            if children.GetAt(i) == widget.native:
                children.RemoveAt(i)
                break

    @property
    def width(self):
        return self.native.ViewportWidth

    @property
    def height(self):
        return self.native.ViewportHeight

    def refreshed(self):
        if self._content:
            layout = self._content.interface.layout
            # Size the inner canvas to fit the laid-out content so the
            # ScrollViewer knows how much to scroll.
            self._content_canvas.Width = max(self.width, layout.width)
            self._content_canvas.Height = max(self.height, layout.height)

    ######################################################################
    # Widget overrides
    ######################################################################

    def set_bounds(self, x, y, width, height):
        super().set_bounds(x, y, width, height)
        # After our own bounds change, trigger a layout pass on the content.
        if self._content:
            self._content.interface.refresh()

    ######################################################################
    # Scroll properties
    ######################################################################

    def get_horizontal(self):
        return self.horizontal

    def set_horizontal(self, value):
        self.horizontal = value
        self.native.HorizontalScrollBarVisibility = (
            ScrollBarVisibility.Auto if value else ScrollBarVisibility.Disabled
        )
        if not value:
            self.interface.on_scroll()
        if self._content:
            self._content.interface.refresh()

    def get_vertical(self):
        return self.vertical

    def set_vertical(self, value):
        self.vertical = value
        self.native.VerticalScrollBarVisibility = (
            ScrollBarVisibility.Auto if value else ScrollBarVisibility.Disabled
        )
        if not value:
            self.interface.on_scroll()
        if self._content:
            self._content.interface.refresh()

    ######################################################################
    # Scroll position
    ######################################################################

    def set_position(self, horizontal, vertical):
        self.native.ChangeView(horizontal, vertical, None)
        self.interface.on_scroll()

    def get_horizontal_position(self):
        return self.native.HorizontalOffset

    def get_vertical_position(self):
        return self.native.VerticalOffset

    def get_max_horizontal_position(self):
        return self.native.ScrollableWidth

    def get_max_vertical_position(self):
        return self.native.ScrollableHeight

    ######################################################################
    # Layout
    ######################################################################

    def rehint(self):
        pass
