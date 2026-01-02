"""Custom exceptions for update-alternatives-tui.

This module defines a hierarchy of exceptions for precise error handling
throughout the application. Each exception includes contextual information
to aid debugging and provide meaningful error messages to users.
"""

from dataclasses import dataclass, field
from typing import Any


class UpdateAlternativesError(Exception):
    """Base exception for all update-alternatives-tui errors.
    
    All custom exceptions in this package inherit from this class,
    allowing for broad exception catching when needed.
    
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
    """Raised when data validation fails.
    
    This is used for validating user input, model data, and
    configuration values.
    """
    
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
        super().__init__(
            f"{field} cannot be empty",
            field=field,
            value=""
        )


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
    """Raised when command execution times out.
    
    Note: Named CommandTimeoutError to avoid conflict with built-in TimeoutError.
    """
    
    def __init__(self, command: list[str], timeout: int) -> None:
        super().__init__(
            f"Command timed out after {timeout} seconds",
            command=command,
            context={"timeout": timeout}
        )


# ============================================================================
# Service Exceptions
# ============================================================================

class ServiceError(UpdateAlternativesError):
    """Base exception for service-layer errors."""
    pass


class AlternativeNotFoundError(ServiceError):
    """Raised when an alternative is not found."""
    
    def __init__(self, name: str) -> None:
        super().__init__(
            f"Alternative not found: {name}",
            context={"alternative_name": name}
        )
        self.name = name


class AlternativeExistsError(ServiceError):
    """Raised when trying to create an alternative that already exists."""
    
    def __init__(self, name: str, path: str) -> None:
        super().__init__(
            f"Alternative already exists: {path} in {name}",
            context={"alternative_name": name, "path": path}
        )
        self.name = name
        self.path = path


class InvalidAlternativeError(ServiceError):
    """Raised when alternative data is invalid."""
    
    def __init__(self, name: str, reason: str) -> None:
        super().__init__(
            f"Invalid alternative '{name}': {reason}",
            context={"alternative_name": name, "reason": reason}
        )
        self.name = name
        self.reason = reason


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
            # Truncate long output
            context["output_preview"] = output[:200] + "..." if len(output) > 200 else output
        super().__init__(message, context)
        self.output = output
        self.line_number = line_number


class InvalidFormatError(ParseError):
    """Raised when output format is unexpected or invalid."""
    
    def __init__(self, expected: str, actual: str = "") -> None:
        super().__init__(
            f"Invalid format: expected {expected}",
            context={"expected_format": expected, "actual": actual[:100] if actual else ""}
        )


# ============================================================================
# Configuration Exceptions
# ============================================================================

class ConfigError(UpdateAlternativesError):
    """Raised when configuration is invalid or cannot be loaded."""
    pass


class ConfigFileNotFoundError(ConfigError):
    """Raised when configuration file is not found."""
    
    def __init__(self, path: str) -> None:
        super().__init__(
            f"Configuration file not found: {path}",
            context={"path": path}
        )
        self.path = path


# ============================================================================
# UI Exceptions
# ============================================================================

class UIError(UpdateAlternativesError):
    """Base exception for UI-related errors."""
    pass


class WidgetError(UIError):
    """Raised when a widget operation fails."""
    
    def __init__(self, widget: str, operation: str, reason: str = "") -> None:
        message = f"Widget error in {widget} during {operation}"
        if reason:
            message = f"{message}: {reason}"
        super().__init__(
            message,
            context={"widget": widget, "operation": operation}
        )


# ============================================================================
# Error Collection
# ============================================================================

@dataclass
class ErrorCollection:
    """Collection of multiple errors for batch operations.
    
    Useful when performing batch operations where multiple
    items may fail, and we want to report all failures.
    """
    errors: list[UpdateAlternativesError] = field(default_factory=list)
    
    def add(self, error: UpdateAlternativesError) -> None:
        """Add an error to the collection."""
        self.errors.append(error)
    
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    def __len__(self) -> int:
        return len(self.errors)
    
    def __iter__(self):
        return iter(self.errors)
    
    def raise_if_errors(self) -> None:
        """Raise a combined error if there are any errors."""
        if self.has_errors():
            messages = [str(e) for e in self.errors]
            raise UpdateAlternativesError(
                f"Multiple errors occurred ({len(self.errors)} total)",
                context={"errors": messages}
            )
