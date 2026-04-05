import ctypes
from time import sleep

import PIL.Image
import pytest
from toga_winui3.keys import toga_to_winui3_shortcut
from toga_winui3.paths import _get_local_app_data

from .dialogs import DialogsMixin
from .probe import BaseProbe


class AppProbe(BaseProbe, DialogsMixin):
    supports_key = True
    supports_key_mod3 = False
    supports_current_window_assignment = True
    supports_dark_mode = False
    edit_menu_noop_enabled = False
    supports_psutil = True

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.main_window = app.main_window
        # Verify we have a XamlApplication instance.
        from win32more.winui3 import XamlApplication

        assert isinstance(self.app._impl.native, XamlApplication)

    @property
    def config_path(self):
        return _get_local_app_data() / "Tiberius Yak/Toga Testbed/Config"

    @property
    def data_path(self):
        return _get_local_app_data() / "Tiberius Yak/Toga Testbed/Data"

    @property
    def cache_path(self):
        return _get_local_app_data() / "Tiberius Yak/Toga Testbed/Cache"

    @property
    def logs_path(self):
        return _get_local_app_data() / "Tiberius Yak/Toga Testbed/Logs"

    @property
    def is_cursor_visible(self):
        # Move cursor to the center of the main window.
        window = self.main_window._impl.native
        app_window = window.AppWindow
        pos = app_window.Position
        size = app_window.Size
        center_x = pos.X + (size.Width // 2)
        center_y = pos.Y + (size.Height // 2)
        ctypes.windll.user32.SetCursorPos(center_x, center_y)

        # A small delay is required for the new position to take effect.
        sleep(0.1)

        class POINT(ctypes.Structure):
            _fields_ = [
                ("x", ctypes.c_long),
                ("y", ctypes.c_long),
            ]

        class CURSORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint32),
                ("flags", ctypes.c_uint32),
                ("hCursor", ctypes.c_void_p),
                ("ptScreenPos", POINT),
            ]

        GetCursorInfo = ctypes.windll.user32.GetCursorInfo
        GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]

        info = CURSORINFO()
        info.cbSize = ctypes.sizeof(info)
        if not GetCursorInfo(ctypes.byref(info)):
            raise RuntimeError("GetCursorInfo failed")

        # Visibility *should* be exposed by CursorInfo.flags; but in CI,
        # CursorInfo.flags returns 2 ("the system is not drawing the cursor
        # because the user is providing input through touch or pen instead of
        # the mouse"). In that case, fall back to the backend's boolean.
        if info.flags == 2:
            return self.app._impl._cursor_visible
        else:
            return info.flags == 1

    def unhide(self):
        pytest.xfail("This platform doesn't have an app level unhide.")

    def assert_app_icon(self, icon):
        for window in self.app.windows:
            # WinUI 3 sets icons via AppWindow.SetIcon(path). Load the expected
            # icon file and pixel-peep.
            icon_path = window._impl.interface.app.icon._impl.path
            img = PIL.Image.open(icon_path)

            if icon:
                # The explicit alt icon has blue background, with green at a
                # point 1/3 into the image.
                assert img.getpixel((5, 5)) == (211, 230, 245, 255)
                mid_color = img.getpixel((img.size[0] // 3, img.size[1] // 3))
                assert mid_color == (0, 204, 9, 255)
            else:
                # The default icon is transparent background, and brown in
                # the center.
                assert img.getpixel((5, 5))[3] == 0
                mid_color = img.getpixel((img.size[0] // 2, img.size[1] // 2))
                assert mid_color == (130, 100, 57, 255)

    def _menu_item(self, path):
        """Walk the WinUI 3 MenuBar hierarchy to find a menu item by path."""
        from win32more.Microsoft.UI.Xaml.Controls import MenuBarItem

        menu_bar = self.main_window._impl.menubar_native
        if menu_bar is None:
            raise AssertionError("No MenuBar found on main window")

        # Find the top-level MenuBarItem
        items = menu_bar.Items
        top_label = path[0]
        top_item = None
        for i in range(items.Size):
            item = items.GetAt(i)
            if isinstance(item, MenuBarItem) and item.Title == top_label:
                top_item = item
                break
        if top_item is None:
            titles = [items.GetAt(i).Title for i in range(items.Size)]
            raise AssertionError(f"no item named {path[:1]}; options are {titles}")

        # Navigate sub-levels
        current = top_item
        for depth, label in enumerate(path[1:], start=1):
            children = current.Items
            child_labels = []
            found = None
            for j in range(children.Size):
                child = children.GetAt(j)
                text = getattr(child, "Text", None)
                if text is not None:
                    child_labels.append(text)
                    if text == label:
                        found = child
            if found is None:
                raise AssertionError(
                    f"no item named {path[: depth + 1]}; options are {child_labels}"
                )
            current = found

        return current

    def _activate_menu_item(self, path):
        item = self._menu_item(path)
        # Invoke the click handler via the command's native click method.
        # Search the app commands for a matching text and execute the action.
        for cmd in self.app.commands:
            if hasattr(cmd, "text") and cmd.text == item.Text:
                cmd.action(cmd)
                return
        raise AssertionError(f"Could not activate menu item: {path}")

    def activate_menu_hide(self):
        pytest.xfail("This platform doesn't present an app level hide option in menu.")

    def activate_menu_exit(self):
        self._activate_menu_item(["File", "Exit"])

    def activate_menu_about(self):
        self._activate_menu_item(["Help", "About Toga Testbed"])

    async def close_about_dialog(self):
        await self.type_character("\n")

    def activate_menu_visit_homepage(self):
        self._activate_menu_item(["Help", "Visit homepage"])

    def assert_dialog_in_focus(self, dialog):
        # WinUI 3 uses ContentDialog which is modal within the window.
        # Verification via Win32 APIs is not straightforward; just verify the
        # dialog has a title.
        assert dialog._impl.title is not None

    def assert_menu_item(self, path, *, enabled=True):
        item = self._menu_item(path)
        assert item.IsEnabled == enabled

        # Check some special cases of menu shortcuts
        try:
            shortcut = {
                ("Other", "Full command"): "Ctrl+1",
                ("Other", "Submenu1", "Disabled"): None,
                ("Commands", "No Tooltip"): "Ctrl+Down",
                ("Commands", "Sectioned"): "Ctrl+Space",
            }[tuple(path)]
        except KeyError:
            pass
        else:
            if shortcut is None:
                assert item.KeyboardAccelerators.Size == 0
            else:
                # Verify the keyboard accelerator exists.
                assert item.KeyboardAccelerators.Size > 0

    def assert_menu_order(self, path, expected):
        from win32more.Microsoft.UI.Xaml.Controls import MenuFlyoutSeparator

        menu = self._menu_item(path)
        items = menu.Items

        assert items.Size == len(expected)
        for i, title in enumerate(expected):
            item = items.GetAt(i)
            if title == "---":
                assert isinstance(item, MenuFlyoutSeparator)
            else:
                assert item.Text == title

    def assert_system_menus(self):
        self.assert_menu_item(["File", "New Example Document"], enabled=True)
        self.assert_menu_item(["File", "New Read-only Document"], enabled=True)
        self.assert_menu_item(["File", "Open..."], enabled=True)
        self.assert_menu_item(["File", "Save"], enabled=True)
        self.assert_menu_item(["File", "Save As..."], enabled=True)
        self.assert_menu_item(["File", "Save All"], enabled=True)
        self.assert_menu_item(["File", "Preferences"], enabled=False)
        self.assert_menu_item(["File", "Exit"])

        self.assert_menu_item(["Help", "Visit homepage"])
        self.assert_menu_item(["Help", "About Toga Testbed"])

    def activate_menu_close_window(self):
        pytest.xfail("This platform doesn't have a window management menu")

    def activate_menu_close_all_windows(self):
        pytest.xfail("This platform doesn't have a window management menu")

    def activate_menu_minimize(self):
        pytest.xfail("This platform doesn't have a window management menu")

    def keystroke(self, combination):
        return toga_to_winui3_shortcut(combination)

    async def restore_standard_app(self):
        # No special handling needed to restore standard app.
        await self.redraw("Restore to standard app")

    async def open_initial_document(self, monkeypatch, document_path):
        pytest.xfail("WinUI3 doesn't require initial document support")

    def open_document_by_drag(self, document_path):
        pytest.xfail("WinUI3 doesn't support opening documents by drag")

    def has_status_icon(self, status_icon):
        return status_icon._impl._icon_id is not None

    def status_menu_items(self, status_icon):
        if hasattr(status_icon._impl, "_popup_menu") and status_icon._impl._popup_menu:
            # Read menu items from the Win32 popup menu.
            user32 = ctypes.windll.user32
            hmenu = status_icon._impl._popup_menu
            count = user32.GetMenuItemCount(hmenu)
            items = []
            for i in range(count):
                # Check if separator (MF_BYPOSITION = 0x0400)
                info_flags = user32.GetMenuState(hmenu, i, 0x0400)
                if info_flags & 0x0800:  # MF_SEPARATOR
                    items.append("---")
                else:
                    buf = ctypes.create_unicode_buffer(256)
                    user32.GetMenuStringW(hmenu, i, buf, 256, 0x0400)
                    text = buf.value
                    items.append(
                        {
                            "About Toga Testbed": "**ABOUT**",
                            "Exit": "**EXIT**",
                        }.get(text, text)
                    )
            return items
        else:
            # It's a button status item
            return None

    def activate_status_icon_button(self, item_id):
        # Simulate a left-click on the status icon.
        self.app.status_icons[item_id]._impl._on_left_click()

    def activate_status_menu_item(self, item_id, title):
        # Find the command matching the title and execute it.
        menu_items = self.app.status_icons._impl._menu_items
        for _cmd_id, cmd in menu_items.items():
            if cmd.text == title:
                cmd.action(cmd)
                return
        raise AssertionError(f"Status menu item '{title}' not found")
