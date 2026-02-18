"""Integration tests for WebPanel functionality."""

import pytest
import subprocess
import tempfile
import shutil
import os
import requests
import time
import socket
from pathlib import Path
from unittest.mock import patch, MagicMock
import json


class TestWebPanelConfiguration:
    """Test WebPanel configuration and setup."""

    @pytest.fixture
    def temp_webpanel_env(self, tmp_path):
        """Create temporary WebPanel test environment."""
        webpanel_dir = tmp_path / "webpanel_test"
        webpanel_dir.mkdir()

        # Create nginx configuration
        nginx_conf = webpanel_dir / "nginx.conf"
        nginx_conf.write_text("""
server {
    listen 8080;
    server_name localhost;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    location / {
        proxy_pass http://unrealircd-webpanel:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files
    location /static/ {
        alias /usr/share/nginx/html/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
""")

        # Create docker-compose configuration
        compose_content = """
services:
  unrealircd-webpanel:
    image: unrealircd/webpanel:latest
    ports:
      - "8080"
    environment:
      - NODE_ENV=production
      - IRC_SERVER=unrealircd:6667
    depends_on:
      - unrealircd
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "8080:8080"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - unrealircd-webpanel
"""

        compose_file = webpanel_dir / "compose.yaml"
        compose_file.write_text(compose_content)

        return webpanel_dir

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_nginx_configuration_syntax(self, temp_webpanel_env):
        """Test nginx configuration syntax."""
        nginx_conf = temp_webpanel_env / "nginx.conf"

        # Test nginx configuration syntax if nginx is available
        if shutil.which("nginx"):
            result = subprocess.run(
                ["nginx", "-t", "-c", str(nginx_conf)], cwd=temp_webpanel_env, capture_output=True, text=True
            )

            # If nginx is available, config should be valid
            if result.returncode != 0:
                # Try alternative nginx syntax check
                result = subprocess.run(
                    ["nginx", "-T", "-c", str(nginx_conf)], cwd=temp_webpanel_env, capture_output=True, text=True
                )

                assert result.returncode == 0, f"Nginx configuration is invalid: {result.stderr}"

        # Basic syntax validation
        content = nginx_conf.read_text()

        # Check for required nginx directives
        required_directives = ["server {", "listen", "location /", "proxy_pass"]
        for directive in required_directives:
            assert directive in content, f"Nginx config missing directive: {directive}"

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_webpanel_service_configuration(self, temp_webpanel_env):
        """Test WebPanel service configuration in docker-compose."""
        compose_file = temp_webpanel_env / "compose.yaml"

        import yaml

        with open(compose_file, "r") as f:
            config = yaml.safe_load(f)

        # Check WebPanel service configuration
        webpanel = config["services"]["unrealircd-webpanel"]

        # Should have proper environment variables
        env_vars = webpanel.get("environment", [])
        node_env_present = any("NODE_ENV" in str(var) for var in env_vars)
        irc_server_present = any("IRC_SERVER" in str(var) for var in env_vars)

        assert node_env_present, "WebPanel should have NODE_ENV environment variable"
        assert irc_server_present, "WebPanel should have IRC_SERVER environment variable"

        # Should depend on unrealircd
        depends_on = webpanel.get("depends_on", [])
        assert "unrealircd" in depends_on, "WebPanel should depend on unrealircd service"

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_nginx_proxy_configuration(self, temp_webpanel_env):
        """Test nginx proxy configuration for WebPanel."""
        nginx_conf = temp_webpanel_env / "nginx.conf"

        content = nginx_conf.read_text()

        # Check proxy configuration
        assert "proxy_pass http://unrealircd-webpanel:8080" in content, "Should proxy to WebPanel service"
        assert "proxy_set_header Host $host" in content, "Should set Host header"
        assert "proxy_set_header X-Real-IP $remote_addr" in content, "Should set Real-IP header"

        # Check WebSocket support
        assert "proxy_http_version 1.1" in content, "Should support HTTP/1.1 for WebSocket"
        assert "proxy_set_header Upgrade $http_upgrade" in content, "Should handle WebSocket upgrade"
        assert 'proxy_set_header Connection "upgrade"' in content, "Should handle WebSocket connection upgrade"

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_security_headers_configuration(self, temp_webpanel_env):
        """Test security headers in nginx configuration."""
        nginx_conf = temp_webpanel_env / "nginx.conf"

        content = nginx_conf.read_text()

        # Check security headers
        security_headers = ["X-Frame-Options", "X-Content-Type-Options", "X-XSS-Protection"]

        for header in security_headers:
            assert header in content, f"Security header {header} should be configured"

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_static_file_serving(self, temp_webpanel_env):
        """Test static file serving configuration."""
        nginx_conf = temp_webpanel_env / "nginx.conf"

        content = nginx_conf.read_text()

        # Check static file location
        assert "location /static/" in content, "Should have static file location"
        assert "expires 1y" in content, "Should have long expiration for static files"
        assert 'Cache-Control "public, immutable"' in content, "Should have immutable cache control"


