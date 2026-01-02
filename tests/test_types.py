"""Tests for update_alternatives_tui.types module.

Tests cover:
- Type aliases verification
- Protocol runtime checking
- Data classes (ExecutionResult, OperationResult)
- Event types
- Configuration types
"""

from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError
from typing import get_type_hints

from update_alternatives_tui.types import (
    # Type aliases
    CommandArgs,
    ReturnCode,
    StdOut,
    StdErr,
    Callback,
    SlaveMapping,
    # Protocols
    Executor,
    AsyncExecutor,
    AlternativesReader,
    AlternativesWriter,
    CacheProtocol,
    OutputParserProtocol,
    DialogProtocol,
    NotificationProtocol,
    # Data classes
    ExecutionResult,
    OperationResult,
    # Events
    AlternativeSelectedEvent,
    AlternativeChangedEvent,
    SearchEvent,
    # Config
    UIConfig,
    ExecutorConfig,
    CacheConfig,
)


# ============================================================================
# Type Alias Tests
# ============================================================================


class TestTypeAliases:
    """Tests for type alias definitions."""

    def test_command_args_is_list_of_str(self) -> None:
        """Test CommandArgs is list[str]."""
        args: CommandArgs = ["update-alternatives", "--query", "editor"]
        assert isinstance(args, list)
        assert all(isinstance(a, str) for a in args)

    def test_return_code_is_int(self) -> None:
        """Test ReturnCode is int."""
        code: ReturnCode = 0
        assert isinstance(code, int)

    def test_stdout_stderr_are_str(self) -> None:
        """Test StdOut and StdErr are str."""
        out: StdOut = "output"
        err: StdErr = "error"
        assert isinstance(out, str)
        assert isinstance(err, str)

    def test_slave_mapping_is_dict(self) -> None:
        """Test SlaveMapping is dict[str, str]."""
        mapping: SlaveMapping = {
            "editor.1.gz": "/usr/share/man/man1/vim.1.gz",
            "editor.fr.1.gz": "/usr/share/man/fr/man1/vim.1.gz",
        }
        assert isinstance(mapping, dict)
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items())


# ============================================================================
# Protocol Tests
# ============================================================================


class TestExecutorProtocol:
    """Tests for Executor protocol."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that Executor is runtime checkable."""
        from typing import runtime_checkable
        
        # This should not raise
        assert hasattr(Executor, "__protocol_attrs__") or hasattr(Executor, "__subclasshook__")

    def test_valid_executor_implementation(self) -> None:
        """Test that valid implementation satisfies protocol."""
        class MockExecutor:
            def execute(self, args: list[str], use_sudo: bool = False):
                return ExecutionResult(0, "", "")
        
        executor = MockExecutor()
        assert isinstance(executor, Executor)

    def test_invalid_executor_missing_method(self) -> None:
        """Test that missing method fails protocol check."""
        class IncompleteExecutor:
            pass
        
        executor = IncompleteExecutor()
        assert not isinstance(executor, Executor)


class TestAlternativesReaderProtocol:
    """Tests for AlternativesReader protocol."""

    def test_valid_reader_implementation(self) -> None:
        """Test that valid implementation satisfies protocol."""
        class MockReader:
            def list_all(self) -> list[str]:
                return ["editor", "pager"]
            
            def get_details(self, name: str):
                return None
            
            def get_selections(self) -> dict:
                return {}
        
        reader = MockReader()
        assert isinstance(reader, AlternativesReader)


class TestCacheProtocol:
    """Tests for CacheProtocol."""

    def test_valid_cache_implementation(self) -> None:
        """Test that valid implementation has required methods."""
        class MockCache:
            def __init__(self):
                self._store: dict = {}
            
            def get(self, key: str):
                return self._store.get(key)
            
            def set(self, key: str, value, ttl: int | None = None) -> None:
                self._store[key] = value
            
            def delete(self, key: str) -> None:
                self._store.pop(key, None)
            
            def clear(self) -> None:
                self._store.clear()
        
        cache = MockCache()
        # Verify it has all protocol methods
        assert hasattr(cache, "get")
        assert hasattr(cache, "set")
        assert hasattr(cache, "delete")
        assert hasattr(cache, "clear")
        
        # Test functionality
        cache.set("key", "value")
        assert cache.get("key") == "value"
        cache.delete("key")
        assert cache.get("key") is None


