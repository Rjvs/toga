# Lessons Learned from Toga Development Sessions

Extracted from Claude Code and Conductor session logs, plan files, code reviews, and terminal output across the WinUI 3 backend, SwiftUI backend planning, and core Toga work.

---

## 1. Platform API Differences Bite Hard — Study the Reference Backend First

**What happened:** Multiple bugs in the WinUI 3 backend stemmed from assuming WinRT/WinUI 3 APIs behave like WinForms equivalents. Examples:
- `PasswordBox` has no `IsReadOnly` property (WinForms `TextBox` does) — required using `IsHitTestVisible` + `IsTabStop` as a workaround.
- WinUI 3's `PointerPressed` fires *before* `DoubleTapped`, so using it for `on_press` causes a spurious press on every double-click. The fix was to switch to `Tapped`/`RightTapped` events.
- `id()` on WinRT COM proxy objects returns different Python wrapper IDs for the same underlying object, breaking all `id()`-based lookups in Table and Tree widgets.

**Lesson:** When implementing a new backend, don't assume the new platform's API mirrors the old one. Read the platform docs for each API you use. Compile a "gotchas" list early — especially around object identity, event ordering, and property availability.

---

## 2. COM/WinRT Object Identity is Not Python Object Identity

**What happened:** Three separate bugs (`Table.get_selection()`, `Tree._reverse_map`, `MapView.pin_count`) all traced to using `id()` on WinRT proxy objects. Each call to `GetAt()` or similar API returns a *new Python wrapper* around the same COM object, so `id()` comparisons and set intersections always fail.

**Lesson:** Never use `id()` to track or compare WinRT/COM proxy objects. Use `Items.IndexOf()` for index-based lookups, or key on the `.value` attribute (the raw COM pointer address) for dictionaries.

---

## 3. Silent `except Exception` Blocks Hide Real Bugs

**What happened:** Code review found four instances of bare `except Exception` blocks that silently swallowed errors — `set_icon`, `get_image_data` (screens and window), and `get_window_state`. These returned empty bytes or a default state, masking real failures.

**Lesson:** Avoid bare `except Exception` that returns a default value. Let exceptions propagate — it's better to crash visibly than to silently return wrong data. If you must catch, log the exception or re-raise after cleanup.

---

## 4. Magic Numbers Create Cross-Backend Drift

**What happened:** The `96 / 72` points-to-pixels conversion factor was hardcoded in 9 places across 6 backends. The WinUI 3 backend *missed* the conversion entirely in `fonts.py`, causing all fonts to render at the wrong size. Meanwhile, the GDI fallback path applied the conversion redundantly.

**Lesson:** Extract cross-backend constants to `core/`. The fix added `POINTS_PER_PIXEL = 96 / 72` to `toga/fonts.py` and updated all backends. When you see a magic number repeated across backends, centralize it immediately.

---

## 5. DPI/HiDPI Handling Requires Careful Dimensional Analysis

**What happened:** Canvas `get_image_data` hardcoded 96 DPI, producing wrong-sized images on HiDPI displays. The first fix attempt introduced a *double-scaling* bug — `CanvasRenderTarget` interprets width/height as DIPs and internally scales by `dpi/96`, but the code passed already-scaled pixel dimensions plus scaled DPI, producing `scale²` pixels.

**Lesson:** When working with DPI-aware APIs, always annotate variables with their units (DIPs vs physical pixels). Write the dimensional analysis as a comment. Test the math at 100%, 150%, and 200% scaling mentally.

---

## 6. Test Probe Handler Names Must Match Implementation

**What happened:** Three test backend probes (slider, table, tree) called handler methods with wrong names — `_on_pointer_pressed` instead of `winui3_pointer_pressed`, `_on_double_tapped` instead of `winui3_double_tapped`, `_on_item_invoked` instead of `winui3_item_invoked`. These tests silently passed because the `hasattr` guards returned `False`, making the tests no-ops.

**Lesson:** When writing test probes, grep the implementation for the actual handler names. Don't guess naming conventions. Consider making test probes fail loudly when the expected handler doesn't exist, rather than using `hasattr` guards that degrade to no-ops.

---

## 7. Type Checker Configuration for Cross-Platform Monorepos is Non-Trivial