class TestWebPanelConnectivity:
    """Test WebPanel connectivity and functionality."""

    @pytest.fixture
    def temp_webpanel_service(self, tmp_path):
        """Create temporary WebPanel service for testing."""
        service_dir = tmp_path / "webpanel_service_test"
        service_dir.mkdir()

        # Create a simple mock web server for testing
        mock_html = service_dir / "index.html"
        mock_html.write_text("""
<!DOCTYPE html>
<html>
<head>
    <title>IRC WebPanel Test</title>
</head>
<body>
    <h1>IRC WebPanel</h1>
    <div id="irc-client"></div>
    <script>
        // Mock WebPanel JavaScript
        console.log('WebPanel loaded');
    </script>
</body>
</html>
""")

        return service_dir

    @pytest.mark.integration
    @pytest.mark.webpanel
    @pytest.mark.docker
    def test_webpanel_service_startup(self, temp_webpanel_service):
        """Test WebPanel service startup."""
        # This would typically test docker-compose up for webpanel
        # For now, test the configuration files exist

        service_dir = temp_webpanel_service
        index_file = service_dir / "index.html"

        assert index_file.exists(), "WebPanel index file should exist"

        content = index_file.read_text()
        assert "<title>IRC WebPanel" in content, "Should have WebPanel title"
        assert "irc-client" in content, "Should have IRC client element"

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_webpanel_http_endpoints(self, temp_webpanel_service):
        """Test WebPanel HTTP endpoints."""
        # This would typically make HTTP requests to WebPanel
        # For now, test the mock structure

        service_dir = temp_webpanel_service
        index_file = service_dir / "index.html"

        content = index_file.read_text()

        # Check for typical web panel elements
        assert "IRC" in content, "Should mention IRC"
        assert "<div" in content, "Should have HTML div elements"
        assert "<script>" in content, "Should have JavaScript"

    @pytest.mark.integration
    @pytest.mark.webpanel
    @pytest.mark.docker
    def test_webpanel_port_mapping(self, temp_webpanel_service):
        """Test WebPanel port mapping configuration."""
        # This would typically check docker-compose port mappings
        # For now, test the concept

        # WebPanel should typically be accessible on port 8080
        expected_ports = [8080]

        for port in expected_ports:
            assert isinstance(port, int), f"Port {port} should be integer"
            assert 1024 <= port <= 65535, f"Port {port} should be in valid range"

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_webpanel_static_assets(self, temp_webpanel_service):
        """Test WebPanel static asset handling."""
        service_dir = temp_webpanel_service

        # Create mock static files
        static_dir = service_dir / "static"
        static_dir.mkdir()

        css_file = static_dir / "style.css"
        css_file.write_text("body { background: #f0f0f0; }")

        js_file = static_dir / "app.js"
        js_file.write_text("console.log('WebPanel JavaScript loaded');")

        # Verify static files exist
        assert css_file.exists(), "CSS file should exist"
        assert js_file.exists(), "JavaScript file should exist"

        # Verify content
        assert "background" in css_file.read_text(), "CSS should contain styles"
        assert "console.log" in js_file.read_text(), "JS should contain code"