class TestNotificationProtocol:
    """Tests for NotificationProtocol."""

    def test_valid_notification_implementation(self) -> None:
        """Test that valid implementation has required methods."""
        class MockNotification:
            def show_message(self, message: str, is_error: bool = False) -> None:
                pass
            
            def clear(self) -> None:
                pass
        
        notif = MockNotification()
        # Verify it has all protocol methods
        assert hasattr(notif, "show_message")
        assert hasattr(notif, "clear")
        
        # Should be callable without error
        notif.show_message("test")
        notif.clear()


# ============================================================================
# ExecutionResult Tests
# ============================================================================


class TestExecutionResult:
    """Tests for ExecutionResult data class."""

    def test_creation(self) -> None:
        """Test basic creation."""
        result = ExecutionResult(return_code=0, stdout="output", stderr="")
        assert result.return_code == 0
        assert result.stdout == "output"
        assert result.stderr == ""

    def test_success_property_true(self) -> None:
        """Test success is True for return code 0."""
        result = ExecutionResult(0, "out", "")
        assert result.success is True

    def test_success_property_false(self) -> None:
        """Test success is False for non-zero return code."""
        result = ExecutionResult(1, "", "error")
        assert result.success is False

    def test_output_property_prefers_stdout(self) -> None:
        """Test output property prefers stdout."""
        result = ExecutionResult(0, "stdout content", "stderr content")
        assert result.output == "stdout content"

    def test_output_property_fallback_to_stderr(self) -> None:
        """Test output property falls back to stderr when stdout is empty."""
        result = ExecutionResult(1, "", "error message")
        assert result.output == "error message"

    def test_output_property_empty(self) -> None:
        """Test output property when both are empty."""
        result = ExecutionResult(0, "", "")
        assert result.output == ""

    def test_frozen(self) -> None:
        """Test that result is immutable."""
        result = ExecutionResult(0, "out", "")
        with pytest.raises(FrozenInstanceError):
            result.return_code = 1  # type: ignore

    def test_equality(self) -> None:
        """Test equality comparison."""
        result1 = ExecutionResult(0, "out", "")
        result2 = ExecutionResult(0, "out", "")
        result3 = ExecutionResult(1, "out", "")
        
        assert result1 == result2
        assert result1 != result3

    def test_hash(self) -> None:
        """Test that result is hashable."""
        result = ExecutionResult(0, "out", "")
        # Should not raise
        hash(result)
        
        # Can be used in sets
        results = {result, ExecutionResult(0, "out", "")}
        assert len(results) == 1


# ============================================================================
# OperationResult Tests
# ============================================================================


class TestOperationResult:
    """Tests for OperationResult data class."""

    def test_ok_creation(self) -> None:
        """Test creating successful result."""
        result = OperationResult.ok("value")
        assert result.value == "value"
        assert result.error is None
        assert result.is_ok is True
        assert result.is_err is False

    def test_err_creation(self) -> None:
        """Test creating error result."""
        result = OperationResult.err("something went wrong")
        assert result.value is None
        assert result.error == "something went wrong"
        assert result.is_ok is False
        assert result.is_err is True

    def test_unwrap_success(self) -> None:
        """Test unwrap on successful result."""
        result = OperationResult.ok(42)
        assert result.unwrap() == 42

    def test_unwrap_error_raises(self) -> None:
        """Test unwrap on error result raises ValueError."""
        result: OperationResult[int] = OperationResult.err("failed")
        with pytest.raises(ValueError, match="failed"):
            result.unwrap()

    def test_unwrap_none_raises(self) -> None:
        """Test unwrap when value is None raises ValueError."""
        result: OperationResult[int] = OperationResult(value=None, error=None)
        with pytest.raises(ValueError, match="None"):
            result.unwrap()

    def test_unwrap_or_with_value(self) -> None:
        """Test unwrap_or returns value when ok."""
        result = OperationResult.ok(42)
        assert result.unwrap_or(0) == 42

    def test_unwrap_or_with_error(self) -> None:
        """Test unwrap_or returns default when error."""
        result: OperationResult[int] = OperationResult.err("failed")
        assert result.unwrap_or(0) == 0

    def test_unwrap_or_with_none_value(self) -> None:
        """Test unwrap_or returns default when value is None."""
        result: OperationResult[int] = OperationResult(value=None, error=None)
        assert result.unwrap_or(0) == 0

    def test_frozen(self) -> None:
        """Test that result is immutable."""
        result = OperationResult.ok("value")
        with pytest.raises(FrozenInstanceError):
            result.value = "new"  # type: ignore

    def test_generic_type(self) -> None:
        """Test with different types."""
        str_result = OperationResult.ok("string")
        int_result = OperationResult.ok(123)
        list_result = OperationResult.ok([1, 2, 3])
        
        assert str_result.unwrap() == "string"
        assert int_result.unwrap() == 123
        assert list_result.unwrap() == [1, 2, 3]