**What happened:** Running `ty check` on the WinUI 3 backend initially produced 6,817 errors. Root causes:
- No `ty.toml` configuration existed (no `python-platform = "windows"`, no search paths).
- The venv had no backend packages installed (win32more, toga-core, travertino).
- `uvx ty check` runs in an isolated env — needed `uv run ty check` instead.
- Dynamic monorepo dependencies (`toga-core == {version}`) couldn't resolve from PyPI — needed `[tool.uv.sources]` to point at local paths.

After configuration: errors dropped from 6,817 to 342, then to a small set of genuine issues.

**Lesson:** When adding type checking to a new backend in a monorepo:
1. Create a `ty.toml` with `python-platform`, `python-version`, and `extra-search-paths`.
2. Add `[tool.uv.sources]` entries for monorepo sibling packages.
3. Use `uv run ty check` (not `uvx ty check`) so the tool sees installed packages.
4. Install the backend and its deps into the venv first.
5. Update CLAUDE.md with the correct check command.

---

## 8. Window State Management is a State Machine — Treat It Like One

**What happened:** The WinUI 3 window state management had multiple interacting bugs:
- `_cached_window_size = None` (used as sentinel) could propagate up through `get_size()`, returning `None` instead of a `Size`.
- The `SizeChanged` event handler updated the cache, racing with `set_window_state`.
- Double `SetPresenter` calls occurred when transitioning between non-NORMAL states.
- `on_show`/`on_hide` double-fired because both `winui3_size_changed` and `winui3_visibility_changed` fired independently for the same minimize/restore transition.

The fix restructured the code into a match/case dispatch table on `(current_state, target_state)` pairs, added `_pending_state_transition` tracking, and added a `_visible` guard against double-firing.

**Lesson:** Window state transitions are a state machine. Model them explicitly with (current, target) pairs rather than scattered if/elif chains. Separate the concerns: who owns the cache, who fires events, who calls native APIs. Match what the reference backend does.

---

## 9. Review Cycles Are Expensive — Get Architecture Right in the Plan

**What happened:** The bozeman workspace went through at least 9 review cycles (Review request v1 through v9), each finding new batches of bugs (8 bugs, then 7, then 7 more, then 3, then 4, then 2). Many of these were systematic — the same class of bug (wrong `id()` usage, wrong handler names, silent exception swallowing) appeared in multiple files.

**Lesson:** Before implementing, compile a "pitfalls checklist" for the platform. After the first review finds a bug class, sweep the entire codebase for that class before submitting the next review. Don't fix bugs one-at-a-time across review cycles.

---

## 10. Memory Management Across Language Bridges Needs Explicit Design

**What happened:** During SwiftUI backend planning, review identified that:
- `Block` instances wrapping Python callbacks can be garbage collected, leaving dangling pointers.
- `ctypes.c_wchar_p` auto-converts to Python `str`, so `CoTaskMemFree(path_ptr)` passes the wrong value, leaking the COM-allocated buffer. Fix: use `ctypes.c_void_p` and `ctypes.wstring_at()`.

**Lesson:** When bridging Python to native code, document the ownership and lifetime of every pointer/object that crosses the boundary. Use `c_void_p` (not `c_wchar_p`) when you need to both read and free a pointer. Store `Block` instances as instance attributes to prevent GC.

---

## 11. `ObjCBlock` vs `Block` in rubicon-objc — Know the Direction

**What happened:** The SwiftUI TODO.md used `ObjCBlock` everywhere for callbacks. Review caught that `ObjCBlock` wraps an *existing* ObjC block for Python to call, while `Block` wraps a *Python callable* for ObjC to call. Toga needs the latter — Python drives the UI and ObjC calls back into Python.

**Lesson:** `ObjCBlock` = ObjC → Python (receiving a block), `Block` = Python → ObjC (creating a block). When setting up callbacks from native code into Python, always use `Block`.

---

## 12. Pre-Validate Architectural Assumptions Before Full Implementation

**What happened:** The SwiftUI backend plan review identified several unvalidated assumptions:
- Would `NSHostingView.fittingSize` return useful dimensions for `rehint()`?
- Would frame-based positioning (`setFrame_`) work without Auto Layout conflicts?
- Would multiple `NSHostingView`s in one parent `NSView` render correctly?
- Would `load_library("TogaBridge")` actually find and load the Swift framework?

The reviewer recommended adding a "Phase 0.5" to validate these before building out the full backend.

