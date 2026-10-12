"""Optional local Jev AI collaboration layer.

This package must never be imported by detector/fusion modules as a dependency.
"""

from x_sentinel.jev_ai.client import (
    JevAIClient,
    JevAIConfigurationError,
    JevAIConnectionError,
    JevAIDisabledError,
    JevAIError,
    JevAIHTTPError,
    JevAIResponseError,
    JevAITimeout,
    JevAIUnavailable,
)
from x_sentinel.jev_ai.schemas import (
    JevContext,
    JevMode,
    JevRequest,
    JevResponse,
    JevStatus,
    JevStatusResponse,
)

__all__ = [
    "JevAIClient",
    "JevAIConfigurationError",
    "JevAIConnectionError",
    "JevAIDisabledError",
    "JevAIError",
    "JevAIHTTPError",
    "JevAIResponseError",
    "JevAITimeout",
    "JevAIUnavailable",
    "JevContext",
    "JevMode",
    "JevRequest",
    "JevResponse",
    "JevStatus",
    "JevStatusResponse",
]
