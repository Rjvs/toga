import pytest

from travertino.constants import (
    BOLD,
    CONDENSED,
    EXPANDED,
    ITALIC,
    NORMAL,
    OBLIQUE,
    SMALL_CAPS,
    SYSTEM_DEFAULT_FONT_SIZE,
)
from travertino.fonts import Font, FontWeight, FontWidth


def assert_font(font, family, size, style, variant, weight):
    assert font.family == family
    assert font.size == size
    assert font.style == style
    assert font.variant == variant
    assert font.weight == weight


@pytest.mark.parametrize(
    "font",
    [
        Font("Comic Sans", "12 pt"),
        Font("Comic Sans", 12),
        Font("Comic Sans", 12, NORMAL, NORMAL, NORMAL),
    ],
)
def test_equality(font):
    assert font == Font("Comic Sans", "12 pt")


@pytest.mark.parametrize(
    "font",
    [
        Font("Comic Sans", 13),
        Font("Comic Sans", 12, ITALIC),
        Font("Times New Roman", 12, NORMAL, NORMAL, NORMAL),
        "a string",
        5,
    ],
)
def test_inqequality(font):
    assert font != Font("Comic Sans", "12 pt")


def test_hash():
    assert hash(Font("Comic Sans", 12)) == hash(Font("Comic Sans", 12))

    assert hash(Font("Comic Sans", 12, weight=BOLD)) != hash(Font("Comic Sans", 12))


@pytest.mark.parametrize(
    "size, kwargs, string",
    [
        (12, {}, "12pt"),
        (12, {"style": ITALIC}, "italic 12pt"),
        (12, {"style": ITALIC, "variant": SMALL_CAPS}, "italic small-caps 12pt"),
        (
            12,
            {"style": ITALIC, "variant": SMALL_CAPS, "weight": BOLD},
            "italic small-caps 700 12pt",
        ),
        (12, {"variant": SMALL_CAPS, "weight": BOLD}, "small-caps 700 12pt"),
        (12, {"weight": BOLD}, "700 12pt"),
        (12, {"style": ITALIC, "weight": BOLD}, "italic 700 12pt"),
        # Check system default size handling
        (SYSTEM_DEFAULT_FONT_SIZE, {}, "system default size"),
        (SYSTEM_DEFAULT_FONT_SIZE, {"style": ITALIC}, "italic system default size"),
    ],
)
def test_repr(size, kwargs, string):
    assert repr(Font("Comic Sans", size, **kwargs)) == f"<Font: {string} Comic Sans>"


@pytest.mark.parametrize("size", [12, "12", "12pt", "12 pt"])
def test_simple_construction(size):
    assert_font(Font("Comic Sans", size), "Comic Sans", 12, NORMAL, NORMAL, NORMAL)


def test_invalid_construction():
    with pytest.raises(ValueError):
        Font("Comic Sans", "12 quatloos")


@pytest.mark.parametrize(
    "family",
    [
        "Comics Sans",
        "Wingdings",
        "'Comic Sans'",
        '"Comic Sans"',
    ],
)
def test_family(family):
    normalized_family = family.replace("'", "").replace('"', "")
    assert_font(Font(family, 12), normalized_family, 12, NORMAL, NORMAL, NORMAL)


@pytest.mark.parametrize(
    "style, result_style",
    [
        (ITALIC, ITALIC),
        ("italic", ITALIC),
        (OBLIQUE, OBLIQUE),
        ("oblique", OBLIQUE),
        ("something else", NORMAL),
    ],
)
def test_style(style, result_style):
    assert_font(
        Font("Comic Sans", 12, style=style),
        "Comic Sans",
        12,
        result_style,
        NORMAL,
        NORMAL,
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"style": ITALIC},
    ],
)
def test_make_normal_style(kwargs):
    f = Font("Comic Sans", 12, **kwargs)
    assert_font(f.normal_style(), "Comic Sans", 12, NORMAL, NORMAL, NORMAL)


@pytest.mark.parametrize(
    "method, result",
    [
        ("italic", ITALIC),
        ("oblique", OBLIQUE),
    ],
)
def test_make_slanted(method, result):
    f = Font("Comic Sans", 12)
    assert_font(getattr(f, method)(), "Comic Sans", 12, result, NORMAL, NORMAL)


@pytest.mark.parametrize(
    "variant, result",
    [
        (SMALL_CAPS, SMALL_CAPS),
        ("small-caps", SMALL_CAPS),
        ("something else", NORMAL),
    ],
)
def test_variant(variant, result):
    assert_font(
        Font("Comic Sans", 12, variant=variant),
        "Comic Sans",
        12,
        NORMAL,
        result,
        NORMAL,
    )


@pytest.mark.parametrize("kwargs", [{}, {"variant": SMALL_CAPS}])
def test_make_normal_variant(kwargs):
    f = Font("Comic Sans", 12, **kwargs)
    assert_font(f.normal_variant(), "Comic Sans", 12, NORMAL, NORMAL, NORMAL)