**Lesson:** For any new backend or major architectural change, build a minimal proof-of-concept that validates the core assumptions before writing production code. Test the happy path of: framework loading, widget creation, property binding, callback wiring, layout, and sizing.

---

## 13. Reuse from Existing Backends Should Be Explicit, Not Assumed

**What happened:** The SwiftUI TODO.md said many modules were "largely the same as Cocoa" but didn't specify which files could be copied verbatim vs which needed modification. Review found that `paths.py`, `screens.py`, `keys.py`, `colors.py`, `icons.py`, `command.py`, `dialogs.py`, and `statusicons.py` could likely be copied wholesale, while `app.py` needed small modifications.

**Lesson:** When planning a new backend, create an explicit table: "copy verbatim", "copy with modifications", "write from scratch". This prevents both unnecessary duplication work and subtle bugs from wrong assumptions about what's shared.

---

## 14. Backend Registration in Entry Points Can Conflict

**What happened:** The SwiftUI backend plan registered as `macOS = "toga_swiftui"`, same key as the Cocoa backend's `macOS = "toga_cocoa"`. Having both installed causes `get_backend()` to raise `RuntimeError("Multiple candidate toga backends found")`.

**Lesson:** Document the backend coexistence strategy up front — whether users should use `TOGA_BACKEND=toga_swiftui`, or whether only one backend should be installed at a time.

---

## 15. Tools Configuration Must Be Part of the Backend Scaffolding

**What happened:** The WinUI 3 backend was developed without type checking configuration, linting rules, or test infrastructure being set up first. This meant bugs accumulated silently and were only found in bulk during code review.

**Lesson:** When scaffolding a new backend, set up tooling (linting, type checking, formatting, test harness) in Phase 1, not Phase 10. Fixing one bug at a time during development is much cheaper than fixing 20 bugs found in review.

---

## 16. Window Decoration Sizes Can Be Zero Before the Window Is Shown

**What happened:** Before a WinUI 3 window is shown, `self.native.Bounds` is zero. The decoration calculation `app_window.Size - bounds` treated the entire window size as decoration, producing an oversized window.

**Lesson:** Guard calculations that depend on window geometry against pre-layout zero values. Add a helper method that returns `(0, 0)` when bounds are zero, and use it consistently across all call sites.

---

## 17. Canvas Path Operations Have Subtle Closing Semantics

**What happened:** The canvas `rect()` method added a redundant line-to-start point before `close_path()`. But `EndFigure(Closed)` already handles the closing segment. The extra zero-length segment disrupted dash-pattern rendering.

**Lesson:** When implementing canvas path operations, understand whether `close_path()` adds an implicit line segment back to the start. Don't add an explicit line-to-start before closing — it creates a zero-length segment that breaks dashing.

---

## 18. Division by Zero Lurks in Graphics Code

**What happened:** Canvas `stroke()` divided dash pattern values by line width (`d / lw`), but line width can be zero. Zero-width strokes produce no visible output anyway.

**Lesson:** Guard division in graphics code. When the divisor can be zero, check whether the operation is meaningful (zero-width stroke = invisible = skip drawing).

---

## 19. The Plan Is Not the Code — Verify Before Citing

**What happened:** The SwiftUI TODO.md contained several technical inaccuracies caught during review — wrong API names (`ObjCBlock` vs `Block`), wrong framework loading approach (`cdll.LoadLibrary` vs `load_library`), missing lifecycle details (Block GC safety, interface/impl weak references).

**Lesson:** Plans and TODO documents are proposals, not specifications. Review them with the same rigor as code. In particular, verify that every API name and code example actually works as written.

---

## 20. Event Ordering Differences Between Platforms Are Hard to Predict

**What happened:** WinUI 3's event order for double-click is: `PointerPressed` → `PointerPressed` → `DoubleTapped`. WinForms fires separate events that don't overlap the same way. This difference caused an extra `on_press` to fire before `on_activate` on double-click.

**Lesson:** Document the event ordering for each platform explicitly. When implementing input handling, test the actual event sequence (or read platform docs carefully) rather than assuming it matches another platform.

---

## 21. Async Initialization Requires Guarding All Dependent Methods

**What happened:** WebView's `get_cookies()` accessed `self.cookie_manager` without waiting for `_initialize()`. This crashes with `AttributeError` if called before WebView2 initialization completes. The fix was to wrap with `run_after_initialization`, matching the existing `evaluate_javascript()` pattern.

