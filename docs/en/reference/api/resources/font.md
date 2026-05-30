{{ component_header("Font") }}

## Usage

For most widget styling, you do not need to create instances of the [`Font`][toga.Font] class. Fonts are applied to widgets using style properties:

```python
import toga
from toga.style.pack import pack, SERIF, BOLD

# Create a bold label in the system's serif font at default system size.
my_label = toga.Label("Hello World", font_family=SERIF, font_weight=BOLD)
```

Toga provides a number of [built-in system fonts][toga.style.pack.Pack.font_family]. Font sizes are specified in [CSS points][css-units]; the default size depends on the platform and the widget.

If you want to use a custom font, the font file must be provided as part of your app's resources, and registered before first use:

```python
import toga

# Register the user font with name "Roboto"
toga.Font.register("Roboto", "resources/Roboto-Regular.ttf")

# Create a label with the new font.
my_label = toga.Label("Hello World", font_family="Roboto")
```

When registering a font, if an invalid value is provided for the style, variant or weight, `NORMAL` will be used.

When a font includes multiple weights, styles or variants, each one must be registered separately, even if they're stored in the same file:

```python
import toga
from toga.style.pack import BOLD

# Register a regular and bold font, contained in separate font files
Font.register("Roboto", "resources/Roboto-Regular.ttf")
Font.register("Roboto", "resources/Roboto-Bold.ttf", weight=BOLD)

# Register a single font file that contains both a regular and bold weight
Font.register("Bahnschrift", "resources/Bahnschrift.ttf")
Font.register("Bahnschrift", "resources/Bahnschrift.ttf", weight=BOLD)
```

On some platforms, you can also use fonts that are already installed on the system without registering them. Simply use the font's family name directly:

```python
import toga

# Use a system-installed font by name
my_label = toga.Label("Hello World", font_family="Helvetica Neue")
```

To discover which font families are available on the current system, use [`Font.installed_families()`][toga.Font.installed_families]:

```python
import toga

# Get the set of all installed font family names
families = toga.Font.installed_families()
```

This returns a set of family name strings. It does not include Toga's predefined generic families (system, message, serif, sans-serif, etc.) or user-registered fonts.

A small number of Toga APIs (e.g., [`Canvas.write_text`][toga.Canvas.write_text]) *do* require the use of [`Font`][toga.Font] instance. In these cases, you can instantiate a Font using similar properties to the ones used for widget styling:

```python
import toga
from toga.style.pack import BOLD

# Obtain a 14 point Serif bold font instance
my_font = toga.Font(SERIF, 14, weight=BOLD)

# Use the font to write on a canvas.
canvas = toga.Canvas()
canvas.write_text("Hello", font=my_font)
```

When constructing your own [`Font`][toga.Font] instance, ensure that the font family you provide is valid; otherwise an [`UnknownFontError`][toga.fonts.UnknownFontError] will be raised.

## Notes

- Arbitrary system-installed fonts can be used on macOS, iOS, Windows, and Linux (GTK and Qt). Android, Textual, and Web backends do not yet support this.
- Font enumeration via `Font.installed_families()` is supported on macOS, iOS, Windows, Linux (GTK and Qt). Android, Textual, and Web backends raise `NotImplementedError`.
- iOS and macOS do not support the use of variant font files (that is, fonts that contain the details of multiple weights/variants in a single file). Variant font files can be registered; however, only the "normal" variant will be used.
- Android and Windows do not support the oblique font style. If an oblique font is specified, Toga will attempt to use an italic style of the same font.
- Android and Windows do not support the small caps font variant. If a Small Caps font is specified, Toga will use the normal variant of the same font.
- Android and Windows do not support font width variations (CSS `font-width` / `font-stretch`). If a non-default `font_width` is specified, it will be ignored and the font will be rendered at its normal width.
- Some platforms allow the use of font weights and variants that aren't explicitly provided by altering the rendering of a normal font (e.g., using a thick pen to render a normal font to render a fake bold, or applying a skew to render a fake italic). Toga only guarantees that the font faces, variants and weights that are actually registered will be available for use.

## Reference

::: toga.Font

::: toga.fonts.UnknownFontError
