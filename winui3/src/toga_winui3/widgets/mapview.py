from __future__ import annotations

import asyncio
import html
import json
from typing import TYPE_CHECKING

from toga.handlers import WeakrefCallable
from toga.types import LatLng

from .base import Widget

if TYPE_CHECKING:
    from win32more.Microsoft.UI.Xaml.Controls import WebView2

MAPVIEW_HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
        crossorigin=""/>
    <script
        src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
        crossorigin=""></script>

    <style>
        html, body {
            height: 100%;
            margin: 0;
        }
        #map {
            height: 100%;
            width: 100%;
        }
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        const map = L.map("map");
        const pins = {};
        const tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 20,
            attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(map);

        map.on('moveend', function() {
            var center = map.getCenter();
            window.chrome.webview.postMessage(JSON.stringify({
                type: 'moveend', lat: center.lat, lng: center.lng
            }));
        });
        map.on('zoomend', function() {
            window.chrome.webview.postMessage(JSON.stringify({
                type: 'zoomend', zoom: map.getZoom()
            }));
        });
    </script>
</body>
</html>
"""  # noqa: E501


def pin_id(pin):
    "Rendering utility; output the ID of the pin"
    return hex(id(pin))


def latlng(location):
    "Rendering utility; output a lat/lng coordinate"
    return f"[{location.lat}, {location.lng}]"


def popup(pin):
    "Rendering utility; output the content of the pin popup"
    title = html.escape(str(pin.title))
    if pin.subtitle:
        subtitle = html.escape(str(pin.subtitle))
        return f"<b>{title}</b><br>{subtitle}"
    else:
        return f"<b>{title}</b>"


class MapView(Widget):
    native: WebView2
    SUPPORTS_ON_SELECT = False

    def create(self):
        from win32more.Microsoft.UI.Xaml.Controls import WebView2

        self.native = WebView2()
        self.native.add_NavigationCompleted(
            WeakrefCallable(self.winui3_navigation_completed)
        )

        # Two-phase startup: WebView2 init → Leaflet HTML load.
        # Commands are queued in the backlog until the page is ready.
        self.backlog = []
        self._init_failed = False

        # Cache location and zoom so getters don't need synchronous JS eval.
        self._location = LatLng(0.0, 0.0)
        self._zoom = 0
        self._pins = set()

        asyncio.ensure_future(self._initialize())

    async def _initialize(self):
        try:
            await self.native.EnsureCoreWebView2Async(None)
        except Exception:
            import warnings

            warnings.warn(
                "WebView2 Runtime is not available. "
                "MapView requires WebView2 to function.",
                stacklevel=2,
            )
            self._init_failed = True
            return

        settings = self.native.CoreWebView2.Settings
        settings.AreDefaultContextMenusEnabled = False
        settings.AreDevToolsEnabled = False
        settings.IsZoomControlEnabled = True
        settings.IsWebMessageEnabled = True

        self.native.CoreWebView2.add_WebMessageReceived(
            WeakrefCallable(self.winui3_web_message_received)
        )

        self.native.CoreWebView2.NavigateToString(MAPVIEW_HTML_CONTENT)

    def winui3_navigation_completed(self, sender, args):
        # NavigationCompleted can fire multiple times (e.g. for the initial
        # about:blank page during EnsureCoreWebView2Async, then again for the
        # Leaflet HTML).  Only replay the backlog once.
        if self.backlog is None:
            return
        for javascript in self.backlog:
            self.native.CoreWebView2.ExecuteScriptAsync(javascript)
        self.backlog = None

    def winui3_web_message_received(self, sender, args):
        """Handle postMessage from Leaflet event listeners to keep cache in sync."""
        try:
            raw = args.TryGetWebMessageAsString()
            message = json.loads(raw)
        except (json.JSONDecodeError, ValueError, AttributeError):
            return

        msg_type = message.get("type")
        if msg_type == "moveend":
            self._location = LatLng(message["lat"], message["lng"])
        elif msg_type == "zoomend":
            self._zoom = message["zoom"]

    def _invoke(self, javascript):
        if self._init_failed:
            return
        if self.backlog is not None:
            self.backlog.append(javascript)
        else:
            self.native.CoreWebView2.ExecuteScriptAsync(javascript)

    ######################################################################
    # Location and zoom
    ######################################################################

    def get_location(self):
        return self._location

    def set_location(self, position):
        self._location = position
        self._invoke(f"map.panTo({latlng(position)});")

    def get_zoom(self):
        return self._zoom

    def set_zoom(self, zoom):
        self._zoom = zoom
        self._invoke(f"map.setZoom({zoom});")

    ######################################################################
    # Pins
    ######################################################################

    def add_pin(self, pin):
        content = json.dumps(popup(pin))
        self._invoke(
            f'pins["{pin_id(pin)}"] = L.marker({latlng(pin.location)}).addTo(map)'
            f".bindPopup({content});"
        )
        self._pins.add(pin_id(pin))

    def update_pin(self, pin):
        content = json.dumps(popup(pin))
        self._invoke(
            f'pins["{pin_id(pin)}"].setLatLng({latlng(pin.location)})'
            f".setPopupContent({content});"
        )

    def remove_pin(self, pin):
        self._invoke(
            f'map.removeLayer(pins["{pin_id(pin)}"]); delete pins["{pin_id(pin)}"];'
        )
        self._pins.discard(pin_id(pin))

    ######################################################################
    # Layout
    ######################################################################

    def rehint(self):
        pass
