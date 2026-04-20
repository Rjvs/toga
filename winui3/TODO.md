# toga-winui3: Porting toga-winforms to WinUI 3 with win32more

## Project Overview

Port the Toga Windows backend from WinForms (via pythonnet/clr) to WinUI 3 (via win32more). The new backend will be called `toga-winui3` with Python module `toga_winui3`.

### Why

- WinUI 3 is Microsoft's modern native UI framework (Fluent Design, Mica, etc.)
- WinForms is legacy (.NET Framework era)
- win32more is pure Python (no C extensions), auto-generated from win32metadata
- WinUI 3 has built-in DPI awareness, dark mode, modern controls

### Key Technology Changes

| Aspect        | WinForms (current)    | WinUI 3 (target)                     |
|---------------|-----------------------|--------------------------------------|
| Python bridge | pythonnet (clr)       | win32more                            |
| UI framework  | System.Windows.Forms  | Microsoft.UI.Xaml                    |
| Window class  | WinForms.Form         | Microsoft.UI.Xaml.Window             |
| App class     | WinForms.Application  | win32more.winui3.XamlApplication     |
| Layout container | WinForms.Panel     | Microsoft.UI.Xaml.Controls.Canvas    |
| Event subs    | `control.Event += handler` | `control.add_Event(handler)`    |
| DPI handling  | Manual (SetProcessDpiAwarenessContext) | WinUI 3 auto-scales |
| Colors        | System.Drawing.Color  | Windows.UI.Color / SolidColorBrush   |
| Fonts         | System.Drawing.Font   | Microsoft.UI.Xaml.Media.FontFamily   |
| Images        | System.Drawing.Bitmap | Microsoft.UI.Xaml.Media.Imaging.BitmapImage |
| XAML loading  | N/A                   | XamlReader.Load() for complex layouts |

---

## Architecture Notes

### Absolute Positioning with Canvas

Toga's layout engine (travertino) computes absolute `(x, y, width, height)` for every widget via `set_bounds()`. WinUI 3's `Canvas` panel supports this via attached properties `Canvas.Left`, `Canvas.Top` and explicit `Width`/`Height`.

This is the key insight: we don't use WinUI 3's built-in layout (StackPanel, Grid) for widget positioning - we use `Canvas` as the container and let travertino drive all layout, just like WinForms uses `Panel` with absolute `Location`/`Size`.

### Event Loop Integration

win32more's `XamlApplication` already integrates with Python's asyncio event loop. The WinForms backend needed a complex custom `WinformsProactorEventLoop` to bridge asyncio and the WinForms message pump. With win32more + WinUI 3, async event handlers just work (`async def on_click(self, sender, e): await ...`).

### DPI Scaling

WinUI 3 handles DPI scaling natively - controls automatically render at the correct scale. No `Scalable` mixin needed.

### WinUI 3 Control Mapping

| Toga Widget          | WinUI 3 Control                  |
|----------------------|----------------------------------|
| Button               | Controls.Button                  |
| Label                | Controls.TextBlock               |
| TextInput            | Controls.TextBox                 |
| PasswordInput        | Controls.PasswordBox             |
| NumberInput          | Controls.NumberBox               |
| MultilineTextInput   | Controls.TextBox (AcceptsReturn) |
| Switch               | Controls.ToggleSwitch            |
| Slider               | Controls.Slider                  |
| ProgressBar          | Controls.ProgressBar             |
| ActivityIndicator    | Controls.ProgressRing            |
| Selection            | Controls.ComboBox                |
| DateInput            | Controls.CalendarDatePicker      |
| TimeInput            | Controls.TimePicker              |
| ImageView            | Controls.Image                   |
| Divider              | Border                           |
| Box                  | Controls.Canvas                  |
| ScrollContainer      | Controls.ScrollViewer            |
| SplitContainer       | Custom (Grid + drag splitter)    |
| OptionContainer      | Controls.TabView                 |
| Table                | Controls.ListView + Grid header  |
| Tree                 | Controls.TreeView                |
| DetailedList         | Controls.ListView                |
| WebView              | Controls.WebView2                |
| Canvas               | Win2D CanvasControl              |
| MapView              | WebView2 + Leaflet.js            |

