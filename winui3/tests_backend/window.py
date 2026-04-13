import asyncio

from win32more.Microsoft.UI.Xaml import Window as WinUIWindow
from win32more.Microsoft.UI.Xaml.Controls import AppBarSeparator, ToolTipService

from toga import Size
from toga.constants import WindowState

from .dialogs import DialogsMixin
from .probe import BaseProbe


class WindowProbe(BaseProbe, DialogsMixin):
    # WinUI 3 supports closable via OverlappedPresenter (unlike WinForms/pythonnet).
    supports_closable = True
    supports_minimizable = True
    supports_move_while_hidden = True
    supports_unminimize = True
    supports_minimize = True
    supports_placement = True
    supports_as_image = True
    supports_focus = True
    fullscreen_presentation_equal_size = True
    maximize_fullscreen_presentation_equal_size = False

    def __init__(self, app, window):
        self.app = app
        self.window = window
        self.impl = window._impl
        super().__init__(window._impl.native)
        assert isinstance(self.native, WinUIWindow)

    async def wait_for_window(
        self,
        message,
        state=None,
    ):
        await self.redraw(message)

        if state:
            timeout = 5
            polling_interval = 0.1
            exception = None
            loop = asyncio.get_running_loop()
            start_time = loop.time()
            while (loop.time() - start_time) < timeout:
                try:
                    assert self.instantaneous_state == state
                    return
                except AssertionError as e:
                    exception = e
                    await asyncio.sleep(polling_interval)
                    continue
            raise exception

    async def cleanup(self):
        self.window.close()
        await self.redraw("Closing window")

    def close(self):
        self.native.Close()

    @property
    def content_size(self):
        client = self.client_size
        top_bars = self.impl._top_bars_height() / self.scale_factor
        return Size(
            client.width,
            client.height - top_bars,
        )

    @property
    def client_size(self):
        bounds = self.native.Bounds
        return Size(
            bounds.Width / self.scale_factor,
            bounds.Height / self.scale_factor,
        )

    @property
    def is_resizable(self):
        try:
            presenter = self.native.AppWindow.Presenter
            return presenter.IsResizable
        except Exception:
            return True

    @property
    def is_minimizable(self):
        try:
            presenter = self.native.AppWindow.Presenter
            return presenter.IsMinimizable
        except Exception:
            return True

    @property
    def is_minimized(self):
        return self.impl.get_window_state() == WindowState.MINIMIZED

    def minimize(self):
        self.impl.set_window_state(WindowState.MINIMIZED)

    def unminimize(self):
        self.impl.set_window_state(WindowState.NORMAL)

    @property
    def container_probe(self):
        return BaseProbe(self.impl.native_content)

    @property
    def instantaneous_state(self):
        return self.impl.get_window_state(in_progress_state=False)

    @property
    def menubar_probe(self):
        bar = getattr(self.impl, "menubar_native", None)
        return BaseProbe(bar) if bar else None

    @property
    def toolbar_probe(self):
        bar = getattr(self.impl, "toolbar_native", None)
        return BaseProbe(bar) if bar else None

    def has_toolbar(self):
        return getattr(self.impl, "toolbar_native", None) is not None

    def _native_toolbar_item(self, index):
        toolbar = self.impl.toolbar_native
        return toolbar.PrimaryCommands.GetAt(index)

    def assert_is_toolbar_separator(self, index, section=False):
        assert isinstance(self._native_toolbar_item(index), AppBarSeparator)

    def assert_toolbar_item(self, index, label, tooltip, has_icon, enabled):
        item = self._native_toolbar_item(index)
        assert item.Label == label
        if tooltip:
            actual_tooltip = ToolTipService.GetToolTip(item)
            assert actual_tooltip == tooltip
        assert (item.Icon is not None) == has_icon
        assert item.IsEnabled == enabled

    def press_toolbar_button(self, index):
        item = self._native_toolbar_item(index)
        # Find the corresponding command and invoke it.
        for cmd in self.app.commands:
            if hasattr(cmd, "_impl") and item in cmd._impl.native:
                cmd.action(cmd)
                return
        # Fallback: command not found for this toolbar item.
        raise AssertionError(
            f"Could not find command for toolbar item at index {index}"
        )
