from travertino.size import at_least
from win32more.Microsoft.UI.Xaml.Controls import Canvas

from toga_winui3.colors import native_brush


class Widget:
    def __init__(self, interface):
        self.interface = interface

        self._container = None
        self.native = None
        self.create()

    def create(self):
        raise NotImplementedError

    def set_app(self, app):
        """Update the widget when assigned to an app."""

    def set_window(self, window):
        """Update the widget when assigned to a window."""

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        if self._container:
            self._container.remove_content(self)

        self._container = container
        if container:
            container.add_content(self)

        for child in self.interface.children:
            child._impl.container = container

        self.refresh()

    def get_tab_index(self):
        return getattr(self.native, "TabIndex", 0)

    def set_tab_index(self, tab_index):
        if hasattr(self.native, "TabIndex"):
            self.native.TabIndex = tab_index

    def get_enabled(self):
        if hasattr(self.native, "IsEnabled"):
            return self.native.IsEnabled
        return True

    def set_enabled(self, value):
        if hasattr(self.native, "IsEnabled"):
            self.native.IsEnabled = value

    def focus(self):
        if hasattr(self.native, "Focus"):
            from win32more.Microsoft.UI.Xaml import FocusState

            self.native.Focus(FocusState.Programmatic)

    # APPLICATOR

    def set_bounds(self, x, y, width, height):
        # WinUI 3 uses DIPs (device independent pixels) which map 1:1 to CSS pixels
        # at standard DPI. The framework handles DPI scaling automatically.
        Canvas.SetLeft(self.native, x)
        Canvas.SetTop(self.native, y)
        self.native.Width = width
        self.native.Height = height

    def set_text_align(self, alignment):
        """Set text alignment; override in subclasses that support it."""

    def set_hidden(self, hidden):
        from win32more.Microsoft.UI.Xaml import Visibility

        self.native.Visibility = Visibility.Collapsed if hidden else Visibility.Visible

    def set_font(self, font):
        # WinUI 3 controls that support text have FontFamily, FontSize, etc.
        # The Font impl's apply() method sets all font properties on the control.
        font._impl.apply(self.native)

    def set_color(self, color):
        if hasattr(self.native, "Foreground"):
            if color is None:
                from win32more.Microsoft.UI.Xaml.Controls import Control

                self.native.ClearValue(Control.ForegroundProperty)
            else:
                self.native.Foreground = native_brush(color)

    def set_background_color(self, color):
        # WinUI 3 natively supports transparency, so no alpha blending hack needed.
        if hasattr(self.native, "Background"):
            if color is None:
                from win32more.Microsoft.UI.Xaml.Controls import Control

                self.native.ClearValue(Control.BackgroundProperty)
            else:
                self.native.Background = native_brush(color)

    # INTERFACE

    def add_child(self, child):
        child.container = self.container

    def insert_child(self, index, child):
        self.add_child(child)

    def remove_child(self, child):
        child.container = None

    def refresh(self):
        # Default values; may be overwritten by rehint().
        self.interface.intrinsic.width = at_least(self.interface._MIN_WIDTH)
        self.interface.intrinsic.height = at_least(self.interface._MIN_HEIGHT)
        # Skip rehint if the widget is not yet in the visual tree.
        # Measure/DesiredSize return zeros before XamlRoot is set.
        if (
            self.native is not None
            and getattr(self.native, "XamlRoot", None) is not None
        ):
            self.rehint()

    def rehint(self):
        """Recalculate the intrinsic size hints for this widget."""
