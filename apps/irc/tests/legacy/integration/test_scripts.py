"""Integration tests for shell scripts used in IRC.atl.chat deployment."""

import pytest
import subprocess
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import stat


class TestInitScript:
    """Test the init.sh script functionality."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure for testing init.sh."""
        # Copy essential files to temp directory
        project_files = ["scripts/init.sh", "env.example"]
        project_dirs = ["src/backend/unrealircd/conf", "src/backend/atheme/conf", "docs/examples/unrealircd/tls"]

        for file in project_files:
            src = Path(__file__).parent.parent.parent / file
            dst = tmp_path / file
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.exists():
                shutil.copy2(src, dst)

        for dir_name in project_dirs:
            src = Path(__file__).parent.parent.parent / dir_name
            dst = tmp_path / dir_name
            if src.exists():
                shutil.copytree(src, dst, dirs_exist_ok=True)

        # Create minimal template files if they don't exist
        unreal_template = tmp_path / "src/backend/unrealircd/conf/unrealircd.conf.template"
        atheme_template = tmp_path / "src/backend/atheme/conf/atheme.conf.template"

        if not unreal_template.exists():
            unreal_template.parent.mkdir(parents=True, exist_ok=True)
            unreal_template.write_text("""
me {
    name "${IRC_DOMAIN}";
    info "Test IRC Server";
};
admin {
    name "${IRC_ADMIN_NAME}";
    email "${IRC_ADMIN_EMAIL}";
};
listen {
    ip "*";
    port 6667;
};
""")

        if not atheme_template.exists():
            atheme_template.parent.mkdir(parents=True, exist_ok=True)
            atheme_template.write_text("""
serverinfo {
    name "${ATHEME_SERVER_NAME}";
    description "Test Services";
};
uplink "ircd" {
    host "${ATHEME_UPLINK_HOST}";
    port ${ATHEME_UPLINK_PORT};
    send_password "${ATHEME_SEND_PASSWORD}";
};
""")

        return tmp_path

    @pytest.mark.integration
    @pytest.mark.slow
    def test_init_script_creates_directories(self, temp_project):
        """Test that init.sh creates required directory structure."""
        init_script = temp_project / "scripts/init.sh"

        # Make script executable
        init_script.chmod(init_script.stat().st_mode | stat.S_IEXEC)

        # Create a minimal .env file
        env_file = temp_project / ".env"
        env_file.write_text("""IRC_DOMAIN=test.irc.chat
IRC_NETWORK_NAME="TestNet"
IRC_ADMIN_NAME="Test Admin"
IRC_ADMIN_EMAIL=admin@test.com
ATHEME_SERVER_NAME=services.test.irc.chat
ATHEME_UPLINK_HOST=localhost
ATHEME_UPLINK_PORT=6667
ATHEME_SEND_PASSWORD=testpass
""")

        # Run init.sh
        result = subprocess.run(
            [str(init_script)],
            cwd=temp_project,
            capture_output=True,
            text=True,
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )

        # Check that script ran successfully
        assert result.returncode == 0, f"Init script failed: {result.stderr}"

        # Check that required directories were created
        expected_dirs = [
            "data/unrealircd",
            "data/atheme",
            "data/letsencrypt",
            "logs/unrealircd",
            "logs/atheme",
            "src/backend/unrealircd/conf/tls",
        ]

        for dir_path in expected_dirs:
            full_path = temp_project / dir_path
            assert full_path.exists(), f"Directory {dir_path} was not created"
            assert full_path.is_dir(), f"{dir_path} is not a directory"

    @pytest.mark.integration
    def test_init_script_creates_env_file(self, temp_project):
        """Test that init.sh creates .env file from template."""
        init_script = temp_project / "scripts/init.sh"
        init_script.chmod(init_script.stat().st_mode | stat.S_IEXEC)

        # Remove any existing .env file
        env_file = temp_project / ".env"
        if env_file.exists():
            env_file.unlink()

        # Ensure env.example exists
        env_example = temp_project / "env.example"
        if not env_example.exists():
            env_example.write_text("""
IRC_DOMAIN=example.com
IRC_NETWORK_NAME=ExampleNet
""")

        # Run init.sh
        result = subprocess.run([str(init_script)], cwd=temp_project, capture_output=True, text=True)

        # Should succeed even without .env initially
        assert result.returncode == 0

        # Should create .env file from template
        assert env_file.exists(), ".env file should be created from template"

    @pytest.mark.integration
    def test_init_script_with_docker_available(self, temp_project):
        """Test init.sh works correctly when Docker is available."""
        init_script = temp_project / "scripts/init.sh"
        init_script.chmod(init_script.stat().st_mode | stat.S_IEXEC)

        # Create a minimal .env file
        env_file = temp_project / ".env"
        env_file.write_text("""IRC_DOMAIN=test.irc.chat
IRC_NETWORK_NAME="Test Network"
IRC_ADMIN_NAME="Test Admin"
IRC_ADMIN_EMAIL=admin@test.com
ATHEME_SERVER_NAME=services.test.irc.chat
ATHEME_UPLINK_HOST=localhost
ATHEME_UPLINK_PORT=6667
ATHEME_SEND_PASSWORD=testpass
""")

        result = subprocess.run([str(init_script)], cwd=temp_project, capture_output=True, text=True)

        # Should succeed when Docker is available
        assert result.returncode == 0
        assert "Docker is available" in result.stdout
        assert "SUCCESS" in result.stdout
        assert "Initialization completed successfully" in result.stdout

        # Verify directories were created
        assert (temp_project / "data").exists()
        assert (temp_project / "logs").exists()
        assert (temp_project / "data/unrealircd").exists()
        assert (temp_project / "data/atheme").exists()
        assert (temp_project / "logs/unrealircd").exists()
        assert (temp_project / "logs/atheme").exists()

    @pytest.mark.integration
    def test_init_script_config_file_generation(self, temp_project):
        """Test that init.sh generates configuration files from templates."""
        init_script = temp_project / "scripts/init.sh"
        init_script.chmod(init_script.stat().st_mode | stat.S_IEXEC)

        # Create .env file with test values
        env_file = temp_project / ".env"
        env_file.write_text("""IRC_DOMAIN=test.irc.chat
IRC_NETWORK_NAME="TestNet"
IRC_ADMIN_NAME="Test Admin"
IRC_ADMIN_EMAIL=admin@test.com
ATHEME_SERVER_NAME=services.test.irc.chat
ATHEME_UPLINK_HOST=localhost
ATHEME_UPLINK_PORT=6667
ATHEME_SEND_PASSWORD=testpass
""")

        # Run init.sh
        result = subprocess.run(
            [str(init_script)],
            cwd=temp_project,
            capture_output=True,
            text=True,
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )

        assert result.returncode == 0

        # Check that config files were generated
        unreal_config = temp_project / "src/backend/unrealircd/conf/unrealircd.conf"
        atheme_config = temp_project / "src/backend/atheme/conf/atheme.conf"

        if unreal_config.exists():
            content = unreal_config.read_text()
            assert "test.irc.chat" in content, "Domain should be substituted in UnrealIRCd config"

        if atheme_config.exists():
            content = atheme_config.read_text()
            assert "services.test.irc.chat" in content, "Server name should be substituted in Atheme config"


