from .constants import (
    BOLD,
    CONDENSED,
    EXPANDED,
    FONT_STYLES,
    FONT_VARIANTS,
    ITALIC,
    NORMAL,
    OBLIQUE,
    SMALL_CAPS,
    STANDARD_AXES,
    SYSTEM_DEFAULT_FONT_SIZE,
    WEIGHT_KEYWORDS,
    WIDTH_KEYWORDS,
)


class FontWeight(int):
    """An int subclass for font weight that compares equal to CSS keyword strings.

    This enables backward compatibility: ``FontWeight(700) == BOLD`` is True,
    and ``FontWeight(400) == NORMAL`` is True, where BOLD="bold" and NORMAL="normal".
    """

    def __new__(cls, value):
        if isinstance(value, str):
            numeric = WEIGHT_KEYWORDS.get(value)
            if numeric is None:
                raise ValueError(
                    f"Invalid font weight keyword {value!r}; "
                    f"valid keywords are: {', '.join(sorted(WEIGHT_KEYWORDS))}"
                )
            return int.__new__(cls, numeric)

        numeric = int.__new__(cls, value)
        if not (1 <= numeric <= 1000):
            raise ValueError(f"Font weight must be between 1 and 1000, got {value!r}")
        return numeric

    def __eq__(self, other):
        if isinstance(other, str):
            return int(self) == WEIGHT_KEYWORDS.get(other, -1)
        return int.__eq__(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return int.__hash__(self)

    def __str__(self):
        # Reverse-map to keyword if it matches one of the standard values
        for keyword, value in WEIGHT_KEYWORDS.items():
            if int(self) == value:
                return keyword
        return str(int(self))

    def __repr__(self):
        return f"FontWeight({int(self)})"


class FontWidth(float):
    """A float subclass for font width (percentage) that compares equal to CSS keywords.

    CSS ``font-width`` (formerly ``font-stretch``) maps to the OpenType ``wdth`` axis.
    Values are percentages: ``100`` is normal, ``75`` is condensed, ``125`` is expanded.
    """

    def __new__(cls, value):
        if isinstance(value, str):
            numeric = WIDTH_KEYWORDS.get(value)
            if numeric is None:
                raise ValueError(
                    f"Invalid font width keyword {value!r}; "
                    f"valid keywords are: {', '.join(sorted(WIDTH_KEYWORDS))}"
                )
            return float.__new__(cls, numeric)

        numeric = float.__new__(cls, value)
        if not (0 < numeric <= 1000):
            raise ValueError(f"Font width must be a positive percentage, got {value!r}")
        return numeric

    def __eq__(self, other):
        if isinstance(other, str):
            return float(self) == WIDTH_KEYWORDS.get(other, -1)
        return float.__eq__(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return float.__hash__(self)

    def __str__(self):
        # Reverse-map to keyword if it matches one of the standard values
        for keyword, value in WIDTH_KEYWORDS.items():
            if float(self) == value:
                return keyword
        # Format without trailing zeros: 87.5 → "87.5%", 100.0 → "100%"
        return f"{float(self):g}%"

    def __repr__(self):
        return f"FontWidth({float(self):g})"


def _normalize_axes(axes):
    """Validate and normalize a custom axes dict to a hashable form."""
    if axes is None:
        return None

    for tag in axes:
        if not isinstance(tag, str) or len(tag) != 4:
            raise ValueError(f"Axis tag {tag!r} must be a 4-character string")
        if tag in STANDARD_AXES:
            raise ValueError(
                f"Standard axis {tag!r} cannot be set via axes dict; "
                f"use the corresponding named parameter instead"
            )

    # Return as a regular dict; frozen form is used only for hashing
    return dict(axes)


class Font:
    def __init__(
        self,
        family,
        size,
        style=NORMAL,
        variant=NORMAL,
        weight=NORMAL,
        width=NORMAL,
        axes=None,
    ):
        if (family[0] == "'" and family[-1] == "'") or (
            family[0] == '"' and family[-1] == '"'
        ):
            self.family = family[1:-1]
        else:
            self.family = family

        try:
            self.size = int(size)
        except ValueError:
            try:
                if size.strip().endswith("pt"):
                    self.size = int(size[:-2])
                else:
                    raise ValueError(f"Invalid font size {size!r}")
            except Exception as exc:
                raise ValueError(f"Invalid font size {size!r}") from exc

        self.style = style if style in FONT_STYLES else NORMAL
        self.variant = variant if variant in FONT_VARIANTS else NORMAL

        # Normalize weight to FontWeight (accepts str keywords or int 1-1000)
        try:
            self.weight = FontWeight(weight)
        except (ValueError, TypeError):
            self.weight = FontWeight(NORMAL)

        # Normalize width to FontWidth (accepts str keywords or numeric percentage)
        try:
            self.width = FontWidth(width)
        except (ValueError, TypeError):
            self.width = FontWidth(NORMAL)

        # Validate and store custom axes
        self.axes = _normalize_axes(axes)

    def _axes_hash(self):
        if self.axes is None:
            return None
        return tuple(sorted(self.axes.items()))

    def __hash__(self):
        return hash(
            (
                "FONT",
                self.family,
                self.size,
                self.style,
                self.variant,
                self.weight,
                self.width,
                self._axes_hash(),
            )
        )

    def __repr__(self):
        parts = []
        if self.style != NORMAL:
            parts.append(self.style)
        if self.variant != NORMAL:
            parts.append(self.variant)
        if self.weight != FontWeight(NORMAL):
            parts.append(str(int(self.weight)))
        if self.width != FontWidth(NORMAL):
            parts.append(str(self.width))
        if self.axes:
            axes_str = " ".join(f"{k}={v}" for k, v in sorted(self.axes.items()))
            parts.append(axes_str)

        prefix = " ".join(parts)
        if prefix:
            prefix += " "

        size_str = (
            "system default size"
            if self.size == SYSTEM_DEFAULT_FONT_SIZE
            else f"{self.size}pt"
        )
        return f"<Font: {prefix}{size_str} {self.family}>"

    def __eq__(self, other):
        try:
            return (
                self.family == other.family
                and self.size == other.size
                and self.style == other.style
                and self.variant == other.variant
                and self.weight == other.weight
                and self.width == other.width
                and self.axes == other.axes
            )
        except AttributeError:
            return False

    def normal_style(self):
        "Generate a normal style version of this font"
        return Font(
            self.family,
            self.size,
            style=NORMAL,
            variant=self.variant,
            weight=self.weight,
            width=self.width,
            axes=self.axes,
        )

    def italic(self):
        "Generate an italic version of this font"
        return Font(
            self.family,
            self.size,
            style=ITALIC,
            variant=self.variant,
            weight=self.weight,
            width=self.width,
            axes=self.axes,
        )

    def oblique(self):
        "Generate an oblique version of this font"
        return Font(
            self.family,
            self.size,
            style=OBLIQUE,
            variant=self.variant,
            weight=self.weight,
            width=self.width,
            axes=self.axes,
        )

    def normal_variant(self):
        "Generate a normal variant of this font"
        return Font(
            self.family,
            self.size,
            style=self.style,
            variant=NORMAL,
            weight=self.weight,
            width=self.width,
            axes=self.axes,
        )

    def small_caps(self):
        "Generate a small-caps variant of this font"
        return Font(
            self.family,
            self.size,
            style=self.style,
            variant=SMALL_CAPS,
            weight=self.weight,
            width=self.width,
            axes=self.axes,
        )

    def normal_weight(self):
        "Generate a normal weight version of this font"
        return Font(
            self.family,
            self.size,
            style=self.style,
            variant=self.variant,
            weight=NORMAL,
            width=self.width,
            axes=self.axes,
        )

    def bold(self):
        "Generate a bold version of this font"
        return Font(
            self.family,
            self.size,
            style=self.style,
            variant=self.variant,
            weight=BOLD,
            width=self.width,
            axes=self.axes,
        )

    def normal_width(self):
        "Generate a normal width version of this font"
        return Font(
            self.family,
            self.size,
            style=self.style,
            variant=self.variant,
            weight=self.weight,
            width=NORMAL,
            axes=self.axes,
        )

    def condensed(self):
        "Generate a condensed version of this font"
        return Font(
            self.family,
            self.size,
            style=self.style,
            variant=self.variant,
            weight=self.weight,
            width=CONDENSED,
            axes=self.axes,
        )

    def expanded(self):
        "Generate an expanded version of this font"
        return Font(
            self.family,
            self.size,
            style=self.style,
            variant=self.variant,
            weight=self.weight,
            width=EXPANDED,
            axes=self.axes,
        )
