"""Command execution abstraction for update-alternatives.

This module provides a clean abstraction layer for executing system commands,
supporting features like retry logic, timeout handling, logging, and
easy mocking for tests.
"""

from __future__ import annotations

import asyncio
import subprocess
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Iterator

from .constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    MAX_OUTPUT_SIZE,
    RETRY_DELAY_BASE,
    UPDATE_ALTERNATIVES_CMD,
)
from .exceptions import (
    CommandNotFoundError,
    CommandTimeoutError,
    ExecutionError,
    PermissionDeniedError,
)
from .logging import LoggerMixin, get_logger

if TYPE_CHECKING:
    pass


# ============================================================================
# Result Data Classes
# ============================================================================

@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Immutable result of command execution.
    
    Attributes:
        return_code: Process return code (0 = success)
        stdout: Standard output content
        stderr: Standard error content
        duration: Execution duration in seconds (optional)
    """
    return_code: int
    stdout: str
    stderr: str
    duration: float = 0.0
    
    @property
    def success(self) -> bool:
        """Check if command succeeded."""
        return self.return_code == 0
    
    @property
    def output(self) -> str:
        """Get primary output (prefer stdout)."""
        return self.stdout if self.stdout else self.stderr
    
    @property
    def error_output(self) -> str:
        """Get error output (prefer stderr)."""
        return self.stderr if self.stderr else self.stdout
    
    def __bool__(self) -> bool:
        """Allow using result in boolean context."""
        return self.success
    
    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"[{status}] rc={self.return_code}, duration={self.duration:.3f}s"
    
    @classmethod
    def ok(cls, stdout: str = "", duration: float = 0.0) -> ExecutionResult:
        """Create a successful result."""
        return cls(return_code=0, stdout=stdout, stderr="", duration=duration)
    
    @classmethod
    def error(
        cls,
        stderr: str,
        return_code: int = 1,
        duration: float = 0.0
    ) -> ExecutionResult:
        """Create an error result."""
        return cls(
            return_code=return_code,
            stdout="",
            stderr=stderr,
            duration=duration
        )


@dataclass
class ExecutionStats:
    """Statistics about command executions.
    
    Useful for monitoring and debugging performance issues.
    """
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_duration: float = 0.0
    retries: int = 0
    
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_calls == 0:
            return 100.0
        return (self.successful_calls / self.total_calls) * 100
    
    @property
    def average_duration(self) -> float:
        """Get average execution duration."""
        if self.total_calls == 0:
            return 0.0
        return self.total_duration / self.total_calls
    
    def record_call(self, result: ExecutionResult) -> None:
        """Record a call execution."""
        self.total_calls += 1
        self.total_duration += result.duration
        if result.success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
    
    def record_retry(self) -> None:
        """Record a retry attempt."""
        self.retries += 1
    
    def reset(self) -> None:
        """Reset all statistics."""
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.total_duration = 0.0
        self.retries = 0


# ============================================================================
# Base Executor Interface
# ============================================================================

class BaseExecutor(ABC, LoggerMixin):
    """Abstract base class for command executors.
    
    This defines the interface that all executors must implement,
    allowing for different implementations (subprocess, async, mock).
    """
    
    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_command: str = UPDATE_ALTERNATIVES_CMD
    ) -> None:
        """Initialize executor.
        
        Args:
            timeout: Command timeout in seconds
            max_retries: Maximum retry attempts for transient failures
            base_command: Base command to execute
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_command = base_command
        self.stats = ExecutionStats()
    
    @abstractmethod
    def execute(
        self,
        args: list[str],
        use_sudo: bool = False
    ) -> ExecutionResult:
        """Execute a command with given arguments.
        
        Args:
            args: Command arguments (excluding base command)
            use_sudo: Whether to prepend sudo
            
        Returns:
            ExecutionResult with return code, stdout, and stderr
        """
        ...
    
    def build_command(
        self,
        args: list[str],
        use_sudo: bool = False
    ) -> list[str]:
        """Build complete command list.
        
        Args:
            args: Command arguments
            use_sudo: Whether to add sudo
            
        Returns:
            Complete command list
        """
        cmd = [self.base_command] + args
        if use_sudo:
            # Use sudo -n (non-interactive) to avoid hanging on password prompt
            cmd = ["sudo", "-n"] + cmd
        return cmd