class TestPrepareConfigScript:
    """Test the prepare-config.sh script functionality."""

    @pytest.fixture
    def temp_project_with_templates(self, tmp_path):
        """Create temporary project with configuration templates."""
        # Copy the prepare-config.sh script
        script_src = Path(__file__).parent.parent.parent / "scripts/prepare-config.sh"
        script_dst = tmp_path / "scripts/prepare-config.sh"
        script_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(script_src, script_dst)
        script_dst.chmod(script_dst.stat().st_mode | stat.S_IEXEC)

        # Create template files
        unreal_template = tmp_path / "src/backend/unrealircd/conf/unrealircd.conf.template"
        atheme_template = tmp_path / "src/backend/atheme/conf/atheme.conf.template"

        unreal_template.parent.mkdir(parents=True, exist_ok=True)
        atheme_template.parent.mkdir(parents=True, exist_ok=True)

        unreal_template.write_text("""
me {
    name "${IRC_DOMAIN}";
    info "${IRC_NETWORK_NAME}";
};
admin {
    name "${IRC_ADMIN_NAME}";
    email "${IRC_ADMIN_EMAIL}";
};
""")

        atheme_template.write_text("""
serverinfo {
    name "${ATHEME_SERVER_NAME}";
    description "${ATHEME_NETNAME}";
};
""")

        return tmp_path

    @pytest.mark.integration
    def test_prepare_config_script_substitution(self, temp_project_with_templates):
        """Test that prepare-config.sh substitutes environment variables."""
        script = temp_project_with_templates / "scripts/prepare-config.sh"

        # Create .env file
        env_file = temp_project_with_templates / ".env"
        env_file.write_text("""IRC_DOMAIN=test.irc.chat
IRC_NETWORK_NAME="Test Network"
IRC_ADMIN_NAME="Test Admin"
IRC_ADMIN_EMAIL=admin@test.com
ATHEME_SERVER_NAME=services.test.irc.chat
ATHEME_NETNAME=TestNet
""")

        # Run the script
        result = subprocess.run(
            [str(script)],
            cwd=temp_project_with_templates,
            capture_output=True,
            text=True,
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )

        # Should succeed
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Check that config files were created with substituted values
        unreal_config = temp_project_with_templates / "src/backend/unrealircd/conf/unrealircd.conf"
        atheme_config = temp_project_with_templates / "src/backend/atheme/conf/atheme.conf"

        if unreal_config.exists():
            content = unreal_config.read_text()
            assert "test.irc.chat" in content
            assert "Test Network" in content

        if atheme_config.exists():
            content = atheme_config.read_text()
            assert "services.test.irc.chat" in content
            assert "TestNet" in content

    @pytest.mark.integration
    def test_prepare_config_script_without_env_file(self, temp_project_with_templates):
        """Test prepare-config.sh behavior without .env file."""
        script = temp_project_with_templates / "scripts/prepare-config.sh"

        # Remove any existing .env file
        env_file = temp_project_with_templates / ".env"
        if env_file.exists():
            env_file.unlink()

        result = subprocess.run([str(script)], cwd=temp_project_with_templates, capture_output=True, text=True)

        # Should succeed but show warnings
        assert result.returncode == 0
        # Script should handle missing .env gracefully

    @pytest.mark.integration
    def test_prepare_config_script_with_envsubst_available(self, temp_project_with_templates):
        """Test prepare-config.sh works correctly when envsubst is available."""
        script = temp_project_with_templates / "scripts/prepare-config.sh"

        # Create .env file with test values
        env_file = temp_project_with_templates / ".env"
        env_file.write_text("""IRC_DOMAIN=test.irc.chat
IRC_NETWORK_NAME="Test Network"
IRC_ADMIN_NAME="Test Admin"
IRC_ADMIN_EMAIL=admin@test.com
ATHEME_SERVER_NAME=services.test.irc.chat
ATHEME_NETNAME=TestNet
""")

        result = subprocess.run([str(script)], cwd=temp_project_with_templates, capture_output=True, text=True)

        # Should succeed when envsubst is available
        assert result.returncode == 0
        assert "All configuration files prepared successfully" in result.stdout

        # Verify configuration files were created with substituted values
        unrealircd_conf = temp_project_with_templates / "src/backend/unrealircd/conf/unrealircd.conf"
        atheme_conf = temp_project_with_templates / "src/backend/atheme/conf/atheme.conf"

        if unrealircd_conf.exists():
            content = unrealircd_conf.read_text()
            assert "test.irc.chat" in content
            assert "Test Network" in content

        if atheme_conf.exists():
            content = atheme_conf.read_text()
            assert "test.irc.chat" in content
            assert "TestNet" in content


