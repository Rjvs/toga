import pytest
from win32more.Microsoft.UI.Xaml.Controls import Button, StackPanel

from .base import SimpleProbe


class ButtonProbe(SimpleProbe):
    native_class = Button

    @property
    def text(self):
        content = self.native.Content
        # If content is a StackPanel, the text is in the TextBlock child.
        if isinstance(content, StackPanel):
            for i in range(content.Children.Size):
                child = content.Children.GetAt(i)
                if hasattr(child, "Text"):
                    return child.Text
            return ""
        # Normalize the zero width space to the empty string.
        if content == "\u200b":
            return ""
        return content or ""

    def assert_no_icon(self):
        content = self.native.Content
        assert not isinstance(content, StackPanel)

    def assert_icon_size(self):
        content = self.native.Content
        if isinstance(content, StackPanel):
            from win32more.Microsoft.UI.Xaml.Controls import Image

            img = content.Children.GetAt(0)
            assert isinstance(img, Image)
            assert img.ActualWidth > 0
            assert img.ActualHeight > 0
        else:
            pytest.fail("Icon does not exist")