# ============================================================================
# Subprocess Executor
# ============================================================================

class SubprocessExecutor(BaseExecutor):
    """Command executor using subprocess module.
    
    This is the standard executor for production use, executing
    commands via subprocess with proper error handling.
    
    Features:
    - Automatic retry for transient failures
    - Timeout handling
    - Output truncation for very large outputs
    - Detailed logging
    - Statistics collection
    - Non-interactive sudo (won't hang on password prompt)
    """
    
    # Error messages that indicate transient failures
    TRANSIENT_ERRORS = frozenset([
        "Resource temporarily unavailable",
        "Cannot allocate memory",
        "Connection refused",
    ])
    
    def execute(
        self,
        args: list[str],
        use_sudo: bool = False
    ) -> ExecutionResult:
        """Execute command with retry logic.
        
        Args:
            args: Command arguments
            use_sudo: Whether to use sudo
            
        Returns:
            ExecutionResult with execution details
        """
        cmd = self.build_command(args, use_sudo)
        last_error: Exception | None = None
        
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                self.stats.record_retry()
                delay = RETRY_DELAY_BASE * (2 ** (attempt - 1))
                self.logger.debug(f"Retry attempt {attempt} after {delay:.2f}s delay")
                time.sleep(delay)
            
            try:
                result = self._execute_once(cmd)
                self.stats.record_call(result)
                
                # Check if we should retry
                if not result.success and self._is_transient_error(result.stderr):
                    last_error = ExecutionError(
                        result.stderr,
                        command=cmd,
                        return_code=result.return_code
                    )
                    continue
                
                return result
                
            except Exception as e:
                last_error = e
                if not self._should_retry(e):
                    raise
        
        # All retries exhausted
        if last_error:
            raise last_error
        
        return ExecutionResult.error("All retry attempts failed")
    
    def _execute_once(self, cmd: list[str]) -> ExecutionResult:
        """Execute command once without retry.
        
        Args:
            cmd: Complete command list
            
        Returns:
            ExecutionResult
            
        Raises:
            CommandNotFoundError: If command is not found
            CommandTimeoutError: If command times out
            PermissionDeniedError: If permission is denied
            ExecutionError: For other errors
        """
        self.logger.debug(f"Executing: {' '.join(cmd)}")
        start_time = time.perf_counter()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            duration = time.perf_counter() - start_time
            
            # Truncate very large outputs
            stdout = self._truncate_output(result.stdout)
            stderr = self._truncate_output(result.stderr)
            
            return ExecutionResult(
                return_code=result.returncode,
                stdout=stdout,
                stderr=stderr,
                duration=duration
            )
            
        except subprocess.TimeoutExpired:
            duration = time.perf_counter() - start_time
            raise CommandTimeoutError(cmd, self.timeout)
            
        except FileNotFoundError:
            raise CommandNotFoundError(cmd[0] if cmd else self.base_command)
            
        except PermissionError as e:
            raise PermissionDeniedError(
                f"executing {' '.join(cmd)}",
                command=cmd
            )
            
        except Exception as e:
            duration = time.perf_counter() - start_time
            raise ExecutionError(
                str(e),
                command=cmd,
                return_code=-1
            )
    
    def _truncate_output(self, output: str) -> str:
        """Truncate output if too large.
        
        Args:
            output: Output string to potentially truncate
            
        Returns:
            Original or truncated output
        """
        if len(output.encode('utf-8')) > MAX_OUTPUT_SIZE:
            truncated = output[:MAX_OUTPUT_SIZE // 2]
            return f"{truncated}\n... [output truncated] ..."
        return output
    
    def _is_transient_error(self, error: str) -> bool:
        """Check if error is transient and worth retrying.
        
        Args:
            error: Error message
            
        Returns:
            True if error is transient
        """
        return any(msg in error for msg in self.TRANSIENT_ERRORS)
    
    def _should_retry(self, error: Exception) -> bool:
        """Check if we should retry after an exception.
        
        Args:
            error: Exception that occurred
            
        Returns:
            True if we should retry
        """
        # Don't retry for these error types
        no_retry_types = (
            CommandNotFoundError,
            PermissionDeniedError,
        )
        return not isinstance(error, no_retry_types)


# ============================================================================
# Async Executor
# ============================================================================

class AsyncSubprocessExecutor(BaseExecutor):
    """Async command executor using asyncio.subprocess.
    
    This executor allows for non-blocking command execution,
    useful for UI applications that need to remain responsive.
    """
    
    async def execute_async(
        self,
        args: list[str],
        use_sudo: bool = False
    ) -> ExecutionResult:
        """Execute command asynchronously.
        
        Args:
            args: Command arguments
            use_sudo: Whether to use sudo
            
        Returns:
            ExecutionResult with execution details
        """
        cmd = self.build_command(args, use_sudo)
        self.logger.debug(f"Async executing: {' '.join(cmd)}")
        
        start_time = time.perf_counter()
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise CommandTimeoutError(cmd, self.timeout)
            
            duration = time.perf_counter() - start_time
            
            return ExecutionResult(
                return_code=process.returncode or 0,
                stdout=stdout_bytes.decode('utf-8', errors='replace'),
                stderr=stderr_bytes.decode('utf-8', errors='replace'),
                duration=duration
            )
            
        except FileNotFoundError:
            raise CommandNotFoundError(cmd[0] if cmd else self.base_command)
            
        except PermissionError:
            raise PermissionDeniedError(
                f"executing {' '.join(cmd)}",
                command=cmd
            )
    
    def execute(
        self,
        args: list[str],
        use_sudo: bool = False
    ) -> ExecutionResult:
        """Synchronous wrapper for async execution.
        
        Args:
            args: Command arguments
            use_sudo: Whether to use sudo
            
        Returns:
            ExecutionResult
        """
        return asyncio.run(self.execute_async(args, use_sudo))


# ============================================================================
# Mock Executor (for testing)
# ============================================================================

@dataclass
class MockCall:
    """Record of a mock executor call."""
    args: list[str]
    use_sudo: bool
    timestamp: float = field(default_factory=time.time)


class MockExecutor(BaseExecutor):
    """Mock executor for testing.
    
    This executor allows tests to control command responses without
    actually executing system commands.
    
    Features:
    - Set specific responses for specific arguments
    - Set default response for unmatched calls
    - Record all calls for verification
    - Support for response sequences
    """
    
    def __init__(self, **kwargs: Any) -> None:
        """Initialize mock executor."""
        super().__init__(**kwargs)
        self._responses: dict[tuple[str, ...], ExecutionResult] = {}
        self._response_sequences: dict[tuple[str, ...], list[ExecutionResult]] = {}
        self._calls: list[MockCall] = []
        self._default_response = ExecutionResult.ok()
    
    def set_response(
        self,
        args: list[str],
        result: ExecutionResult
    ) -> MockExecutor:
        """Set response for specific arguments.
        
        Args:
            args: Arguments to match
            result: Result to return
            
        Returns:
            Self for method chaining
        """
        self._responses[tuple(args)] = result
        return self
    
    def set_response_sequence(
        self,
        args: list[str],
        results: list[ExecutionResult]
    ) -> MockExecutor:
        """Set a sequence of responses for specific arguments.
        
        Each call will return the next response in the sequence.
        After exhausting the sequence, returns the last response.
        
        Args:
            args: Arguments to match
            results: List of results to return in sequence
            
        Returns:
            Self for method chaining
        """
        if not results:
            raise ValueError("Response sequence cannot be empty")
        self._response_sequences[tuple(args)] = list(results)
        return self
    
    def set_default_response(self, result: ExecutionResult) -> MockExecutor:
        """Set default response for unmatched calls.
        
        Args:
            result: Default result to return
            
        Returns:
            Self for method chaining
        """
        self._default_response = result
        return self
    
    def execute(
        self,
        args: list[str],
        use_sudo: bool = False
    ) -> ExecutionResult:
        """Return mocked response.
        
        Args:
            args: Command arguments
            use_sudo: Whether sudo was requested
            
        Returns:
            Mocked ExecutionResult
        """
        # Record the call
        self._calls.append(MockCall(args=args, use_sudo=use_sudo))
        
        key = tuple(args)
        
        # Check for response sequence
        if key in self._response_sequences:
            sequence = self._response_sequences[key]
            if len(sequence) > 1:
                return sequence.pop(0)
            return sequence[0]  # Return last response repeatedly
        
        # Check for specific response
        if key in self._responses:
            return self._responses[key]
        
        # Return default
        return self._default_response
    
    @property
    def calls(self) -> list[MockCall]:
        """Get all recorded calls."""
        return self._calls.copy()
    
    @property
    def call_count(self) -> int:
        """Get number of calls made."""
        return len(self._calls)
    
    def get_calls_with_args(self, args: list[str]) -> list[MockCall]:
        """Get calls matching specific arguments.
        
        Args:
            args: Arguments to match
            
        Returns:
            List of matching calls
        """
        return [c for c in self._calls if c.args == args]
    
    def was_called_with(
        self,
        args: list[str],
        use_sudo: bool | None = None
    ) -> bool:
        """Check if executor was called with specific arguments.
        
        Args:
            args: Arguments to check
            use_sudo: If specified, also check sudo flag
            
        Returns:
            True if matching call was made
        """
        for call in self._calls:
            if call.args == args:
                if use_sudo is None or call.use_sudo == use_sudo:
                    return True
        return False
    
    def assert_called_with(
        self,
        args: list[str],
        use_sudo: bool | None = None
    ) -> None:
        """Assert executor was called with specific arguments.
        
        Args:
            args: Expected arguments
            use_sudo: If specified, expected sudo flag
            
        Raises:
            AssertionError: If no matching call was found
        """
        if not self.was_called_with(args, use_sudo):
            raise AssertionError(
                f"Expected call with args={args}, use_sudo={use_sudo}\n"
                f"Actual calls: {self._calls}"
            )
    
    def assert_call_count(self, expected: int) -> None:
        """Assert number of calls made.
        
        Args:
            expected: Expected call count
            
        Raises:
            AssertionError: If call count doesn't match
        """
        actual = len(self._calls)
        if actual != expected:
            raise AssertionError(
                f"Expected {expected} calls, got {actual}\n"
                f"Calls: {self._calls}"
            )
    
    def reset(self) -> None:
        """Reset mock state."""
        self._responses.clear()
        self._response_sequences.clear()
        self._calls.clear()
        self._default_response = ExecutionResult.ok()
        self.stats.reset()


# ============================================================================
# Executor Context Manager
# ============================================================================

@contextmanager
def executor_context(
    executor_type: type[BaseExecutor] = SubprocessExecutor,
    **kwargs: Any
) -> Iterator[BaseExecutor]:
    """Context manager for executor lifecycle.
    
    This provides a clean way to use an executor with proper
    cleanup and statistics logging.
    
    Args:
        executor_type: Type of executor to create
        **kwargs: Arguments passed to executor constructor
        
    Yields:
        Configured executor instance
        
    Example:
        with executor_context(timeout=60) as executor:
            result = executor.execute(["--get-selections"])
    """
    logger = get_logger(__name__)
    executor = executor_type(**kwargs)
    
    logger.debug(f"Created {executor_type.__name__}")
    
    try:
        yield executor
    finally:
        stats = executor.stats
        logger.debug(
            f"Executor stats: {stats.total_calls} calls, "
            f"{stats.success_rate:.1f}% success, "
            f"{stats.average_duration:.3f}s avg duration, "
            f"{stats.retries} retries"
        )


# ============================================================================
# Decorators
# ============================================================================

def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    delay_base: float = RETRY_DELAY_BASE
) -> Callable:
    """Decorator to add retry logic to functions.
    
    Args:
        max_retries: Maximum retry attempts
        delay_base: Base delay for exponential backoff
        
    Returns:
        Decorated function
        
    Example:
        @with_retry(max_retries=3)
        def flaky_operation():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Exception | None = None
            
            for attempt in range(max_retries + 1):
                if attempt > 0:
                    delay = delay_base * (2 ** (attempt - 1))
                    time.sleep(delay)
                
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
            
            if last_error:
                raise last_error
            
        return wrapper
    return decorator
