"""Tests for update_alternatives_tui.exceptions module.

Tests cover:
- Base exception class (UpdateAlternativesError)
- Validation exceptions
- Execution exceptions
- Service exceptions
- Parser exceptions
- Configuration exceptions
- UI exceptions
- ErrorCollection utility
"""

from __future__ import annotations

import pytest

from update_alternatives_tui.exceptions import (
    # Base
    UpdateAlternativesError,
    # Validation
    ValidationError,
    EmptyValueError,
    InvalidValueError,
    # Execution
    ExecutionError,
    CommandNotFoundError,
    PermissionDeniedError,
    CommandTimeoutError,
    # Service
    ServiceError,
    AlternativeNotFoundError,
    AlternativeExistsError,
    InvalidAlternativeError,
    # Parser
    ParseError,
    InvalidFormatError,
    # Config
    ConfigError,
    ConfigFileNotFoundError,
    # UI
    UIError,
    WidgetError,
    # Collection
    ErrorCollection,
)


# ============================================================================
# Base Exception Tests
# ============================================================================


class TestUpdateAlternativesError:
    """Tests for the base exception class."""

    def test_basic_creation(self) -> None:
        """Test basic exception creation."""
        error = UpdateAlternativesError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.context == {}

    def test_with_context(self) -> None:
        """Test exception with context."""
        error = UpdateAlternativesError(
            "Failed operation",
            context={"key": "value", "count": 42}
        )
        assert "key='value'" in str(error)
        assert "count=42" in str(error)
        assert error.context["key"] == "value"

    def test_repr(self) -> None:
        """Test repr output."""
        error = UpdateAlternativesError("error msg", context={"x": 1})
        repr_str = repr(error)
        assert "UpdateAlternativesError" in repr_str
        assert "error msg" in repr_str

    def test_is_exception(self) -> None:
        """Test that it's a proper exception."""
        error = UpdateAlternativesError("test")
        assert isinstance(error, Exception)
        
        # Can be raised and caught
        with pytest.raises(UpdateAlternativesError):
            raise error

    def test_inheritance_chain(self) -> None:
        """Test exception inheritance chain."""
        error = UpdateAlternativesError("test")
        assert isinstance(error, Exception)
        assert isinstance(error, BaseException)


# ============================================================================
# Validation Exception Tests
# ============================================================================


class TestValidationError:
    """Tests for ValidationError."""

    def test_basic_creation(self) -> None:
        """Test basic creation."""
        error = ValidationError("Invalid input")
        assert "Invalid input" in str(error)
        assert isinstance(error, UpdateAlternativesError)

    def test_with_field_and_value(self) -> None:
        """Test with field and value."""
        error = ValidationError(
            "Value out of range",
            field="priority",
            value=-1
        )
        assert error.field == "priority"
        assert error.value == -1
        assert "field='priority'" in str(error)

    def test_inheritance(self) -> None:
        """Test inheritance chain."""
        error = ValidationError("test")
        assert isinstance(error, UpdateAlternativesError)


class TestEmptyValueError:
    """Tests for EmptyValueError."""

    def test_creation(self) -> None:
        """Test error creation."""
        error = EmptyValueError("name")
        assert "name" in str(error)
        assert "cannot be empty" in str(error)
        assert error.field == "name"
        assert error.value == ""

    def test_different_fields(self) -> None:
        """Test with different field names."""
        fields = ["path", "link", "priority", "alternative"]
        for field in fields:
            error = EmptyValueError(field)
            assert field in str(error)


class TestInvalidValueError:
    """Tests for InvalidValueError."""

    def test_basic_creation(self) -> None:
        """Test basic creation."""
        error = InvalidValueError("priority", -5)
        assert "priority" in str(error)
        assert "-5" in str(error)
        assert error.field == "priority"
        assert error.value == -5

    def test_with_reason(self) -> None:
        """Test with reason."""
        error = InvalidValueError("path", "relative/path", "must be absolute")
        assert "must be absolute" in str(error)

    def test_with_various_types(self) -> None:
        """Test with various value types."""
        # String value
        error1 = InvalidValueError("name", "")
        assert error1.value == ""
        
        # List value
        error2 = InvalidValueError("args", [1, 2, 3])
        assert error2.value == [1, 2, 3]
        
        # None value
        error3 = InvalidValueError("required", None)
        assert error3.value is None


# ============================================================================
# Execution Exception Tests
# ============================================================================


