from win32more.Microsoft.UI.Xaml.Controls import Canvas


class Container:
    def __init__(self, native_parent):
        self.native_parent = native_parent
        self.native_width = self.native_height = 0
        self.content = None

        # Use Canvas for absolute positioning - travertino computes all
        # (x, y, width, height) values and we apply them via Canvas.SetLeft/SetTop.
        self.native_content = Canvas()
        native_parent.Content = self.native_content

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
        # Remove first to prevent duplicates and ensure top-Z positioning
        # (equivalent to WinForms' Controls.Add + BringToFront).
        self.remove_content(widget)
        self.native_content.Children.Append(widget.native)

    def remove_content(self, widget):
        children = self.native_content.Children
        for i in range(children.Size):
            if children.GetAt(i) == widget.native:
                children.RemoveAt(i)
                break