---

## Implementation Phases

### Phases 0-8: Core Implementation ✅

All widgets, infrastructure, and supporting systems are implemented except Canvas. See the source files for implementation details.

Fix known gaps in implemented widgets:

- [x] Tree: `scroll_to_node()` uses `ContainerFromNode` + `StartBringIntoView` after expanding ancestors
- [x] DetailedList: Row icons rendered (Image 40x40 in horizontal StackPanel)
- [x] OptionContainer: Tab icons via `TabViewItem.IconSource` with `BitmapIconSource`

### Phase 9: Test Backend Rewrite ✅ (initial rewrite)

All 38 test files in `tests_backend/` have been rewritten from WinForms to WinUI 3. All `System.Windows.Forms`, `System.Drawing`, and `toga_winforms` imports replaced with WinUI 3 equivalents via win32more.

- [x] Identify gaps in test coverage and where practical add tests for missing functionality, otherwise document the missing tests here, along with reasoning for not implementing them.

    **Fixed (would cause test failures):**
    - [x] `multilinetextinput.py`: `vertical_scroll_position` was hardcoded to 0; now reads `ScrollViewer.VerticalOffset` via `VisualTreeHelper`
    - [x] `multilinetextinput.py`: `document_height` returned viewport height; now reads `ScrollViewer.ExtentHeight`
    - [x] `table.py`: `scroll_position` was hardcoded to 0; now reads `ScrollViewer.VerticalOffset` from the `ListView`
    - [x] `table.py`: `max_scroll_position` returned viewport height; now reads `ScrollViewer.ScrollableHeight`

    **Acceptable no-ops (matching WinForms behaviour):**
    - `progressbar.py`: `wait_for_animation()` — no-op (internal animation, same as WinForms)
    - `imageview.py`: `assert_image_size()` — no-op (auto-scaled internally, same as WinForms)
    - `scrollcontainer.py`: `wait_for_scroll_completion()` — no-op (same as WinForms)
    - `splitcontainer.py`: `wait_for_split()` — no-op (same as WinForms)
    - `table.py`: `wait_for_scroll_completion()` — no-op (same as WinForms)

    **Acceptable skips (platform limitation or matching WinForms):**
    - `table.py`: `resize_column()` — WinUI3 Grid has no column resize API
    - `tree.py`: Mouse hover/click methods (4) — native TreeView handles hover/expand internally
    - `optioncontainer.py`: `assert_supports_content_based_rehint()` — same as WinForms
    - `mapview.py`: `select_pin()` — same as WinForms
    - `timeinput.py`: `min_value`/`max_value` return None — WinUI3 TimePicker has no native min/max; `supports_limits = False` gates the tests

    **Hardware probes not needed:** testbed hardware tests skip `"windows"` platform

- [ ] Run toga testbed against new backend
- [ ] Fix test failures

### Phase 10: Review and Refactor

#### Phase 10.1: Refactor for correctness

- [x] All widget, infrastructure, and supporting module implementations need to be compared method-by-method against the WinForms reference backend and the Toga core interface contracts. Ensure all methods are implemented and behave equivalently, have the same parameters, accept and return the same types. Document recommended changes as TODOs here:

    **widgets/table.py**
    - [x] No icon support

    **widgets/tree.py**
    - [x] No icon support

    **widgets/detailedlist.py**
    - [x] No icon/image display

    **widgets/mapview.py**
    - [x] `get_location()` and `get_zoom()` return cached values

    **widgets/container.py**
    - [x] `add_content` does not manage Z-order

#### Phase 10.2: Refactor for behaviour

