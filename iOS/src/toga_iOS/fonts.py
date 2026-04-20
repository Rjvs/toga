from pathlib import Path

from fontTools.ttLib import TTFont
from rubicon.objc import ObjCClass, ObjCInstance

from toga.fonts import (
    _IMPL_CACHE,
    _REGISTERED_FONT_CACHE,
    CURSIVE,
    FANTASY,
    ITALIC,
    MESSAGE,
    MONOSPACE,
    OBLIQUE,
    POINTS_PER_PIXEL,
    SANS_SERIF,
    SERIF,
    SYSTEM,
    SYSTEM_DEFAULT_FONT_SIZE,
    UnknownFontError,
)
from toga_iOS.libs import (
    NSURL,
    UIFont,
    UIFontDescriptorTraitBold,
    UIFontDescriptorTraitCondensed,
    UIFontDescriptorTraitExpanded,
    UIFontDescriptorTraitItalic,
)
from toga_iOS.libs.core_text import (
    core_text,
    kCTFontManagerScopeProcess,
    kCTFontVariationAttribute,
)

NSMutableDictionary = ObjCClass("NSMutableDictionary")
NSNumber = ObjCClass("NSNumber")

# CSS font-weight (1-1000) to Apple font weight (~-1.0 to 1.0) mapping.
# Anchor points from Apple's UIFontWeight constants.
_APPLE_WEIGHT_ANCHORS = [
    (1, -1.0),
    (100, -0.80),  # UltraLight
    (200, -0.60),  # Thin
    (300, -0.40),  # Light
    (400, 0.00),  # Regular
    (500, 0.23),  # Medium
    (600, 0.30),  # Semibold
    (700, 0.40),  # Bold
    (800, 0.56),  # Heavy
    (900, 0.62),  # Black
    (1000, 1.00),
]


def _css_weight_to_apple(css_weight):
    """Map CSS font-weight (1-1000) to Apple font weight (~-1.0 to 1.0)
    using piecewise linear interpolation between known anchor points."""
    css_weight = int(css_weight)
    for i in range(1, len(_APPLE_WEIGHT_ANCHORS)):
        css_hi, apple_hi = _APPLE_WEIGHT_ANCHORS[i]
        if css_weight <= css_hi:
            css_lo, apple_lo = _APPLE_WEIGHT_ANCHORS[i - 1]
            t = (css_weight - css_lo) / (css_hi - css_lo)
            return apple_lo + t * (apple_hi - apple_lo)
    return _APPLE_WEIGHT_ANCHORS[-1][1]


def _tag_to_fourcc(tag):
    """Convert a 4-character OpenType tag to its integer FourCharCode."""
    return (ord(tag[0]) << 24) | (ord(tag[1]) << 16) | (ord(tag[2]) << 8) | ord(tag[3])


def _apply_core_text_variations(font, axes):
    """Apply custom OpenType variation axes to a font via CoreText."""
    variation = NSMutableDictionary.alloc().init()
    for tag, value in axes.items():
        key = NSNumber.numberWithInt(_tag_to_fourcc(tag))
        val = NSNumber.numberWithDouble(float(value))
        variation.setObject(val, forKey=key)

    attrs = NSMutableDictionary.alloc().init()
    attrs.setObject(variation, forKey=kCTFontVariationAttribute)

    descriptor = ObjCInstance(core_text.CTFontDescriptorCreateWithAttributes(attrs))
    return ObjCInstance(
        core_text.CTFontCreateCopyWithAttributes(font, 0.0, None, descriptor)
    )


_CUSTOM_FONT_NAMES = {}