# ============================================================================
# Event Types Tests
# ============================================================================


class TestAlternativeSelectedEvent:
    """Tests for AlternativeSelectedEvent."""

    def test_creation(self) -> None:
        """Test event creation."""
        event = AlternativeSelectedEvent(name="editor", group=None)
        assert event.name == "editor"
        assert event.group is None

    def test_frozen(self) -> None:
        """Test that event is immutable."""
        event = AlternativeSelectedEvent(name="editor", group=None)
        with pytest.raises(FrozenInstanceError):
            event.name = "pager"  # type: ignore


class TestAlternativeChangedEvent:
    """Tests for AlternativeChangedEvent."""

    def test_creation(self) -> None:
        """Test event creation."""
        event = AlternativeChangedEvent(
            name="editor",
            old_path="/usr/bin/vim",
            new_path="/usr/bin/nano",
            operation="set"
        )
        assert event.name == "editor"
        assert event.old_path == "/usr/bin/vim"
        assert event.new_path == "/usr/bin/nano"
        assert event.operation == "set"

    def test_with_none_paths(self) -> None:
        """Test event with None paths (for install/remove)."""
        event = AlternativeChangedEvent(
            name="editor",
            old_path=None,
            new_path="/usr/bin/new",
            operation="install"
        )
        assert event.old_path is None


class TestSearchEvent:
    """Tests for SearchEvent."""

    def test_creation(self) -> None:
        """Test event creation."""
        event = SearchEvent(query="vim", result_count=5)
        assert event.query == "vim"
        assert event.result_count == 5

    def test_empty_query(self) -> None:
        """Test with empty query."""
        event = SearchEvent(query="", result_count=100)
        assert event.query == ""
        assert event.result_count == 100


# ============================================================================
# Configuration Types Tests
# ============================================================================


class TestUIConfig:
    """Tests for UIConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = UIConfig()
        assert config.theme == "dark"
        assert config.show_clock is True
        assert config.confirm_destructive is True
        assert config.search_debounce_ms == 300

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = UIConfig(
            theme="light",
            show_clock=False,
            confirm_destructive=False,
            search_debounce_ms=500
        )
        assert config.theme == "light"
        assert config.show_clock is False
        assert config.confirm_destructive is False
        assert config.search_debounce_ms == 500

    def test_mutable(self) -> None:
        """Test that config is mutable (not frozen)."""
        config = UIConfig()
        config.theme = "light"
        assert config.theme == "light"


class TestExecutorConfig:
    """Tests for ExecutorConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ExecutorConfig()
        assert config.timeout == 30
        assert config.use_sudo is True
        assert config.max_retries == 3

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = ExecutorConfig(timeout=60, use_sudo=False, max_retries=5)
        assert config.timeout == 60
        assert config.use_sudo is False
        assert config.max_retries == 5


class TestCacheConfig:
    """Tests for CacheConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.ttl_selections == 60
        assert config.ttl_details == 120
        assert config.max_size == 100

    def test_disabled_cache(self) -> None:
        """Test disabled cache configuration."""
        config = CacheConfig(enabled=False)
        assert config.enabled is False


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and corner scenarios."""

    def test_execution_result_with_large_output(self) -> None:
        """Test ExecutionResult with very large output."""
        large_output = "x" * 1000000  # 1MB
        result = ExecutionResult(0, large_output, "")
        assert len(result.stdout) == 1000000
        assert result.output == large_output

    def test_execution_result_with_unicode(self) -> None:
        """Test ExecutionResult with unicode content."""
        result = ExecutionResult(0, "日本語出力", "エラー")
        assert "日本語" in result.stdout
        assert result.output == "日本語出力"

    def test_operation_result_with_complex_type(self) -> None:
        """Test OperationResult with complex nested type."""
        data = {"key": [1, 2, {"nested": True}]}
        result = OperationResult.ok(data)
        assert result.unwrap() == data

    def test_operation_result_chaining(self) -> None:
        """Test chaining OperationResult operations."""
        result = OperationResult.ok(10)
        
        # Simulate transformation
        if result.is_ok:
            value = result.unwrap() * 2
            new_result = OperationResult.ok(value)
        else:
            new_result = OperationResult.err("original error")
        
        assert new_result.unwrap() == 20
