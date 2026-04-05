from win32more.Microsoft.UI.Xaml.Controls import Image, ListView, StackPanel

from .base import SimpleProbe


class DetailedListProbe(SimpleProbe):
    native_class = ListView
    supports_actions = False
    supports_refresh = False

    @property
    def row_count(self):
        return self.native.Items.Size

    def assert_cell_content(self, row, title, subtitle, icon=None):
        # Row structure:
        #   StackPanel (horizontal)
        #     -> [Image (icon, optional)]
        #     -> StackPanel (vertical)
        #          -> TextBlock (title)
        #          -> TextBlock (subtitle)
        row_panel = self.native.Items.GetAt(row)
        children = row_panel.Children

        text_stack = None
        has_image = False
        for i in range(children.Size):
            child = children.GetAt(i)
            if isinstance(child, Image):
                has_image = True
            elif isinstance(child, StackPanel):
                text_stack = child
                break

        assert text_stack is not None, "Could not find text stack in row"

        title_block = text_stack.Children.GetAt(0)
        subtitle_block = text_stack.Children.GetAt(1)
        assert title_block.Text == title
        assert subtitle_block.Text == subtitle

        if icon is not None:
            assert has_image, "Expected icon but no Image found in row"
        else:
            assert not has_image, "Found unexpected Image in row"

    async def select_row(self, row, add=False):
        if add:
            item = self.native.Items.GetAt(row)
            self.native.SelectedItems.Append(item)
        else:
            self.native.SelectedIndex = row

    async def activate_row(self, row):
        await self.select_row(row)
        if hasattr(self.impl, "_on_double_tapped"):
            self.impl._on_double_tapped(self.native, None)
