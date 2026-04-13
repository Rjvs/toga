# Project Instructions

Do the correct thing, not the simplest thing; minimal patches now that fail to deal with structural issues only create higher maintenance cost in the future.

All code should be performant, correct and complete.

Tasks are not complete until pre-release hook is clean `prek run --all-files` will let you know about any issues you need to fix.

Defensive programming is important; the common case should always be the default and "falling back" should always require an active measure; it should not be able to happen by forgetting a parameter.

There are skills available;
- knowledge about WinUI3 is in windows-ui skill
- there is a win32more skill
- we have a toga skill and a toga-dev skill

## Project Overview

Our aim is to create a fully-functional WinUI3-based backend for Toga.  It's very important that all of the Toga API types are correct and provide funtionally equivalent information as the WinForms backend.
All features present in the toga-winforms backend should be equally functional in the new toga-winui3 backend.  Obviously the implementations themselves will be different but all components must uphold to Toga contract
and behave the way that a Toga backend is supposed to behave.  It should all be tested thoroughly, using the Toga testing standards and the tests should be equivalent to all of the other backends.

## Semantic Versioning

Bump the semver version in `pyproject.toml` when a session makes user-visible changes (patch for fixes, minor for features, major only with approval). No bump for CI, docs, or invisible refactors.

## Commands

```bash
# Setup
uv sync --group dev
prek install

# Lint, format & type check (single command)
prek run --all-files

# Lint & format separately
uvx ruff check --fix
uvx ruff format
# Type check separately
uv run ty check

# Regenerate win32more type stubs (after updating win32more)
uv run python tools/generate_win32more_stubs.py

# Tests
uv run pytest
uv run tox
```
