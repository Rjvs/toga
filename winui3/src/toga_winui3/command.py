import sys

from win32more.Microsoft.UI.Xaml.Controls import (
    MenuFlyoutItem,
)
from win32more.Microsoft.UI.Xaml.Input import KeyboardAccelerator
from win32more.Windows.System import VirtualKey, VirtualKeyModifiers

from toga import Command as StandardCommand, Group, Key
from toga.handlers import WeakrefCallable

from .keys import toga_to_winui3_key


class Command:
    def __init__(self, interface):
        self.interface = interface
        self.native = []

    @classmethod
    def standard(cls, app, id):
        # ---- File menu -----------------------------------
        if id == StandardCommand.NEW:
            return {
                "text": "New",
                "shortcut": Key.MOD_1 + "n",
                "group": Group.FILE,
                "section": 0,
                "order": 0,
            }
        elif id == StandardCommand.OPEN:
            return {
                "text": "Open...",
                "shortcut": Key.MOD_1 + "o",
                "group": Group.FILE,
                "section": 0,
                "order": 10,
            }
        elif id == StandardCommand.SAVE:
            return {
                "text": "Save",
                "shortcut": Key.MOD_1 + "s",
                "group": Group.FILE,
                "section": 0,
                "order": 20,
            }
        elif id == StandardCommand.SAVE_AS:
            return {
                "text": "Save As...",
                "shortcut": Key.MOD_1 + "S",
                "group": Group.FILE,
                "section": 0,
                "order": 21,
            }
        elif id == StandardCommand.SAVE_ALL:
            return {
                "text": "Save All",
                "shortcut": Key.MOD_1 + Key.MOD_2 + "s",
                "group": Group.FILE,
                "section": 0,
                "order": 22,
            }
        elif id == StandardCommand.PREFERENCES:
            return {
                "text": "Preferences",
                "group": Group.FILE,
                "section": sys.maxsize - 1,
            }
        elif id == StandardCommand.EXIT:
            return {
                "text": "Exit",
                "group": Group.FILE,
                "section": sys.maxsize,
            }
        # ---- Help menu -----------------------------------
        elif id == StandardCommand.VISIT_HOMEPAGE:
            return {
                "text": "Visit homepage",
                "enabled": app.home_page is not None,
                "group": Group.HELP,
            }
        elif id == StandardCommand.ABOUT:
            return {
                "text": f"About {app.formal_name}",
                "group": Group.HELP,
                "section": sys.maxsize,
            }

        raise ValueError(f"Unknown standard command {id!r}")

    def winui3_click(self, sender, event):
        return self.interface.action()

    def set_enabled(self, value):
        if self.native:
            for widget in self.native:
                if hasattr(widget, "IsEnabled"):
                    widget.IsEnabled = self.interface.enabled

    def create_menu_item(self):
        """Create a WinUI 3 MenuFlyoutItem for this command."""
        item = MenuFlyoutItem()
        item.Text = self.interface.text
        item.IsEnabled = self.interface.enabled
        item.add_Click(WeakrefCallable(self.winui3_click))

        # Add keyboard accelerator if a shortcut is defined.
        if self.interface.shortcut:
            try:
                keys = toga_to_winui3_key(self.interface.shortcut)
                if keys:
                    accel = KeyboardAccelerator()
                    modifiers = VirtualKeyModifiers.None_
                    main_key = None
                    for k in keys:
                        if k == VirtualKey.Control:
                            modifiers |= VirtualKeyModifiers.Control
                        elif k == VirtualKey.Menu:
                            modifiers |= VirtualKeyModifiers.Menu
                        elif k == VirtualKey.Shift:
                            modifiers |= VirtualKeyModifiers.Shift
                        else:
                            main_key = k
                    if main_key is not None:
                        accel.Key = main_key
                        accel.Modifiers = modifiers
                        item.KeyboardAccelerators.Append(accel)
            except (ValueError, AttributeError) as e:
                import warnings

                warnings.warn(
                    f"Failed to apply keyboard shortcut "
                    f"{self.interface.shortcut!r} for "
                    f"{self.interface.text!r}: {e}",
                    stacklevel=2,
                )

        self.native.append(item)
        return item
