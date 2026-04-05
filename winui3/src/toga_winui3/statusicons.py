import ctypes
import warnings
from ctypes import wintypes

import toga
from toga.command import Group, Separator

# Shell_NotifyIcon constants
NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

# Window message for tray icon callbacks
WM_APP = 0x8000
WM_TRAYICON = WM_APP + 1

# Mouse messages delivered via lParam
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_COMMAND = 0x0111

# LoadImage constants
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x00000010
LR_DEFAULTSIZE = 0x00000040

# Menu constants
MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
MF_POPUP = 0x00000010
MF_GRAYED = 0x00000001
TPM_BOTTOMALIGN = 0x0020
TPM_LEFTALIGN = 0x0000


class _NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", ctypes.c_wchar * 128),
    ]


# Keep references alive to prevent GC of callback
_subclass_installed = False
_SUBCLASSPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long,  # LRESULT
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
    ctypes.POINTER(wintypes.UINT),  # uIdSubclass
    ctypes.POINTER(wintypes.DWORD),  # dwRefData
)
_subclass_callback_ref = None

# Map uID -> StatusIcon instance for dispatch
_icon_registry = {}
_next_icon_id = 1


def _get_main_hwnd():
    """Get the HWND of the main window."""
    app = toga.App.app
    if app and app.main_window and app.main_window._impl:
        try:
            from win32more.Microsoft.UI import Win32Interop

            window_id = app.main_window._impl.native.AppWindow.Id
            return Win32Interop.GetWindowFromWindowId(window_id)
        except Exception:
            pass
    return None


def _ensure_subclass(hwnd):
    """Install a window subclass to receive tray icon messages."""
    global _subclass_installed, _subclass_callback_ref

    if _subclass_installed:
        return

    def _subclass_proc(hwnd, msg, wparam, lparam, uid_subclass, ref_data):
        if msg == WM_TRAYICON:
            icon_id = wparam
            mouse_msg = lparam & 0xFFFF
            icon = _icon_registry.get(icon_id)
            if icon is not None:
                if mouse_msg == WM_LBUTTONUP:
                    icon._on_left_click()
                elif mouse_msg == WM_RBUTTONUP:
                    icon._on_right_click()
            return 0

        if msg == WM_COMMAND:
            # Menu item click from TrackPopupMenu.
            cmd_id = wparam & 0xFFFF
            # Look up the command in all StatusIconSets.
            app = toga.App.app
            if app and hasattr(app, "status_icons"):
                menu_items = app.status_icons._impl._menu_items
                cmd = menu_items.get(cmd_id)
                if cmd and cmd.action:
                    cmd.action(cmd)
                    return 0

        # Call the next handler in the subclass chain.
        return ctypes.windll.comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    _subclass_callback_ref = _SUBCLASSPROC(_subclass_proc)
    ctypes.windll.comctl32.SetWindowSubclass(hwnd, _subclass_callback_ref, 1, 0)
    _subclass_installed = True


class StatusIcon:
    def __init__(self, interface):
        self.interface = interface
        self.native = None
        self._icon_id = None
        self._hwnd = None
        self._hicon = None

    def _destroy_hicon(self):
        """Release the current HICON handle to prevent GDI resource leaks."""
        if self._hicon:
            ctypes.windll.user32.DestroyIcon(self._hicon)
            self._hicon = None

    def set_icon(self, icon):
        if self._icon_id is None:
            return

        # Fall back to app icon when no icon is provided.
        if not icon:
            icon = toga.App.app.icon

        hicon = self._load_hicon(icon)
        if hicon:
            self._destroy_hicon()
            self._hicon = hicon
            nid = self._make_nid()
            nid.uFlags = NIF_ICON
            nid.hIcon = hicon
            ctypes.windll.shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))

    def create(self):
        global _next_icon_id

        self._hwnd = _get_main_hwnd()
        if not self._hwnd:
            return

        _ensure_subclass(self._hwnd)

        self._icon_id = _next_icon_id
        _next_icon_id += 1
        _icon_registry[self._icon_id] = self

        nid = self._make_nid()
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP

        # Set tooltip text
        tip = self.interface.text or ""
        nid.szTip = tip[:127]

        # Set callback message
        nid.uCallbackMessage = WM_TRAYICON

        # Load icon, falling back to app icon.
        icon = self.interface.icon
        if not icon:
            icon = toga.App.app.icon
        hicon = self._load_hicon(icon)
        if hicon:
            self._hicon = hicon
            nid.hIcon = hicon

        ctypes.windll.shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

    def remove(self):
        if self._icon_id is not None:
            nid = self._make_nid()
            ctypes.windll.shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
            self._destroy_hicon()
            _icon_registry.pop(self._icon_id, None)
            self._icon_id = None

    def _make_nid(self):
        nid = _NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(_NOTIFYICONDATAW)
        nid.hWnd = self._hwnd
        nid.uID = self._icon_id
        return nid

    @staticmethod
    def _load_hicon(icon):
        """Load a win32 HICON from a toga Icon, or return None."""
        if icon and icon._impl and icon._impl.path:
            return ctypes.windll.user32.LoadImageW(
                None,
                str(icon._impl.path),
                IMAGE_ICON,
                0,
                0,
                LR_LOADFROMFILE | LR_DEFAULTSIZE,
            )
        return None

    def _on_left_click(self):
        pass

    def _on_right_click(self):
        pass