**Lesson:** When a widget has an async initialization step, *every* method that depends on the initialized state must go through the initialization gate. Search for all references to initialized-only attributes and guard them.

---

## 22. MapView Init Failure Uses the Same Sentinel as Success

**What happened:** `MapView._initialize()` sets `self.backlog = None` on both success (all backlog items executed) and failure (init failed). After failure, `_invoke()` sees `backlog is None` and tries to execute JS on an uninitialized WebView2, crashing.

**Lesson:** Don't overload `None` as both "done successfully" and "failed". Use a distinct flag (`_init_failed`) or an enum state to distinguish states that require different handling.

---

## 23. Iterative Code Review Works — But Systematic Sweeps Work Better

**What happened:** The bozeman workspace ran 9+ review rounds. Each found new issues, but many were instances of the same bug class (wrong handler names, silent exception swallowing, `id()` on COM objects). If the first review's findings had been swept across the entire codebase, subsequent rounds would have been much lighter.

**Lesson:** After a review finds a bug class, immediately grep for all instances of that pattern before fixing just the reported ones. Pattern-based sweeps (`grep -r 'except Exception' winui3/`, `grep -r 'id(.*native' winui3/`) catch systematic issues that file-by-file review misses.

---

## 24. Font Size Conversion Bugs Are Invisible Until Visual Testing

**What happened:** The WinUI 3 backend omitted the points-to-DIPs conversion in `fonts.py`. All fonts rendered at the wrong size, but this wouldn't show up in any automated test — only in visual inspection.

**Lesson:** For visual properties (font size, colors, layout), add automated assertions where possible (e.g., `assert native_font_size == expected * POINTS_PER_PIXEL`), and flag properties that can only be verified visually in test documentation.

---

## 25. Coordinating Multiple Workspaces Needs Clear Boundaries

**What happened:** Work was split across multiple Conductor workspaces (bozeman for WinUI 3 bug fixes, brasilia for SwiftUI planning, san-marino, winnipeg). This helped parallelize work but required careful coordination to avoid conflicts.

**Lesson:** When splitting work across workspaces, define clear boundaries: which files each workspace owns, which branch each workspace operates on, and how to merge. Don't let two workspaces modify the same files.

---

## 26. `set_text` / `set_icon` Circular Dependency Requires a Shadow Variable

**What happened:** In `button.py`, `set_text()` called `set_icon()`, which internally called `get_text()` to retrieve the current label text — but at the time of the call, `set_text` hadn't yet updated the native control, so `get_text()` returned the old value. The icon's label always lagged one call behind.

**Lesson:** When `set_A` calls `set_B` and `set_B` reads back the value of A, there's a temporal coupling bug. Break the cycle with a shadow instance variable that's set at the beginning of `set_A`, and have `set_B` read the shadow rather than the (not-yet-updated) native control.

---

## 27. WinUI3 Has No Native Paint Callback — Canvas Requires Win2D

**What happened:** WinUI3/XAML is a retained-mode UI framework with no `OnPaint`/`drawRect_` equivalent. Toga's Canvas relies on immediate-mode rendering. This requires `Win2D` (`win32more-microsoft-graphics-win2d`), which must be added as a dependency.

**Lesson:** Don't attempt to implement Canvas without first confirming Win2D is in the project's dependencies. Verify the dependency installs and imports correctly before writing any implementation code — otherwise you burn an entire session on exploration that can't produce runnable code.

---

## 28. `args.InvokedItem` in TreeView Returns the Content Grid, Not the Node

**What happened:** The Tree widget's `_on_item_invoked` handler used `args.InvokedItem` to get the activated item. WinUI3's `TreeViewItemInvokedEventArgs.InvokedItem` returns the Content Grid (the visual container), not the `TreeViewNode`. The fix was to use `self._tree_view.SelectedNode` instead.

**Lesson:** WinUI3's `TreeView.ItemInvoked` event passes the content object (whatever was set as the node's Content), not the `TreeViewNode`. Use `TreeView.SelectedNode` in the handler.

---

## 29. Change Handlers That Re-Set Values Must Guard Against Reentry

**What happened:** In `timeinput.py`, the `on_change` callback fired twice during min/max clamping — once for the user's input and once when the clamped value was re-set.

**Lesson:** When a change handler re-sets a value (e.g., for clamping), add a `return` after the clamping assignment or use a reentry guard (`_updating = True` flag) to prevent recursive firing.

