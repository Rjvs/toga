from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
from http.cookiejar import Cookie, CookieJar
from typing import TYPE_CHECKING

import toga

if TYPE_CHECKING:
    from win32more.Microsoft.UI.Xaml.Controls import WebView2
from toga.handlers import WeakrefCallable
from toga.widgets.webview import CookiesResult, JavaScriptResult

from .base import Widget


def requires_initialization(method):
    def wrapper(self, *args, **kwargs):
        def task():
            method(self, *args, **kwargs)

        self.run_after_initialization(task)

    return wrapper


class WebView(Widget):
    native: WebView2

    def create(self):
        from win32more.Microsoft.UI.Xaml.Controls import WebView2

        self.native = WebView2()
        self.native.add_NavigationCompleted(
            WeakrefCallable(self.winui3_navigation_completed)
        )
        self.loaded_future = None

        # CoreWebView2 requires async initialization. Methods decorated with
        # @requires_initialization are queued until init completes.
        self.corewebview2_available = None
        self.pending_tasks = []
        asyncio.ensure_future(self._initialize())

        # URL allowed by user interaction or on_navigation_starting handler.
        self._allowed_url = None

        # Folder for temporarily storing content larger than ~1.5 MB.
        self._large_content_dir = (
            toga.App.app.paths.cache / f"toga/webview-{self.interface.id}"
        )

    def __del__(self):  # pragma: nocover
        shutil.rmtree(self._large_content_dir, ignore_errors=True)

    async def _initialize(self):
        try:
            await self.native.EnsureCoreWebView2Async(None)
        except Exception:
            import warnings

            warnings.warn(
                "WebView2 Runtime is not available. "
                "Install it from https://developer.microsoft.com/en-us/microsoft-edge/webview2/",
                stacklevel=2,
            )
            self.corewebview2_available = False
            self.pending_tasks = None
            return

        self.corewebview2_available = True

        settings = self.native.CoreWebView2.Settings
        self.default_user_agent = settings.UserAgent

        # Initialize cookie manager.
        self.cookie_manager = self.native.CoreWebView2.CookieManager

        debug = False
        settings.AreBrowserAcceleratorKeysEnabled = debug
        settings.AreDefaultContextMenusEnabled = debug
        settings.AreDefaultScriptDialogsEnabled = True
        settings.AreDevToolsEnabled = debug
        settings.IsBuiltInErrorPageEnabled = True
        settings.IsScriptEnabled = True
        settings.IsWebMessageEnabled = True
        settings.IsStatusBarEnabled = debug
        settings.IsSwipeNavigationEnabled = False
        settings.IsZoomControlEnabled = True

        self.native.CoreWebView2.add_NavigationStarting(
            WeakrefCallable(self.winui3_navigation_starting)
        )

        for task in self.pending_tasks:
            task()
        self.pending_tasks = None

    def run_after_initialization(self, task):
        if self.corewebview2_available:
            task()
        elif self.pending_tasks is not None:
            self.pending_tasks.append(task)
        # else: init failed, silently drop the task

    ######################################################################
    # Native event handlers
    ######################################################################

    def winui3_navigation_completed(self, sender, args):
        self.interface.on_webview_load()

        if self.loaded_future:
            self.loaded_future.set_result(None)
            self.loaded_future = None

    def winui3_navigation_starting(self, sender, event):
        if self.interface.on_navigation_starting._raw:
            if self._allowed_url == "about:blank" or self._allowed_url == event.Uri:
                allow = True
            else:
                self._allowed_url = None
                result = self.interface.on_navigation_starting(url=event.Uri)
                if isinstance(result, bool):
                    allow = result
                else:
                    # Async handler — deny until the coroutine completes.
                    allow = False
            if not allow:
                event.Cancel = True

    ######################################################################
    # URL and content
    ######################################################################

    def get_url(self):
        source = self.native.Source
        if source is None:  # pragma: nocover
            return None
        url = str(source)
        return None if url == "about:blank" else url

    @requires_initialization
    def set_url(self, value, future=None):
        from win32more.Windows.Foundation import Uri

        if self.interface.on_navigation_starting._raw:
            self._allowed_url = value
        self.loaded_future = future
        if value is None:
            self.set_content("about:blank", "")
        else:
            self.native.Source = Uri(value)

    @requires_initialization
    def set_content(self, root_url, content):
        if self.interface.on_navigation_starting._raw:
            self._allowed_url = "about:blank"
        if len(content) > 1572834:
            # The WebView2 limit for NavigateToString is about 1.5 MB.
            self._large_content_dir.mkdir(parents=True, exist_ok=True)
            h = hashlib.new("sha1")
            h.update(bytes(self.interface.id, "utf-8"))
            h.update(bytes(root_url, "utf-8"))
            file_name = h.hexdigest() + ".html"
            file_path = self._large_content_dir / file_name
            file_path.write_text(content, encoding="utf-8")
            self.set_url(file_path.as_uri())
        else:
            self.native.CoreWebView2.NavigateToString(content)

    ######################################################################
    # User agent
    ######################################################################

    def get_user_agent(self):
        if self.corewebview2_available:
            return self.native.CoreWebView2.Settings.UserAgent
        return ""  # pragma: nocover

    @requires_initialization
    def set_user_agent(self, value):
        self.native.CoreWebView2.Settings.UserAgent = (
            self.default_user_agent if value is None else value
        )

    ######################################################################
    # Cookies
    ######################################################################

    def get_cookies(self):
        result = CookiesResult()

        async def _get():
            cookies = await self.cookie_manager.GetCookiesAsync(None)
            cookie_jar = CookieJar()
            for i in range(cookies.Count):
                cookie = cookies.GetAt(i)
                cookie_jar.set_cookie(
                    Cookie(
                        version=0,
                        name=cookie.Name,
                        value=cookie.Value,
                        port=None,
                        port_specified=False,
                        domain=cookie.Domain,
                        domain_specified=True,
                        domain_initial_dot=False,
                        path=cookie.Path,
                        path_specified=True,
                        secure=cookie.IsSecure,
                        expires=None,
                        discard=cookie.IsSession,
                        comment=None,
                        comment_url=None,
                        rest={},
                        rfc2109=False,
                    )
                )
            result.set_result(cookie_jar)

        self.run_after_initialization(lambda: asyncio.ensure_future(_get()))
        return result

    ######################################################################
    # JavaScript
    ######################################################################

    def evaluate_javascript(self, javascript, on_result=None):
        result = JavaScriptResult(on_result)

        async def _eval():
            raw = await self.native.CoreWebView2.ExecuteScriptAsync(javascript)
            value = json.loads(raw)
            result.set_result(value)

        self.run_after_initialization(lambda: asyncio.ensure_future(_eval()))
        return result

    ######################################################################
    # Layout
    ######################################################################

    def rehint(self):
        pass
