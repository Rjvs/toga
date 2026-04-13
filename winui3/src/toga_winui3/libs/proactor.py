import asyncio
import sys
import threading
import traceback
from asyncio import events

from toga.handlers import WeakrefCallable


class WinUI3ProactorEventLoop(asyncio.ProactorEventLoop):
    """Asyncio event loop integrated with the WinUI 3 XAML message pump.

    Uses a DispatcherQueueTimer to periodically process asyncio events on the
    UI thread, mirroring the approach used by the WinForms backend's
    WinformsProactorEventLoop (which uses Task.Delay/ContinueWith + Invoke).

    The DispatcherQueueTimer fires its Tick callback directly on the UI thread,
    so no cross-thread marshaling is needed.
    """

    def run_forever(self, app):
        """Set up the asyncio event loop, integrate it with the WinUI 3
        XAML message pump, and start the application.

        :param app: The Toga App implementation instance.
        """
        self.call_soon(self._loop_self_reading)

        # Remember the application.
        self.app = app
        self._dispatcher_timer = None

        # Set up the Proactor running state — equivalent to
        # BaseEventLoop.run_forever() setup.
        if sys.version_info < (3, 13):
            self._check_closed()
            if self.is_running():  # pragma: no cover
                raise RuntimeError("This event loop is already running")
            if events._get_running_loop() is not None:  # pragma: no cover
                raise RuntimeError(
                    "Cannot run the event loop while another loop is running"
                )
            self._thread_id = threading.get_ident()
            self._old_agen_hooks = sys.get_asyncgen_hooks()
            sys.set_asyncgen_hooks(
                firstiter=self._asyncgen_firstiter_hook,
                finalizer=self._asyncgen_finalizer_hook,
            )

            events._set_running_loop(self)
        else:  # pragma: no cover
            self._orig_state = self._run_forever_setup()

        # Start the XAML application. This is blocking (like
        # WinForms.Application.Run). OnLaunched will call app.create()
        # which calls start_ticking() to begin asyncio integration.
        from win32more.winui3 import XamlApplication

        XamlApplication.Start(app._winui3_app_class)

    def start_ticking(self):
        """Begin periodic asyncio event processing on the UI thread.

        Must be called from the UI thread after the XAML application has
        launched (typically from App.create via OnLaunched).
        """
        from win32more.Microsoft.UI.Dispatching import DispatcherQueue
        from win32more.Windows.Foundation import TimeSpan

        dq = DispatcherQueue.GetForCurrentThread()
        self._dispatcher_timer = dq.CreateTimer()
        interval = TimeSpan()
        interval.Duration = 50000  # 5 ms in 100-nanosecond units
        self._dispatcher_timer.Interval = interval
        self._dispatcher_timer.IsRepeating = True
        self._dispatcher_timer.add_Tick(WeakrefCallable(self._on_tick))
        self._dispatcher_timer.Start()

    def _on_tick(self, sender, args):
        """Process one iteration of the asyncio event loop.

        Called by the DispatcherQueueTimer on the UI thread.
        """
        try:
            if self.app._is_exiting:
                self._stop_ticking()
                self._cleanup()
                return

            self._run_once()

            # Ensure there is always something for the select call to process,
            # preventing the event loop from blocking.
            self.call_soon(self._loop_self_reading)

            # Adjust timer interval based on pending work.
            if self._ready:
                self._set_tick_interval(0)
            elif self._scheduled:
                first = self._scheduled[0]
                ms_until = int(max(0, (first.when() - self.time()) * 1000))
                self._set_tick_interval(min(5, ms_until))
            else:
                self._set_tick_interval(5)

        # Exceptions thrown by this method will be silently ignored by WinRT.
        except BaseException:  # pragma: no cover
            traceback.print_exc()

    def _set_tick_interval(self, ms):
        """Update the timer interval in milliseconds."""
        if self._dispatcher_timer is not None:
            from win32more.Windows.Foundation import TimeSpan

            interval = TimeSpan()
            interval.Duration = ms * 10000  # Convert ms to 100-nanosecond units
            self._dispatcher_timer.Interval = interval

    def _stop_ticking(self):
        """Stop the periodic timer."""
        if self._dispatcher_timer is not None:
            self._dispatcher_timer.Stop()
            self._dispatcher_timer = None

    def _cleanup(self):  # pragma: no cover
        """Perform cleanup when the app exits.

        This duplicates the 'finally' behavior of BaseEventLoop.run_forever().
        """
        if sys.version_info < (3, 13):
            self._stopping = False
            self._thread_id = None
            events._set_running_loop(None)
            self._set_coroutine_origin_tracking(False)
            sys.set_asyncgen_hooks(*self._old_agen_hooks)
        else:
            self._run_forever_cleanup()
