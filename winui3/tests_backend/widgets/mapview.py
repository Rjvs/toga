import asyncio
import json

import pytest
from win32more.Microsoft.UI.Xaml.Controls import WebView2

from .base import SimpleProbe


def region_eq(r1, r2):
    return (
        pytest.approx(r1[0]["lat"]) == pytest.approx(r2[0]["lat"])
        and pytest.approx(r1[1]["lat"]) == pytest.approx(r2[1]["lat"])
        and pytest.approx(r1[0]["lng"]) == pytest.approx(r2[0]["lng"])
        and pytest.approx(r1[1]["lng"]) == pytest.approx(r2[1]["lng"])
    )


class MapViewProbe(SimpleProbe):
    native_class = WebView2

    async def _eval_js(self, js):
        """Evaluate JavaScript and return the parsed result."""
        result = await self.native.CoreWebView2.ExecuteScriptAsync(js)
        return json.loads(result)

    async def _map_region(self):
        northeast = await self._eval_js(
            "JSON.stringify(map.getBounds().getNorthEast());"
        )
        southwest = await self._eval_js(
            "JSON.stringify(map.getBounds().getSouthWest());"
        )
        # _eval_js returns the JSON string; parse it again since
        # ExecuteScriptAsync wraps the result.
        if isinstance(northeast, str):
            northeast = json.loads(northeast)
        if isinstance(southwest, str):
            southwest = json.loads(southwest)
        return northeast, southwest

    async def tile_longitude_span(self):
        northeast, southwest = await self._map_region()
        return 256 * (northeast["lng"] - southwest["lng"]) / self.width

    @property
    def pin_count(self):
        # Can't use sync invoke; use the backlog/cached state if available.
        # For test purposes, count pins via the impl's tracking.
        if hasattr(self.impl, "_pins"):
            return len(self.impl._pins)
        return 0

    async def select_pin(self, pin):
        pytest.skip("WinUI3 MapView doesn't support selecting pins")

    async def wait_for_map(self, message, max_delay=0.5):
        initial = await self._map_region()
        previous = initial
        panning = True

        tick_count = 0
        delta = 0.2
        while panning and tick_count < (max_delay / delta):
            await asyncio.sleep(delta)
            current = await self._map_region()

            panning = not region_eq(current, previous)
            if region_eq(current, initial):
                panning = True

            previous = current
            tick_count += 1

        await self.redraw(message)
