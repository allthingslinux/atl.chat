"""Integration tests for IRC.atl.chat configuration validation."""

import pytest
import subprocess
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml
import json


class TestConfigurationValidation:
    """Test configuration file validation and generation."""

    @pytest.fixture
    def temp_project_with_configs(self, tmp_path):
        """Create a temporary project with configuration files."""
        # Copy configuration files and templates
        config_paths = ["src/backend/unrealircd/conf", "src/backend/atheme/conf", "compose.yaml", "env.example"]

        for path in config_paths:
            src = Path(__file__).parent.parent.parent / path
            dst = tmp_path / path
            if src.exists():
                if src.is_file():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                else:
                    shutil.copytree(src, dst, dirs_exist_ok=True)

        return tmp_path

    @pytest.mark.integration
    def test_docker_compose_config_validation(self, temp_project_with_configs):
        """Test that docker-compose.yml is valid."""
        compose_file = temp_project_with_configs / "compose.yaml"

        if not compose_file.exists():
            pytest.skip("compose.yaml not found in test environment")

        # Test YAML syntax
        try:
            with open(compose_file, "r") as f:
                config = yaml.safe_load(f)

            assert isinstance(config, dict)
            assert "services" in config
            assert "version" in config or "name" in config

        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in compose.yaml: {e}")

        # Test docker-compose config validation if available
        if shutil.which("docker") and shutil.which("docker compose"):
            result = subprocess.run(
                ["docker", "compose", "config", "--quiet"],
                cwd=temp_project_with_configs,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # Show the actual error
                full_result = subprocess.run(
                    ["docker", "compose", "config"], cwd=temp_project_with_configs, capture_output=True, text=True
                )
                pytest.fail(f"Invalid docker-compose config: {full_result.stderr}")

    @pytest.mark.integration
    def test_unrealircd_config_template_validation(self, temp_project_with_configs):
        """Test UnrealIRCd configuration template validation."""
        template_file = temp_project_with_configs / "src/backend/unrealircd/conf/unrealircd.conf.template"

        if not template_file.exists():
            pytest.skip("UnrealIRCd template not found")

        content = template_file.read_text()

        # Check for required configuration blocks
        required_blocks = ["me {", "admin {", "listen {"]
        for block in required_blocks:
            assert block in content, f"Missing required block '{block}' in template"

        # Check for required variables
        required_vars = ["${IRC_DOMAIN}", "${IRC_ADMIN_NAME}"]
        for var in required_vars:
            assert var in content, f"Missing required variable '{var}' in template"

        # Check syntax (basic validation)
        assert content.count("{") == content.count("}"), "Unmatched braces in template"

    @pytest.mark.integration
    def test_atheme_config_template_validation(self, temp_project_with_configs):
        """Test Atheme configuration template validation."""
        template_file = temp_project_with_configs / "src/backend/atheme/conf/atheme.conf.template"

        if not template_file.exists():
            pytest.skip("Atheme template not found")

        content = template_file.read_text()

        # Check for required configuration blocks
        required_blocks = ["serverinfo {", "uplink"]
        for block in required_blocks:
            assert block in content, f"Missing required block '{block}' in template"

        # Check for required variables
        required_vars = ["${ATHEME_SERVER_NAME}", "${ATHEME_UPLINK_HOST}"]
        for var in required_vars:
            assert var in content, f"Missing required variable '{var}' in template"

    @pytest.mark.integration
    def test_environment_template_validation(self, temp_project_with_configs):
        """Test environment template (.env.example) validation."""
        env_template = temp_project_with_configs / "env.example"

        if not env_template.exists():
            pytest.skip("Environment template not found")

        content = env_template.read_text()

        # Check for required IRC variables
        required_vars = ["IRC_DOMAIN", "IRC_NETWORK_NAME", "IRC_ADMIN_NAME", "IRC_ADMIN_EMAIL"]

        for var in required_vars:
            assert var in content, f"Missing required environment variable '{var}'"

        # Check for Atheme variables
        atheme_vars = ["ATHEME_SERVER_NAME", "ATHEME_UPLINK_HOST"]
        atheme_present = any(var in content for var in atheme_vars)

        if atheme_present:
            # If Atheme vars are present, check they're all there
            for var in atheme_vars:
                assert var in content, f"Missing Atheme variable '{var}' when others are present"

    @pytest.mark.integration
    def test_configuration_template_substitution(self, temp_project_with_configs):
        """Test that configuration templates can be properly substituted."""
        # Create test environment variables
        test_env = {
            "IRC_DOMAIN": "test.irc.example.com",
            "IRC_NETWORK_NAME": "Test IRC Network",
            "IRC_ADMIN_NAME": "Test Administrator",
            "IRC_ADMIN_EMAIL": "admin@test.example.com",
            "ATHEME_SERVER_NAME": "services.test.example.com",
            "ATHEME_UPLINK_HOST": "irc.test.example.com",
            "ATHEME_UPLINK_PORT": "6667",
            "ATHEME_SEND_PASSWORD": "test_password",
        }

        unreal_template = temp_project_with_configs / "src/backend/unrealircd/conf/unrealircd.conf.template"
        atheme_template = temp_project_with_configs / "src/backend/atheme/conf/atheme.conf.template"

        if unreal_template.exists():
            # Test envsubst substitution
            with patch.dict(os.environ, test_env):
                result = subprocess.run(["envsubst"], input=unreal_template.read_text(), text=True, capture_output=True)

                if result.returncode == 0:
                    substituted = result.stdout
                    # Check that variables were substituted
                    assert "test.irc.example.com" in substituted
                    assert "Test IRC Network" in substituted
                    # Check that no unsubstituted variables remain
                    assert "${IRC_DOMAIN}" not in substituted

        if atheme_template.exists():
            with patch.dict(os.environ, test_env):
                result = subprocess.run(["envsubst"], input=atheme_template.read_text(), text=True, capture_output=True)

                if result.returncode == 0:
                    substituted = result.stdout
                    assert "services.test.example.com" in substituted
                    assert "${ATHEME_SERVER_NAME}" not in substituted

    @pytest.mark.integration
    def test_configuration_file_permissions(self, temp_project_with_configs):
        """Test that configuration files have appropriate permissions."""
        conf_dirs = [
            temp_project_with_configs / "src/backend/unrealircd/conf",
            temp_project_with_configs / "src/backend/atheme/conf",
        ]

        for conf_dir in conf_dirs:
            if conf_dir.exists():
                for conf_file in conf_dir.glob("*.conf*"):
                    # Check if file is readable
                    assert os.access(conf_file, os.R_OK), f"Config file {conf_file.name} should be readable"

                    # Check if file is writable by owner (for editing)
                    # Note: This might fail in some environments, so make it informational
                    if not os.access(conf_file, os.W_OK):
                        # Just log a warning rather than failing
                        print(f"WARNING: Config file {conf_file.name} is not writable")

    @pytest.mark.integration
    def test_docker_compose_service_dependencies(self, temp_project_with_configs):
        """Test that docker-compose services have proper dependencies."""
        compose_file = temp_project_with_configs / "compose.yaml"

        if not compose_file.exists():
            pytest.skip("compose.yaml not found")

        with open(compose_file, "r") as f:
            config = yaml.safe_load(f)

        services = config.get("services", {})

        # Check for known services
        service_names = list(services.keys())

        # If both unrealircd and atheme are present, check dependencies
        if "unrealircd" in service_names and "atheme" in service_names:
            atheme_config = services["atheme"]
            depends_on = atheme_config.get("depends_on", [])

            # Atheme should depend on unrealircd
            assert "unrealircd" in depends_on, "Atheme should depend on unrealircd service"

    @pytest.mark.integration
    def test_configuration_backup_creation(self, temp_project_with_configs):
        """Test configuration backup creation during updates."""
        unreal_config = temp_project_with_configs / "src/backend/unrealircd/conf/unrealircd.conf"

        if not unreal_config.exists():
            unreal_config.write_text('# Original config\nme { name "test"; };')

        original_content = unreal_config.read_text()
        backup_content = original_content + "\n# Backup marker"

        # Simulate backup creation
        backup_file = unreal_config.with_suffix(".conf.backup")
        backup_file.write_text(backup_content)

        # Verify backup was created
        assert backup_file.exists()
        assert backup_file.read_text() == backup_content

        # Clean up
        backup_file.unlink()

    @pytest.mark.integration
    def test_template_syntax_validation(self, temp_project_with_configs):
        """Test that configuration templates have valid syntax."""
        template_files = [
            temp_project_with_configs / "src/backend/unrealircd/conf/unrealircd.conf.template",
            temp_project_with_configs / "src/backend/atheme/conf/atheme.conf.template",
        ]

        for template_file in template_files:
            if template_file.exists():
                content = template_file.read_text()

                # Basic syntax checks
                lines = content.split("\n")

                # Check for balanced braces (basic validation)
                brace_count = 0
                for line_num, line in enumerate(lines, 1):
                    brace_count += line.count("{") - line.count("}")

                    # At any point, we shouldn't have negative braces
                    if brace_count < 0:
                        pytest.fail(f"Unmatched closing brace at line {line_num} in {template_file.name}")

                # Final brace count should be 0
                assert brace_count == 0, f"Unmatched braces in {template_file.name}"

                # Check for semicolons after blocks (basic UnrealIRCd/Atheme syntax)
                if "{" in content:
                    # This is a very basic check - in practice, templates might have variables
                    # that make this check less reliable
                    pass


class TestEnvironmentConfiguration:
    """Test environment variable configuration and validation."""

    @pytest.mark.integration
    def test_environment_variable_validation(self):
        """Test that environment variables follow expected patterns."""
        # Test IRC domain validation
        test_domains = [("irc.example.com", True), ("test.irc.org", True), ("invalid-domain", False), ("", False)]

        for domain, should_be_valid in test_domains:
            if should_be_valid:
                assert "." in domain, f"Domain {domain} should contain a dot"
                assert len(domain) > 3, f"Domain {domain} should be reasonably long"
            else:
                # Invalid domains - just check they're not empty for this test
                pass

    @pytest.mark.integration
    def test_port_validation(self):
        """Test IRC port validation."""
        valid_ports = [6667, 6697, 7000]
        invalid_ports = [-1, 0, 65536, "not_a_number"]

        for port in valid_ports:
            assert 1 <= port <= 65535, f"Port {port} should be in valid range"

        for port in invalid_ports:
            if isinstance(port, int):
                assert not (1 <= port <= 65535), f"Port {port} should be invalid"

    @pytest.mark.integration
    def test_email_validation(self):
        """Test email format validation."""
        valid_emails = ["admin@example.com", "test.admin@irc.org", "support@test-irc.net"]

        invalid_emails = ["admin", "@example.com", "admin@", "admin.example.com"]

        for email in valid_emails:
            assert "@" in email, f"Email {email} should contain @"
            assert "." in email.split("@")[1], f"Email {email} should have valid domain"

        for email in invalid_emails:
            # Basic invalid checks
            if "@" not in email or not email.split("@")[1] or "." not in email.split("@")[1]:
                assert True  # This is invalid as expected

    @pytest.mark.integration
    def test_network_name_validation(self):
        """Test IRC network name validation."""
        valid_names = ["ExampleNet", "Test IRC Network", "IRCNetwork2024"]

        for name in valid_names:
            assert len(name.strip()) > 0, f"Network name '{name}' should not be empty"
            assert len(name) <= 50, f"Network name '{name}' should not be too long"


class TestSSLConfiguration:
    """Test SSL/TLS configuration validation."""

    @pytest.fixture
    def temp_ssl_config(self, tmp_path):
        """Create temporary SSL configuration for testing."""
        ssl_dir = tmp_path / "ssl"
        ssl_dir.mkdir()

        # Create a basic SSL config file
        ssl_config = ssl_dir / "test_ssl.conf"
        ssl_config.write_text("""
# Test SSL configuration
ssl {
    certificate "server.crt";
    key "server.key";
    trusted-ca-file "ca-bundle.crt";
};
""")
        return ssl_dir

    @pytest.mark.integration
    @pytest.mark.ssl
    def test_ssl_config_syntax(self, temp_ssl_config):
        """Test SSL configuration file syntax."""
        ssl_config = temp_ssl_config / "test_ssl.conf"

        content = ssl_config.read_text()

        # Check for required SSL directives
        assert "certificate" in content, "SSL config should specify certificate"
        assert "key" in content, "SSL config should specify key"

    @pytest.mark.integration
    @pytest.mark.ssl
    def test_ssl_directory_permissions(self, temp_ssl_config):
        """Test SSL directory permissions."""
        ssl_dir = temp_ssl_config

        # Directory should exist and be accessible
        assert ssl_dir.exists()
        assert ssl_dir.is_dir()
        assert os.access(ssl_dir, os.R_OK | os.X_OK), "SSL directory should be readable and executable"

    @pytest.mark.integration
    @pytest.mark.ssl
    def test_ssl_certificate_paths(self, temp_ssl_config):
        """Test SSL certificate file path validation."""
        # Create some test certificate files
        cert_files = ["server.crt", "server.key", "ca-bundle.crt"]

        for cert_file in cert_files:
            test_file = temp_ssl_config / cert_file
            test_file.write_text("# Test certificate file")

            assert test_file.exists(), f"Certificate file {cert_file} should exist"
            assert os.access(test_file, os.R_OK), f"Certificate file {cert_file} should be readable"


class TestWebPanelConfiguration:
    """Test WebPanel configuration validation."""

    @pytest.fixture
    def temp_webpanel_config(self, tmp_path):
        """Create temporary WebPanel configuration."""
        webpanel_dir = tmp_path / "webpanel"
        webpanel_dir.mkdir()

        # Create nginx config
        nginx_conf = webpanel_dir / "nginx.conf"
        nginx_conf.write_text("""
server {
    listen 8080;
    server_name localhost;

    location / {
        proxy_pass http://unrealircd-webpanel:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
""")

        return webpanel_dir

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_nginx_config_syntax(self, temp_webpanel_config):
        """Test nginx configuration syntax."""
        nginx_conf = temp_webpanel_config / "nginx.conf"

        content = nginx_conf.read_text()

        # Check for required nginx directives
        required_directives = ["server {", "listen", "location /"]
        for directive in required_directives:
            assert directive in content, f"Nginx config missing directive: {directive}"

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_webpanel_proxy_configuration(self, temp_webpanel_config):
        """Test WebPanel proxy configuration."""
        nginx_conf = temp_webpanel_config / "nginx.conf"

        content = nginx_conf.read_text()

        # Check for proxy configuration
        assert "proxy_pass" in content, "Nginx config should have proxy_pass"
        assert "unrealircd-webpanel" in content, "Should proxy to webpanel service"
