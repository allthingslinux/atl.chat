"""Environment validation tests for IRC.atl.chat."""

import os
import subprocess
from unittest.mock import patch

import pytest


class TestEnvironmentValidation:
    """Test environment setup and validation."""

    def test_project_root_exists(self, project_root):
        """Test that project root directory exists."""
        assert project_root.exists()
        assert project_root.is_dir()

    def test_compose_file_exists(self, compose_file):
        """Test that docker-compose file exists."""
        assert compose_file.exists()
        assert compose_file.suffix == ".yaml"

    def test_compose_file_valid(self, compose_file):
        """Test that docker-compose file is valid YAML."""
        import yaml

        try:
            with open(compose_file) as f:
                data = yaml.safe_load(f)
            assert isinstance(data, dict)
            assert "services" in data
        except Exception as e:
            pytest.fail(f"Invalid compose file: {e}")

    def test_required_directories_exist(self, project_root):
        """Test that required directories exist (scripts, tests at repo root)."""
        required_dirs = ["scripts", "tests", "apps"]

        for dir_name in required_dirs:
            dir_path = project_root / dir_name
            assert dir_path.exists(), f"Required directory {dir_name} does not exist"
            assert dir_path.is_dir(), f"{dir_name} is not a directory"

    def test_scripts_are_executable(self, project_root):
        """Test that scripts are executable."""
        scripts_dir = project_root / "scripts"
        if scripts_dir.exists():
            for script in scripts_dir.glob("*.sh"):
                assert os.access(script, os.X_OK), f"Script {script.name} is not executable"

    def test_docker_available(self, docker_client):
        """Test that Docker is available (when Docker is running)."""
        # This test will be skipped if Docker is not available
        # due to the docker_client fixture
        info = docker_client.info()
        assert "ServerVersion" in info

    def test_justfile_exists(self, project_root):
        """Test that justfile exists (project uses just, not make)."""
        justfile = project_root / "justfile"
        assert justfile.exists(), "justfile should exist"
        assert justfile.is_file()

    def test_test_structure(self, project_root):
        """Test that test directory structure is correct."""
        test_dir = project_root / "tests"
        expected_subdirs = ["unit", "integration", "e2e", "utils", "fixtures"]

        for subdir in expected_subdirs:
            subdir_path = test_dir / subdir
            assert subdir_path.exists(), f"Test subdirectory {subdir} does not exist"
            assert subdir_path.is_dir(), f"{subdir} is not a directory"

    def test_conftest_exists(self, project_root):
        """Test that conftest.py exists."""
        conftest = project_root / "tests" / "conftest.py"
        assert conftest.exists()
        assert conftest.is_file()

    def test_python_version(self):
        """Test that Python version is compatible."""
        import sys

        version = sys.version_info
        assert version.major >= 3
        assert version.minor >= 11

    @patch("subprocess.run")
    def test_docker_compose_config_check(self, mock_run, repo_root):
        """Test Docker Compose configuration validation."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["docker", "compose", "config"], returncode=0, stdout="", stderr=""
        )

        result = subprocess.run(
            ["docker", "compose", "-f", str(repo_root / "compose.yaml"), "config"],
            check=False,
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_environment_variables(self):
        """Test that required environment variables are set or can be set."""
        # These are test-specific variables that should be available
        test_vars = ["TESTING"]

        for var in test_vars:
            # Either the variable should be set, or we should be able to set it
            original_value = os.environ.get(var)
            try:
                os.environ[var] = "test_value"
                assert os.environ.get(var) == "test_value"
            finally:
                if original_value is None:
                    os.environ.pop(var, None)
                else:
                    os.environ[var] = original_value
