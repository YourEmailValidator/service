class EmailFormatError(Exception):
    """Raised when the email format is invalid."""


class DisposableEmailError(Exception):
    """Raised when the email domain is disposable."""


class EmailMXRecordError(Exception):
    """Raised when the email domain has no valid MX records."""
