class WebclipError(Exception):
    """Base domain error."""


class ConfigurationError(WebclipError):
    """Raised when configuration is invalid."""


class AdapterNotFoundError(WebclipError):
    """Raised when no adapter can process the target URL."""

