"""Command execution abstraction for update-alternatives.

This module provides a clean abstraction for executing system commands,
with timeout handling, logging, and mock support for tests.
"""

from __future__ import annotations

import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

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
from .logging import LoggerMixin


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
        duration: Execution duration in seconds
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
    def error(cls, stderr: str, return_code: int = 1, duration: float = 0.0) -> ExecutionResult:
        """Create an error result."""
        return cls(return_code=return_code, stdout="", stderr=stderr, duration=duration)


# ============================================================================
# Base Executor Interface
# ============================================================================

class BaseExecutor(ABC, LoggerMixin):
    """Abstract base class for command executors."""
    
    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_command: str = UPDATE_ALTERNATIVES_CMD
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_command = base_command
    
    @abstractmethod
    def execute(self, args: list[str], use_sudo: bool = False) -> ExecutionResult:
        """Execute a command with given arguments."""
        ...
    
    def build_command(self, args: list[str], use_sudo: bool = False) -> list[str]:
        """Build complete command list."""
        cmd = [self.base_command] + args
        if use_sudo:
            cmd = ["sudo", "-n"] + cmd
        return cmd


# ============================================================================
# Subprocess Executor
# ============================================================================

class SubprocessExecutor(BaseExecutor):
    """Command executor using subprocess module.
    
    Features:
    - Automatic retry for transient failures
    - Timeout handling
    - Output truncation for large outputs
    - Non-interactive sudo
    """
    
    TRANSIENT_ERRORS = frozenset([
        "Resource temporarily unavailable",
        "Cannot allocate memory",
        "Connection refused",
    ])
    
    def execute(self, args: list[str], use_sudo: bool = False) -> ExecutionResult:
        """Execute command with retry logic."""
        cmd = self.build_command(args, use_sudo)
        last_error: Exception | None = None
        
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                delay = RETRY_DELAY_BASE * (2 ** (attempt - 1))
                self.logger.debug(f"Retry attempt {attempt} after {delay:.2f}s delay")
                time.sleep(delay)
            
            try:
                result = self._execute_once(cmd)
                
                if not result.success and self._is_transient_error(result.stderr):
                    last_error = ExecutionError(
                        result.stderr, command=cmd, return_code=result.return_code
                    )
                    continue
                
                return result
                
            except Exception as e:
                last_error = e
                if not self._should_retry(e):
                    raise
        
        if last_error:
            raise last_error
        return ExecutionResult.error("All retry attempts failed")
    
    def _execute_once(self, cmd: list[str]) -> ExecutionResult:
        """Execute command once without retry."""
        self.logger.debug(f"Executing: {' '.join(cmd)}")
        start_time = time.perf_counter()
        
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout
            )
            duration = time.perf_counter() - start_time
            
            return ExecutionResult(
                return_code=result.returncode,
                stdout=self._truncate_output(result.stdout),
                stderr=self._truncate_output(result.stderr),
                duration=duration
            )
            
        except subprocess.TimeoutExpired:
            raise CommandTimeoutError(cmd, self.timeout)
        except FileNotFoundError:
            raise CommandNotFoundError(cmd[0] if cmd else self.base_command)
        except PermissionError:
            raise PermissionDeniedError(f"executing {' '.join(cmd)}", command=cmd)
        except Exception as e:
            raise ExecutionError(str(e), command=cmd, return_code=-1)
    
    def _truncate_output(self, output: str) -> str:
        """Truncate output if too large (UTF-8 safe)."""
        encoded = output.encode('utf-8')
        if len(encoded) > MAX_OUTPUT_SIZE:
            target_bytes = MAX_OUTPUT_SIZE // 2
            truncated = encoded[:target_bytes].decode('utf-8', errors='ignore')
            return f"{truncated}\n... [output truncated] ..."
        return output
    
    def _is_transient_error(self, error: str) -> bool:
        """Check if error is transient and worth retrying."""
        return any(msg in error for msg in self.TRANSIENT_ERRORS)
    
    def _should_retry(self, error: Exception) -> bool:
        """Check if we should retry after an exception."""
        return not isinstance(error, (CommandNotFoundError, PermissionDeniedError))


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
    
    Allows tests to control command responses without executing system commands.
    """
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._responses: dict[tuple[str, ...], ExecutionResult] = {}
        self._response_sequences: dict[tuple[str, ...], list[ExecutionResult]] = {}
        self._calls: list[MockCall] = []
        self._default_response = ExecutionResult.ok()
    
    def set_response(self, args: list[str], result: ExecutionResult) -> MockExecutor:
        """Set response for specific arguments."""
        self._responses[tuple(args)] = result
        return self
    
    def set_response_sequence(self, args: list[str], results: list[ExecutionResult]) -> MockExecutor:
        """Set a sequence of responses for specific arguments."""
        if not results:
            raise ValueError("Response sequence cannot be empty")
        self._response_sequences[tuple(args)] = list(results)
        return self
    
    def set_default_response(self, result: ExecutionResult) -> MockExecutor:
        """Set default response for unmatched calls."""
        self._default_response = result
        return self
    
    def execute(self, args: list[str], use_sudo: bool = False) -> ExecutionResult:
        """Return mocked response."""
        self._calls.append(MockCall(args=args, use_sudo=use_sudo))
        key = tuple(args)
        
        if key in self._response_sequences:
            sequence = self._response_sequences[key]
            return sequence.pop(0) if len(sequence) > 1 else sequence[0]
        
        if key in self._responses:
            return self._responses[key]
        
        return self._default_response
    
    @property
    def calls(self) -> list[MockCall]:
        """Get all recorded calls."""
        return self._calls.copy()
    
    @property
    def call_count(self) -> int:
        """Get number of calls made."""
        return len(self._calls)
    
    def was_called_with(self, args: list[str], use_sudo: bool | None = None) -> bool:
        """Check if executor was called with specific arguments."""
        for call in self._calls:
            if call.args == args and (use_sudo is None or call.use_sudo == use_sudo):
                return True
        return False
    
    def assert_called_with(self, args: list[str], use_sudo: bool | None = None) -> None:
        """Assert executor was called with specific arguments."""
        if not self.was_called_with(args, use_sudo):
            raise AssertionError(
                f"Expected call with args={args}, use_sudo={use_sudo}\n"
                f"Actual calls: {self._calls}"
            )
    
    def reset(self) -> None:
        """Reset mock state."""
        self._responses.clear()
        self._response_sequences.clear()
        self._calls.clear()
        self._default_response = ExecutionResult.ok()
