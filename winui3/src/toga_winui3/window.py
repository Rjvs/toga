from __future__ import annotations

from typing import TYPE_CHECKING

from win32more.Microsoft.UI.Windowing import (
    AppWindowPresenterKind,
    OverlappedPresenterState,
)
from win32more.Microsoft.UI.Xaml import (
    VerticalAlignment,
    Window as WinUIWindow,
)
from win32more.Microsoft.UI.Xaml.Controls import (
    AppBarButton,
    AppBarSeparator,
    BitmapIcon,
    CommandBar,
    MenuBar,
    MenuBarItem,
    MenuFlyoutSeparator,
    MenuFlyoutSubItem,
    Orientation,
    StackPanel,
    ToolTipService,
)
from win32more.Microsoft.UI.Xaml.Media import MicaBackdrop

from toga.command import Separator
from toga.constants import WindowState
from toga.handlers import WeakrefCallable
from toga.types import Position, Size

from .container import Container
from .screens import Screen as ScreenImpl

if TYPE_CHECKING:  # pragma: no cover
    from toga.types import PositionT, SizeT


class Window(Container):
    native: WinUIWindow

    def __init__(self, interface, title, position, size):
        self.interface = interface

        self.create()
        super().__init__(self.native)

        self._in_presentation_mode = False
        self._pending_state_transition = None
        self._previous_state = WindowState.NORMAL
        self._cached_window_size = Size(int(size[0]), int(size[1]))
        self._min_window_size = None  # (width, height) in native pixels, or None

        # Enforce resizable/minimizable constraints via the OverlappedPresenter.
        presenter = self.native.AppWindow.Presenter
        presenter.IsResizable = self.interface.resizable
        presenter.IsMinimizable = self.interface.minimizable
        presenter.IsMaximizable = self.interface.resizable

        self.set_title(title)
        self.set_size(size)
        if position:
            self.set_position(position)

    def create(self):
        self.native = WinUIWindow()
        # Apply Mica backdrop for modern Windows look
        self.native.SystemBackdrop = MicaBackdrop()

        # Wire up window events.  Use AppWindow.Closing (not Window.Closed)
        # so we can cancel the close and let on_close() decide.
        self._closing_token = self.native.AppWindow.add_Closing(
            WeakrefCallable(self.winui3_closing)
        )
        self._size_changed_token = self.native.add_SizeChanged(
            WeakrefCallable(self.winui3_size_changed)
        )
        self._activated_token = self.native.add_Activated(
            WeakrefCallable(self.winui3_activated)
        )
        self._visibility_token = self.native.add_VisibilityChanged(
            WeakrefCallable(self.winui3_visibility_changed)
        )

    ######################################################################
    # Native event handlers
    ######################################################################

    def winui3_closing(self, sender, args):
        # If the app is exiting, allow the close unconditionally.
        if self.interface.app._impl._is_exiting:
            return

        # If the window is closable, delegate to on_close() which will
        # decide whether to actually close (potentially calling our close()).
        # Always cancel the native close; if on_close() approves, it will
        # call window.close() which removes this handler first.
        if self.interface.closable:
            args.Cancel = True
            self.interface.on_close()
        else:
            # Non-closable windows: always cancel.
            args.Cancel = True

    def winui3_size_changed(self, sender, args):
        # Enforce minimum window size (WinUI 3 has no native MinimumSize property).
        if self._min_window_size:
            app_window = self.native.AppWindow
            current = app_window.Size
            min_w, min_h = self._min_window_size
            clamped_w = max(current.Width, min_w)
            clamped_h = max(current.Height, min_h)
            if clamped_w != current.Width or clamped_h != current.Height:
                from win32more.Windows.Graphics import SizeInt32

                new_size = SizeInt32()
                new_size.Width = clamped_w
                new_size.Height = clamped_h
                app_window.Resize(new_size)
                return  # Resize will trigger another SizeChanged

        current_state = self.get_window_state()
        if current_state != WindowState.MINIMIZED:
            self.interface.on_resize()
            self.resize_content()

        if self._previous_state != current_state:
            if self._previous_state == WindowState.MINIMIZED:
                self.interface.on_show()
            elif current_state == WindowState.MINIMIZED:
                self.interface.on_hide()
            self._previous_state = current_state

    def winui3_visibility_changed(self, sender, args):
        if self.native.Visible:
            self.interface.on_show()
        else:
            self.interface.on_hide()

    def winui3_activated(self, sender, args):
        from win32more.Microsoft.UI.Xaml import WindowActivationState

        if args.WindowActivationState != WindowActivationState.Deactivated:
            # Track this as the active window on the app.
            if hasattr(self.interface, "app") and self.interface.app:
                self.interface.app._impl._active_window = self.interface
            self.interface.on_gain_focus()
        else:
            self.interface.on_lose_focus()

    ######################################################################
    # Window properties
    ######################################################################

    def get_title(self):
        return self.native.Title

    def set_title(self, title):
        self.native.Title = title

    ######################################################################
    # Window lifecycle
    ######################################################################

    def close(self):
        # Clear active-window reference if this window is the active one.
        if hasattr(self.interface, "app") and self.interface.app:
            app_impl = self.interface.app._impl
            if app_impl._active_window is self.interface:
                app_impl._active_window = None

        # Remove event handlers so the close goes through without
        # being cancelled (mirrors WinForms FormClosing -= pattern).
        if self._closing_token is not None:
            self.native.AppWindow.remove_Closing(self._closing_token)
            self._closing_token = None
        if self._size_changed_token is not None:
            self.native.remove_SizeChanged(self._size_changed_token)
            self._size_changed_token = None
        if self._activated_token is not None:
            self.native.remove_Activated(self._activated_token)
            self._activated_token = None
        if self._visibility_token is not None:
            self.native.remove_VisibilityChanged(self._visibility_token)
            self._visibility_token = None
        self.native.Close()

    def set_app(self, app):
        if app and app.interface.icon and app.interface.icon._impl:
            icon_path = app.interface.icon._impl.path
            if icon_path:
                self.native.AppWindow.SetIcon(str(icon_path))

    def show(self):
        if self.interface.content is not None:
            self.interface.content.refresh()
        self.native.Activate()

    ######################################################################
    # Window content and resources
    ######################################################################

    def _top_bars_height(self):
        return 0

    def refreshed(self):
        super().refreshed()
        if self.interface.content:
            layout = self.interface.content.layout
            scale = self._dpi_scale()
            decor_w, decor_h = self._decoration_size()
            top_bars = self._top_bars_height()
            # min_width/min_height are in DIPs; convert to physical and add decor.
            self._min_window_size = (
                int(layout.min_width * scale) + decor_w,
                int((layout.min_height + top_bars) * scale) + decor_h,
            )

    def resize_content(self):
        # Get the content area size from the WinUI 3 window.
        # WinUI 3 content area is the full window minus title bar.
        bounds = self.native.Bounds
        vertical_shift = self._top_bars_height()
        super().resize_content(
            bounds.Width,
            bounds.Height - vertical_shift,
        )

    ######################################################################
    # Window size
    ######################################################################

    def _dpi_scale(self):
        """Return the DPI scale factor for this window's current screen."""
        return self.get_current_screen()._scale_factor

    def _decoration_size(self):
        """Return (decor_w, decor_h) in physical pixels.

        Returns (0, 0) when Bounds is zero (window not yet laid out).
        """
        bounds = self.native.Bounds
        if bounds.Width == 0 and bounds.Height == 0:
            return 0, 0
        scale = self._dpi_scale()
        app_window = self.native.AppWindow
        decor_w = app_window.Size.Width - int(bounds.Width * scale)
        decor_h = app_window.Size.Height - int(bounds.Height * scale)
        return decor_w, decor_h

    def get_size(self) -> Size:
        """Return the content area size in CSS pixels (DIPs).

        Window.Bounds gives the content area in DIPs; AppWindow.Size is
        physical pixels including title bar and borders.
        """
        if self.interface.state == WindowState.MINIMIZED:
            if self._cached_window_size is not None:
                return self._cached_window_size
            # Defensive fallback: should not happen if set_window_state
            # correctly caches before minimizing.
            return Size(0, 0)

        bounds = self.native.Bounds
        return Size(int(bounds.Width), int(bounds.Height))

    def set_size(self, size: SizeT):
        """Set the content area size from CSS pixels (DIPs).

        We must convert DIPs → physical pixels and add window decoration
        (title bar + borders) which are in physical pixels.
        """
        from win32more.Windows.Graphics import SizeInt32

        scale = self._dpi_scale()
        app_window = self.native.AppWindow
        decor_w, decor_h = self._decoration_size()

        native_size = SizeInt32()
        native_size.Width = int(size[0] * scale) + decor_w
        native_size.Height = int(size[1] * scale) + decor_h
        app_window.Resize(native_size)

    ######################################################################
    # Window position
    ######################################################################

    def get_current_screen(self):
        try:
            from win32more.Microsoft.UI import Win32Interop

            window_id = self.native.AppWindow.Id
            hwnd = Win32Interop.GetWindowFromWindowId(window_id)
            return ScreenImpl.from_hwnd(hwnd)
        except Exception:
            return ScreenImpl.primary()

    def get_position(self) -> Position:
        """Return window position in CSS pixels (DIPs).

        AppWindow.Position is in physical pixels; scale by the primary
        screen's DPI factor (matching WinForms which uses the primary screen
        for the coordinate system).
        """
        app_window = self.native.AppWindow
        pos = app_window.Position
        primary_scale = ScreenImpl.primary()._scale_factor
        return Position(int(pos.X / primary_scale), int(pos.Y / primary_scale))

    def set_position(self, position: PositionT):
        from win32more.Windows.Graphics import PointInt32

        primary_scale = ScreenImpl.primary()._scale_factor
        app_window = self.native.AppWindow
        point = PointInt32()
        point.X = int(position[0] * primary_scale)
        point.Y = int(position[1] * primary_scale)
        app_window.Move(point)

    ######################################################################
    # Window visibility
    ######################################################################

    def get_visible(self):
        return self.native.Visible

    def hide(self):
        self.native.AppWindow.Hide()

    ######################################################################
    # Window state
    ######################################################################

    def get_window_state(self, in_progress_state=False):
        if in_progress_state and self._pending_state_transition:
            return self._pending_state_transition

        if self._in_presentation_mode:
            return WindowState.PRESENTATION

        app_window = self.native.AppWindow
        presenter = app_window.Presenter

        if presenter.Kind == AppWindowPresenterKind.FullScreen:
            return WindowState.FULLSCREEN

        if presenter.Kind == AppWindowPresenterKind.Overlapped:
            state = presenter.State
            if state == OverlappedPresenterState.Maximized:
                return WindowState.MAXIMIZED
            elif state == OverlappedPresenterState.Minimized:
                return WindowState.MINIMIZED

        return WindowState.NORMAL

    def set_window_state(self, state):
        # If the app is in presentation mode, but this window isn't, then exit
        # app presentation mode before setting the requested state — unless
        # we're entering presentation mode ourselves.
        if state != WindowState.PRESENTATION and any(
            window.state == WindowState.PRESENTATION
            for window in self.interface.app.windows
            if window != self.interface
        ):
            self.interface.app.exit_presentation_mode()

        current_state = self.get_window_state()
        if current_state == state:
            return

        self._pending_state_transition = state
        app_window = self.native.AppWindow

        match current_state, state:
            case WindowState.NORMAL, WindowState.MAXIMIZED:
                app_window.SetPresenter(AppWindowPresenterKind.Default)
                app_window.Presenter.Maximize()

            case WindowState.NORMAL, WindowState.MINIMIZED:
                # Cache size before minimizing (WinUI 3 may report 0x0).
                self._cached_window_size = self.interface.size
                app_window.SetPresenter(AppWindowPresenterKind.Default)
                app_window.Presenter.Minimize()

            case WindowState.NORMAL, WindowState.FULLSCREEN:
                app_window.SetPresenter(AppWindowPresenterKind.FullScreen)

            case WindowState.NORMAL, WindowState.PRESENTATION:
                self._enter_presentation_mode()

            case _:
                # Non-NORMAL → target: restore to NORMAL first, then recurse.
                if current_state == WindowState.PRESENTATION:
                    self._exit_presentation_mode()
                else:
                    app_window.SetPresenter(AppWindowPresenterKind.Default)

                self.set_window_state(state)
                return  # recursive call handles _pending_state_transition

        self._pending_state_transition = None

    def _enter_presentation_mode(self):
        """Enter presentation mode (fullscreen).

        Override in MainWindow to hide menus.
        """
        self._before_presentation_mode_screen = self.interface.screen
        self._in_presentation_mode = True
        self.native.AppWindow.SetPresenter(AppWindowPresenterKind.FullScreen)

    def _exit_presentation_mode(self):
        """Exit presentation mode. Override in MainWindow to restore menus."""
        self._in_presentation_mode = False
        self.native.AppWindow.SetPresenter(AppWindowPresenterKind.Default)
        if hasattr(self, "_before_presentation_mode_screen"):
            self.interface.screen = self._before_presentation_mode_screen
            del self._before_presentation_mode_screen

    ######################################################################
    # Window capabilities
    ######################################################################

    def get_image_data(self):
        """Capture window content as PNG image bytes using GDI."""
        from .libs.screenshot import capture_rect

        app_window = self.native.AppWindow
        pos = app_window.Position
        bounds = self.native.Bounds
        scale = self._dpi_scale()
        decor_w, decor_h = self._decoration_size()
        # decor_h is the total vertical decoration (title bar + bottom border).
        # The bottom border is half the horizontal decoration (symmetric).
        bottom_border = decor_w // 2
        title_bar_height = decor_h - bottom_border
        x = pos.X
        y = pos.Y + title_bar_height
        w = int(bounds.Width * scale)
        h = int(bounds.Height * scale)
        return capture_rect(x, y, w, h)