---

## 30. Scroll Position Probes Need Visual Tree Walking

**What happened:** Test backend probes for scroll-related properties were returning hardcoded 0 values. The fix required a `find_scroll_viewer` helper that uses `VisualTreeHelper` to locate the internal `ScrollViewer` inside composite WinUI3 controls.

**Lesson:** WinUI3 composite controls contain an internal `ScrollViewer` that's not directly accessible as a property. Use `VisualTreeHelper` to walk the visual tree. Put this as a shared utility in the test backend base.

---

## 31. WinUI3 Properties Are Already in DIPs — Don't Double-Scale

**What happened:** When implementing scroll position probes, the WinForms reference was dividing by `scale_factor` for DPI compensation. But WinUI3 XAML properties (`ScrollViewer.VerticalOffset`, `ExtentHeight`, etc.) are already in DIPs.

**Lesson:** Don't blindly copy scaling logic from WinForms. WinForms returns physical pixels; WinUI3 XAML properties return DIPs. Check each property's unit before applying scale_factor.

---

## 32. Confirm Dependencies Before Starting Large Implementations

**What happened:** A Canvas implementation session hit the rate limit just at the point of confirming that `win32more-microsoft-graphics-win2d` wasn't in the project dependencies — architecture was understood but nothing was implemented.

**Lesson:** Before starting a large implementation that requires a new external dependency, confirm the dependency is available and installs correctly. This avoids sessions that do expensive exploration but can't produce runnable code.

---

## 33. `warnings.warn()` Beats Silent Exception Swallowing

**What happened:** `app.py`'s `set_icon()` and `command.py`'s keyboard accelerator failures silently dropped exceptions. The fix was to emit `warnings.warn()` with correct `stacklevel`.

**Lesson:** For non-fatal failures (icon load, shortcut registration), use `warnings.warn()` instead of bare `except`. This surfaces issues during testing without crashing. Always set `stacklevel` correctly.

---

## 34. The WinForms Backend Is the Ground Truth — Read It First

**What happened:** Across all sessions, the consistent successful pattern was: read WinForms reference implementation → check core interface contract → implement. The WinForms backend is the most mature reference.

**Lesson:** When implementing any Toga backend widget, always read the WinForms backend equivalent first. Then check the core interface to catch methods WinForms doesn't implement. Don't start from first principles — start from the reference.

---

## 35. Explore → Plan → Implement in Batches → Lint/Check → Update TODO

**What happened:** Sessions that followed this pattern introduced less rework. Sessions that skipped straight to implementation had more bugs. The plan catches interface mismatches before writing code. Batching by related files reduces cognitive load. Checking the linter after each batch surfaces issues while context is fresh.

**Lesson:** For backend widget work in Toga, the explore-plan-batch-implement pattern reduces errors. Don't skip the planning step for complex widgets.

---

## 36. Use `SHGetKnownFolderPath`, Not Hardcoded Paths

**What happened:** `paths.py` was using `Path.home() / "AppData/Local"`. The correct approach is `SHGetKnownFolderPath(FOLDERID_LocalAppData)` via ctypes, which works correctly in enterprise environments with redirected profiles.

**Lesson:** On Windows, always use proper Windows APIs for well-known folder paths. Hardcoded path components break in corporate AD environments where paths are redirected.

---

## 37. `int` Subclass `__repr__` vs `__str__` — Python's f-string Gotcha

**What happened:** `FontWeight` subclasses `int` and overrides `__repr__` to show named weights. But Python f-strings call `__str__`, not `__repr__`. Without an explicit `__str__`, CSS output emitted `FontWeight(700)` instead of `700` or `bold`.

**Lesson:** When subclassing `int` (or any primitive) and overriding `__repr__`, always add `__str__` explicitly. `int.__str__` is inherited, but as soon as you add `__repr__`, the repr leaks into f-strings and other str() contexts.

---

## 38. Don't Block a User Path with "Use X Instead" Unless X Exists

**What happened:** `STANDARD_AXES` included `slnt` and `opsz`, blocking them from the `axes` escape hatch with a message saying "use the named property instead." But no named properties existed for `slnt` or `opsz` — users were deadlocked with no way to set these axes.

**Lesson:** Whenever you block a user path with "use X instead," verify X actually exists. Defensive validation that blocks access with no alternative is worse than no validation at all.

