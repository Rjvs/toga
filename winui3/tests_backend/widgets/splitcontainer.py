from win32more.Microsoft.UI.Xaml.Controls import Grid

from .base import SimpleProbe


class SplitContainerProbe(SimpleProbe):
    native_class = Grid
    border_size = 5  # Splitter width in DIPs
    direction_change_preserves_position = True

    def __init__(self, widget):
        super().__init__(widget)
        # Verify both panels exist.
        assert len(self.impl.panels) == 2

    def move_split(self, position):
        # The WinUI 3 impl uses proportional star sizing (0-1).
        # Convert the pixel position to a proportion of the total available space.
        from toga.constants import Direction

        if self.impl._direction == Direction.VERTICAL:
            total = self.native.ActualWidth - self.impl._splitter.ActualWidth
        else:
            total = self.native.ActualHeight - self.impl._splitter.ActualHeight
        if total > 0:
            self.impl.set_position((position * self.scale_factor) / total)

    async def wait_for_split(self):
        pass
