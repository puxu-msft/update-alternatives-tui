"""Tests for update_alternatives_tui.executor module.

Tests cover:
- ExecutionResult dataclass
- Command execution basics
- Error handling
- Mock executor behavior
"""

from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

from update_alternatives_tui.executor import (
    SubprocessExecutor,
    MockExecutor,
    ExecutionResult,
)
from update_alternatives_tui.exceptions import (
    CommandNotFoundError,
)


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_success_result(self) -> None:
        """Test successful execution result."""
        result = ExecutionResult(
            return_code=0,
            stdout="output",
            stderr="",
        )
        assert result.success is True
        assert result.return_code == 0
        assert result.stdout == "output"

    def test_failure_result(self) -> None:
        """Test failed execution result."""
        result = ExecutionResult(
            return_code=1,
            stdout="",
            stderr="error",
        )
        assert result.success is False
        assert result.stderr == "error"

    def test_output_prefers_stdout(self) -> None:
        """Test output property prefers stdout."""
        result = ExecutionResult(
            return_code=0,
            stdout="stdout content",
            stderr="stderr content",
        )
        assert result.output == "stdout content"

    def test_output_falls_back_to_stderr(self) -> None:
        """Test output property falls back to stderr."""
        result = ExecutionResult(
            return_code=1,
            stdout="",
            stderr="error content",
        )
        assert result.output == "error content"

    def test_frozen(self) -> None:
        """Test that ExecutionResult is immutable."""
        result = ExecutionResult(0, "out", "")
        with pytest.raises(FrozenInstanceError):
            result.return_code = 1  # type: ignore[misc]

    def test_bool_context(self) -> None:
        """Test boolean context."""
        success = ExecutionResult(0, "", "")
        failure = ExecutionResult(1, "", "")
        
        assert bool(success) is True
        assert bool(failure) is False

    def test_ok_factory(self) -> None:
        """Test ok factory method."""
        result = ExecutionResult.ok("output")
        assert result.success is True
        assert result.stdout == "output"

    def test_error_factory(self) -> None:
        """Test error factory method."""
        result = ExecutionResult.error("error message", return_code=2)
        assert result.success is False
        assert result.stderr == "error message"
        assert result.return_code == 2

    def test_equality(self) -> None:
        """Test equality comparison."""
        result1 = ExecutionResult(0, "out", "")
        result2 = ExecutionResult(0, "out", "")
        result3 = ExecutionResult(1, "out", "")
        
        assert result1 == result2
        assert result1 != result3

    def test_hashable(self) -> None:
        """Test that ExecutionResult is hashable."""
        result = ExecutionResult(0, "out", "")
        # Should not raise
        hash(result)
        
        # Can be used in sets
        results = {result, ExecutionResult(0, "out", "")}
        assert len(results) == 1


class TestMockExecutor:
    """Tests for MockExecutor class."""

    def test_default_success(self) -> None:
        """Test default behavior returns success."""
        executor = MockExecutor()
        result = executor.execute(["--get-selections"])
        
        assert result.success is True
        assert result.return_code == 0

    def test_set_response(self) -> None:
        """Test setting custom response."""
        executor = MockExecutor()
        executor.set_response(
            ["--query", "editor"],
            ExecutionResult.ok("query output"),
        )
        
        result = executor.execute(["--query", "editor"])
        assert result.stdout == "query output"

    def test_set_failure_response(self) -> None:
        """Test setting failure response."""
        executor = MockExecutor()
        executor.set_response(
            ["--invalid"],
            ExecutionResult.error("invalid option"),
        )
        
        result = executor.execute(["--invalid"])
        assert result.success is False
        assert result.stderr == "invalid option"

    def test_call_count(self) -> None:
        """Test call count property."""
        executor = MockExecutor()
        
        assert executor.call_count == 0
        executor.execute(["--test"])
        assert executor.call_count == 1
        executor.execute(["--test"])
        assert executor.call_count == 2

    def test_was_called_with(self) -> None:
        """Test was_called_with method."""
        executor = MockExecutor()
        executor.execute(["--query", "editor"])
        
        assert executor.was_called_with(["--query", "editor"]) is True
        assert executor.was_called_with(["--other"]) is False

    def test_assert_called_with(self) -> None:
        """Test assert_called_with method."""
        executor = MockExecutor()
        executor.execute(["--query", "editor"])
        
        # Should not raise
        executor.assert_called_with(["--query", "editor"])
        
        # Should raise
        with pytest.raises(AssertionError):
            executor.assert_called_with(["--other"])

    def test_reset(self) -> None:
        """Test reset method."""
        executor = MockExecutor()
        executor.set_response(["test"], ExecutionResult.ok("test"))
        executor.execute(["test"])
        executor.reset()
        
        assert executor.call_count == 0

    def test_response_sequence(self) -> None:
        """Test response sequence."""
        executor = MockExecutor()
        executor.set_response_sequence(
            ["--test"],
            [
                ExecutionResult.ok("first"),
                ExecutionResult.ok("second"),
                ExecutionResult.ok("third"),
            ],
        )
        
        assert executor.execute(["--test"]).stdout == "first"
        assert executor.execute(["--test"]).stdout == "second"
        assert executor.execute(["--test"]).stdout == "third"
        # After sequence exhausted, returns last
        assert executor.execute(["--test"]).stdout == "third"

    def test_default_response(self) -> None:
        """Test setting default response."""
        executor = MockExecutor()
        executor.set_default_response(ExecutionResult.ok("default"))
        
        result = executor.execute(["any", "args"])
        assert result.stdout == "default"

    def test_calls_property(self) -> None:
        """Test calls property returns copy."""
        executor = MockExecutor()
        executor.execute(["--test"])
        
        calls = executor.calls
        assert len(calls) == 1
        assert calls[0].args == ["--test"]


class TestSubprocessExecutor:
    """Tests for SubprocessExecutor class."""

    def test_run_simple_command(self) -> None:
        """Test running a simple command."""
        executor = SubprocessExecutor(base_command="echo")
        result = executor.execute(["hello"])
        
        assert result.success is True
        assert "hello" in result.stdout

    def test_run_command_failure(self) -> None:
        """Test handling command failure."""
        executor = SubprocessExecutor(base_command="false")
        result = executor.execute([])
        
        assert result.success is False
        assert result.return_code != 0

    def test_run_nonexistent_command(self) -> None:
        """Test running nonexistent command raises error."""
        executor = SubprocessExecutor(base_command="this_command_does_not_exist_12345")
        
        with pytest.raises(CommandNotFoundError):
            executor.execute([])


class TestExecutorProtocol:
    """Tests verifying executor protocol compliance."""

    def test_subprocess_executor_has_execute(self) -> None:
        """Test SubprocessExecutor has execute method."""
        executor = SubprocessExecutor()
        assert hasattr(executor, "execute")
        assert callable(executor.execute)

    def test_mock_executor_has_execute(self) -> None:
        """Test MockExecutor has execute method."""
        executor = MockExecutor()
        assert hasattr(executor, "execute")
        assert callable(executor.execute)

    def test_executors_return_execution_result(self) -> None:
        """Test that executors return ExecutionResult."""
        mock_exec = MockExecutor()
        
        mock_result = mock_exec.execute(["test"])
        
        assert isinstance(mock_result, ExecutionResult)
