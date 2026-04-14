"""Generate .pyi type stubs for win32more modules used by toga-winui3.

Parses win32more source files and extracts class definitions, properties,
events, and enums into .pyi stub files that ty can understand.

The stubs deliberately use `Any` for most property types to avoid creating
a web of cross-module stub dependencies. The primary goal is to make ty
aware that classes have the right attributes, not to fully type every
win32more API.

Usage:
    .venv/bin/python3 winui3/tools/generate_win32more_stubs.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Root paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STUBS_DIR = REPO_ROOT / "winui3" / "stubs"
SITE_PACKAGES = (
    REPO_ROOT / ".venv" / "lib" / "python3.13" / "site-packages"
)
WIN32MORE_ROOT = SITE_PACKAGES / "win32more"

# All win32more modules imported by the winui3 backend.
MODULES = [
    "win32more",
    "win32more.Microsoft.Graphics.Canvas",
    "win32more.Microsoft.Graphics.Canvas.Brushes",
    "win32more.Microsoft.Graphics.Canvas.Geometry",
    "win32more.Microsoft.Graphics.Canvas.Text",
    "win32more.Microsoft.Graphics.Canvas.UI.Xaml",
    "win32more.Microsoft.UI",
    "win32more.Microsoft.UI.Input",
    "win32more.Microsoft.UI.Text",
    "win32more.Microsoft.UI.Windowing",
    "win32more.Microsoft.UI.Xaml",
    "win32more.Microsoft.UI.Xaml.Controls",
    "win32more.Microsoft.UI.Xaml.Controls.Primitives",
    "win32more.Microsoft.UI.Xaml.Input",
    "win32more.Microsoft.UI.Xaml.Media",
    "win32more.Microsoft.UI.Xaml.Media.Animation",
    "win32more.Microsoft.UI.Xaml.Media.Imaging",
    "win32more.Windows.Foundation",
    "win32more.Windows.Foundation.Collections",
    "win32more.Windows.Foundation.Numerics",
    "win32more.Windows.Storage.Streams",
    "win32more.Windows.System",
    "win32more.Windows.UI",
    "win32more.Windows.UI.Text",
    "win32more.Windows.Win32.UI.WindowsAndMessaging",
    "win32more.winui3",
]


def module_to_path(module: str) -> Path:
    """Convert a dotted module name to its source file path."""
    parts = module.split(".")
    return WIN32MORE_ROOT.parent / Path(*parts) / "__init__.py"


def module_to_stub_path(module: str) -> Path:
    """Convert a dotted module name to its stub file path."""
    parts = module.split(".")
    return STUBS_DIR / Path(*parts) / "__init__.pyi"


def parse_type_annotation(node: ast.expr) -> str:
    """Convert an AST expression node to a type string."""
    if isinstance(node, ast.Constant):
        if node.value is ...:
            return "..."
        return repr(node.value)
    elif isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        value = parse_type_annotation(node.value)
        return f"{value}.{node.attr}"
    elif isinstance(node, ast.Subscript):
        value = parse_type_annotation(node.value)
        slice_val = parse_type_annotation(node.slice)
        return f"{value}[{slice_val}]"
    elif isinstance(node, ast.Tuple):
        return ", ".join(parse_type_annotation(e) for e in node.elts)
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = parse_type_annotation(node.left)
        right = parse_type_annotation(node.right)
        return f"{left} | {right}"
    return "Any"


def _decorator_name(node: ast.expr) -> str:
    """Get the name of a decorator."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _is_interface_class(node: ast.ClassDef) -> bool:
    """Check if a class is an internal interface definition (IFoo).

    Interface classes start with 'I' + uppercase and don't have property()
    assignments — they only have method stubs.
    """
    if not (node.name.startswith("I") and len(node.name) > 1 and node.name[1].isupper()):
        return False

    for item in node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and isinstance(item.value, ast.Call):
                    if isinstance(item.value.func, ast.Name) and item.value.func.id == "property":
                        return False
    return True


def resolve_base_class(extends_annotation: str | None, current_module: str) -> str | None:
    """Convert a fully-qualified extends annotation to a stub-local reference.

    If the base class is in the same module, return just the class name.
    If it's in a different stubbed module, return the qualified reference.
    Otherwise return None (will fall back to no explicit base).
    """
    if not extends_annotation:
        return None

    # Strip 'win32more.' prefix
    if not extends_annotation.startswith("win32more."):
        return None

    full_ref = extends_annotation  # e.g. 'win32more.Microsoft.UI.Xaml.Controls.Panel'
    # Split into module + class name - the class name is the last component
    parts = full_ref.split(".")
    class_name = parts[-1]
    ref_module = ".".join(parts[:-1])

    if ref_module == current_module:
        # Same module — just use the class name
        return class_name

    # Different module — check if we have stubs for it
    if ref_module in _STUBBED_MODULES:
        return full_ref

    return None


# Will be populated during generation
_STUBBED_MODULES: set[str] = set()


