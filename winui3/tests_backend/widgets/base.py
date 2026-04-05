import pytest
from pytest import approx
from win32more.Microsoft.UI.Xaml import FocusState, Visibility
from win32more.Microsoft.UI.Xaml.Controls import ScrollViewer
from win32more.Microsoft.UI.Xaml.Media import VisualTreeHelper

from toga.style.pack import JUSTIFY, LEFT

from ..probe import BaseProbe
from .properties import toga_color


def find_scroll_viewer(element):
    """Walk the visual tree to find the first ScrollViewer descendant."""
    count = VisualTreeHelper.GetChildrenCount(element)
    for i in range(count):
        child = VisualTreeHelper.GetChild(element, i)
        if isinstance(child, ScrollViewer):
            return child
        result = find_scroll_viewer(child)
        if result is not None:
            return result
    return None


class SimpleProbe(BaseProbe):
    invalid_size_while_hidden = False

    def __init__(self, widget):
        self.app = widget.app
        self.widget = widget
        self.impl = widget._impl
        super().__init__(self.impl.native)
        assert isinstance(self.native, self.native_class)

    def assert_container(self, container):
        assert self.widget._impl.container is container._impl.container
        # In WinUI 3, the widget should be a child of the container's Canvas.
        canvas = container._impl.container.native_content
        found = False
        for i in range(canvas.Children.Size):
            if canvas.Children.GetAt(i) == self.native:
                found = True
                break
        assert found, "Widget not found in container's Canvas children"

    def assert_not_contained(self):
        assert self.widget._impl.container is None

    def assert_text_align(self, expected):
        # WinUI 3 supports Justified alignment (unlike WinForms), but it falls
        # back to LEFT when the control doesn't support it.
        actual = self.text_align
        if expected == JUSTIFY:
            assert actual in {JUSTIFY, LEFT}
        else:
            assert actual == expected

    @property
    def enabled(self):
        return self.native.IsEnabled

    @property
    def color(self):
        brush = self.native.Foreground
        if brush is None:
            return None
        return toga_color(brush)

    @property
    def background_color(self):
        native_bg = self.native.Background
        parent_bg = (
            self.widget.parent._impl.native.Background if self.widget.parent else None
        )
        return (
            toga_color(native_bg) if native_bg else None,
            toga_color(parent_bg) if parent_bg else None,
            (
                # self.impl.interface.style.background_color can be None or TRANSPARENT
                # and so there will be no alpha value on them. In such cases return 0
                # as the original alpha value.
                getattr(self.widget.style.background_color, "a", 0)
            ),
        )

    @property
    def hidden(self):
        return self.native.Visibility == Visibility.Collapsed

    @property
    def shrink_on_resize(self):
        return True

    def assert_layout(self, size, position):
        # Widget is contained and in a window.
        assert self.widget._impl.container is not None

        # size and position is as expected.
        assert (self.width, self.height) == approx(size, abs=1)
        assert (self.x, self.y) == approx(position, abs=1)

    async def press(self):
        # WinUI 3 controls don't expose OnClick directly; invoke the impl handler.
        if hasattr(self.impl, "_on_click"):
            self.impl._on_click(self.native, None)
        elif hasattr(self.impl, "_on_press"):
            self.impl._on_press(self.native, None)

    @property
    def is_hidden(self):
        return self.native.Visibility == Visibility.Collapsed

    @property
    def has_focus(self):
        return self.native.FocusState != FocusState.Unfocused

    async def undo(self):
        pytest.skip("Undo not supported on this platform")

    async def redo(self):
        pytest.skip("Redo not supported on this platform")