class SimpleStatusIcon(StatusIcon):
    def _on_left_click(self):
        self.interface.on_press()


class MenuStatusIcon(StatusIcon):
    def __init__(self, interface):
        super().__init__(interface)
        self._popup_menu = None

    def remove(self):
        self._destroy_popup_menu()
        super().remove()

    def _destroy_popup_menu(self):
        """Destroy the popup menu handle to prevent resource leaks."""
        if self._popup_menu:
            ctypes.windll.user32.DestroyMenu(self._popup_menu)
            self._popup_menu = None

    def _on_right_click(self):
        self._show_context_menu()

    def _on_left_click(self):
        self._show_context_menu()

    def _show_context_menu(self):
        if not self._popup_menu:
            return

        user32 = ctypes.windll.user32

        # Get cursor position for menu placement.
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))

        # SetForegroundWindow is required before TrackPopupMenu to ensure
        # the menu dismisses properly when clicking elsewhere.
        user32.SetForegroundWindow(self._hwnd)

        user32.TrackPopupMenu(
            self._popup_menu,
            TPM_LEFTALIGN | TPM_BOTTOMALIGN,
            pt.x,
            pt.y,
            0,
            self._hwnd,
            None,
        )


class StatusIconSet:
    def __init__(self, interface):
        self.interface = interface
        self._menu_items = {}

    def _get_submenu(self, group, group_cache, root_menu):
        """Get or create a submenu for a group within a popup menu."""
        try:
            return group_cache[group]
        except KeyError:
            pass

        if group is None:
            raise ValueError("Unknown top level item")

        parent_menu = self._get_submenu(group.parent, group_cache, root_menu)

        user32 = ctypes.windll.user32
        submenu = user32.CreatePopupMenu()
        user32.AppendMenuW(parent_menu, MF_STRING | MF_POPUP, submenu, group.text)

        group_cache[group] = submenu
        return submenu

    def create(self):
        # Determine the primary status icon for the COMMANDS group.
        primary_group = self.interface._primary_menu_status_icon
        if primary_group is None:
            return

        # Build group cache: each MenuStatusIcon gets its own popup menu.
        # Destroy any existing popup menus before creating new ones.
        group_cache = {}
        for menu_icon in self.interface._menu_status_icons:
            menu_icon._impl._destroy_popup_menu()
            hmenu = ctypes.windll.user32.CreatePopupMenu()
            group_cache[menu_icon] = hmenu
            menu_icon._impl._popup_menu = hmenu

        # Map the COMMANDS group to the primary status icon's menu.
        group_cache[Group.COMMANDS] = group_cache[primary_group]
        self._menu_items = {}

        cmd_id = 1000
        for cmd in self.interface.commands:
            try:
                submenu = self._get_submenu(cmd.group, group_cache, None)
            except ValueError:
                warnings.warn(
                    f"Skipping command {cmd.text!r}: unknown group {cmd.group!r}",
                    stacklevel=2,
                )
                continue

            if isinstance(cmd, Separator):
                ctypes.windll.user32.AppendMenuW(submenu, MF_SEPARATOR, 0, None)
            else:
                flags = MF_STRING
                if not cmd.enabled:
                    flags |= MF_GRAYED
                ctypes.windll.user32.AppendMenuW(submenu, flags, cmd_id, cmd.text)
                self._menu_items[cmd_id] = cmd
                cmd_id += 1