class ClassInfo:
    """Extracted information about a win32more class."""

    def __init__(self, name: str):
        self.name = name
        self.extends: str | None = None
        self.is_enum = False
        self.enum_base: str | None = None
        self.enum_values: list[tuple[str, object]] = []
        self.is_structure = False
        self.struct_fields: list[str] = []  # field names for Structure types
        self.properties: list[tuple[str, bool]] = []  # (name, writable)
        self.events: list[str] = []  # event names
        self.class_properties: list[str] = []  # metaclass property names
        self.methods: list[tuple[str, int, bool]] = []  # (name, param_count, is_classmethod)
        self.has_init = False  # whether class defines __init__


def extract_classes(source_path: Path) -> list[ClassInfo]:
    """Parse a win32more source file and extract class information."""
    if not source_path.exists():
        return []

    source = source_path.read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        print(f"  Warning: Could not parse {source_path}", file=sys.stderr)
        return []

    classes: list[ClassInfo] = []

    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        # Skip metaclass definitions and interface definitions
        if node.name.startswith("_") and node.name.endswith("_Meta_"):
            continue
        if _is_interface_class(node):
            continue

        # Determine if it's an enum
        is_enum = False
        enum_base = None

        is_structure = False
        for base in node.bases:
            base_str = parse_type_annotation(base)
            if base_str == "Enum" or base_str.endswith(".Enum"):
                is_enum = True
            elif base_str in (
                "Int32", "UInt32", "Int64", "UInt64", "Int16", "UInt16",
                "Byte", "SByte",
            ):
                enum_base = base_str
            elif base_str in ("Structure", "Union"):
                is_structure = True

        info = ClassInfo(node.name)
        info.is_enum = is_enum
        info.is_structure = is_structure
        info.enum_base = enum_base

        for item in node.body:
            # Extract annotations (extends, struct fields)
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                if item.target.id == "extends":
                    if item.value:
                        info.extends = parse_type_annotation(item.value)
                    elif item.annotation:
                        info.extends = parse_type_annotation(item.annotation)
                elif is_structure and not item.target.id.startswith("_"):
                    info.struct_fields.append(item.target.id)

            # Extract enum values
            if is_enum and isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and isinstance(item.value, ast.Constant):
                        if not target.id.startswith("_"):
                            info.enum_values.append((target.id, item.value.value))

            # Extract methods (non-getter/setter/event methods)
            if isinstance(item, ast.FunctionDef):
                is_classmethod_dec = any(
                    _decorator_name(d) in ("winrt_classmethod", "winrt_factorymethod")
                    for d in item.decorator_list
                )

                if item.name == "__init__":
                    info.has_init = True
                elif (
                    not item.name.startswith("get_")
                    and not item.name.startswith("put_")
                    and not item.name.startswith("add_")
                    and not item.name.startswith("remove_")
                    and not item.name.startswith("_")
                    and item.name != "CreateInstance"
                ):
                    # Regular method — count non-self params
                    param_count = len(item.args.args) - 1  # subtract self/cls
                    info.methods.append(
                        (item.name, max(param_count, 0), is_classmethod_dec)
                    )
                elif item.name.startswith("add_") or item.name.startswith("remove_"):
                    # Event subscription methods — expose directly
                    param_count = len(item.args.args) - 1
                    info.methods.append(
                        (item.name, max(param_count, 0), False)
                    )

            # Extract property() and event() assignments
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and isinstance(item.value, ast.Call):
                        func = item.value
                        if isinstance(func.func, ast.Name):
                            if func.func.id == "property" and func.args:
                                writable = (
                                    len(func.args) > 1
                                    and parse_type_annotation(func.args[1]) != "None"
                                )
                                info.properties.append((target.id, writable))
                            elif func.func.id == "event":
                                info.events.append(target.id)

                    elif isinstance(target, ast.Attribute) and isinstance(item.value, ast.Call):
                        # _Meta_.PropertyName = property(...)
                        func = item.value
                        if isinstance(func.func, ast.Name) and func.func.id == "property":
                            info.class_properties.append(target.attr)

        classes.append(info)

    return classes


def generate_stub(module: str, classes: list[ClassInfo]) -> str:
    """Generate .pyi stub content for a list of classes."""
    lines: list[str] = []
    lines.append("# Auto-generated type stubs for win32more")
    lines.append("# Generated by winui3/tools/generate_win32more_stubs.py")
    lines.append("# Property types are typed as Any; the goal is attribute existence,")
    lines.append("# not full type safety for win32more internals.")
    lines.append("")
    lines.append("from typing import Any")
    lines.append("")

    # Collect base class imports needed from other modules
    imports_needed: dict[str, set[str]] = {}  # module -> {class_name}
    local_class_names = {cls.name for cls in classes}

    for cls in classes:
        base = resolve_base_class(cls.extends, module)
        if base and "." in base:
            # It's a fully-qualified reference to another module
            parts = base.rsplit(".", 1)
            mod = parts[0]
            name = parts[1]
            imports_needed.setdefault(mod, set()).add(name)

    for mod in sorted(imports_needed):
        names = sorted(imports_needed[mod])
        lines.append(f"from {mod} import {', '.join(names)}")

    if imports_needed:
        lines.append("")

    for cls in classes:
        if cls.is_enum:
            _generate_enum_stub(lines, cls)
        elif cls.is_structure:
            _generate_structure_stub(lines, cls)
        else:
            _generate_class_stub(lines, cls, module)
        lines.append("")

    return "\n".join(lines)


