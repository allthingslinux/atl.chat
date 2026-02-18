"""UnrealIRCd controller for testing.

Adapted from irctest's UnrealIRCd controller for our testing infrastructure.
"""

import contextlib
import fcntl
import functools
import shutil
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import ContextManager

from ..fixtures.docker_fixtures import DockerControllerMixin
from .atheme_controller import AthemeController
from .base_controllers import BaseServerController, DirectoryBasedController


def _filelock(path: Path) -> Callable[[], ContextManager]:
    """Alternative to multiprocessing.Lock that works with pytest-xdist"""

    @contextlib.contextmanager
    def f() -> Iterator[None]:
        with open(path, "a") as fd:
            fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
            yield

    return f


@functools.lru_cache
def _installed_version() -> int:
    """Get the installed UnrealIRCd version."""
    try:
        output = subprocess.check_output(["unrealircd", "-v"], universal_newlines=True)
        if "UnrealIRCd-5." in output:
            return 5
        elif "UnrealIRCd-6." in output:
            return 6
        else:
            # Default to version 6 features if we can't determine
            return 6
    except (subprocess.CalledProcessError, FileNotFoundError):
        # If unrealircd is not found or fails, assume version 6
        return 6


class UnrealircdController(BaseServerController, DirectoryBasedController, DockerControllerMixin):
    """Controller for managing UnrealIRCd instances during testing."""

    software_name = "UnrealIRCd"
    supported_sasl_mechanisms = {"PLAIN"}
    supports_sts = False
    services_controller_class = AthemeController

    extban_mute_char = "quiet" if _installed_version() >= 6 else "q"
    software_version = _installed_version()

    def __init__(self, test_config, container_fixture=None):
        super().__init__(test_config, container_fixture=container_fixture)

        # Set port from container if available
        if self.container:
            container_ports = self.get_container_ports()
            self.port = container_ports.get("6697/tcp", 6697)

    def create_config(self) -> None:
        """Create the configuration directory and basic files."""
        super().create_config()
        if self.directory:
            (self.directory / "server.conf").touch()

    def run(
        self,
        hostname: str,
        port: int,
        *,
        password: str | None = None,
        ssl: bool = False,
        run_services: bool = False,
        faketime: str | None = None,
    ) -> None:
        """Start the UnrealIRCd server using Docker container."""
        if self.container is None:
            raise RuntimeError("Container fixture not provided - this controller requires Docker")

        self.hostname = hostname

        # Copy real config files instead of generating them
        self._copy_real_config_files()

        # The container is already running via pytest-docker-tools
        # Get the actual mapped ports from the container
        container_ports = self.get_container_ports()
        self.port = container_ports.get("6697/tcp", port)
        if ssl:
            self.tls_port = container_ports.get("6697/tcp", port + 30)

        self.wait_for_container_ready()

        if run_services and self.services_controller_class:
            # For services, we'd need to get the services port from the real config
            # For now, skip services in Docker testing
            pass

    def _copy_real_config_files(self):
        """Copy the real UnrealIRCd configuration files for testing."""
        if not self.directory:
            return

        # Source directory with real configs
        source_dir = Path(__file__).parent.parent.parent / "src" / "backend" / "unrealircd" / "conf"

        # Copy all config files
        for config_file in source_dir.glob("*.conf"):
            shutil.copy2(config_file, self.directory / config_file.name)

        # Copy subdirectories
        for subdir in ["help", "aliases", "tls"]:
            if (source_dir / subdir).exists():
                shutil.copytree(source_dir / subdir, self.directory / subdir, dirs_exist_ok=True)

        # Copy other necessary files
        for pattern in ["*.list", "*.default.conf", "*.optional.conf"]:
            for file in source_dir.glob(pattern):
                shutil.copy2(file, self.directory / file.name)

    def kill_proc(self) -> None:
        """Kill the UnrealIRCd process."""
        if self.proc:
            self.proc.kill()
            try:
                self.proc.wait(5)  # wait for it to actually die
            except subprocess.TimeoutExpired:
                pass  # Already killed
            self.proc = None


def get_unrealircd_controller_class() -> type[UnrealircdController]:
    """Factory function to get the UnrealIRCd controller class."""
    return UnrealircdController