class TestHealthCheckScript:
    """Test the health-check.sh script functionality."""

    @pytest.fixture
    def health_check_script(self, tmp_path):
        """Create a copy of the health-check.sh script for testing."""
        script_src = Path(__file__).parent.parent.parent / "scripts/health-check.sh"
        script_dst = tmp_path / "health-check.sh"
        shutil.copy2(script_src, script_dst)
        script_dst.chmod(script_dst.stat().st_mode | stat.S_IEXEC)
        return script_dst

    @pytest.mark.integration
    def test_health_check_success_with_open_port(self, health_check_script):
        """Test health check succeeds when port is open."""
        # Test with a known open port (like 22 for SSH if available, or skip)
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Try to bind to a port for testing
            sock.bind(("localhost", 0))
            port = sock.getsockname()[1]
            sock.listen(1)

            result = subprocess.run(
                [str(health_check_script)],
                cwd=health_check_script.parent,
                capture_output=True,
                text=True,
                env={**os.environ, "IRC_PORT": str(port)},
            )

            # Should succeed
            assert result.returncode == 0
            assert "SUCCESS" in result.stdout

        finally:
            sock.close()

    @pytest.mark.integration
    def test_health_check_failure_with_closed_port(self, health_check_script):
        """Test health check fails when port is closed."""
        # Use a definitely closed port
        result = subprocess.run(
            [str(health_check_script)],
            cwd=health_check_script.parent,
            capture_output=True,
            text=True,
            env={**os.environ, "IRC_PORT": "12345"},  # Hopefully closed port
        )

        # Should fail
        assert result.returncode != 0
        assert "FAILED" in result.stdout

    @pytest.mark.integration
    def test_health_check_with_custom_port(self, health_check_script):
        """Test health check with custom port from environment."""
        result = subprocess.run(
            [str(health_check_script)],
            cwd=health_check_script.parent,
            capture_output=True,
            text=True,
            env={**os.environ, "IRC_PORT": "9999"},  # Closed port
        )

        assert result.returncode != 0
        assert "port 9999" in result.stdout

    @pytest.mark.integration
    def test_health_check_with_netcat_available(self, health_check_script):
        """Test health check works correctly when nc/netcat are available."""
        # Test with a closed port using IRC_PORT environment variable
        result = subprocess.run(
            [str(health_check_script)],
            cwd=health_check_script.parent,
            capture_output=True,
            text=True,
            env={**os.environ, "IRC_PORT": "9999"},
        )

        # Should fail due to connection refused, not missing tools
        assert result.returncode != 0
        # Should not complain about missing nc/netcat
        assert "Neither 'nc' nor 'netcat' available" not in result.stdout
        assert "command not found" not in result.stderr

        # Should attempt to connect to the specified port
        assert "Checking UnrealIRCd health on port 9999" in result.stdout