class Font:
    def __init__(self, interface):
        self.interface = interface

    def load_predefined_system_font(self):
        """Use one of the system font names Toga predefines."""
        try:
            # Built in fonts have known names; no need to interrogate a file.
            font_name = {
                SYSTEM: SYSTEM,
                MESSAGE: SYSTEM,  # No separate "message" font on iOS
                SERIF: "Times-Roman",
                SANS_SERIF: "Helvetica",
                CURSIVE: "Snell Roundhand",
                FANTASY: "Papyrus",
                MONOSPACE: "Courier New",
            }[self.interface.family]

        except KeyError as exc:
            msg = f"{self.interface} not a predefined system font"
            raise UnknownFontError(msg) from exc

        self._assign_native(font_name)

    def load_user_registered_font(self):
        """Use a font that the user has registered in their code."""
        font_key = self.interface._registered_font_key(
            family=self.interface.family,
            weight=self.interface.weight,
            style=self.interface.style,
            variant=self.interface.variant,
        )
        try:
            font_path = _REGISTERED_FONT_CACHE[font_key]
        except KeyError as exc:
            msg = f"{self.interface} not a user-registered font"
            raise UnknownFontError(msg) from exc

        # Yes, user has registered this font.
        try:
            # A font *file* an only be registered once under iOS, so check if it's
            # already registered.
            font_name = _CUSTOM_FONT_NAMES[font_path]

        except KeyError as exc:
            # Attempt to register the font file.
            if not Path(font_path).is_file():
                msg = f"Font file {font_path} could not be found"
                raise ValueError(msg) from exc

            font_url = NSURL.fileURLWithPath(font_path)
            success = core_text.CTFontManagerRegisterFontsForURL(
                font_url, kCTFontManagerScopeProcess, None
            )
            if not success:
                msg = f"Unable to load font file {font_path}"
                raise ValueError(msg) from exc

            ttfont = TTFont(font_path)
            # Preserve the Postscript font name contained in the
            # font file.
            font_name = ttfont["name"].getBestFullName()
            _CUSTOM_FONT_NAMES[font_path] = font_name

        self._assign_native(font_name)

    def load_arbitrary_system_font(self):
        """Use a font available on the system."""
        self._assign_native(self.interface.family)
        # Fonts *can* fail safe - creating a font object where the family doesn't match
        # the requested name. If a font wasn't loaded, or the loaded font name doesn't
        # match the font request, assume the font wasn't found.
        if self.native is None or self.native.fontName != self.interface.family:
            # If it wasn't a match, purge the font cache of the loaded font
            self.native = None
            del _IMPL_CACHE[self.interface]
            raise UnknownFontError(f"Unknown system font: {self.interface.family}")

    def _assign_native(self, font_name):
        if self.interface.size == SYSTEM_DEFAULT_FONT_SIZE:
            size = UIFont.labelFontSize
        else:
            # A "point" in Apple APIs is equivalent to a CSS pixel, but the Toga
            # public API works in CSS points, which are slightly larger
            # (https://developer.apple.com/library/archive/documentation/GraphicsAnimation/Conceptual/HighResolutionOSX/Explained/Explained.html).
            size = self.interface.size * POINTS_PER_PIXEL

        # Construct the UIFont with the best weight support available.
        # System font supports fine-grained numeric weight via systemFontOfSize:weight:.
        if font_name == SYSTEM:
            apple_weight = _css_weight_to_apple(self.interface.weight)
            font = UIFont.systemFontOfSize(size, weight=apple_weight)
            has_numeric_weight = True
        else:
            font = UIFont.fontWithName(font_name, size=size)
            has_numeric_weight = False

        # Apply weight and style traits.
        traits = 0
        # Only use Bold trait when numeric weight wasn't already applied
        if not has_numeric_weight and self.interface.weight >= 600:
            traits |= UIFontDescriptorTraitBold
        if self.interface.style in {ITALIC, OBLIQUE}:
            traits |= UIFontDescriptorTraitItalic

        if traits:
            # If there is no font with the requested traits, this returns None.
            descriptor = font.fontDescriptor.fontDescriptorWithSymbolicTraits(traits)
            if descriptor is not None:
                font_with_traits = UIFont.fontWithDescriptor(descriptor, size=size)
                font = font_with_traits or font

        # Apply width traits separately to avoid all-or-nothing trait failure.
        width = float(self.interface.width)
        width_trait = 0
        if width < 100:
            width_trait = UIFontDescriptorTraitCondensed
        elif width > 100:
            width_trait = UIFontDescriptorTraitExpanded

        if width_trait:
            # Combine with existing symbolic traits to preserve weight/style
            current_traits = font.fontDescriptor.symbolicTraits
            descriptor = font.fontDescriptor.fontDescriptorWithSymbolicTraits(
                current_traits | width_trait
            )
            if descriptor is not None:
                font_with_width = UIFont.fontWithDescriptor(descriptor, size=size)
                font = font_with_width or font

        # Apply custom OpenType variation axes via CoreText
        if self.interface.axes:
            font = _apply_core_text_variations(font, self.interface.axes)

        self.native = font
        _IMPL_CACHE[self.interface] = self
