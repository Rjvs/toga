import asyncio
from pathlib import Path


class DialogsMixin:
    supports_multiple_select_folder = False

    def _setup_dialog_result(self, dialog, result):
        """Override the dialog's _show_async to directly set the future result."""

        def automated_show(host_window, future):
            async def _auto_resolve():
                # Give the event loop a chance to run.
                await self.redraw("Dialog auto-resolving", delay=0.1)
                if not future.done():
                    future.set_result(result)

            # Don't call orig_show (which would open a real ContentDialog or picker).
            # Instead, store the future and auto-resolve it.
            dialog._impl.future = future
            asyncio.create_task(_auto_resolve(), name="auto-resolve-dialog")

        dialog._impl.show = automated_show

    def setup_info_dialog_result(self, dialog, pre_close_test_method=None):
        self._setup_dialog_result(dialog, None)

    def setup_question_dialog_result(self, dialog, result):
        self._setup_dialog_result(dialog, result)

    def setup_confirm_dialog_result(self, dialog, result):
        self._setup_dialog_result(dialog, result)

    def setup_error_dialog_result(self, dialog):
        self._setup_dialog_result(dialog, None)

    def setup_stack_trace_dialog_result(self, dialog, result):
        self._setup_dialog_result(dialog, result)

    def setup_save_file_dialog_result(self, dialog, result):
        if result is None:
            self._setup_dialog_result(dialog, None)
        else:
            self._setup_dialog_result(dialog, Path(result))

    def setup_open_file_dialog_result(self, dialog, result, multiple_select):
        if result is None:
            self._setup_dialog_result(dialog, None)
        elif multiple_select:
            self._setup_dialog_result(dialog, [Path(p) for p in result])
        else:
            self._setup_dialog_result(dialog, Path(result))

    def setup_select_folder_dialog_result(self, dialog, result, multiple_select):
        if result is None:
            self._setup_dialog_result(dialog, None)
        elif multiple_select:
            self._setup_dialog_result(dialog, [Path(p) for p in result])
        else:
            self._setup_dialog_result(dialog, Path(result))

    def is_modal_dialog(self, dialog):
        return True