- [x] Using the win32more and windows-ui skills, review all widget, infrastructure, and supporting module implementations and ensure that they do what they are intended to do (that behaviour would be consistent with toga-winforms or toga-cocoa). Document recommended changes as TODOs here:

    **Bugs fixed:**
    - [x] `widgets/timeinput.py`: `_on_time_changed()` double-fired `on_change()` during min/max clamping (setting `self.native.Time` re-triggers `TimeChanged`)
    - [x] `widgets/numberinput.py`: `set_readonly()` used `IsEnabled` which grays out the control; now uses `IsHitTestVisible`/`IsTabStop` to block interaction without visual disability
    - [x] `widgets/numberinput.py`: Removed dead code (`is_valid()`, `set_error()`, `clear_error()`) not part of NumberInput contract
    - [x] `app.py`: `set_icon()` silently swallowed all exceptions; now emits `warnings.warn()`
    - [x] `command.py`: Keyboard accelerator errors silently dropped; now emits `warnings.warn()`
    - [x] `dialogs.py`: `initial_directory` parameter accepted but never applied to WinRT file pickers; now uses `SuggestedFolder` property

    **Known WinUI3 limitations (not fixable without custom controls):**
    - NumberBox has no `IsReadOnly` property; workaround uses `IsHitTestVisible`/`IsTabStop`
    - WinUI3 TimePicker has no native min/max; manual clamping causes brief visual flicker of unclamped value
    - WinRT `SuggestedFolder` on `FileOpenPicker`/`FolderPicker` is experimental in Windows App SDK 2.0+

    **Verified intentional differences from WinForms (NOT bugs):**
    - `container.py`: No DPI `scale_in`/`scale_out` — WinUI3 uses DIPs natively
    - `window.py show()`: Uses `Activate()` — required for WinUI3 window display
    - `window.py on_show/on_hide`: Inline event firing is correct
    - `widgets/base.py`: Defensive `hasattr`/`getattr` for `TabIndex`/`IsEnabled`/`Focus` — correct for WinUI3 controls
    - `widgets/base.py refresh()`: XamlRoot guard is correct — `Measure`/`DesiredSize` return zeros before visual tree attachment
    - Different native controls (NumberBox, PasswordBox, ToggleSwitch, etc.) are expected WinUI3 equivalents
    - Async dialog system is WinUI3-native
    - `selection.py` parallel `_items` list is architecturally necessary (WinUI3 ComboBoxItem doesn't store source objects)
    - `textinput.py`/`passwordinput.py`: Red border for errors vs ErrorProvider icon is functionally equivalent
    - `statusicons.py`: `warnings.warn()` for unknown groups instead of ValueError is reasonable for auxiliary UI
    - `imageview.py`: No explicit DPI scaling needed — WinUI3 handles natively

#### Phase 10.3: Refactor for performance

- [x] 18 potential performance issues identified; 13 assessed as premature optimisation (GUI-speed operations, not tight loops) and skipped. 5 genuine correctness/quality improvements implemented:

    **Theme-adaptive colours (correctness):**
    - [x] `widgets/divider.py`: Replaced broad `except Exception` cascade with `theme_brush()` utility using `HasKey()` check
    - [x] `widgets/textinput.py` + `widgets/passwordinput.py`: Replaced duplicate hardcoded `_ERROR_BRUSH` singleton with theme resource `SystemFillColorCriticalBrush` (adapts to dark/light theme); extracted shared helper to `_utils.py`
    - [x] `widgets/splitcontainer.py`: Replaced hardcoded gray splitter colour with theme resource `ControlStrokeColorDefaultBrush`

    **API usage (code quality):**
    - [x] `widgets/table.py` + `widgets/detailedlist.py`: Replaced manual `for i, row in enumerate(…)` loop in `source_change()` with `self.interface.data.index(item)` (Toga core API, uses C-level `list.index()`)

    **Resource leak (correctness):**
    - [x] `statusicons.py`: Track HICON handles from `LoadImageW`; call `DestroyIcon()` on previous handle in `set_icon()` and `remove()` to prevent GDI resource leaks

    **Skipped items (premature optimisation):**
    - Deferred imports in `dialogs.py` — Python caches after first import; moving to top-level adds startup cost
    - `app_window.Presenter` access in `window.py` — already cached where possible; re-fetch after `SetPresenter()` is correct
    - Sequential `Children.Append()` in `window.py` — one-time setup; WinUI 3 batches layout passes within same message loop iteration
    - `create_menus`/`create_toolbar` in `window.py` — already reuse objects; only recreate when absent
    - `font.interface.*` access in `fonts.py` — each accessed exactly once per code path
    - `_refresh()` guards in `screens.py` — lazy init; only triggers once
    - `string.replace()` in `keys.py` — 3 iterations max on short strings, human-speed key events
    - `hasattr()` checks in `base.py` — correct defensive pattern; different controls have different capabilities
    - Linear search in `container.py` — small collections; `IVector` has no `Remove(element)` method
    - Viewport properties in `scrollcontainer.py` — simple property reads, accessed once each
    - Tuple creation in `canvas.py` — CPython free-list optimised; standard Python pattern
    - `Children.Size` in `tree.py` — simple property read, not a computation
    - `ActualWidth`/`ActualHeight` in `splitcontainer.py` — read-only properties; do not trigger layout

#### Phase 10.4: Refactor for style

- [x] Reviewed all implementations against Toga style guide (toga-winforms, toga-gtk, toga-cocoa conventions). Changes implemented:

    **Event handler naming (HIGH PRIORITY):**
    - [x] Renamed all `_on_*` event handlers to `winui3_*` prefix across ~20 widget files + `window.py`, matching the `{backend}_` convention used by winforms (`winforms_click`), GTK (`gtk_clicked`), and already in `command.py` (`winui3_click`)

    **WeakrefCallable wrapping:**
    - [x] Wrapped all event registrations in `WeakrefCallable` to prevent reference cycles, matching winforms and GTK patterns. Added `from toga.handlers import WeakrefCallable` to all affected widget files

    **Deprecated method style:**
    - [x] Updated comment blocks in `selection.py`, `table.py`, `detailedlist.py`, `tree.py` to match winforms style with date annotation (`# March 2026: In 0.5.3 and earlier…`)
    - [x] Moved `import warnings` inline into deprecated methods (only loaded on deprecated path), matching winforms pattern

---

## References

### Skills

The following skills are available;

- `win32more`
- `windows-ui` (documents WinUI 3)
- `toga-dev` (documents Toga style guide and development practices)

---

## Important Details to Remember

### win32more Patterns

- Import: `from win32more.Microsoft.UI.Xaml.Controls import Button, TextBlock`
- App: subclass `XamlApplication`, override `OnLaunched`, call `XamlApplication.Start(App)`
- Events: `control.add_Click(handler)` or `control.Click += handler`
- XAML strings: `XamlReader.Load(xaml_string)` returns UIElement
- Custom controls: use `XamlClass` mixin with `LoadComponentFromString`
- Async handlers: `async def handler(self, sender, e): await ...` just works
- Named elements: `XamlLoader.Load(self, xaml)` auto-binds `x:Name` attributes
- Error checking: `if FAILED(hr): raise WinError(hr)` for COM calls
- ContentDialog: must set `XamlRoot` before `ShowAsync()`
- File dialogs: `FileOpenPicker(window.AppWindow.Id)` (App SDK version)

### Toga Backend Contract

- Backend class gets `interface` arg pointing to core widget
- `create()` method instantiates native control as `self.native`
- `set_bounds(x, y, w, h)` positions widget (CSS pixels)
- `rehint()` reports intrinsic size via `self.interface.intrinsic.width/height`
- `refresh()` triggers layout recalculation
- Container manages child widgets via `add_content()` / `remove_content()`
- Entry points in pyproject.toml register all backend classes

### WinUI 3 Canvas Positioning

```python
from win32more.Microsoft.UI.Xaml.Controls import Canvas
# Position a child element:
Canvas.SetLeft(element, x)
Canvas.SetTop(element, y)
element.Width = width
element.Height = height
```

### Key Differences from WinForms

- No `BackColor` / `ForeColor` -- use `Background` (Brush) and `Foreground` (Brush)
- No `PreferredSize` -- must measure controls differently for `rehint()`
- No manual DPI scaling needed -- WinUI 3 handles it natively
- No `CreateGraphics()` hack -- WinUI 3 rendering is composition-based
- Transparency is native -- no alpha blending workaround needed
- No `Label.TextAlign` -- use `TextBlock.TextAlignment` and `TextBlock.VerticalAlignment`
- Tab order: `Control.TabIndex` -> `UIElement.TabIndex` (same concept)