---

## 39. `datetime.date.fromtimestamp()` Is Timezone-Sensitive — Wrong Dates West of UTC

**What happened:** The WinUI 3 DateInput converted tick values using `fromtimestamp()`, which interprets midnight-UTC ticks in local time. In negative-UTC-offset timezones, this returns the previous day. WinForms avoids this by extracting year/month/day components directly.

**Lesson:** Never use `fromtimestamp()` for date-only operations — use `datetime.utcfromtimestamp()` or direct component extraction. Timezone bugs in date widgets only manifest for users in negative-offset timezones, making them invisible in most dev environments.

---

## 40. ABI Mismatch in ctypes: `POINTER(UINT)` vs `UINT_PTR`

**What happened:** A `_SUBCLASSPROC` callback declared `uIdSubclass` as `ctypes.POINTER(UINT)` (pointer-to-int) instead of `UINT_PTR` (pointer-sized integer). On x64 these are different sizes, causing memory corruption.

**Lesson:** Win32 callback type declarations are safety-critical. `*_PTR` types (`UINT_PTR`, `DWORD_PTR`) are pointer-sized integers, not pointers-to-integers. Always verify against the MSDN signature.

---

## 41. Layout Bugs Look Identical to Code Bugs

**What happened:** New Roboto Flex labels were added to the font example but placed below a text area with `flex=1`. The user couldn't see them and reported "didn't see any Roboto Flex." The assistant's first hypothesis was wrong (a code problem). Moving the labels to the top of the layout fixed it.

**Lesson:** When a user reports "it's not working" for a GUI widget, verify the widget is actually visible on screen before debugging the code. Content scrolled off-screen or hidden by flex expansion is a common false lead.

---

## 42. When Users Interrupt, Stop — Don't Continue with a Modified Version

**What happened:** In multiple sessions, the user interrupted the assistant mid-planning when it proposed the wrong approach (creating static TTFs from a variable font, using `uvx ty` instead of `uv run ty`). The interrupt signals a fundamental direction problem, not just a detail.

**Lesson:** When the user interrupts, immediately stop and ask for clarification rather than continuing with a modified version of the same approach. Don't assume the direction was mostly right.

---

## 43. CSS "Points" vs Apple "Points" — A Naming Collision That Causes Bugs

**What happened:** When documenting font size conversion, a comment needed to clarify that a "point" in Apple APIs is a CSS pixel (1/96 inch), not a typographic point (1/72 inch). The `96/72` conversion exists because Toga's public API uses typographic points.

**Lesson:** Apple's UI unit called a "point" is NOT a typographic point. It's a device-independent pixel at 96 dpi. Document this explicitly in font-related code to prevent future confusion.

---

## 44. Toga Housekeeping Checklist for Every Feature

**What happened:** In multiple sessions, the user asked "have we done all the Toga paperwork?" after implementation was done. Missing items found: unused pytest imports, missing towncrier change note, outdated docstrings.

**Lesson:** For every Toga feature, the checklist is: (1) towncrier change note in `changes/<issue>.feature.md`, (2) platform docs updated, (3) core/Pack docstrings updated, (4) no unused imports, (5) dummy backend updated if interface changed. Don't consider a feature complete until this is done.

---

## 45. win32more Has No Static Type Stubs — Generate Them

**What happened:** ty was configured and could find win32more, but 338+ unresolved-attribute errors remained because win32more uses metaclasses and decorators that ty can't follow. The solution was a stub generator script that parsed win32more source AST and emitted `.pyi` files.

**Lesson:** When a dynamic Python library uses metaclass patterns, expect mass false positives from type checkers. The solution is to generate `.pyi` stubs from the source. This is a significant investment but reduces noise dramatically.

---

## 46. Add Native Type Annotations to Widget Classes — Eliminates Union Errors

**What happened:** ty saw `self.native` as `Widget | None` (from the base class) and generated 160+ `unresolved-attribute` and 78 `invalid-assignment` errors across all widget classes. Adding class-level `native: WinUIButton` annotations to each concrete widget fixed this.

**Lesson:** For platform backends, always add explicit class-level type annotations for `native` in every widget class. Without it, the type checker is blind to all native API calls. The user noted: "annotations are obviously beneficial and should really have been added already."

---

## 47. Cross-Workspace Code Review Catches What Implementing Agents Miss