class MainWindow(Window):
    def __init__(self, interface, title, position, size):
        super().__init__(interface, title, position, size)

        # Now that Container.__init__ has created native_content (the Canvas)
        # and set it as window.Content, wrap it in a StackPanel so MenuBar
        # and CommandBar can sit above the content area.
        self._root_panel = StackPanel()
        self._root_panel.Orientation = Orientation.Vertical

        # Replace the window's direct Content with the StackPanel,
        # and re-parent the Canvas inside it.
        self.native.Content = self._root_panel
        self.native_content.VerticalAlignment = VerticalAlignment.Stretch
        self._root_panel.Children.Append(self.native_content)

    def create(self):
        super().create()
        self.toolbar_native = None
        self.menubar_native = None

    def _top_bars_height(self):
        from win32more.Microsoft.UI.Xaml import Visibility

        height = 0
        if self.menubar_native and self.menubar_native.Visibility == Visibility.Visible:
            height += self.menubar_native.ActualHeight
        if self.toolbar_native and self.toolbar_native.Visibility == Visibility.Visible:
            height += self.toolbar_native.ActualHeight
        return height

    def _enter_presentation_mode(self):
        from win32more.Microsoft.UI.Xaml import Visibility

        if self.menubar_native:
            self.menubar_native.Visibility = Visibility.Collapsed
        if self.toolbar_native:
            self.toolbar_native.Visibility = Visibility.Collapsed
        super()._enter_presentation_mode()
        self.resize_content()

    def _exit_presentation_mode(self):
        from win32more.Microsoft.UI.Xaml import Visibility

        super()._exit_presentation_mode()
        if self.menubar_native:
            self.menubar_native.Visibility = Visibility.Visible
        if self.toolbar_native:
            self.toolbar_native.Visibility = Visibility.Visible
        self.resize_content()

    def _submenu(self, group, group_cache):
        """Get or create the submenu for a command group."""
        try:
            return group_cache[group]
        except KeyError:
            pass

        if group is None:
            raise ValueError("Unknown top level item")

        parent_menu = self._submenu(group.parent, group_cache)

        if group.parent is None:
            # Top-level group: use a MenuBarItem.
            submenu = MenuBarItem()
            submenu.Title = group.text
            self.menubar_native.Items.Append(submenu)
        else:
            # Nested group: use a MenuFlyoutSubItem.
            submenu = MenuFlyoutSubItem()
            submenu.Text = group.text
            parent_menu.Items.Append(submenu)

        group_cache[group] = submenu
        return submenu

    def create_menus(self):
        if self.menubar_native:
            # Clear existing menu items.
            self.menubar_native.Items.Clear()
        else:
            self.menubar_native = MenuBar()
            # Insert at position 0 (before the content Canvas).
            self._root_panel.Children.InsertAt(0, self.menubar_native)

        group_cache = {None: self.menubar_native}

        for cmd in self.interface.app.commands:
            submenu = self._submenu(cmd.group, group_cache)
            if isinstance(cmd, Separator):
                submenu.Items.Append(MenuFlyoutSeparator())
            else:
                item = cmd._impl.create_menu_item()
                submenu.Items.Append(item)

        self.resize_content()

    def create_toolbar(self):
        if self.interface.toolbar:
            if self.toolbar_native:
                self.toolbar_native.PrimaryCommands.Clear()
            else:
                self.toolbar_native = CommandBar()
                # Insert after menubar (if present) but before the Canvas.
                insert_idx = 1 if self.menubar_native else 0
                self._root_panel.Children.InsertAt(insert_idx, self.toolbar_native)

            prev_group = None
            for cmd in self.interface.toolbar:
                if isinstance(cmd, Separator):
                    self.toolbar_native.PrimaryCommands.Append(AppBarSeparator())
                    prev_group = None
                else:
                    # Insert separator between different groups.
                    if prev_group is not None and prev_group != cmd.group:
                        self.toolbar_native.PrimaryCommands.Append(AppBarSeparator())

                    prev_group = cmd.group

                    btn = AppBarButton()
                    btn.Label = cmd.text
                    if cmd.tooltip is not None:
                        ToolTipService.SetToolTip(btn, cmd.tooltip)
                    if cmd.icon is not None and cmd.icon._impl:
                        icon = BitmapIcon()
                        icon_path = cmd.icon._impl.path
                        if icon_path:
                            from win32more.Windows.Foundation import Uri

                            icon.UriSource = Uri(f"file:///{icon_path}")
                        btn.Icon = icon
                    btn.IsEnabled = cmd.enabled
                    btn.add_Click(WeakrefCallable(cmd._impl.winui3_click))
                    cmd._impl.native.append(btn)
                    self.toolbar_native.PrimaryCommands.Append(btn)

        elif self.toolbar_native:
            idx = _index_of_child(self._root_panel, self.toolbar_native)
            if idx is not None:
                self._root_panel.Children.RemoveAt(idx)
            self.toolbar_native = None

        self.resize_content()


def _index_of_child(panel, child):
    """Find the index of a child in a Panel's Children collection."""
    children = panel.Children
    for i in range(children.Size):
        if children.GetAt(i) == child:
            return i
    return None