class TestSSLManagerScript:
    """Test the ssl-manager.sh script functionality."""

    @pytest.fixture
    def ssl_manager_script(self, tmp_path):
        """Create a copy of the ssl-manager.sh script for testing."""
        script_src = Path(__file__).parent.parent.parent / "scripts/ssl-manager.sh"
        script_dst = tmp_path / "ssl-manager.sh"
        shutil.copy2(script_src, script_dst)
        script_dst.chmod(script_dst.stat().st_mode | stat.S_IEXEC)
        return script_dst

    @pytest.fixture
    def minimal_env_file(self, tmp_path):
        """Create a minimal .env file for SSL manager testing."""
        env_file = tmp_path / ".env"
        env_file.write_text("""
# Minimal SSL configuration for testing
SSL_EMAIL=test@example.com
SSL_DOMAIN=test.example.com
""")
        return env_file

    @pytest.mark.integration
    @pytest.mark.ssl
    def test_ssl_manager_help_command(self, ssl_manager_script, tmp_path):
        """Test that SSL manager shows help information."""
        # Create a minimal .env file in the project root (tmp_path.parent)
        env_file = tmp_path.parent / ".env"
        env_file.write_text("SSL_EMAIL=test@example.com\nSSL_DOMAIN=test.example.com\n")

        result = subprocess.run([str(ssl_manager_script), "--help"], cwd=tmp_path, capture_output=True, text=True)

        # The SSL manager script doesn't have --help, so it will fail, but shouldn't fail due to missing .env
        # Just check that it doesn't fail with the .env error
        assert ".env file not found" not in result.stderr

    @pytest.mark.integration
    @pytest.mark.ssl
    def test_ssl_manager_missing_env_file(self, ssl_manager_script, tmp_path):
        """Test SSL manager behavior when .env file is missing."""
        # Remove any existing .env file from the project root
        env_file = tmp_path.parent / ".env"
        if env_file.exists():
            env_file.unlink()

        result = subprocess.run([str(ssl_manager_script), "check"], cwd=tmp_path, capture_output=True, text=True)

        # Should fail when .env is missing
        assert result.returncode != 0
        assert ".env file not found" in result.stderr

    @pytest.mark.integration
    @pytest.mark.ssl
    def test_ssl_manager_invalid_command(self, ssl_manager_script, tmp_path):
        """Test SSL manager with invalid command."""
        # Create a minimal .env file in the project root (tmp_path.parent)
        env_file = tmp_path.parent / ".env"
        env_file.write_text("SSL_EMAIL=test@example.com\nSSL_DOMAIN=test.example.com\n")

        result = subprocess.run(
            [str(ssl_manager_script), "invalid_command"], cwd=tmp_path, capture_output=True, text=True
        )

        # Should fail (either due to invalid command or script logic)
        assert result.returncode != 0

    @pytest.mark.integration
    @pytest.mark.ssl
    @pytest.mark.slow
    def test_ssl_manager_check_command(self, ssl_manager_script, tmp_path):
        """Test SSL manager check command with minimal setup."""
        # Create a minimal .env file in the project root (tmp_path.parent)
        env_file = tmp_path.parent / ".env"
        env_file.write_text("SSL_EMAIL=test@example.com\nSSL_DOMAIN=test.example.com\n")

        result = subprocess.run([str(ssl_manager_script), "check"], cwd=tmp_path, capture_output=True, text=True)

        # Should complete (may show that certificates don't exist)
        # Just check that it doesn't fail due to missing .env
        assert ".env file not found" not in result.stderr


