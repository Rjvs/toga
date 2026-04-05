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
        # The WinUI 3 impl uses proportional star sizing; position is in pixels.
        # Convert pixel position to the appropriate star ratio.
        self.impl._update_split_position(position * self.scale_factor)

    async def wait_for_split(self):
        pass
