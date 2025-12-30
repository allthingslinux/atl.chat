# Legacy Test Suite

This directory contains the original integration test suite that has been replaced by the new consolidated test suite in `tests/consolidated/`.

## What Changed

The original test suite was scattered across many files with inconsistent patterns and no standardized server management. The new consolidated suite:

- Uses a **controller pattern** inspired by [irctest](https://github.com/progval/irctest)
- Provides **controlled IRC server instances** for each test
- Has **consistent test patterns** and rich assertions
- Is **organized by functionality** rather than by implementation

## Directory Structure

- **`integration/`** - The original integration tests that were migrated to `tests/consolidated/`

## Status

These tests are **deprecated** and should not be used for new development. They are kept for:

- **Reference**: To see how the old tests worked
- **Regression testing**: To ensure the new framework produces equivalent results
- **Historical purposes**: To track the evolution of the testing framework

## Migration

If you need to run these tests, they should still work with the current `conftest.py`, but new tests should be written in the consolidated structure.

## Future Plans

This directory may be removed in a future version once confidence in the new consolidated test suite is established.
