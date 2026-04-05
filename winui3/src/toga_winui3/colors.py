from win32more.Windows.UI import Color

from toga.colors import rgb

CACHE = {}


def native_color(c):
    try:
        return CACHE[c]
    except KeyError:
        color = Color()
        color.A = int(c.rgb.a * 255)
        color.R = int(c.rgb.r)
        color.G = int(c.rgb.g)
        color.B = int(c.rgb.b)
        CACHE[c] = color
        return color


def native_brush(c):
    from win32more.Microsoft.UI.Xaml.Media import SolidColorBrush

    return SolidColorBrush(native_color(c))


def toga_color(c):
    return rgb(c.R, c.G, c.B, c.A / 255)
