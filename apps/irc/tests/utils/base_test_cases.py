"""Base test case classes for IRC testing.

Adapted from irctest's cases.py for comprehensive IRC protocol testing.
"""

from __future__ import annotations

import contextlib
import functools
import time
from collections.abc import Callable, Container, Hashable, Iterable, Iterator
from typing import (
    Any,
    Generic,
    TypeVar,
    cast,
)

import pytest

from ..controllers.base_controllers import BaseServerController, TestCaseControllerConfig
from ..irc_utils.message_parser import Message
from .irc_test_client import IRCTestClient


class ConnectionClosed(Exception):
    """Raised when the IRC connection is unexpectedly closed"""

    pass


class ChannelJoinException(Exception):
    """Raised when joining a channel fails"""

    def __init__(self, code: str, params: list[str]):
        super().__init__(f"Failed to join channel ({code}): {params}")
        self.code = code
        self.params = params


# Channel join failure numerics from RFC 1459/2812
CHANNEL_JOIN_FAIL_NUMERICS = frozenset(
    [
        "403",  # ERR_NOSUCHCHANNEL
        "405",  # ERR_TOOMANYCHANNELS
        "471",  # ERR_CHANNELISFULL
        "472",  # ERR_UNKNOWNMODE
        "473",  # ERR_INVITEONLYCHAN
        "474",  # ERR_BANNEDFROMCHAN
        "475",  # ERR_BADCHANNELKEY
        "476",  # ERR_BADCHANMASK
        "477",  # ERR_NOCHANMODES
        "485",  # ERR_UNIQOPPRIVSNEEDED
        "494",  # ERR_OWNMODE
        "500",  # ERR_NOSUCHCHANNEL (some implementations)
    ]
)

# Type variables for generic test cases
TController = TypeVar("TController", bound=BaseServerController)
TClientName = TypeVar("TClientName", bound=Hashable | int)


def retry(f: Callable[..., Any]) -> Callable[..., Any]:
    """Retry the function if it raises ConnectionClosed; as a workaround for flaky
    connection, such as::

        1: connects to server.
        1 -> S: NICK foo
        1 -> S: USER username * * :Realname
        S -> 1: :My.Little.Server NOTICE * :*** Found your hostname (cached)
        S -> 1: :My.Little.Server NOTICE * :*** Checking Ident
        S -> 1: :My.Little.Server NOTICE * :*** No Ident response
        S -> 1: ERROR :Closing Link: cpu-pool.com (Use a different port)
    """

    @functools.wraps(f)
    def newf(*args: Any, **kwargs: Any) -> Any:
        try:
            return f(*args, **kwargs)
        except ConnectionClosed:
            time.sleep(1)
            return f(*args, **kwargs)

    return newf