class TestScriptIntegration:
    """Test integration between scripts."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_init_and_prepare_config_integration(self, tmp_path):
        """Test that init.sh and prepare-config.sh work together."""
        # Copy both scripts
        for script_name in ["init.sh", "prepare-config.sh"]:
            src = Path(__file__).parent.parent.parent / f"scripts/{script_name}"
            dst = tmp_path / f"scripts/{script_name}"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            dst.chmod(dst.stat().st_mode | stat.S_IEXEC)

        # Create minimal project structure
        env_file = tmp_path / ".env"
        env_file.write_text("""IRC_DOMAIN=integration.test
IRC_NETWORK_NAME="Integration Test"
IRC_ADMIN_NAME="Integration Admin"
IRC_ADMIN_EMAIL=admin@integration.test
ATHEME_SERVER_NAME=services.integration.test
ATHEME_UPLINK_HOST=localhost
ATHEME_UPLINK_PORT=6667
ATHEME_SEND_PASSWORD=int_pass
""")

        # Run init.sh first
        init_script = tmp_path / "scripts/init.sh"
        result1 = subprocess.run([str(init_script)], cwd=tmp_path, capture_output=True, text=True)

        assert result1.returncode == 0, f"Init script failed: {result1.stderr}"

        # Then run prepare-config.sh
        config_script = tmp_path / "scripts/prepare-config.sh"
        result2 = subprocess.run([str(config_script)], cwd=tmp_path, capture_output=True, text=True)

        assert result2.returncode == 0, f"Config script failed: {result2.stderr}"

        # Verify integration worked
        unreal_config = tmp_path / "src/backend/unrealircd/conf/unrealircd.conf"
        if unreal_config.exists():
            content = unreal_config.read_text()
            assert "integration.test" in content
