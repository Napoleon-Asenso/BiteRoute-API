"""Custom application exceptions and error classification."""

from typing import Any


class AppException(Exception):
    """Base exception class for all domain and operational application errors."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code: int = status_code
        self.code: str = code
        self.message: str = message


class BadRequestException(AppException):
    """Exception raised for client input syntax or clamping violations (HTTP 400)."""

    def __init__(self, message: str, code: str = "BAD_REQUEST") -> None:
        super().__init__(status_code=400, code=code, message=message)


class MalformedIdentifierException(BadRequestException):
    """Exception raised when a path identifier fails UUIDv4 syntax validation (HTTP 400)."""

    def __init__(self, identifier_value: str) -> None:
        message = f"Value '{identifier_value}' is not a valid UUIDv4 identifier."
        super().__init__(message=message, code="MALFORMED_IDENTIFIER")


class NotFoundException(AppException):
    """Exception raised when an entity cannot be found (HTTP 404)."""

    def __init__(self, entity_name: str, entity_id: str | Any) -> None:
        message = f"{entity_name} with id '{entity_id}' was not found."
        super().__init__(status_code=404, code="RESOURCE_NOT_FOUND", message=message)


class UnprocessableEntityException(AppException):
    """Exception raised for semantic or payload structure failures (HTTP 422)."""

    def __init__(self, message: str, code: str = "UNPROCESSABLE_ENTITY") -> None:
        super().__init__(status_code=422, code=code, message=message)


class RateLimitExceededException(AppException):
    """Exception raised when a client IP quota has been exhausted (HTTP 429)."""

    def __init__(self, retry_after: int) -> None:
        message = f"Too many requests. Please wait {retry_after} seconds before retrying."
        super().__init__(status_code=429, code="RATE_LIMIT_EXCEEDED", message=message)
        self.retry_after: int = retry_after


class ConflictException(AppException):
    """Exception raised when an operation conflicts with existing entity state (HTTP 409)."""

    def __init__(self, message: str, code: str = "CONFLICT") -> None:
        super().__init__(status_code=409, code=code, message=message)