class _IRCTestCase(Generic[TController]):
    """Base class for test cases.

    It implements various `assert*` method that look like unittest's,
    but is actually based on the `assert` statement so derived classes are
    pytest-style rather than unittest-style.

    It also calls setUp() and tearDown() like unittest would.
    """

    # Will be set by conftest.py
    controllerClass: type[TController] | None = None
    show_io: bool = False

    controller: TController

    __new__ = object.__new__  # pytest won't collect Generic subclasses otherwise

    @staticmethod
    def config() -> TestCaseControllerConfig:
        """Some configuration to pass to the controllers.
        For example, Oragono only enables its MySQL support if
        config()["chathistory"]=True.
        """
        return TestCaseControllerConfig()

    def setUp(self, controller=None) -> None:
        if controller is not None:
            self.controller = controller
        elif hasattr(self, "controller") and self.controller is not None:
            # Controller was already injected by autouse fixture
            pass
        elif self.controllerClass is not None:
            self.controller = self.controllerClass(self.config())
        if self.show_io:
            print("---- new test ----")

    def tearDown(self) -> None:
        pass

    def setup_method(self, method: Callable[..., Any]) -> None:
        self.setUp()

    def teardown_method(self, method: Callable[..., Any]) -> None:
        self.tearDown()

    def assertMessageMatch(
        self,
        msg: Message,
        command: str | Any | None = None,
        params: list[str | None | Any] | None = None,
        target: str | None = None,
        tags: dict[str | Any, str | Any | None] | None = None,
        nick: str | None = None,
        fail_msg: str | None = None,
        extra_format: tuple = (),
        prefix: None | str | Any = None,
        **kwargs: Any,
    ) -> None:
        """Helper for partially comparing a message.

        Takes the message as first arguments, and comparisons to be made
        as keyword arguments.

        Uses pattern matching on the params argument.
        """
        error = self.messageDiffers(
            msg,
            command=command,
            params=params,
            target=target,
            tags=tags,
            nick=nick,
            fail_msg=fail_msg,
            extra_format=extra_format,
            prefix=prefix,
            **kwargs,
        )
        if error:
            raise AssertionError(error)

    def messageEqual(
        self,
        msg: Message,
        command: str | Any | None = None,
        params: list[str | None | Any] | None = None,
        **kwargs: Any,
    ) -> bool:
        """Boolean negation of `messageDiffers` (returns a boolean,
        not an optional string)."""
        return not self.messageDiffers(msg, command=command, params=params, **kwargs)

    def messageDiffers(
        self,
        msg: Message,
        command: str | None | Any = None,
        params: list[str | None | Any] | None = None,
        target: str | None = None,
        tags: dict[str | Any, str | Any | None] | None = None,
        nick: str | None = None,
        fail_msg: str | None = None,
        extra_format: tuple = (),
        prefix: None | str | Any = None,
        **kwargs: Any,
    ) -> str | None:
        """Returns an error message if the message doesn't match the given arguments,
        or None if it matches."""
        for key, value in kwargs.items():
            if getattr(msg, key) != value:
                fail_msg = fail_msg or "expected {param} to be {expects}, got {got}: {msg}"
                return fail_msg.format(
                    *extra_format,
                    got=getattr(msg, key),
                    expects=value,
                    param=key,
                    msg=msg,
                )

        if command is not None and not self._match_string(msg.command, command):
            fail_msg = fail_msg or "expected command to match {expects}, got {got}: {msg}"
            return fail_msg.format(*extra_format, got=msg.command, expects=command, msg=msg)

        if prefix is not None and not self._match_string(msg.prefix, prefix):
            fail_msg = fail_msg or "expected prefix to match {expects}, got {got}: {msg}"
            return fail_msg.format(*extra_format, got=msg.prefix, expects=prefix, msg=msg)

        if params is not None and not self._match_list(list(msg.params), params):
            fail_msg = fail_msg or "expected params to match {expects}, got {got}: {msg}"
            return fail_msg.format(*extra_format, got=msg.params, expects=params, msg=msg)

        if tags is not None and not self._match_dict(msg.tags, tags):
            fail_msg = fail_msg or "expected tags to match {expects}, got {got}: {msg}"
            return fail_msg.format(*extra_format, got=msg.tags, expects=tags, msg=msg)

        if nick is not None:
            got_nick = msg.prefix.split("!")[0] if msg.prefix else None
            if nick != got_nick:
                fail_msg = fail_msg or "expected nick to be {expects}, got {got} instead: {msg}"
                return fail_msg.format(*extra_format, got=got_nick, expects=nick, msg=msg)

        return None

    def _match_string(self, got: str | None, expected: str | Any) -> bool:
        """Match a string against expected value (supports wildcards)."""
        if hasattr(expected, "match"):
            # It's a pattern object
            return expected.match(got) if got else False
        return got == expected

    def _match_list(self, got: list[str], expected: list[str | None | Any]) -> bool:
        """Match a list against expected pattern."""
        if len(got) != len(expected):
            return False

        for g, e in zip(got, expected, strict=False):
            if e is None:
                continue  # None means we don't care about this parameter
            if hasattr(e, "match"):
                if not e.match(g):
                    return False
            elif g != e:
                return False

        return True

    def _match_dict(self, got: dict[str, str], expected: dict[str | Any, str | Any | None]) -> bool:
        """Match a dict against expected pattern."""
        for key, expected_value in expected.items():
            if hasattr(key, "match"):
                # Pattern key - check if any key matches
                found = False
                for got_key in got:
                    if key.match(got_key):
                        if expected_value is None:
                            found = True
                            break
                        elif hasattr(expected_value, "match"):
                            if expected_value.match(got.get(got_key, "")):
                                found = True
                                break
                        elif got.get(got_key) == expected_value:
                            found = True
                            break
                if not found:
                    return False
            # Exact key match
            elif expected_value is None:
                if key not in got:
                    return False
            elif hasattr(expected_value, "match"):
                if not expected_value.match(got.get(key, "")):
                    return False
            elif got.get(key) != expected_value:
                return False

        return True

    def assertIn(
        self,
        member: Any,
        container: Iterable[Any] | Container[Any],
        msg: str | None = None,
        fail_msg: str | None = None,
        extra_format: tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, item=member, list=container, msg=msg)
        assert member in container, msg

    def assertNotIn(
        self,
        member: Any,
        container: Iterable[Any] | Container[Any],
        msg: str | None = None,
        fail_msg: str | None = None,
        extra_format: tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, item=member, list=container, msg=msg)
        assert member not in container, msg

    def assertEqual(
        self,
        got: Any,
        expects: Any,
        msg: Any = None,
        fail_msg: str | None = None,
        extra_format: tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        assert got == expects, msg

    def assertNotEqual(
        self,
        got: Any,
        expects: Any,
        msg: Any = None,
        fail_msg: str | None = None,
        extra_format: tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        assert got != expects, msg

    def assertGreater(
        self,
        got: Any,
        expects: Any,
        msg: Any = None,
        fail_msg: str | None = None,
        extra_format: tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        assert got > expects, msg

    def assertGreaterEqual(
        self,
        got: Any,
        expects: Any,
        msg: Any = None,
        fail_msg: str | None = None,
        extra_format: tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        assert got >= expects, msg

    def assertLess(
        self,
        got: Any,
        expects: Any,
        msg: Any = None,
        fail_msg: str | None = None,
        extra_format: tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        assert got < expects, msg

    def assertLessEqual(
        self,
        got: Any,
        expects: Any,
        msg: Any = None,
        fail_msg: str | None = None,
        extra_format: tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        assert got <= expects, msg

    def assertTrue(
        self,
        got: Any,
        msg: Any = None,
        fail_msg: str | None = None,
        extra_format: tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, msg=msg)
        assert got, msg

    def assertFalse(
        self,
        got: Any,
        msg: Any = None,
        fail_msg: str | None = None,
        extra_format: tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, msg=msg)
        assert not got, msg

    @contextlib.contextmanager
    def assertRaises(self, exception: type[Exception]) -> Iterator[None]:
        with pytest.raises(exception):
            yield


class BaseServerTestCase(_IRCTestCase[BaseServerController], Generic[TClientName]):
    """Basic class for server tests. Handles spawning a server and exchanging
    messages with it."""

    show_io: bool  # set by conftest.py

    password: str | None = None
    ssl = False
    server_support: dict[str, str | None] | None
    run_services = False

    faketime: str | None = None
    """If not None and the controller supports it and libfaketime is available,
    runs the server using faketime and this value set as the $FAKETIME env variable.
    Tests must check ``self.controller.faketime_enabled`` is True before
    relying on this."""

    __new__ = object.__new__  # pytest won't collect Generic[] subclasses otherwise

    def setUp(self) -> None:
        super().setUp()
        self.server_support = None
        (self.hostname, self.port) = self.controller.get_hostname_and_port()
        self.controller.run(
            self.hostname,
            self.port,
            password=self.password,
            ssl=self.ssl,
            run_services=self.run_services,
            faketime=self.faketime,
        )
        self.clients: dict[TClientName, IRCTestClient] = {}

    def tearDown(self) -> None:
        if hasattr(self, "controller") and self.controller is not None:
            self.controller.kill()
        for client in list(self.clients):
            self.removeClient(client)

    def addClient(self, name: TClientName | None = None, show_io: bool | None = None) -> TClientName:
        """Connects a client to the server and adds it to the dict.
        If 'name' is not given, uses the lowest unused non-negative integer."""
        self.controller.wait_for_port()
        if self.run_services:
            self.controller.wait_for_services()
        if not name:
            used_ids: list[int] = [int(name) for name in self.clients if isinstance(name, (int, str))]
            new_name = max(used_ids + [0]) + 1
            name = cast(TClientName, new_name)
        show_io = show_io if show_io is not None else self.show_io
        self.clients[name] = IRCTestClient(name=name, show_io=show_io)
        self.clients[name].connect(self.hostname, self.port, use_ssl=getattr(self, "ssl", False))
        return name

    def removeClient(self, name: TClientName) -> None:
        """Disconnects the client, without QUIT."""
        if name in self.clients:
            self.clients[name].disconnect()
            del self.clients[name]

    def getMessages(self, client: TClientName, **kwargs: Any) -> list[Message]:
        if kwargs.get("synchronize", True):
            time.sleep(self.controller.sync_sleep_time)
        return self.clients[client].getMessages(**kwargs)

    def getMessage(self, client: TClientName, **kwargs: Any) -> Message:
        if kwargs.get("synchronize", True):
            time.sleep(self.controller.sync_sleep_time)
        return self.clients[client].getMessage(**kwargs)

    def getRegistrationMessage(self, client: TClientName) -> Message:
        """Filter notices, do not send pings."""
        while True:
            msg = self.getMessage(
                client,
                synchronize=False,
                filter_pred=lambda m: m.command not in ("NOTICE", "001"),  # RPL_WELCOME
            )
            if msg.command == "PING":
                # Hi Unreal
                self.sendLine(client, "PONG :" + msg.params[0])
            else:
                return msg

    def sendLine(self, client: TClientName, line: str | bytes) -> None:
        return self.clients[client].sendLine(line)

    def getCapLs(self, client: TClientName, as_list: bool = False) -> list[str] | dict[str, str | None]:
        """Waits for a CAP LS block, parses all CAP LS messages, and return
        the dict capabilities, with their values.

        If as_list is given, returns the raw list (ie. key/value not split)
        in case the order matters (but it shouldn't)."""
        caps = []
        while True:
            m = self.getRegistrationMessage(client)
            self.assertMessageMatch(m, command="CAP")
            self.assertEqual(m.params[1], "LS", fail_msg="Expected CAP * LS, got {got}")
            if m.params[2] == "*":
                caps.extend(m.params[3].split())
            else:
                caps.extend(m.params[2].split())
                if not as_list:
                    return self._cap_list_to_dict(caps)
                return caps

    def _cap_list_to_dict(self, caps: list[str]) -> dict[str, str | None]:
        """Convert capability list to dictionary."""
        result = {}
        for cap in caps:
            if "=" in cap:
                key, value = cap.split("=", 1)
                result[key] = value
            else:
                result[cap] = None
        return result

    def assertDisconnected(self, client: TClientName) -> None:
        try:
            self.getMessages(client)
            self.getMessages(client)
        except (OSError, ConnectionClosed):
            if client in self.clients:
                del self.clients[client]
            return
        else:
            raise AssertionError("Client not disconnected.")

    def skipToWelcome(self, client: TClientName) -> list[Message]:
        """Skip to the point where we are registered
        <https://tools.ietf.org/html/rfc2812#section-3.1>
        """
        result = []
        while True:
            m = self.getMessage(client, synchronize=False)
            result.append(m)
            if m.command == "001":
                return result
            elif m.command == "PING":
                # Hi, Unreal
                self.sendLine(client, "PONG :" + m.params[0])

    def requestCapabilities(
        self,
        client: TClientName,
        capabilities: list[str],
        skip_if_cap_nak: bool = False,
    ) -> None:
        self.sendLine(client, "CAP REQ :{}".format(" ".join(capabilities)))
        m = self.getRegistrationMessage(client)
        try:
            self.assertMessageMatch(m, command="CAP", fail_msg="Expected CAP ACK, got: {msg}")
            self.assertEqual(m.params[1], "ACK", m, fail_msg="Expected CAP ACK, got: {msg}")
        except AssertionError:
            if skip_if_cap_nak:
                raise runner.CapabilityNotSupported(" or ".join(capabilities))
            else:
                raise

    def authenticateClient(self, client: TClientName, account: str, password: str) -> None:
        self.sendLine(client, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(client)
        self.assertMessageMatch(m, command="AUTHENTICATE", params=["+"])
        self.sendLine(client, self._sasl_plain_blob(account, password))
        m = self.getRegistrationMessage(client)
        self.assertIn(m.command, ["900", "903"], str(m))

    def _sasl_plain_blob(self, account: str, password: str) -> str:
        """Create SASL PLAIN authentication blob."""
        import base64

        auth_string = f"{account}\x00{account}\x00{password}"
        return base64.b64encode(auth_string.encode()).decode()

    @retry
    def connectClient(
        self,
        nick: str,
        name: TClientName | None = None,
        capabilities: list[str] | None = None,
        skip_if_cap_nak: bool = False,
        show_io: bool | None = None,
        account: str | None = None,
        password: str | None = None,
        ident: str = "username",
    ) -> TClientName:
        """Connections a new client, does the cap negotiation
        and connection registration, and skips to the end of the MOTD.
        Returns the client name."""
        client = self.addClient(name, show_io=show_io)
        if capabilities:
            self.sendLine(client, "CAP LS 302")
            self.getCapLs(client)
            self.requestCapabilities(client, capabilities, skip_if_cap_nak)
        if password is not None:
            if "sasl" not in (capabilities or ()):
                raise ValueError("Used 'password' option without sasl capability")
            self.authenticateClient(client, account or nick, password)

        self.sendLine(client, f"NICK {nick}")
        self.sendLine(client, "USER %s * * :Realname" % (ident,))
        if capabilities:
            self.sendLine(client, "CAP END")

        welcome = self.skipToWelcome(client)
        self.sendLine(client, "PING foo")

        # Skip all that happy welcoming stuff
        self.server_support = {}
        while True:
            m = self.getMessage(client)
            if m.command == "PONG":
                break
            elif m.command == "005":
                for param in m.params[1:-1]:
                    if "=" in param:
                        (key, value) = param.split("=", 1)
                        self.server_support[key] = value
                    else:
                        self.server_support[param] = None
            welcome.append(m)

        self.targmax: dict[str, str | None] = dict(  # type: ignore[assignment]
            item.split(":", 1) for item in (self.server_support.get("TARGMAX") or "").split(",") if item
        )

        return client

    def joinClient(self, client: TClientName, channel: str) -> None:
        self.sendLine(client, f"JOIN {channel}")
        received = {m.command for m in self.getMessages(client)}
        self.assertIn(
            "366",
            received,
            fail_msg="Join to {} failed, {item} is not in the set of received responses: {list}",
            extra_format=(channel,),
        )

    def joinChannel(self, client: TClientName, channel: str) -> None:
        self.sendLine(client, f"JOIN {channel}")
        # wait until we see them join the channel
        joined = False
        while not joined:
            for msg in self.getMessages(client):
                if msg.command == "JOIN" and len(msg.params) > 0 and msg.params[0].lower() == channel.lower():
                    joined = True
                    break
                elif msg.command in CHANNEL_JOIN_FAIL_NUMERICS:
                    raise ChannelJoinException(msg.command, msg.params)


# Import runner here to avoid circular imports
from . import runner
