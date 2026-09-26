class APIError(Exception):
    """Domain error returned to API clients as JSON."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        **extra: object,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = {"code": code, "message": message, **extra}


class ResetRefused(RuntimeError):
    """Raised when a reset would touch something other than the local dev database."""
