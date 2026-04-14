from io import BytesIO
from math import cos, sin

from PIL import Image as PILImage
from win32more.Microsoft.Graphics.Canvas import (
    CanvasAntialiasing,
    CanvasRenderTarget,
)
from win32more.Microsoft.Graphics.Canvas.Brushes import CanvasSolidColorBrush
from win32more.Microsoft.Graphics.Canvas.Geometry import (
    CanvasFigureLoop,
    CanvasFilledRegionDetermination,
    CanvasGeometry,
    CanvasPathBuilder,
    CanvasStrokeStyle,
)
from win32more.Microsoft.Graphics.Canvas.Text import (
    CanvasTextFormat,
    CanvasTextLayout,
)
from win32more.Microsoft.Graphics.Canvas.UI.Xaml import CanvasControl
from win32more.Windows.Foundation.Numerics import Matrix3x2, Vector2
from win32more.Windows.UI import Color

from toga.colors import TRANSPARENT, rgb
from toga.constants import Baseline, FillRule
from toga.handlers import WeakrefCallable
from toga.widgets.canvas.geometry import arc_to_bezier, round_rect, sweepangle
from toga_winui3.colors import native_color

from .base import Widget

BLACK = native_color(rgb(0, 0, 0))


######################################################################
# Pure-Python 3x2 affine transform matrix
######################################################################


class TransformMatrix:
    """A 3x2 affine transform matrix with math operations.

    Layout::

        | m11  m12 |
        | m21  m22 |
        | m31  m32 |   (m31, m32) = translation

    Points are transformed as:
        x' = x*m11 + y*m21 + m31
        y' = x*m12 + y*m22 + m32
    """

    __slots__ = ("m11", "m12", "m21", "m22", "m31", "m32")

    def __init__(self, m11=1.0, m12=0.0, m21=0.0, m22=1.0, m31=0.0, m32=0.0):
        self.m11 = m11
        self.m12 = m12
        self.m21 = m21
        self.m22 = m22
        self.m31 = m31
        self.m32 = m32

    @classmethod
    def identity(cls):
        return cls()

    @classmethod
    def rotation(cls, radians):
        c, s = cos(radians), sin(radians)
        return cls(c, s, -s, c, 0.0, 0.0)

    @classmethod
    def scaling(cls, sx, sy):
        return cls(sx, 0.0, 0.0, sy, 0.0, 0.0)

    @classmethod
    def translation(cls, tx, ty):
        return cls(1.0, 0.0, 0.0, 1.0, tx, ty)

    def multiply(self, other):
        """Return self @ other (self applied first, then other)."""
        return TransformMatrix(
            self.m11 * other.m11 + self.m12 * other.m21,
            self.m11 * other.m12 + self.m12 * other.m22,
            self.m21 * other.m11 + self.m22 * other.m21,
            self.m21 * other.m12 + self.m22 * other.m22,
            self.m31 * other.m11 + self.m32 * other.m21 + other.m31,
            self.m31 * other.m12 + self.m32 * other.m22 + other.m32,
        )

    def invert(self):
        """Return the inverse matrix. Raises ValueError if singular."""
        det = self.m11 * self.m22 - self.m12 * self.m21
        if abs(det) < 1e-15:
            raise ValueError("Matrix is not invertible")
        inv_det = 1.0 / det
        return TransformMatrix(
            self.m22 * inv_det,
            -self.m12 * inv_det,
            -self.m21 * inv_det,
            self.m11 * inv_det,
            (self.m21 * self.m32 - self.m22 * self.m31) * inv_det,
            (self.m12 * self.m31 - self.m11 * self.m32) * inv_det,
        )

    def transform_point(self, x, y):
        return (
            x * self.m11 + y * self.m21 + self.m31,
            x * self.m12 + y * self.m22 + self.m32,
        )

    def to_native(self):
        m = Matrix3x2()
        m.M11 = self.m11
        m.M12 = self.m12
        m.M21 = self.m21
        m.M22 = self.m22
        m.M31 = self.m31
        m.M32 = self.m32
        return m

    @classmethod
    def from_native(cls, m):
        return cls(m.M11, m.M12, m.M21, m.M22, m.M31, m.M32)

    def copy(self):
        return TransformMatrix(
            self.m11, self.m12, self.m21, self.m22, self.m31, self.m32
        )


######################################################################
# State: drawing style container
######################################################################


