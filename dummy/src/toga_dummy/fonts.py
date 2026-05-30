from toga.fonts import UnknownFontError

from .utils import LoggedObject


class Font(LoggedObject):
    def __init__(self, interface):
        super().__init__()
        self.interface = interface

    def load_predefined_system_font(self):
        if self.interface.family not in {
            "system",
            "message",
            "serif",
            "sans-serif",
            "cursive",
            "fantasy",
            "monospace",
        }:
            raise UnknownFontError(f"{self.interface} not a predefined system font")

    def load_user_registered_font(self):
        if self.interface.family == "Bogus Font":
            raise UnknownFontError(f"{self.interface} not a user-registered font")

    def load_arbitrary_system_font(self):
        raise UnknownFontError("Arbitrary system fonts not yet supported on dummy")

    @staticmethod
    def installed_families():
        return {"Font Family 1", "Font Family 2", "Font Family 3"}

    def __eq__(self, other):
        return all(
            [
                self.interface.family == other.interface.family,
                self.interface.size == other.interface.size,
                self.interface.weight == other.interface.weight,
                self.interface.width == other.interface.width,
                self.interface.variant == other.interface.variant,
                self.interface.style == other.interface.style,
                self.interface.axes == other.interface.axes,
            ]
        )