def _generate_enum_stub(lines: list[str], cls: ClassInfo) -> None:
    """Generate stub for an enum class."""
    lines.append(f"class {cls.name}(int):")
    if cls.enum_values:
        for name, _ in cls.enum_values:
            lines.append(f"    {name}: int")
    else:
        lines.append("    ...")


def _generate_structure_stub(lines: list[str], cls: ClassInfo) -> None:
    """Generate stub for a Structure/Union class (C-style struct).

    Structure types can be constructed with positional args matching their
    fields (e.g. Thickness(4, 2, 4, 2)) so we emit __init__ with *args.
    """
    lines.append(f"class {cls.name}:")
    lines.append("    def __init__(self, *args: Any, **kwargs: Any) -> None: ...")
    if cls.struct_fields:
        for name in cls.struct_fields:
            lines.append(f"    {name}: Any")
    else:
        lines.append("    ...")


def _generate_class_stub(lines: list[str], cls: ClassInfo, module: str) -> None:
    """Generate stub for a ComPtr-based class."""
    base = resolve_base_class(cls.extends, module)

    if base and "." in base:
        # Use just the class name since we imported it
        base = base.rsplit(".", 1)[1]

    if base:
        lines.append(f"class {cls.name}({base}):")
    else:
        lines.append(f"class {cls.name}:")

    has_content = False

    # __init__ with *args, **kwargs so constructors work
    if cls.has_init:
        lines.append("    def __init__(self, *args: Any, **kwargs: Any) -> None: ...")
        has_content = True

    # Properties — all typed as Any for simplicity
    for name, writable in cls.properties:
        lines.append(f"    {name}: Any")
        has_content = True

    # Events
    for name in cls.events:
        lines.append(f"    {name}: Any")
        has_content = True

    # Class properties
    for name in cls.class_properties:
        lines.append(f"    {name}: Any")
        has_content = True

    # Methods
    seen_methods: set[str] = set()
    for name, param_count, is_classmethod in cls.methods:
        if name in seen_methods:
            continue
        seen_methods.add(name)

        params = ", ".join(f"_p{i}: Any = ..." for i in range(param_count))
        if is_classmethod:
            if params:
                lines.append(f"    @classmethod")
                lines.append(f"    def {name}(cls, {params}) -> Any: ...")
            else:
                lines.append(f"    @classmethod")
                lines.append(f"    def {name}(cls) -> Any: ...")
        else:
            if params:
                lines.append(f"    def {name}(self, {params}) -> Any: ...")
            else:
                lines.append(f"    def {name}(self) -> Any: ...")
        has_content = True

    if not has_content:
        lines.append("    ...")


def generate_all_stubs() -> None:
    """Main entry point: generate stubs for all required modules."""
    print(f"Generating win32more stubs in {STUBS_DIR}")
    print(f"Reading win32more source from {WIN32MORE_ROOT}")
    print()

    if not WIN32MORE_ROOT.exists():
        print(
            "Error: win32more is not installed. Run:\n"
            "  uv pip install -e ./core -e ./winui3 -e ./travertino",
            file=sys.stderr,
        )
        sys.exit(1)

    # Pre-populate the set of modules we'll have stubs for
    _STUBBED_MODULES.update(MODULES)

    total_classes = 0
    total_modules = 0

    for module in MODULES:
        source_path = module_to_path(module)
        stub_path = module_to_stub_path(module)

        if not source_path.exists():
            print(f"  Skip {module} (source not found at {source_path})")
            continue

        classes = extract_classes(source_path)
        if not classes:
            # Still create an empty stub so imports resolve
            stub_path.parent.mkdir(parents=True, exist_ok=True)
            stub_path.write_text(
                "# Auto-generated type stubs for win32more\n"
                "from typing import Any\n"
            )
            print(f"  {module}: empty stub (no public classes)")
            total_modules += 1
            continue

        stub_content = generate_stub(module, classes)
        stub_path.parent.mkdir(parents=True, exist_ok=True)
        stub_path.write_text(stub_content)

        print(f"  {module}: {len(classes)} classes")
        total_classes += len(classes)
        total_modules += 1

    # Create __init__.pyi for intermediate packages
    _create_package_inits(STUBS_DIR / "win32more")

    print()
    print(f"Generated stubs for {total_classes} classes across {total_modules} modules")
    print(f"Output: {STUBS_DIR}")


def _create_package_inits(root: Path) -> None:
    """Create __init__.pyi files for all intermediate package directories."""
    for dirpath in sorted(root.rglob("*")):
        if dirpath.is_dir():
            init = dirpath / "__init__.pyi"
            if not init.exists():
                init.write_text(
                    "# Auto-generated package marker\n"
                    "from typing import Any\n"
                )


if __name__ == "__main__":
    generate_all_stubs()