class State:
    """Drawing state that can be saved and restored.

    Stores raw color/style values rather than native brush/pen objects, because
    Win2D brushes require a resource creator (the drawing session) at creation
    time and cannot be pre-created or cloned.
    """

    def __init__(
        self,
        previous_state,
        fill_color,
        stroke_color,
        line_width,
        line_dash=None,
        singular=False,
    ):
        self.previous_state = previous_state
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.line_width = line_width
        self.line_dash = line_dash
        self.singular = singular
        self.transform = TransformMatrix.identity()

    @classmethod
    def for_impl(cls, impl):
        return cls(
            previous_state=None,
            fill_color=BLACK,
            stroke_color=BLACK,
            line_width=2.0,
        )

    def new_state(self, previous_state):
        new = type(self)(
            previous_state=previous_state,
            fill_color=self.fill_color,
            stroke_color=self.stroke_color,
            line_width=self.line_width,
            line_dash=list(self.line_dash) if self.line_dash else None,
            singular=self.singular,
        )
        return new


######################################################################
# Context: drawing session wrapper
######################################################################

# Segment types stored in subpath lists
_LINE = 0
_BEZIER = 1
_CLOSE = 2


class Context:
    def __init__(self, impl, native):
        self.native = native
        self.native.Antialiasing = CanvasAntialiasing.Antialiased
        self.impl = impl
        self.states = [State.for_impl(self.impl)]
        self.begin_path()

        # Backwards compatibility for Toga <= 0.5.3
        self.in_fill = False
        self.in_stroke = False

    # ── State management ─────────────────────────────────────────────

    @property
    def state(self):
        return self.states[-1]

    def save(self):
        saved_transform = TransformMatrix.from_native(self.native.Transform)
        self.states.append(self.state.new_state(saved_transform))

    def restore(self):
        if len(self.states) <= 1:
            # Nothing to restore — the bottom state has no previous_state.
            return
        popped = self.states.pop()
        self.native.Transform = popped.previous_state.to_native()
        self._transform_paths(popped.transform)

    # ── Style setters ────────────────────────────────────────────────

    def set_fill_style(self, color):
        self.state.fill_color = native_color(color)

    def set_stroke_style(self, color):
        self.state.stroke_color = native_color(color)

    def set_line_width(self, line_width):
        self.state.line_width = line_width

    def set_line_dash(self, line_dash):
        self.state.line_dash = line_dash

    # ── Path management ──────────────────────────────────────────────
    #
    # We accumulate path segments as Python tuples and build CanvasGeometry
    # on demand at fill/stroke time. Each subpath has a start point and a
    # list of segments. We track start points in a parallel list so that
    # _build_geometry can reconstruct the geometry from all subpaths.

    def begin_path(self):
        self._subpaths = [[]]
        self._subpath_starts = [None]
        self._current_point = None

    @property
    def _current_subpath(self):
        return self._subpaths[-1]

    def _ensure_subpath(self, default_x, default_y):
        """Ensure there is a subpath with a start point (HTML spec rule)."""
        if self._subpath_starts[-1] is None:
            self._subpath_starts[-1] = (default_x, default_y)
            self._current_point = (default_x, default_y)

    def _new_subpath(self, start=None):
        """Start a new subpath with the given start point."""
        self._subpaths.append([])
        self._subpath_starts.append(start)
        if start is not None:
            self._current_point = start

    def move_to(self, x, y):
        self._new_subpath((x, y))

    def close_path(self):
        start = self._subpath_starts[-1]
        if start is not None and self._current_subpath:
            sx, sy = start
            # Don't add an explicit _LINE to start — EndFigure(Closed) in
            # _build_geometry handles the closing segment automatically.
            # Adding both causes a redundant zero-length segment that
            # disrupts dash-pattern rendering.
            self._current_subpath.append((_CLOSE,))
            # Start a new subpath at the start of the closed one
            self._new_subpath((sx, sy))

    def line_to(self, x, y):
        self._ensure_subpath(x, y)
        self._current_subpath.append((_LINE, x, y))
        self._current_point = (x, y)

    def bezier_curve_to(self, cp1x, cp1y, cp2x, cp2y, x, y):
        self._ensure_subpath(cp1x, cp1y)
        self._current_subpath.append((_BEZIER, cp1x, cp1y, cp2x, cp2y, x, y))
        self._current_point = (x, y)

    def quadratic_curve_to(self, cpx, cpy, x, y):
        self._ensure_subpath(cpx, cpy)
        lx, ly = self._current_point
        # Convert quadratic to cubic bezier (same formula as WinForms)
        self._current_subpath.append(
            (
                _BEZIER,
                lx + 2 / 3 * (cpx - lx),
                ly + 2 / 3 * (cpy - ly),
                x + 2 / 3 * (cpx - x),
                y + 2 / 3 * (cpy - y),
                x,
                y,
            )
        )
        self._current_point = (x, y)

    def arc(self, x, y, radius, startangle, endangle, counterclockwise):
        self.ellipse(x, y, radius, radius, 0, startangle, endangle, counterclockwise)

    def ellipse(
        self, x, y, radiusx, radiusy, rotation, startangle, endangle, counterclockwise
    ):
        # Build the transform: translate(x, y) @ rotate(rotation) @
        # scale(radiusx, radiusy) @ rotate(startangle)
        matrix = (
            TransformMatrix.translation(x, y)
            .multiply(TransformMatrix.rotation(rotation))
            .multiply(TransformMatrix.scaling(radiusx, radiusy))
            .multiply(TransformMatrix.rotation(startangle))
        )

        bezier_points = arc_to_bezier(
            sweepangle(startangle, endangle, counterclockwise)
        )

        # Transform all bezier points
        transformed = [matrix.transform_point(bx, by) for bx, by in bezier_points]

        # Ensure subpath exists
        if self._subpath_starts[-1] is None:
            self._subpath_starts[-1] = transformed[0]
            self._current_point = transformed[0]
        elif not self._current_subpath and self._current_point:
            # Subpath has a start (from move_to) but no segments yet — the
            # start was set by move_to. We keep it as is; CanvasPathBuilder
            # will draw from BeginFigure(start) and add segments.
            pass

        # Add bezier segments (points come in groups of 3 after the start point)
        for i in range(1, len(transformed), 3):
            cp1 = transformed[i]
            cp2 = transformed[i + 1]
            end = transformed[i + 2]
            self._current_subpath.append(
                (
                    _BEZIER,
                    cp1[0],
                    cp1[1],
                    cp2[0],
                    cp2[1],
                    end[0],
                    end[1],
                )
            )

        self._current_point = transformed[-1]

    def rect(self, x, y, width, height):
        self._new_subpath((x, y))
        self._current_subpath.append((_LINE, x + width, y))
        self._current_subpath.append((_LINE, x + width, y + height))
        self._current_subpath.append((_LINE, x, y + height))
        self._current_subpath.append((_CLOSE,))
        self._new_subpath()
        self._current_point = None

    def round_rect(self, x, y, width, height, radii):
        round_rect(self, x, y, width, height, radii)

    # ── Geometry building ────────────────────────────────────────────

    def _build_geometry(self, fill_rule=None):
        """Build a CanvasGeometry from accumulated subpath segments."""
        builder = CanvasPathBuilder(self.native)
        if fill_rule is not None:
            if fill_rule == FillRule.EVENODD:
                builder.SetFilledRegionDetermination(
                    CanvasFilledRegionDetermination.Alternate
                )
            else:
                builder.SetFilledRegionDetermination(
                    CanvasFilledRegionDetermination.Winding
                )

        for idx, subpath in enumerate(self._subpaths):
            if not subpath:
                continue

            start = (
                self._subpath_starts[idx] if idx < len(self._subpath_starts) else None
            )
            if start is None:
                continue

            is_closed = any(seg[0] == _CLOSE for seg in subpath)
            builder.BeginFigure(Vector2(X=start[0], Y=start[1]))

            for seg in subpath:
                if seg[0] == _LINE:
                    builder.AddLine(Vector2(X=seg[1], Y=seg[2]))
                elif seg[0] == _BEZIER:
                    builder.AddCubicBezier(
                        Vector2(X=seg[1], Y=seg[2]),
                        Vector2(X=seg[3], Y=seg[4]),
                        Vector2(X=seg[5], Y=seg[6]),
                    )
                # _CLOSE is handled by EndFigure

            builder.EndFigure(
                CanvasFigureLoop.Closed if is_closed else CanvasFigureLoop.Open
            )

        return CanvasGeometry.CreatePath(builder)

    # ── Fill and stroke ──────────────────────────────────────────────

    def fill(self, fill_rule):
        if self.state.singular:
            return
        geometry = self._build_geometry(fill_rule)
        brush = CanvasSolidColorBrush(self.native, self.state.fill_color)
        self.native.FillGeometry(geometry, brush)

    def stroke(self):
        if self.state.singular:
            return
        geometry = self._build_geometry()
        brush = CanvasSolidColorBrush(self.native, self.state.stroke_color)
        if self.state.line_dash:
            lw = self.state.line_width
            if lw == 0:
                return
            style = CanvasStrokeStyle()
            style.CustomDashStyle = [d / lw for d in self.state.line_dash]
            self.native.DrawGeometry(geometry, brush, lw, style)
        else:
            self.native.DrawGeometry(geometry, brush, self.state.line_width)

    # ── Transforms ───────────────────────────────────────────────────

    def rotate(self, radians):
        # Apply to native transform
        rot = TransformMatrix.rotation(radians)
        current = TransformMatrix.from_native(self.native.Transform)
        self.native.Transform = current.multiply(rot).to_native()

        # Update state cumulative transform
        self.state.transform = self.state.transform.multiply(rot)

        # Apply inverse to paths so they stay in place visually
        self._transform_paths(rot.invert())

    def scale(self, sx, sy):
        if sx == 0:
            sx = 2**-24
            self.state.singular = True
        if sy == 0:
            sy = 2**-24
            self.state.singular = True

        sc = TransformMatrix.scaling(sx, sy)
        current = TransformMatrix.from_native(self.native.Transform)
        self.native.Transform = current.multiply(sc).to_native()

        self.state.transform = self.state.transform.multiply(sc)
        self._transform_paths(TransformMatrix.scaling(1 / sx, 1 / sy))

    def translate(self, tx, ty):
        tr = TransformMatrix.translation(tx, ty)
        current = TransformMatrix.from_native(self.native.Transform)
        self.native.Transform = current.multiply(tr).to_native()

        self.state.transform = self.state.transform.multiply(tr)
        self._transform_paths(TransformMatrix.translation(-tx, -ty))

    def reset_transform(self):
        old_transform = TransformMatrix.from_native(self.native.Transform)
        # Reset native to identity
        self.native.Transform = TransformMatrix.identity().to_native()

        # Forward-transform paths by the old matrix (undo previous inverse)
        self._transform_paths(old_transform)

        # Update state transform
        inverse = old_transform.invert()
        self.state.transform = self.state.transform.multiply(inverse)

        self.state.singular = False
        # No DPI scaling needed in WinUI 3

    def _transform_paths(self, matrix):
        """Apply a transform matrix to all path segment coordinates."""
        for subpath in self._subpaths:
            for i, seg in enumerate(subpath):
                if seg[0] == _LINE:
                    nx, ny = matrix.transform_point(seg[1], seg[2])
                    subpath[i] = (_LINE, nx, ny)
                elif seg[0] == _BEZIER:
                    cp1x, cp1y = matrix.transform_point(seg[1], seg[2])
                    cp2x, cp2y = matrix.transform_point(seg[3], seg[4])
                    ex, ey = matrix.transform_point(seg[5], seg[6])
                    subpath[i] = (_BEZIER, cp1x, cp1y, cp2x, cp2y, ex, ey)

        # Transform tracked points
        if self._current_point is not None:
            self._current_point = matrix.transform_point(*self._current_point)
        for i, sp in enumerate(self._subpath_starts):
            if sp is not None:
                self._subpath_starts[i] = matrix.transform_point(*sp)

    # ── Text ─────────────────────────────────────────────────────────

    def write_text(self, text, x, y, font, baseline, line_height):
        # Text should not affect current paths, so save them
        saved_subpaths = self._subpaths
        saved_current_point = self._current_point
        saved_subpath_starts = self._subpath_starts

        self._text_draw(text, x, y, font, baseline, line_height)

        # Restore paths
        self._subpaths = saved_subpaths
        self._current_point = saved_current_point
        self._subpath_starts = saved_subpath_starts

    def _text_draw(self, text, x, y, font, baseline, line_height):
        lines = text.split("\n")
        scaled_line_height = self.impl._line_height(font, line_height)
        total_height = scaled_line_height * len(lines)

        if baseline == Baseline.TOP:
            top = y
        elif baseline == Baseline.MIDDLE:
            top = y - (total_height / 2)
        elif baseline == Baseline.BOTTOM:
            top = y - total_height
        else:
            # Default to Baseline.ALPHABETIC
            top = y - font.metric("CellAscent")

        text_format = self._make_text_format(font)

        for line_num, line in enumerate(lines):
            line_y = top + (scaled_line_height * line_num)
            layout = CanvasTextLayout(
                self.native, line, text_format, float("inf"), float("inf")
            )
            text_geom = CanvasGeometry.CreateText(layout)

            # Translate to the target position
            text_geom = text_geom.Transform(
                TransformMatrix.translation(x, line_y).to_native()
            )

            if self.in_fill:
                brush = CanvasSolidColorBrush(self.native, self.state.fill_color)
                self.native.FillGeometry(text_geom, brush)
            if self.in_stroke:
                brush = CanvasSolidColorBrush(self.native, self.state.stroke_color)
                self.native.DrawGeometry(text_geom, brush, self.state.line_width)

    def _make_text_format(self, font):
        fmt = CanvasTextFormat()
        fmt.FontFamily = font.native_family.Source
        fmt.FontSize = font.native_size
        fmt.FontWeight = font.native_weight
        fmt.FontStyle = font.native_style
        return fmt

    # ── Images ───────────────────────────────────────────────────────

    def draw_image(self, image, x, y, width, height):
        from win32more.Windows.Foundation import Rect

        bitmap = self.impl._get_canvas_bitmap(self.native, image)
        if bitmap is not None:
            dest = Rect()
            dest.X = x
            dest.Y = y
            dest.Width = width
            dest.Height = height
            self.native.DrawImageToRect(bitmap, dest)