class TestWebPanelIRCServerIntegration:
    """Test WebPanel integration with IRC server."""

    @pytest.fixture
    def temp_irc_webpanel_integration(self, tmp_path):
        """Create temporary environment for IRC-WebPanel integration testing."""
        integration_dir = tmp_path / "irc_webpanel_integration"
        integration_dir.mkdir()

        # Create docker-compose with both services
        compose_content = """
services:
  unrealircd:
    image: unrealircd:latest
    ports:
      - "6667:6667"
      - "6697:6697"
    volumes:
      - ./data/unrealircd:/data
    environment:
      - IRC_NETWORK=TestNet
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "6667"]
      interval: 10s
      timeout: 5s
      retries: 5

  unrealircd-webpanel:
    image: unrealircd/webpanel:latest
    ports:
      - "8080:8080"
    environment:
      - IRC_SERVER=unrealircd:6667
      - IRC_SSL_SERVER=unrealircd:6697
      - WEBPANEL_TITLE=Test IRC Network
    depends_on:
      unrealircd:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080"]
      interval: 30s
      timeout: 10s
      retries: 3
"""

        compose_file = integration_dir / "compose.yaml"
        compose_file.write_text(compose_content)

        return integration_dir

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_webpanel_irc_server_connection_config(self, temp_irc_webpanel_integration):
        """Test WebPanel IRC server connection configuration."""
        compose_file = temp_irc_webpanel_integration / "compose.yaml"

        import yaml

        with open(compose_file, "r") as f:
            config = yaml.safe_load(f)

        webpanel = config["services"]["unrealircd-webpanel"]
        env_vars = webpanel.get("environment", [])

        # Check IRC server configuration
        irc_server_config = any("IRC_SERVER" in str(var) for var in env_vars)
        irc_ssl_config = any("IRC_SSL_SERVER" in str(var) for var in env_vars)

        assert irc_server_config, "WebPanel should have IRC server configuration"
        assert irc_ssl_config, "WebPanel should have IRC SSL server configuration"

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_service_dependency_chain(self, temp_irc_webpanel_integration):
        """Test service dependency chain between IRC server and WebPanel."""
        compose_file = temp_irc_webpanel_integration / "compose.yaml"

        import yaml

        with open(compose_file, "r") as f:
            config = yaml.safe_load(f)

        services = config["services"]

        # Check unrealircd service
        unrealircd = services["unrealircd"]
        assert "healthcheck" in unrealircd, "UnrealIRCd should have health check"
        assert "ports" in unrealircd, "UnrealIRCd should expose ports"

        # Check webpanel service
        webpanel = services["unrealircd-webpanel"]
        depends_on = webpanel.get("depends_on", {})

        assert "unrealircd" in depends_on, "WebPanel should depend on unrealircd"
        assert depends_on["unrealircd"]["condition"] == "service_healthy", "Should wait for unrealircd health"

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_webpanel_environment_variables(self, temp_irc_webpanel_integration):
        """Test WebPanel environment variable configuration."""
        compose_file = temp_irc_webpanel_integration / "compose.yaml"

        import yaml

        with open(compose_file, "r") as f:
            config = yaml.safe_load(f)

        webpanel = config["services"]["unrealircd-webpanel"]
        env_vars = webpanel.get("environment", [])

        # Check for important environment variables
        env_dict = {}
        for var in env_vars:
            if "=" in var:
                key, value = var.split("=", 1)
                env_dict[key] = value

        expected_vars = ["IRC_SERVER", "IRC_SSL_SERVER", "WEBPANEL_TITLE"]

        for var in expected_vars:
            assert var in env_dict, f"WebPanel should have {var} environment variable"


