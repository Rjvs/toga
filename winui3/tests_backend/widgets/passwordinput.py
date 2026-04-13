from win32more.Microsoft.UI.Xaml.Controls import PasswordBox

from .base import SimpleProbe


class PasswordInputProbe(SimpleProbe):
    native_class = PasswordBox

    @property
    def value(self):
        if self.placeholder_visible:
            return self.native.PlaceholderText
        return self.native.Password

    @property
    def value_hidden(self):
        return True

    @property
    def placeholder_visible(self):
        return not self.native.Password

    @property
    def placeholder_hides_on_focus(self):
        return False

    @property
    def readonly(self):
        return not self.native.IsHitTestVisible