**What happened:** A code review agent in a separate workspace found a real bug: the dummy backend's `Font.__eq__` was missing `width` after `axes` was added. The implementing agent had missed this symmetry bug.

**Lesson:** Parallel code review agents catch things the implementing agent misses, especially symmetry/consistency bugs (fields in equality checks, fields in repr, etc.). Running a separate review pass is worth it for significant features.

---

## 48. Verify Claims About Code Behavior Before Documenting Them

**What happened:** The assistant described `str(FontWeight(700))` returning `"bold"` before implementing `__str__`. Tests showed it actually returned `"FontWeight(700)"` (the repr). The `__str__` method had to be added after the fact.

**Lesson:** When making claims about how code behaves (especially string representations of custom types), run a quick test or trace through the code path before committing to the behavior in design documents, tests, or explanations to the user.

---

## 49. `briefcase dev` Exits 0 From Any Directory — Even Without a Project

**What happened:** `briefcase dev` was run from the repo root instead of `examples/font/`. It exited 0 (success) but did nothing useful.

**Lesson:** `briefcase dev` silently succeeds from any directory, even without a Briefcase project. Always `cd` to the correct directory first and verify by checking for a `pyproject.toml` with `[tool.briefcase]`.

---

## 50. Stubs and Installed Packages Conflict in ty's Search Path

**What happened:** When `win32more` was both installed via pip AND present as stubs in `extra-paths`, ty saw both and produced 5,000+ errors. The fix was to ensure stubs take priority or remove the installed package.

**Lesson:** With ty, having both a `.pyi` stub directory AND the real package installed can cause conflicts. Prefer stubs-only for packages that ty can't handle natively.

---

## 51. Never Use Magic Integers for Enum Values — Names Differ Across Platforms

**What happened:** In `dialogs.py`, `TextWrapping = 1` was commented as `# TextWrapping.Wrap`, but in WinUI 3, `1` = `NoWrap` and `2` = `Wrap`. The same error appeared in `multilinetextinput.py`. The code "looked right" because magic numbers don't fail at import or type-check time.

**Lesson:** Never use integer literals for WinUI 3 enum values — always use the named enum (`TextWrapping.Wrap`). When porting from WinForms, enum integer mappings often differ between frameworks. Named constants let the type checker catch mismatches.

---

## 52. `debug = True` Left in Production Code

**What happened:** `webview.py` shipped with `debug = True` hardcoded, enabling DevTools, context menus, and accelerator keys that should not be available in production. Only caught in a dedicated audit.

**Lesson:** Debug flags must be the first thing reverted after debugging. Add debug flag review to the pre-commit audit checklist.

---

## 53. Unstaged New Files Are Invisible Bugs

**What happened:** `src/toga_winui3/widgets/_utils.py` was created and imported by 14 widget files but never staged in git. The code passed all local static checks because the file existed locally. On a fresh checkout it would fail immediately with `ModuleNotFoundError`.

**Lesson:** When creating new utility modules imported by many files, verify they appear in `git status` and are staged. After writing a new file, always check `git status` before declaring done.

---

## 54. Test Probes Must Exercise Real Native Event Pipelines

**What happened:** The Canvas test probe was implemented using mock pointer args that called implementation handlers directly, bypassing the native `add_PointerPressed` event wiring. The user caught this: "Shouldn't the tests be testing Toga compatibility instead of using native classes?"

**Lesson:** Test probes must exercise the real native event pipeline to verify event subscriptions are actually connected. Calling handler methods directly only tests handler logic, not that handlers are wired up. Use OS-level input injection (Win32 `SendInput`, etc.) matching how other backends simulate events.

---

## 55. Read toga-core for Widget API Contracts, Not Just WinForms

**What happened:** Slider was implemented with `set_range(range)` taking a tuple — but toga-core calls `get_min()`, `set_min()`, `get_max()`, `set_max()` individually. Source listener methods used old names (`insert`) instead of new (`source_insert`). Multiple stubs had wrong method signatures.

**Lesson:** When implementing a widget, verify the exact method signatures toga-core dispatches by reading the core widget source. The core is the authority. WinForms may have legacy patterns or deprecated aliases that don't match the current API.

---

## 56. Missing Method Call Parentheses on WinRT Objects Silently Succeed

**What happened:** `mapview.py` had `args.TryGetWebMessageAsString` (missing `()`) instead of `args.TryGetWebMessageAsString()`. The expression returns the bound method object, which is truthy, so no error is raised — but the MapView's location/zoom tracking silently broke.

