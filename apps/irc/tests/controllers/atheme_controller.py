"""Atheme services controller for testing.

Adapted from irctest's Atheme controller for our testing infrastructure.
"""

import shutil
from pathlib import Path

from .base_controllers import BaseServicesController, DirectoryBasedController


class AthemeController(BaseServicesController, DirectoryBasedController):
    """Controller for managing Atheme services during testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.services_hostname: str | None = None
        self.services_port: int | None = None

    def create_config(self) -> None:
        """Create the configuration directory and copy real config files."""
        super().create_config()

        if self.directory:
            # Source directory with real configs
            source_dir = Path(__file__).parent.parent.parent / "src" / "backend" / "atheme" / "conf"

            # Copy all config files (just like UnrealIRCd does)
            for config_file in source_dir.glob("*.conf"):
                shutil.copy2(config_file, self.directory / config_file.name)

            # For testing, we need to modify the uplink configuration
            # The production config has hardcoded values, but tests need dynamic ones
            # We'll update it in the run() method with the correct hostname/port

    def run(self, protocol: str, server_hostname: str, server_port: int) -> None:
        """Start the Atheme services."""
        if self.proc is not None:
            raise RuntimeError("Services already running")

        self.services_hostname = server_hostname
        self.services_port = server_port
        self.create_config()

        if self.directory:
            config_file = self.directory / "atheme.conf"

            # Update the config file with the correct server connection details
            if config_file.exists():
                content = config_file.read_text()
                # Replace the uplink configuration with test values
                import re

                content = re.sub(r'uplink "[^"]*" \{', 'uplink "test.server" {', content)
                content = re.sub(r'host = "[^"]*";', f'host = "{server_hostname}";', content)
                content = re.sub(r"port = \d+;", f"port = {server_port};", content)
                config_file.write_text(content)

            self.proc = self.execute(
                [
                    "atheme-services",
                    "-f",
                    config_file,
                ]
            )

    def wait_for_services(self) -> None:
        """Wait for Atheme services to be ready."""
        super().wait_for_services()


def get_atheme_controller_class() -> type[AthemeController]:
    """Factory function to get the Atheme controller class."""
    return AthemeController