class TestExecutionError:
    """Tests for ExecutionError."""

    def test_basic_creation(self) -> None:
        """Test basic creation."""
        error = ExecutionError("Command failed")
        assert "Command failed" in str(error)
        assert isinstance(error, UpdateAlternativesError)

    def test_with_all_details(self) -> None:
        """Test with all details."""
        error = ExecutionError(
            "Command failed",
            command=["update-alternatives", "--set", "editor"],
            return_code=1,
            stdout="",
            stderr="Permission denied"
        )
        assert error.command == ["update-alternatives", "--set", "editor"]
        assert error.return_code == 1
        assert error.stdout == ""
        assert error.stderr == "Permission denied"
        assert "command=" in str(error)

    def test_context_includes_command_string(self) -> None:
        """Test that context includes command as string."""
        error = ExecutionError(
            "Failed",
            command=["cmd", "arg1", "arg2"]
        )
        assert "cmd arg1 arg2" in str(error)


class TestCommandNotFoundError:
    """Tests for CommandNotFoundError."""

    def test_default_command(self) -> None:
        """Test with default command."""
        error = CommandNotFoundError()
        assert "update-alternatives" in str(error)
        assert "not found" in str(error)
        assert error.return_code == -1

    def test_custom_command(self) -> None:
        """Test with custom command."""
        error = CommandNotFoundError("custom-cmd")
        assert "custom-cmd" in str(error)


class TestPermissionDeniedError:
    """Tests for PermissionDeniedError."""

    def test_creation(self) -> None:
        """Test error creation."""
        error = PermissionDeniedError("set editor")
        assert "Permission denied" in str(error)
        assert "set editor" in str(error)
        assert "sudo" in str(error).lower()

    def test_with_command(self) -> None:
        """Test with command details."""
        error = PermissionDeniedError(
            "set editor",
            command=["update-alternatives", "--set", "editor", "/usr/bin/vim"]
        )
        assert error.command is not None
        assert error.return_code == 1


class TestCommandTimeoutError:
    """Tests for CommandTimeoutError."""

    def test_creation(self) -> None:
        """Test error creation."""
        error = CommandTimeoutError(
            command=["long-running", "command"],
            timeout=30
        )
        assert "30" in str(error)
        assert "timed out" in str(error).lower()
        assert error.context["timeout"] == 30


# ============================================================================
# Service Exception Tests
# ============================================================================


class TestServiceError:
    """Tests for ServiceError."""

    def test_inheritance(self) -> None:
        """Test inheritance chain."""
        error = ServiceError("Service failed")
        assert isinstance(error, UpdateAlternativesError)


class TestAlternativeNotFoundError:
    """Tests for AlternativeNotFoundError."""

    def test_creation(self) -> None:
        """Test error creation."""
        error = AlternativeNotFoundError("nonexistent")
        assert "nonexistent" in str(error)
        assert "not found" in str(error).lower()
        assert error.name == "nonexistent"
        assert error.context["alternative_name"] == "nonexistent"


class TestAlternativeExistsError:
    """Tests for AlternativeExistsError."""

    def test_creation(self) -> None:
        """Test error creation."""
        error = AlternativeExistsError("editor", "/usr/bin/vim")
        assert "editor" in str(error)
        assert "/usr/bin/vim" in str(error)
        assert "exists" in str(error).lower()
        assert error.name == "editor"
        assert error.path == "/usr/bin/vim"


class TestInvalidAlternativeError:
    """Tests for InvalidAlternativeError."""

    def test_creation(self) -> None:
        """Test error creation."""
        error = InvalidAlternativeError("editor", "path is not executable")
        assert "editor" in str(error)
        assert "path is not executable" in str(error)
        assert error.name == "editor"
        assert error.reason == "path is not executable"


# ============================================================================
# Parser Exception Tests
# ============================================================================


class TestParseError:
    """Tests for ParseError."""

    def test_basic_creation(self) -> None:
        """Test basic creation."""
        error = ParseError("Failed to parse output")
        assert "Failed to parse" in str(error)
        assert isinstance(error, UpdateAlternativesError)

    def test_with_details(self) -> None:
        """Test with line number and output."""
        error = ParseError(
            "Invalid line format",
            output="some output text",
            line_number=42
        )
        assert error.output == "some output text"
        assert error.line_number == 42
        assert "line_number=42" in str(error)

    def test_long_output_truncated(self) -> None:
        """Test that long output is truncated in context."""
        long_output = "x" * 500
        error = ParseError("Parse failed", output=long_output)
        # Preview should be truncated
        assert len(error.context.get("output_preview", "")) <= 203  # 200 + "..."


class TestInvalidFormatError:
    """Tests for InvalidFormatError."""

    def test_creation(self) -> None:
        """Test error creation."""
        error = InvalidFormatError("query output format")
        assert "query output format" in str(error)
        assert "Invalid format" in str(error)

    def test_with_actual(self) -> None:
        """Test with actual format."""
        error = InvalidFormatError("Name: value", "garbage: stuff")
        assert "expected" in str(error).lower()


