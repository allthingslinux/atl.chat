"""Test utilities and helper functions."""

import shutil
import tempfile
from pathlib import Path

import pytest


def create_temp_file(content: str = "test content", suffix: str = ".txt") -> Path:
    """Create a temporary file with given content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
        f.write(content)
        return Path(f.name)


def create_temp_dir() -> Path:
    """Create a temporary directory."""
    return Path(tempfile.mkdtemp())


def cleanup_temp_files(*paths: Path):
    """Clean up temporary files and directories."""
    for path in paths:
        if path.exists():
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)


class AssertHelpers:
    """Helper methods for common assertions."""

    @staticmethod
    def assert_file_exists(path: Path):
        """Assert that a file exists."""
        assert path.exists(), f"File {path} does not exist"
        assert path.is_file(), f"Path {path} is not a file"

    @staticmethod
    def assert_dir_exists(path: Path):
        """Assert that a directory exists."""
        assert path.exists(), f"Directory {path} does not exist"
        assert path.is_dir(), f"Path {path} is not a directory"

    @staticmethod
    def assert_file_contains(path: Path, content: str):
        """Assert that a file contains specific content."""
        AssertHelpers.assert_file_exists(path)
        file_content = path.read_text()
        assert content in file_content, f"Content '{content}' not found in {path}"

    @staticmethod
    def assert_dict_contains_keys(data: dict, keys: list):
        """Assert that a dictionary contains all specified keys."""
        for key in keys:
            assert key in data, f"Key '{key}' not found in dictionary"


# Pytest fixtures for test helpers
@pytest.fixture
def temp_file():
    """Provide a temporary file fixture."""
    path = create_temp_file()
    yield path
    cleanup_temp_files(path)


@pytest.fixture
def temp_directory():
    """Provide a temporary directory fixture."""
    path = create_temp_dir()
    yield path
    cleanup_temp_files(path)


@pytest.fixture
def assert_helpers():
    """Provide assertion helper methods."""
    return AssertHelpers()
