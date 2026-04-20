from win32more.Microsoft.UI.Xaml import TextAlignment, VerticalAlignment
from win32more.Microsoft.UI.Xaml.Media import SolidColorBrush

from toga.colors import rgb
from toga.style.pack import BOTTOM, CENTER, JUSTIFY, LEFT, RIGHT, TOP


def toga_color(color):
    """Convert a WinUI 3 Color or SolidColorBrush to a toga color."""
    if color is None:
        return None
    if isinstance(color, SolidColorBrush):
        color = color.Color
    return rgb(color.R, color.G, color.B, color.A / 255)


def toga_x_text_align(alignment):
    return {
        TextAlignment.Left: LEFT,
        TextAlignment.Center: CENTER,
        TextAlignment.Right: RIGHT,
        TextAlignment.Justify: JUSTIFY,
        TextAlignment.DetectFromContent: LEFT,
    }[alignment]


def toga_y_text_align(alignment):
    return {
        VerticalAlignment.Top: TOP,
        VerticalAlignment.Center: CENTER,
        VerticalAlignment.Bottom: BOTTOM,
        VerticalAlignment.Stretch: TOP,
    }[alignment]