######################################################################
# Canvas widget
######################################################################


class Canvas(Widget):
    native: CanvasControl

    def create(self):
        self.native = CanvasControl()
        self._default_background_color = TRANSPARENT
        self.dragging = False
        self._bitmap_cache = {}

        self.native.add_Draw(WeakrefCallable(self.winui3_draw))
        self.native.add_SizeChanged(WeakrefCallable(self.winui3_size_changed))
        self.native.add_PointerPressed(WeakrefCallable(self.winui3_pointer_pressed))
        self.native.add_PointerMoved(WeakrefCallable(self.winui3_pointer_moved))
        self.native.add_PointerReleased(WeakrefCallable(self.winui3_pointer_released))
        self.native.add_Tapped(WeakrefCallable(self.winui3_tapped))
        self.native.add_RightTapped(WeakrefCallable(self.winui3_right_tapped))
        self.native.add_DoubleTapped(WeakrefCallable(self.winui3_double_tapped))

    # ── Drawing ──────────────────────────────────────────────────────

    def winui3_draw(self, sender, args):
        context = Context(self, args.DrawingSession)
        self.interface.root_state._draw(context)

    def redraw(self):
        self.native.Invalidate()

    # ── Resize ───────────────────────────────────────────────────────

    def winui3_size_changed(self, sender, args):
        self.interface.on_resize(
            width=self.native.ActualWidth,
            height=self.native.ActualHeight,
        )

    # ── Pointer events ───────────────────────────────────────────────

    def winui3_pointer_pressed(self, sender, args):
        point = args.GetCurrentPoint(self.native)
        if (
            point.Properties.IsLeftButtonPressed
            or point.Properties.IsRightButtonPressed
        ):
            self.dragging = True
        self.native.CapturePointer(args.Pointer)

    def winui3_tapped(self, sender, args):
        # Tapped only fires on single taps (not the second click of a
        # double-tap), matching WinForms' Clicks==1 guard for on_press.
        pos = args.GetPosition(self.native)
        self.interface.on_press(pos.X, pos.Y)

    def winui3_right_tapped(self, sender, args):
        pos = args.GetPosition(self.native)
        self.interface.on_alt_press(pos.X, pos.Y)

    def winui3_pointer_moved(self, sender, args):
        if not self.dragging:
            return
        point = args.GetCurrentPoint(self.native)
        x, y = point.Position.X, point.Position.Y
        if point.Properties.IsLeftButtonPressed:
            self.interface.on_drag(x, y)
        elif point.Properties.IsRightButtonPressed:
            self.interface.on_alt_drag(x, y)

    def winui3_pointer_released(self, sender, args):
        self.dragging = False
        point = args.GetCurrentPoint(self.native)
        x, y = point.Position.X, point.Position.Y
        # IsRightButtonPressed is False on release of right button, so we check
        # which button was released by checking if left was still pressed.
        if point.Properties.IsLeftButtonPressed:
            # Right button released while left still held
            self.interface.on_alt_release(x, y)
        elif point.Properties.IsRightButtonPressed:
            # Left button released while right still held
            self.interface.on_release(x, y)
        else:
            # Both released — check the pointer update kind or use a heuristic.
            # PointerReleased fires for each button separately. We track which
            # button was involved via PointerUpdateKind.
            kind = point.Properties.PointerUpdateKind
            # PointerUpdateKind: LeftButtonReleased=2, RightButtonReleased=5
            if kind == 5:
                self.interface.on_alt_release(x, y)
            else:
                self.interface.on_release(x, y)
        self.native.ReleasePointerCapture(args.Pointer)

    def winui3_double_tapped(self, sender, args):
        pos = args.GetPosition(self.native)
        self.interface.on_activate(pos.X, pos.Y)

    # ── Handler stubs (core widget stores handlers) ──────────────────

    def set_on_resize(self, handler):
        pass

    def set_on_press(self, handler):
        pass

    def set_on_release(self, handler):
        pass

    def set_on_drag(self, handler):
        pass

    def set_on_alt_press(self, handler):
        pass

    def set_on_alt_release(self, handler):
        pass

    def set_on_alt_drag(self, handler):
        pass

    # ── Text measurement ─────────────────────────────────────────────

    def _line_height(self, font, line_height):
        if line_height is None:
            return font.metric("LineSpacing")
        else:
            # WinUI 3 font sizes are in DIPs (CSS pixels), no conversion needed
            return font.native_size * line_height

    def measure_text(self, text, font, line_height):
        fmt = CanvasTextFormat()
        fmt.FontFamily = font.native_family.Source
        fmt.FontSize = font.native_size
        fmt.FontWeight = font.native_weight
        fmt.FontStyle = font.native_style

        lines = text.split("\n")
        # A trailing newline produces an extra empty line visually,
        # but we don't measure width for it.
        widths = []
        for line in lines:
            layout = CanvasTextLayout(
                self.native, line, fmt, float("inf"), float("inf")
            )
            bounds = layout.LayoutBoundsIncludingTrailingWhitespace
            widths.append(bounds.Width)

        num_lines = len(lines)
        return (
            max(widths) if widths else 0,
            self._line_height(font, line_height) * num_lines,
        )

    # ── Image data export ────────────────────────────────────────────

    def get_image_data(self):
        # Use the window's DPI scale so HiDPI displays produce full-resolution
        # images (matching the WinForms backend which captures at physical
        # pixel resolution).
        window = self.interface.window
        if window and window._impl:
            scale = window._impl._dpi_scale()
        else:
            scale = 1.0
        dpi = 96 * scale

        dip_width = max(1, int(self.native.ActualWidth))
        dip_height = max(1, int(self.native.ActualHeight))
        px_width = max(1, int(dip_width * scale))
        px_height = max(1, int(dip_height * scale))

        # Render to an offscreen CanvasRenderTarget; pass DIPs so Win2D scales
        # internally by dpi/96 to produce the correct physical pixel buffer.
        render_target = CanvasRenderTarget(self.native, dip_width, dip_height, dpi)
        ds = render_target.CreateDrawingSession()

        # Clear with background color
        bg = self.interface.style.background_color
        if bg and bg != TRANSPARENT:
            ds.Clear(native_color(bg))
        else:
            ds.Clear(Color(A=0, R=0, G=0, B=0))

        # Redraw canvas content into the offscreen target
        context = Context(self, ds)
        self.interface.root_state._draw(context)

        ds.Close()

        # Extract pixel bytes and encode to PNG using Pillow
        pixel_bytes = bytes(render_target.GetPixelBytes())
        img = PILImage.frombytes("RGBA", (px_width, px_height), pixel_bytes, "raw", "BGRA")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    # ── Background color ─────────────────────────────────────────────

    def set_background_color(self, color):
        if color is None or color == TRANSPARENT:
            self.native.ClearColor = Color(A=0, R=0, G=0, B=0)
        else:
            self.native.ClearColor = native_color(color)

    # ── Image cache for draw_image ───────────────────────────────────

    def _get_canvas_bitmap(self, resource_creator, image):
        """Get or create a CanvasBitmap for the given toga Image.

        Uses .GetResults() to synchronously complete WinRT async operations.
        """
        from win32more.Microsoft.Graphics.Canvas import CanvasBitmap
        from win32more.Windows.Storage.Streams import (
            DataWriter,
            InMemoryRandomAccessStream,
        )

        if image in self._bitmap_cache:
            return self._bitmap_cache[image]

        data = image._impl.get_data()
        if not data:
            return None

        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream)
        writer.WriteBytes(data)
        writer.StoreAsync().GetResults()
        writer.FlushAsync().GetResults()
        stream.Seek(0)

        bitmap = CanvasBitmap.LoadAsync(resource_creator, stream).GetResults()
        self._bitmap_cache[image] = bitmap
        return bitmap

    # ── Layout ───────────────────────────────────────────────────────

    def rehint(self):
        pass