def test_make_small_caps():
    f = Font("Comic Sans", 12)
    assert_font(f.small_caps(), "Comic Sans", 12, NORMAL, SMALL_CAPS, NORMAL)


@pytest.mark.parametrize(
    "weight, result",
    [
        (BOLD, BOLD),
        ("bold", BOLD),
        ("something else", NORMAL),
    ],
)
def test_weight(weight, result):
    assert_font(
        Font("Comic Sans", 12, weight=weight),
        "Comic Sans",
        12,
        NORMAL,
        NORMAL,
        result,
    )


@pytest.mark.parametrize("kwargs", [{}, {"weight": BOLD}])
def test_make_normal_weight(kwargs):
    f = Font("Comic Sans", 12, **kwargs)
    assert_font(f.normal_weight(), "Comic Sans", 12, NORMAL, NORMAL, NORMAL)


def test_make_bold():
    f = Font("Comic Sans", 12)
    assert_font(f.bold(), "Comic Sans", 12, NORMAL, NORMAL, BOLD)


######################################################################
# FontWeight tests
######################################################################


class TestFontWeight:
    def test_from_keyword(self):
        assert FontWeight("normal") == 400
        assert FontWeight("bold") == 700

    def test_from_int(self):
        assert FontWeight(350) == 350
        assert FontWeight(100) == 100
        assert FontWeight(900) == 900

    def test_invalid_keyword(self):
        with pytest.raises(ValueError, match="Invalid font weight keyword"):
            FontWeight("heavy")

    def test_out_of_range(self):
        with pytest.raises(ValueError, match="between 1 and 1000"):
            FontWeight(0)
        with pytest.raises(ValueError, match="between 1 and 1000"):
            FontWeight(1001)

    def test_backward_compat_equality(self):
        """FontWeight compares equal to CSS keyword strings."""
        assert FontWeight(400) == "normal"
        assert FontWeight(700) == "bold"
        assert FontWeight(400) == NORMAL
        assert FontWeight(700) == BOLD

    def test_backward_compat_inequality(self):
        assert FontWeight(400) != "bold"
        assert FontWeight(700) != "normal"
        assert FontWeight(350) != "normal"
        assert FontWeight(350) != "bold"

    def test_hash_consistency(self):
        """FontWeight hashes like its int value."""
        assert hash(FontWeight(400)) == hash(400)
        assert hash(FontWeight(700)) == hash(700)

    def test_repr(self):
        assert repr(FontWeight(400)) == "FontWeight(400)"
        assert repr(FontWeight(700)) == "FontWeight(700)"

    def test_nested_construction(self):
        """FontWeight(FontWeight(x)) works."""
        w = FontWeight(350)
        assert FontWeight(w) == 350


######################################################################
# Numeric weight in Font construction
######################################################################


class TestNumericWeight:
    def test_numeric_weight_construction(self):
        font = Font("Recursive", 16, weight=350)
        assert font.weight == 350
        assert isinstance(font.weight, FontWeight)

    def test_keyword_weight_normalizes_to_int(self):
        font = Font("Recursive", 16, weight=BOLD)
        assert font.weight == 700
        assert isinstance(font.weight, FontWeight)

    def test_default_weight_is_400(self):
        font = Font("Recursive", 16)
        assert font.weight == 400
        assert font.weight == NORMAL

    def test_numeric_weight_repr(self):
        assert repr(Font("Recursive", 16, weight=350)) == "<Font: 350 16pt Recursive>"

    def test_numeric_weight_hash(self):
        """Fonts with same numeric weight hash the same."""
        assert hash(Font("Recursive", 16, weight=700)) == hash(
            Font("Recursive", 16, weight=BOLD)
        )

    def test_numeric_weight_equality(self):
        """Fonts with equivalent weights are equal."""
        assert Font("Recursive", 16, weight=700) == Font(
            "Recursive", 16, weight=BOLD
        )

    def test_helper_methods_preserve_weight(self):
        f = Font("Recursive", 16, weight=350)
        assert f.italic().weight == 350
        assert f.oblique().weight == 350
        assert f.small_caps().weight == 350
        assert f.normal_style().weight == 350
        assert f.normal_variant().weight == 350


######################################################################
# Custom axes tests
######################################################################