**Lesson:** In win32more, WinRT method calls must include `()`. Without them, the expression returns a truthy method object with no runtime error. Be especially careful in conditionals and event handlers.

---

## 57. win32more Event Subscriptions Return Tokens — Store Them

**What happened:** Many event subscriptions (e.g., `add_SizeChanged()`) discarded the returned `EventRegistrationToken`. Without the token, events cannot be unsubscribed, leading to resource leaks or handler calls on destroyed objects.

**Lesson:** Always store the token returned by `add_EventName()` (e.g., `self._size_changed_token = ...`). Unsubscribe in the widget's cleanup/close path. This mirrors the WinRT C# `EventRegistrationToken` pattern.

---

## 58. `else` Branches That Assume Initialization Are Fragile

**What happened:** `webview.py` had `else: self.pending_tasks.append(...)` instead of `elif self.pending_tasks is not None: ...`. When WebView2 runtime is unavailable, `self.pending_tasks` is never set, so the `else` crashes.

**Lesson:** When a feature depends on an optional runtime, guard the uninitialized case explicitly with `elif`. `else` branches that assume state has been initialized are fragile — always check the condition.

---

## 59. Use `AppWindow.Closing` (Not `Window.Closed`) for Cancellable Close

**What happened:** The initial window implementation used `Window.Closed` which fires after close and cannot be cancelled. Toga's `on_close` handler needs to be able to cancel closure. The fix was switching to `AppWindow.Closing` which has a `Cancel` property.

**Lesson:** Know which close events support cancellation. `Window.Closed` is post-hoc; `AppWindow.Closing` is pre-close and cancellable. Check if an event fires before or after the action when you need veto power.

---

## 60. Pre-Commit Hooks Modify Files Between Write and Edit — Re-Read

**What happened:** After writing a Python file, a ruff formatting hook automatically modified it. The next edit used stale in-memory content, requiring a re-read. This happened multiple times across sessions.

**Lesson:** After any Write tool call on Python files, assume a formatting hook may have modified the file. Always re-read before making subsequent edits.

---

## 61. Dedicated Audit Passes Find More Bugs Than Development Review

**What happened:** Two dedicated audit sessions found bugs that implementation, static analysis, and linting all missed: missing `()` on WinRT method calls, hardcoded `debug = True`, wrong `TextWrapping` enum values, DPI scaling issues, `else` vs `elif`, unstaged files, redundant overrides, and duplicate helpers.

**Lesson:** Schedule dedicated audit/review passes per major component, separate from implementation. Semantic bugs (wrong enum value, wrong branch condition, missing parentheses) are invisible to linters and type checkers.

---

## 62. TODO.md Is Load-Bearing Context — Keep It Precise

**What happened:** The WinUI 3 project was managed through a `TODO.md` tracking phases and checkboxes. When it got stale (items checked with remaining sub-issues, deferred items with no rationale), sessions became less effective. A dedicated cleanup session was eventually needed.

**Lesson:** For multi-session projects, keep the TODO precise: don't leave items checked if sub-tasks remain, document rationale for deferred items, and add implementation notes as discoveries are made. Cleanup sessions are necessary but avoidable with ongoing hygiene.

---

## 63. Use `raise NotImplementedError` Instead of ABC for Toga Backend Base Classes

**What happened:** `base.py` used `ABC` and `@abstractmethod` on `create()`, but other methods were intentional no-ops without `@abstractmethod`. Ruff B027 fires on abstract classes with empty non-abstract methods. The fix was to drop `ABC` entirely.

**Lesson:** In Toga backends, express "must override" with `raise NotImplementedError` rather than `ABC` + `@abstractmethod`, because many base methods have intentional no-op defaults. Mixing the two creates confusion and linter warnings.

---

## 64. Budget Explicit Review Phases for Platform Ports

**What happened:** The WinUI 3 port required: initial implementation, systematic correctness audit, performance/idiom refactor, test backend rewrite, and two "ready to commit?" audits. Each pass found real bugs. The ratio of review time to implementation time was high because there's no test suite runnable on the dev machine.

**Lesson:** For a platform port, budget explicit review phases from the start. Don't treat the first implementation pass as "done" — it establishes structure but will have correctness gaps, especially when you can't run the code locally.
