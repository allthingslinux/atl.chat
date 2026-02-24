"""IRC test client for testing IRC protocol compliance.

Adapted from irctest's client_mock.py for our testing infrastructure.
"""

import contextlib
import socket
import ssl
import time
from typing import Any

from ..irc_utils.message_parser import Message


class IRCTestClient:
    """Simple IRC client for testing purposes."""

    def __init__(self, name: str = "testclient", show_io: bool = False):
        self.name = name
        self.show_io = show_io
        self.sock: socket.socket | None = None
        self.connected = False
        self.buffer = ""
        self.messages: list[Message] = []

    def connect(self, hostname: str, port: int, use_ssl: bool = False) -> None:
        """Connect to IRC server."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(30)

        try:
            self.sock.connect((hostname, port))
            self.connected = True

            if use_ssl:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.sock = context.wrap_socket(self.sock)

        except (OSError, ssl.SSLError) as e:
            self.connected = False
            raise e

    def disconnect(self) -> None:
        """Disconnect from IRC server."""
        if self.sock:
            with contextlib.suppress(BaseException):
                self.sock.close()
        self.connected = False
        self.sock = None

    def sendLine(self, line: str) -> None:
        """Send a line to the server."""
        if not self.connected or not self.sock:
            raise RuntimeError("Not connected to server")

        if not line.endswith("\r\n"):
            line += "\r\n"

        self.sock.send(line.encode())

        if self.show_io:
            print(f"{time.time():.3f} C: {line.strip()}")

    def _recv_data(self, timeout: float = 1.0) -> str:
        """Receive data from socket with timeout."""
        if not self.connected or not self.sock:
            return ""

        self.sock.settimeout(timeout)
        try:
            data = self.sock.recv(4096).decode()
            if self.show_io and data:
                print(f"{time.time():.3f} S: {data.strip()}")
            return data
        except TimeoutError:
            return ""
        except OSError:
            self.connected = False
            return ""

    def getMessages(self, synchronize: bool = True) -> list[Message]:
        """Get all available messages from the server."""
        if synchronize:
            # Send a PING to synchronize
            self.sendLine("PING :sync")
            start_time = time.time()
            while time.time() - start_time < 5:  # Wait up to 5 seconds
                data = self._recv_data(0.1)
                if data:
                    self.buffer += data
                    if "PONG :sync" in self.buffer:
                        break
                time.sleep(0.01)

        # Get any remaining data
        data = self._recv_data(0.1)
        if data:
            self.buffer += data

        # Parse messages from buffer
        messages = []
        while "\r\n" in self.buffer:
            line, self.buffer = self.buffer.split("\r\n", 1)
            if line.strip():
                try:
                    msg = Message.parse(line)
                    messages.append(msg)
                except Exception:
                    # If parsing fails, continue - some servers send malformed messages
                    continue

        return messages

    def getMessage(self, **kwargs: Any) -> Message:
        """Get a single message, optionally filtered."""
        synchronize = kwargs.get("synchronize", True)
        filter_pred = kwargs.get("filter_pred")

        while True:
            messages = self.getMessages(synchronize=synchronize)
            for msg in messages:
                if not filter_pred or filter_pred(msg):
                    return msg

            if not self.connected:
                raise ConnectionClosed("Connection lost while waiting for message")

            time.sleep(0.01)


class ConnectionClosed(Exception):
    """Raised when the IRC connection is unexpectedly closed."""

    pass