class TestCustomAxes:
    def test_axes_construction(self):
        font = Font("Recursive", 16, axes={"CASL": 0.5, "MONO": 1})
        assert font.axes == {"CASL": 0.5, "MONO": 1}

    def test_no_axes_default(self):
        font = Font("Recursive", 16)
        assert font.axes is None

    def test_standard_axis_rejected(self):
        with pytest.raises(ValueError, match="Standard axis"):
            Font("Recursive", 16, axes={"wght": 400})
        with pytest.raises(ValueError, match="Standard axis"):
            Font("Recursive", 16, axes={"wdth": 100})
        with pytest.raises(ValueError, match="Standard axis"):
            Font("Recursive", 16, axes={"ital": 1})

    def test_invalid_axis_tag_length(self):
        with pytest.raises(ValueError, match="4-character"):
            Font("Recursive", 16, axes={"CA": 0.5})

    def test_axes_in_repr(self):
        font = Font("Recursive", 16, axes={"CASL": 0.5, "MONO": 1})
        r = repr(font)
        assert "CASL=0.5" in r
        assert "MONO=1" in r

    def test_axes_equality(self):
        f1 = Font("Recursive", 16, axes={"CASL": 0.5})
        f2 = Font("Recursive", 16, axes={"CASL": 0.5})
        f3 = Font("Recursive", 16, axes={"CASL": 0.8})
        f4 = Font("Recursive", 16)
        assert f1 == f2
        assert f1 != f3
        assert f1 != f4

    def test_axes_hash(self):
        f1 = Font("Recursive", 16, axes={"CASL": 0.5})
        f2 = Font("Recursive", 16, axes={"CASL": 0.5})
        assert hash(f1) == hash(f2)

    def test_helper_methods_preserve_axes(self):
        axes = {"CASL": 0.5, "MONO": 1}
        f = Font("Recursive", 16, axes=axes)
        assert f.italic().axes == axes
        assert f.bold().axes == axes
        assert f.normal_weight().axes == axes
        assert f.small_caps().axes == axes


######################################################################
# FontWidth tests
######################################################################


class TestFontWidth:
    def test_from_keyword(self):
        assert FontWidth("normal") == 100.0
        assert FontWidth("condensed") == 75.0
        assert FontWidth("expanded") == 125.0
        assert FontWidth("ultra-condensed") == 50.0
        assert FontWidth("ultra-expanded") == 200.0

    def test_from_number(self):
        assert FontWidth(87.5) == 87.5
        assert FontWidth(100) == 100.0
        assert FontWidth(75) == 75.0

    def test_invalid_keyword(self):
        with pytest.raises(ValueError, match="Invalid font width keyword"):
            FontWidth("narrow")

    def test_out_of_range(self):
        with pytest.raises(ValueError, match="positive percentage"):
            FontWidth(0)
        with pytest.raises(ValueError, match="positive percentage"):
            FontWidth(-50)

    def test_backward_compat_equality(self):
        """FontWidth compares equal to CSS keyword strings."""
        assert FontWidth(100) == "normal"
        assert FontWidth(75) == "condensed"
        assert FontWidth(125) == "expanded"
        assert FontWidth(100) == NORMAL

    def test_backward_compat_inequality(self):
        assert FontWidth(100) != "condensed"
        assert FontWidth(75) != "normal"

    def test_hash_consistency(self):
        assert hash(FontWidth(100)) == hash(100.0)

    def test_str(self):
        assert str(FontWidth(100)) == "normal"
        assert str(FontWidth(75)) == "condensed"
        assert str(FontWidth(87.5)) == "semi-condensed"
        assert str(FontWidth(80)) == "80%"

    def test_repr(self):
        assert repr(FontWidth(100)) == "FontWidth(100)"
        assert repr(FontWidth(75)) == "FontWidth(75)"
        assert repr(FontWidth(87.5)) == "FontWidth(87.5)"


######################################################################
# Width in Font construction
######################################################################


class TestFontWidth_InFont:
    def test_width_construction(self):
        font = Font("Recursive", 16, width=CONDENSED)
        assert font.width == 75.0
        assert font.width == CONDENSED
        assert isinstance(font.width, FontWidth)

    def test_numeric_width_construction(self):
        font = Font("Recursive", 16, width=87.5)
        assert font.width == 87.5

    def test_default_width_is_normal(self):
        font = Font("Recursive", 16)
        assert font.width == 100.0
        assert font.width == NORMAL

    def test_width_in_repr(self):
        font = Font("Recursive", 16, width=CONDENSED)
        assert "condensed" in repr(font)

    def test_width_equality(self):
        f1 = Font("Recursive", 16, width=75)
        f2 = Font("Recursive", 16, width=CONDENSED)
        f3 = Font("Recursive", 16, width=EXPANDED)
        assert f1 == f2
        assert f1 != f3

    def test_width_hash(self):
        assert hash(Font("Recursive", 16, width=75)) == hash(
            Font("Recursive", 16, width=CONDENSED)
        )

    def test_helper_methods_preserve_width(self):
        f = Font("Recursive", 16, width=CONDENSED)
        assert f.italic().width == CONDENSED
        assert f.bold().width == CONDENSED
        assert f.normal_weight().width == CONDENSED
        assert f.small_caps().width == CONDENSED
        assert f.normal_style().width == CONDENSED

    def test_width_helper_methods(self):
        f = Font("Recursive", 16)
        assert f.condensed().width == CONDENSED
        assert f.expanded().width == EXPANDED
        assert f.normal_width().width == NORMAL