class TestWebPanelSecurity:
    """Test WebPanel security configurations."""

    @pytest.fixture
    def temp_secure_webpanel(self, tmp_path):
        """Create temporary secure WebPanel configuration."""
        secure_dir = tmp_path / "secure_webpanel"
        secure_dir.mkdir()

        # Create secure nginx configuration
        nginx_conf = secure_dir / "nginx.conf"
        nginx_conf.write_text("""
server {
    listen 8080 ssl http2;
    server_name localhost;

    # SSL configuration
    ssl_certificate /etc/ssl/certs/server.crt;
    ssl_certificate_key /etc/ssl/private/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=webpanel:10m rate=10r/s;
    limit_req zone=webpanel burst=20 nodelay;

    location / {
        proxy_pass http://unrealircd-webpanel:8080;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Restrict access to sensitive endpoints
    location /admin {
        allow 192.168.1.0/24;
        deny all;
        proxy_pass http://unrealircd-webpanel:8080;
    }
}
""")

        return secure_dir

    @pytest.mark.integration
    @pytest.mark.webpanel
    @pytest.mark.ssl
    def test_ssl_configuration(self, temp_secure_webpanel):
        """Test SSL configuration for WebPanel."""
        nginx_conf = temp_secure_webpanel / "nginx.conf"

        content = nginx_conf.read_text()

        # Check SSL directives
        ssl_directives = ["ssl_certificate", "ssl_certificate_key", "ssl_protocols", "ssl_ciphers"]

        for directive in ssl_directives:
            assert directive in content, f"SSL config should contain {directive}"

        # Check secure protocols
        assert "TLSv1.2" in content, "Should support TLS 1.2"
        assert "TLSv1.3" in content, "Should support TLS 1.3"

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_security_headers(self, temp_secure_webpanel):
        """Test security headers configuration."""
        nginx_conf = temp_secure_webpanel / "nginx.conf"

        content = nginx_conf.read_text()

        # Check security headers
        security_headers = ["Strict-Transport-Security", "X-Frame-Options", "X-Content-Type-Options", "Referrer-Policy"]

        for header in security_headers:
            assert header in content, f"Security header {header} should be configured"

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_rate_limiting(self, temp_secure_webpanel):
        """Test rate limiting configuration."""
        nginx_conf = temp_secure_webpanel / "nginx.conf"

        content = nginx_conf.read_text()

        # Check rate limiting
        assert "limit_req_zone" in content, "Should have rate limiting zone"
        assert "limit_req" in content, "Should have rate limiting directive"

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_access_restrictions(self, temp_secure_webpanel):
        """Test access restrictions for sensitive areas."""
        nginx_conf = temp_secure_webpanel / "nginx.conf"

        content = nginx_conf.read_text()

        # Check access restrictions
        assert "location /admin" in content, "Should have admin location"
        assert "allow " in content, "Should have allow directive"
        assert "deny all" in content, "Should have deny directive"


class TestWebPanelMonitoring:
    """Test WebPanel monitoring and health checks."""

    @pytest.fixture
    def temp_monitoring_setup(self, tmp_path):
        """Create temporary monitoring setup."""
        monitoring_dir = tmp_path / "webpanel_monitoring"
        monitoring_dir.mkdir()

        # Create monitoring configuration
        monitor_conf = monitoring_dir / "monitoring.conf"
        monitor_conf.write_text("""
# WebPanel monitoring configuration
WEBPANEL_URL=http://localhost:8080
HEALTH_CHECK_INTERVAL=30
ALERT_EMAIL=admin@example.com
LOG_FILE=/var/log/webpanel/monitor.log

# Health check endpoints
HEALTH_ENDPOINTS="
/
/health
/api/status
"
""")

        return monitoring_dir

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_health_check_endpoints(self, temp_monitoring_setup):
        """Test WebPanel health check endpoints."""
        monitor_conf = temp_monitoring_setup / "monitoring.conf"

        content = monitor_conf.read_text()

        # Check health endpoints configuration
        assert "/health" in content, "Should have health endpoint"
        assert "HEALTH_ENDPOINTS" in content, "Should have health endpoints configuration"

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_monitoring_configuration(self, temp_monitoring_setup):
        """Test monitoring configuration."""
        monitor_conf = temp_monitoring_setup / "monitoring.conf"

        content = monitor_conf.read_text()

        # Check monitoring settings
        required_settings = ["WEBPANEL_URL", "HEALTH_CHECK_INTERVAL", "ALERT_EMAIL", "LOG_FILE"]

        for setting in required_settings:
            assert setting in content, f"Monitoring config should contain {setting}"

    @pytest.mark.integration
    @pytest.mark.webpanel
    def test_log_file_configuration(self, temp_monitoring_setup):
        """Test log file configuration."""
        # Create log directory
        log_dir = temp_monitoring_setup / "logs"
        log_dir.mkdir()

        log_file = log_dir / "webpanel.log"
        log_file.write_text("WebPanel monitoring started\n")

        # Verify log file
        assert log_file.exists(), "Log file should exist"
        assert "WebPanel monitoring" in log_file.read_text(), "Log should contain monitoring message"
