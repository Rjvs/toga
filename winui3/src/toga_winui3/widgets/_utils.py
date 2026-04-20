def unbounded_size():
    """Return an unbounded Size for WinUI 3 Measure() calls.

    Used by widget rehint() methods to measure intrinsic size without
    width/height constraints.
    """
    from win32more.Windows.Foundation import Size

    size = Size()
    size.Width = float("inf")
    size.Height = float("inf")
    return size


# Hardcoded error red fallback matching the system critical colour.
_ERROR_FALLBACK = (255, 196, 43, 28)


def get_error_brush():
    """Return the theme-aware error brush for input validation borders."""
    return theme_brush("SystemFillColorCriticalBrush", fallback_rgba=_ERROR_FALLBACK)


def theme_brush(key, *, fallback_rgba=None):
    """Look up a WinUI 3 theme brush by resource key.

    Returns the theme-aware brush if found in the current application's
    resource dictionary.  Falls back to a :class:`SolidColorBrush` built
    from *fallback_rgba* ``(A, R, G, B)`` when the key is absent or the
    application is not yet initialised.
    """
    from win32more.Microsoft.UI.Xaml import Application

    try:
        resources = Application.Current.Resources
        if resources.HasKey(key):
            return resources.Lookup(key)
    except Exception:
        # Application may not be initialised yet (e.g. during tests).
        pass

    if fallback_rgba is not None:
        from win32more.Microsoft.UI.Xaml.Media import SolidColorBrush
        from win32more.Windows.UI import Color

        a, r, g, b = fallback_rgba
        return SolidColorBrush(Color(A=a, R=r, G=g, B=b))
    return None