# ============================================================================
# Config Exception Tests
# ============================================================================


class TestConfigError:
    """Tests for ConfigError."""

    def test_inheritance(self) -> None:
        """Test inheritance chain."""
        error = ConfigError("Config invalid")
        assert isinstance(error, UpdateAlternativesError)


class TestConfigFileNotFoundError:
    """Tests for ConfigFileNotFoundError."""

    def test_creation(self) -> None:
        """Test error creation."""
        error = ConfigFileNotFoundError("/etc/myconfig.toml")
        assert "/etc/myconfig.toml" in str(error)
        assert "not found" in str(error).lower()
        assert error.path == "/etc/myconfig.toml"


# ============================================================================
# UI Exception Tests
# ============================================================================


class TestUIError:
    """Tests for UIError."""

    def test_inheritance(self) -> None:
        """Test inheritance chain."""
        error = UIError("UI failed")
        assert isinstance(error, UpdateAlternativesError)


class TestWidgetError:
    """Tests for WidgetError."""

    def test_basic_creation(self) -> None:
        """Test basic creation."""
        error = WidgetError("StatusWidget", "render")
        assert "StatusWidget" in str(error)
        assert "render" in str(error)

    def test_with_reason(self) -> None:
        """Test with reason."""
        error = WidgetError("DataTable", "update", "no data available")
        assert "no data available" in str(error)


# ============================================================================
# ErrorCollection Tests
# ============================================================================


class TestErrorCollection:
    """Tests for ErrorCollection utility."""

    def test_empty_collection(self) -> None:
        """Test empty collection."""
        collection = ErrorCollection()
        assert len(collection) == 0
        assert collection.has_errors() is False

    def test_add_errors(self) -> None:
        """Test adding errors."""
        collection = ErrorCollection()
        collection.add(UpdateAlternativesError("Error 1"))
        collection.add(UpdateAlternativesError("Error 2"))
        
        assert len(collection) == 2
        assert collection.has_errors() is True

    def test_iteration(self) -> None:
        """Test iterating over errors."""
        collection = ErrorCollection()
        errors = [
            UpdateAlternativesError("Error 1"),
            ValidationError("Error 2"),
        ]
        for e in errors:
            collection.add(e)
        
        collected = list(collection)
        assert len(collected) == 2
        assert collected[0].message == "Error 1"

    def test_raise_if_errors_empty(self) -> None:
        """Test raise_if_errors with no errors."""
        collection = ErrorCollection()
        # Should not raise
        collection.raise_if_errors()

    def test_raise_if_errors_with_errors(self) -> None:
        """Test raise_if_errors with errors."""
        collection = ErrorCollection()
        collection.add(UpdateAlternativesError("Error 1"))
        collection.add(UpdateAlternativesError("Error 2"))
        
        with pytest.raises(UpdateAlternativesError) as exc_info:
            collection.raise_if_errors()
        
        assert "2 total" in str(exc_info.value)
        assert "errors" in exc_info.value.context

    def test_mixed_error_types(self) -> None:
        """Test with mixed error types."""
        collection = ErrorCollection()
        collection.add(ValidationError("validation failed"))
        collection.add(ExecutionError("execution failed"))
        collection.add(ParseError("parse failed"))
        
        assert len(collection) == 3
        
        # All should be UpdateAlternativesError
        for error in collection:
            assert isinstance(error, UpdateAlternativesError)


# ============================================================================
# Exception Hierarchy Tests
# ============================================================================


class TestExceptionHierarchy:
    """Test the exception inheritance hierarchy."""

    def test_all_inherit_from_base(self) -> None:
        """Test that all exceptions inherit from base."""
        exception_classes = [
            ValidationError,
            EmptyValueError,
            InvalidValueError,
            ExecutionError,
            CommandNotFoundError,
            PermissionDeniedError,
            CommandTimeoutError,
            ServiceError,
            AlternativeNotFoundError,
            AlternativeExistsError,
            InvalidAlternativeError,
            ParseError,
            InvalidFormatError,
            ConfigError,
            ConfigFileNotFoundError,
            UIError,
            WidgetError,
        ]
        
        for cls in exception_classes:
            error = cls.__new__(cls)
            assert isinstance(error, UpdateAlternativesError), \
                f"{cls.__name__} should inherit from UpdateAlternativesError"

    def test_catch_by_base_class(self) -> None:
        """Test catching specific exceptions by base class."""
        # ValidationError can be caught as UpdateAlternativesError
        try:
            raise ValidationError("test")
        except UpdateAlternativesError as e:
            assert isinstance(e, ValidationError)
        
        # ExecutionError subclasses can be caught by parent
        try:
            raise CommandNotFoundError()
        except ExecutionError as e:
            assert isinstance(e, CommandNotFoundError)
