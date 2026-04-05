import asyncio
from pathlib import Path


class BaseDialog:
    def show(self, host_window, future):
        self.future = future
        # WinUI 3 dialogs are async-native, so we can use them directly.
        asyncio.ensure_future(self._show_async(host_window))

    async def _show_async(self, host_window):
        raise NotImplementedError


class MessageDialog(BaseDialog):
    def __init__(
        self, title, message, buttons=None, success_result=None, icon_glyph=None
    ):
        super().__init__()
        self.title = title
        self.message = message
        self.success_result = success_result
        self.icon_glyph = icon_glyph

    async def _show_async(self, host_window):
        from win32more.Microsoft.UI.Xaml.Controls import (
            ContentDialog,
            ContentDialogResult,
        )

        dialog = ContentDialog()
        dialog.Title = self.title

        if self.icon_glyph:
            dialog.Content = _dialog_content_with_icon(self.message, self.icon_glyph)
        else:
            dialog.Content = self.message

        if self.success_result == "yes":
            dialog.PrimaryButtonText = "Yes"
            dialog.CloseButtonText = "No"
        elif self.success_result == "ok_cancel":
            dialog.PrimaryButtonText = "OK"
            dialog.CloseButtonText = "Cancel"
        else:
            dialog.CloseButtonText = "OK"

        # ContentDialog requires XamlRoot
        if host_window and hasattr(host_window, "_impl"):
            content = host_window._impl.native.Content
            if content:
                dialog.XamlRoot = content.XamlRoot

        result = await dialog.ShowAsync()

        if self.success_result:
            self.future.set_result(result == ContentDialogResult.Primary)
        else:
            self.future.set_result(None)


class InfoDialog(MessageDialog):
    def __init__(self, title, message):
        super().__init__(title, message)


class QuestionDialog(MessageDialog):
    def __init__(self, title, message):
        super().__init__(title, message, success_result="yes")


class ConfirmDialog(MessageDialog):
    def __init__(self, title, message):
        super().__init__(
            title,
            message,
            success_result="ok_cancel",
            icon_glyph="\ue7ba",  # Warning
        )


class ErrorDialog(MessageDialog):
    def __init__(self, title, message=None):
        super().__init__(title, message, icon_glyph="\ue783")  # ErrorBadge


class StackTraceDialog(BaseDialog):
    def __init__(self, title, message, content, retry):
        super().__init__()
        self.title = title
        self.message = message
        self.content = content
        self.retry = retry

    async def _show_async(self, host_window):
        from win32more.Microsoft.UI.Xaml import TextWrapping
        from win32more.Microsoft.UI.Xaml.Controls import (
            ContentDialog,
            ContentDialogResult,
            Orientation,
            ScrollViewer,
            StackPanel,
            TextBlock,
        )
        from win32more.Microsoft.UI.Xaml.Media import FontFamily

        dialog = ContentDialog()
        dialog.Title = self.title

        # Build structured content: message + scrollable monospace trace.
        panel = StackPanel()
        panel.Orientation = Orientation.Vertical
        panel.Spacing = 8

        msg_block = TextBlock()
        msg_block.Text = self.message or ""
        msg_block.TextWrapping = TextWrapping.Wrap
        panel.Children.Append(msg_block)

        trace_block = TextBlock()
        trace_block.Text = self.content or ""
        trace_block.FontFamily = FontFamily("Consolas")
        trace_block.TextWrapping = TextWrapping.Wrap
        trace_block.IsTextSelectionEnabled = True

        scroll = ScrollViewer()
        scroll.Content = trace_block
        scroll.MaxHeight = 300
        panel.Children.Append(scroll)

        dialog.Content = panel

        if self.retry:
            dialog.PrimaryButtonText = "Retry"
            dialog.CloseButtonText = "Quit"
        else:
            dialog.CloseButtonText = "OK"

        if host_window and hasattr(host_window, "_impl"):
            content = host_window._impl.native.Content
            if content:
                dialog.XamlRoot = content.XamlRoot

        result = await dialog.ShowAsync()

        if self.retry:
            self.future.set_result(result == ContentDialogResult.Primary)
        else:
            self.future.set_result(None)


