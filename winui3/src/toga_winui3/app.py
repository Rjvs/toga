import asyncio

from win32more.winui3 import XamlApplication

from toga.dialogs import InfoDialog

from .screens import Screen as ScreenImpl


class App:
    # WinUI 3 apps exit when the last window is closed
    CLOSE_ON_LAST_WINDOW = True
    # WinUI 3 apps use default command line handling
    HANDLES_COMMAND_LINE = False

    def __init__(self, interface):
        self.interface = interface
        self.interface._impl = self

        # Track whether the app is exiting.
        self._is_exiting = False
        # Required by core's exit_presentation_mode().
        self._exiting_presentation = False

        # Cursor visibility tracking
        self._cursor_visible = True

        # Active window tracking (set by Window._on_activated)
        self._active_window = None

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def create(self):
        self.native = _WinUI3App._instance
        # Populate the main window as soon as the event loop is running.
        self.loop.call_soon(self.interface._startup)

    ######################################################################
    # Commands and menus
    ######################################################################

    def create_standard_commands(self):
        pass

    def create_menus(self):
        # WinUI 3 menus are created on the Window.
        for window in self.interface.windows:
            if hasattr(window._impl, "create_menus"):
                window._impl.create_menus()

    ######################################################################
    # App lifecycle
    ######################################################################

    def exit(self):  # pragma: no cover
        self._is_exiting = True
        # Close all windows to trigger app exit
        for window in list(self.interface.windows):
            window._impl.close()

    def main_loop(self):
        # Store a reference to this App impl so _WinUI3App can find it.
        _WinUI3App._app_impl = self
        XamlApplication.Start(_WinUI3App)

    def set_icon(self, icon):
        # Set the icon on all existing windows.
        if icon and icon._impl:
            icon_path = str(icon._impl.path)
            for window in self.interface.windows:
                try:
                    window._impl.native.AppWindow.SetIcon(icon_path)
                except Exception as e:
                    import warnings

                    warnings.warn(
                        f"Failed to set icon on window: {e}",
                        stacklevel=2,
                    )

    def set_main_window(self, window):
        pass

    ######################################################################
    # App resources
    ######################################################################

    def get_primary_screen(self):
        return ScreenImpl.primary()

    def get_screens(self):
        return ScreenImpl.all_screens()

    ######################################################################
    # App state
    ######################################################################

    def get_dark_mode_state(self):
        try:
            from win32more.Windows.UI.ViewManagement import UIColorType, UISettings

            settings = UISettings()
            fg = settings.GetColorValue(UIColorType.Foreground)
            # If the foreground is light, the system is in dark mode.
            return (int(fg.R) + int(fg.G) + int(fg.B)) > 381
        except Exception:
            return None

    ######################################################################
    # App capabilities
    ######################################################################

    def beep(self):
        from win32more.Windows.Win32.UI.WindowsAndMessaging import MB_OK, MessageBeep

        MessageBeep(MB_OK)

    def show_about_dialog(self):
        message_parts = []
        if self.interface.version is not None:
            message_parts.append(
                f"{self.interface.formal_name} v{self.interface.version}"
            )
        else:
            message_parts.append(self.interface.formal_name)

        if self.interface.author is not None:
            message_parts.append(f"Author: {self.interface.author}")
        if self.interface.description is not None:
            message_parts.append(f"\n{self.interface.description}")
        asyncio.create_task(
            self.interface.dialog(
                InfoDialog(
                    f"About {self.interface.formal_name}", "\n".join(message_parts)
                )
            )
        )

    ######################################################################
    # Cursor control
    ######################################################################

    def hide_cursor(self):
        if self._cursor_visible:
            from win32more.Windows.Win32.UI.WindowsAndMessaging import ShowCursor

            ShowCursor(False)
            self._cursor_visible = False

    def show_cursor(self):
        if not self._cursor_visible:
            from win32more.Windows.Win32.UI.WindowsAndMessaging import ShowCursor

            ShowCursor(True)
            self._cursor_visible = True

    ######################################################################
    # Window control
    ######################################################################

    def get_current_window(self):
        # Validate the tracked active window is still alive.
        if (
            self._active_window is not None
            and self._active_window in self.interface.windows
        ):
            return self._active_window._impl
        # Stale or unset — clear and fall back to first window.
        self._active_window = None
        for window in self.interface.windows:
            return window._impl
        return None

    def set_current_window(self, window):
        window._impl.native.Activate()


class _WinUI3App(XamlApplication):
    """Internal XamlApplication subclass that bridges win32more's app lifecycle
    with Toga's App implementation."""

    _app_impl = None
    _instance = None

    def OnLaunched(self, args):
        _WinUI3App._instance = self
        self._app_impl = _WinUI3App._app_impl
        self._app_impl.create()
