"""Custom exceptions for update-alternatives-tui.

This module defines a hierarchy of exceptions for precise error handling.
Each exception includes contextual information for debugging.

Exception Hierarchy:
    UpdateAlternativesError (base)
    ├── ValidationError
    │   ├── EmptyValueError
    │   └── InvalidValueError
    ├── ExecutionError
    │   ├── CommandNotFoundError
    │   ├── PermissionDeniedError
    │   └── CommandTimeoutError
    └── ParseError
        └── InvalidFormatError
"""

from typing import Any

from .constants import FORMAT_ERROR_PREVIEW_MAX_LENGTH, OUTPUT_PREVIEW_MAX_LENGTH


class UpdateAlternativesError(Exception):
    """Base exception for all update-alternatives-tui errors.
    
    Attributes:
        message: Human-readable error description
        context: Additional contextual information for debugging
    """
    
    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        self.message = message
        self.context = context or {}
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.context:
            ctx_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.message} ({ctx_str})"
        return self.message
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r}, context={self.context!r})"


# ============================================================================
# Validation Exceptions
# ============================================================================

class ValidationError(UpdateAlternativesError):
    """Raised when data validation fails."""
    
    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        **kwargs: Any
    ) -> None:
        context = kwargs.pop("context", {})
        if field:
            context["field"] = field
        if value is not None:
            context["value"] = value
        super().__init__(message, context)
        self.field = field
        self.value = value


class EmptyValueError(ValidationError):
    """Raised when a required value is empty or missing."""
    
    def __init__(self, field: str) -> None:
        super().__init__(f"{field} cannot be empty", field=field, value="")


class InvalidValueError(ValidationError):
    """Raised when a value is invalid."""
    
    def __init__(self, field: str, value: Any, reason: str = "") -> None:
        message = f"Invalid value for {field}: {value!r}"
        if reason:
            message = f"{message} - {reason}"
        super().__init__(message, field=field, value=value)


# ============================================================================
# Execution Exceptions
# ============================================================================

class ExecutionError(UpdateAlternativesError):
    """Raised when command execution fails."""
    
    def __init__(
        self,
        message: str,
        command: list[str] | None = None,
        return_code: int | None = None,
        stdout: str = "",
        stderr: str = "",
        **kwargs: Any
    ) -> None:
        context = kwargs.pop("context", {})
        if command:
            context["command"] = " ".join(command)
        if return_code is not None:
            context["return_code"] = return_code
        super().__init__(message, context)
        self.command = command
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr


class CommandNotFoundError(ExecutionError):
    """Raised when update-alternatives command is not found."""
    
    def __init__(self, command: str = "update-alternatives") -> None:
        super().__init__(
            f"Command not found: {command}",
            command=[command],
            return_code=-1
        )


class PermissionDeniedError(ExecutionError):
    """Raised when permission is denied for an operation."""
    
    def __init__(self, operation: str, command: list[str] | None = None) -> None:
        super().__init__(
            f"Permission denied: {operation}. Try running with sudo.",
            command=command,
            return_code=1
        )


class CommandTimeoutError(ExecutionError):
    """Raised when command execution times out."""
    
    def __init__(self, command: list[str], timeout: int) -> None:
        super().__init__(
            f"Command timed out after {timeout} seconds",
            command=command,
            context={"timeout": timeout}
        )


# ============================================================================
# Parser Exceptions
# ============================================================================

class ParseError(UpdateAlternativesError):
    """Raised when parsing command output fails."""
    
    def __init__(
        self,
        message: str,
        output: str = "",
        line_number: int | None = None,
        **kwargs: Any
    ) -> None:
        context = kwargs.pop("context", {})
        if line_number is not None:
            context["line_number"] = line_number
        if output:
            if len(output) > OUTPUT_PREVIEW_MAX_LENGTH:
                context["output_preview"] = output[:OUTPUT_PREVIEW_MAX_LENGTH] + "..."
            else:
                context["output_preview"] = output
        super().__init__(message, context)
        self.output = output
        self.line_number = line_number


class InvalidFormatError(ParseError):
    """Raised when output format is unexpected or invalid."""
    
    def __init__(self, expected: str, actual: str = "") -> None:
        actual_preview = actual[:FORMAT_ERROR_PREVIEW_MAX_LENGTH] if actual else ""
        super().__init__(
            f"Invalid format: expected {expected}",
            context={"expected_format": expected, "actual": actual_preview}
        )