def _dialog_content_with_icon(message, glyph):
    """Create a StackPanel with an icon glyph and message text."""
    from win32more.Microsoft.UI.Xaml import TextWrapping, Thickness
    from win32more.Microsoft.UI.Xaml.Controls import (
        FontIcon,
        Orientation,
        StackPanel,
        TextBlock,
    )
    from win32more.Microsoft.UI.Xaml.Media import FontFamily

    panel = StackPanel()
    panel.Orientation = Orientation.Horizontal
    panel.Spacing = 12

    icon = FontIcon()
    icon.Glyph = glyph
    icon.FontFamily = FontFamily("Segoe Fluent Icons")
    icon.FontSize = 24
    icon.Margin = Thickness(0, 4, 0, 0)
    panel.Children.Append(icon)

    text = TextBlock()
    text.Text = message or ""
    text.TextWrapping = TextWrapping.Wrap
    panel.Children.Append(text)

    return panel


def _get_window_id(host_window):
    """Get the AppWindow.Id for a host window, needed by file pickers."""
    if host_window and hasattr(host_window, "_impl"):
        return host_window._impl.native.AppWindow.Id
    return None


def _build_file_type_filter(file_types):
    """Build a flat extension list for FileOpenPicker."""
    if not file_types:
        return ["*"]
    return [f".{ft}" if not ft.startswith(".") else ft for ft in file_types]


def _build_file_type_choices(file_types):
    """Build description-to-extensions map for FileSavePicker.

    Returns an ordered dict of {description: [extensions]} suitable for
    ``picker.FileTypeChoices.Insert(description, extensions)``.
    """
    if not file_types:
        return {"All Files": ["*"]}

    choices = {}
    for ft in file_types:
        ext = f".{ft}" if not ft.startswith(".") else ft
        desc = f"{ext.lstrip('.').upper()} files ({ext})"
        choices.setdefault(desc, []).append(ext)
    return choices


class SaveFileDialog(BaseDialog):
    def __init__(self, title, filename, initial_directory, file_types):
        super().__init__()
        self.title = title
        self.filename = filename
        self.initial_directory = initial_directory
        self.file_types = file_types

    async def _show_async(self, host_window):
        from win32more.Microsoft.Windows.Storage.Pickers import FileSavePicker

        window_id = _get_window_id(host_window)
        if window_id is None:
            self.future.set_result(None)
            return

        picker = FileSavePicker(window_id)
        if self.initial_directory:
            picker.SuggestedFolder = str(self.initial_directory)
        if self.filename:
            picker.SuggestedFileName = self.filename

        for desc, exts in _build_file_type_choices(self.file_types).items():
            picker.FileTypeChoices.Insert(desc, exts)

        file = await picker.PickSaveFileAsync()
        if file:
            self.future.set_result(Path(file.Path))
        else:
            self.future.set_result(None)


class OpenFileDialog(BaseDialog):
    def __init__(self, title, initial_directory, file_types, multiple_select):
        super().__init__()
        self.title = title
        self.initial_directory = initial_directory
        self.file_types = file_types
        self.multiple_select = multiple_select

    async def _show_async(self, host_window):
        from win32more.Microsoft.Windows.Storage.Pickers import FileOpenPicker

        window_id = _get_window_id(host_window)
        if window_id is None:
            self.future.set_result(None)
            return

        picker = FileOpenPicker(window_id)
        if self.initial_directory:
            picker.SuggestedFolder = str(self.initial_directory)
        for ext in _build_file_type_filter(self.file_types):
            picker.FileTypeFilter.Append(ext)

        if self.multiple_select:
            files = await picker.PickMultipleFilesAsync()
            if files and files.Size > 0:
                self.future.set_result(
                    [Path(files.GetAt(i).Path) for i in range(files.Size)]
                )
            else:
                self.future.set_result(None)
        else:
            file = await picker.PickSingleFileAsync()
            if file:
                self.future.set_result(Path(file.Path))
            else:
                self.future.set_result(None)


class SelectFolderDialog(BaseDialog):
    def __init__(self, title, initial_directory, multiple_select):
        super().__init__()
        self.title = title
        self.initial_directory = initial_directory
        self.multiple_select = multiple_select

    async def _show_async(self, host_window):
        from win32more.Microsoft.Windows.Storage.Pickers import FolderPicker

        window_id = _get_window_id(host_window)
        if window_id is None:
            self.future.set_result(None)
            return

        picker = FolderPicker(window_id)
        if self.initial_directory:
            picker.SuggestedFolder = str(self.initial_directory)
        picker.FileTypeFilter.Append("*")

        folder = await picker.PickSingleFolderAsync()
        if folder:
            result = Path(folder.Path)
            if self.multiple_select:
                self.future.set_result([result])
            else:
                self.future.set_result(result)
        else:
            self.future.set_result(None)
