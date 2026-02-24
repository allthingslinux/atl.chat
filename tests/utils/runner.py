"""Test runner utilities and exceptions.

Adapted from irctest's runner module for handling test execution and exceptions.
"""

from typing import Any


class NotImplementedByController(Exception):
    """Raised when a controller doesn't implement a required feature."""

    pass


class CapabilityNotSupported(Exception):
    """Raised when a capability is not supported by the server."""

    pass


class OptionalSaslMechanismNotSupported(Exception):
    """Raised when an optional SASL mechanism is not supported."""

    pass


def skipUnlessHasMechanism(mechanism: str) -> Any:
    """Decorator to skip tests if SASL mechanism is not supported."""

    def decorator(f: Any) -> Any:
        def newf(self: Any, *args: Any, **kwargs: Any) -> Any:
            if mechanism not in self.controller.supported_sasl_mechanisms:
                raise OptionalSaslMechanismNotSupported(mechanism)
            return f(self, *args, **kwargs)

        return newf

    return decorator


def xfailIf(condition: Any, reason: str) -> Any:
    """Decorator to mark tests as expected to fail under certain conditions."""

    def decorator(f: Any) -> Any:
        def newf(self: Any, *args: Any, **kwargs: Any) -> Any:
            if condition(self, *args, **kwargs):
                try:
                    return f(self, *args, **kwargs)
                except Exception:
                    import pytest

                    pytest.xfail(reason)
                    raise AssertionError()  # make mypy happy
            else:
                return f(self, *args, **kwargs)

        return newf

    return decorator


def xfailIfSoftware(names: Any, reason: str) -> Any:
    """Decorator to mark tests as expected to fail for specific software."""

    def pred(testcase: Any, *args: Any, **kwargs: Any) -> bool:
        return testcase.controller.software_name in names

    return xfailIf(pred, reason)
