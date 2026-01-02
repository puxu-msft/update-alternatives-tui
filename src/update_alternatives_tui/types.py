"""Type definitions and protocols for update-alternatives-tui.

This module defines type aliases, protocols, and type variables used
throughout the application for better type safety and documentation.
"""

from abc import abstractmethod
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Generic,
    Protocol,
    TypeAlias,
    TypeVar,
    runtime_checkable,
)

if TYPE_CHECKING:
    from .models import (
        Alternative,
        AlternativeGroup,
        CommandResult,
        SelectionInfo,
    )


# ============================================================================
# Type Variables
# ============================================================================

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)

# Model type variables
AlternativeT = TypeVar("AlternativeT", bound="Alternative")
GroupT = TypeVar("GroupT", bound="AlternativeGroup")


# ============================================================================
# Type Aliases
# ============================================================================

# Command execution types
CommandArgs: TypeAlias = list[str]
ReturnCode: TypeAlias = int
StdOut: TypeAlias = str
StdErr: TypeAlias = str

# Callback types
Callback: TypeAlias = Callable[[], None]
AsyncCallback: TypeAlias = Callable[[], Coroutine[Any, Any, None]]
ErrorHandler: TypeAlias = Callable[[Exception], None]
ProgressCallback: TypeAlias = Callable[[int, int], None]  # (current, total)

# Result types
ExecutionTuple: TypeAlias = tuple[ReturnCode, StdOut, StdErr]

# Slave types
SlaveName: TypeAlias = str
SlaveLink: TypeAlias = str
SlavePath: TypeAlias = str
SlaveMapping: TypeAlias = dict[SlaveName, SlavePath]
SlaveDefinition: TypeAlias = tuple[SlaveName, SlaveLink, SlavePath]

# Selection types
SelectionsMap: TypeAlias = dict[str, "SelectionInfo"]

# Filter types
FilterPredicate: TypeAlias = Callable[["AlternativeGroup"], bool]
SortKey: TypeAlias = Callable[["Alternative"], Any]

# JSON-compatible types
JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
JsonDict: TypeAlias = dict[str, JsonValue]


# ============================================================================
# Protocols - Command Execution
# ============================================================================

@runtime_checkable
class Executor(Protocol):
    """Protocol for command executors.
    
    Implementations of this protocol handle the actual execution
    of system commands, allowing for dependency injection and testing.
    """
    
    def execute(
        self,
        args: CommandArgs,
        use_sudo: bool = False
    ) -> "ExecutionResult":
        """Execute a command with given arguments.
        
        Args:
            args: Command arguments (excluding base command)
            use_sudo: Whether to run with sudo
            
        Returns:
            ExecutionResult with return code, stdout, and stderr
        """
        ...


@runtime_checkable
class AsyncExecutor(Protocol):
    """Protocol for async command executors."""
    
    async def execute_async(
        self,
        args: CommandArgs,
        use_sudo: bool = False
    ) -> "ExecutionResult":
        """Execute a command asynchronously.
        
        Args:
            args: Command arguments
            use_sudo: Whether to run with sudo
            
        Returns:
            ExecutionResult with return code, stdout, and stderr
        """
        ...


# ============================================================================
# Protocols - Service Layer
# ============================================================================

@runtime_checkable
class AlternativesReader(Protocol):
    """Protocol for reading alternatives information."""
    
    def list_all(self) -> list[str]:
        """Get list of all alternative names."""
        ...
    
    def get_details(self, name: str) -> "AlternativeGroup | None":
        """Get detailed information about an alternative."""
        ...
    
    def get_selections(self) -> SelectionsMap:
        """Get all selections."""
        ...


@runtime_checkable
class AlternativesWriter(Protocol):
    """Protocol for modifying alternatives."""
    
    def set_alternative(self, name: str, path: str) -> "CommandResult":
        """Set a specific alternative."""
        ...
    
    def set_auto(self, name: str) -> "CommandResult":
        """Set alternative to auto mode."""
        ...
    
    def remove(self, name: str, path: str) -> "CommandResult":
        """Remove an alternative."""
        ...


class CacheProtocol(Protocol[T]):
    """Protocol for cache implementations."""
    
    def get(self, key: str) -> T | None:
        """Get a cached value."""
        ...
    
    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Set a cached value with optional TTL."""
        ...
    
    def delete(self, key: str) -> None:
        """Delete a cached value."""
        ...
    
    def clear(self) -> None:
        """Clear all cached values."""
        ...


# ============================================================================
# Protocols - Parser
# ============================================================================

class OutputParserProtocol(Protocol):
    """Protocol for command output parsers."""
    
    def parse_selections(self, output: str) -> list["SelectionInfo"]:
        """Parse --get-selections output."""
        ...
    
    def parse_query(self, output: str) -> "AlternativeGroup | None":
        """Parse --query output."""
        ...


# ============================================================================
# Protocols - UI Components
# ============================================================================

class DialogProtocol(Protocol[T_co]):
    """Protocol for modal dialogs."""
    
    async def show(self) -> T_co:
        """Show the dialog and wait for result."""
        ...


class NotificationProtocol(Protocol):
    """Protocol for notification systems."""
    
    def show_message(self, message: str, is_error: bool = False) -> None:
        """Show a notification message."""
        ...
    
    def clear(self) -> None:
        """Clear current notification."""
        ...


# ============================================================================
# Data Classes for Type Safety
# ============================================================================

@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Immutable result of command execution.
    
    This is a type-safe replacement for tuples in execution results.
    """
    return_code: ReturnCode
    stdout: StdOut
    stderr: StdErr
    
    @property
    def success(self) -> bool:
        """Check if command succeeded."""
        return self.return_code == 0
    
    @property
    def output(self) -> str:
        """Get combined output (prefer stdout, fallback to stderr)."""
        return self.stdout if self.stdout else self.stderr


@dataclass(frozen=True, slots=True)
class OperationResult(Generic[T]):
    """Generic result type for operations that may fail.
    
    Similar to Rust's Result<T, E> type.
    """
    value: T | None
    error: str | None
    
    @property
    def is_ok(self) -> bool:
        """Check if operation succeeded."""
        return self.error is None
    
    @property
    def is_err(self) -> bool:
        """Check if operation failed."""
        return self.error is not None
    
    def unwrap(self) -> T:
        """Get the value, raising if error.
        
        Raises:
            ValueError: If operation failed
        """
        if self.error is not None:
            raise ValueError(self.error)
        if self.value is None:
            raise ValueError("Operation returned None")
        return self.value
    
    def unwrap_or(self, default: T) -> T:
        """Get the value or a default if error."""
        return self.value if self.is_ok and self.value is not None else default
    
    @classmethod
    def ok(cls, value: T) -> "OperationResult[T]":
        """Create a successful result."""
        return cls(value=value, error=None)
    
    @classmethod
    def err(cls, error: str) -> "OperationResult[T]":
        """Create an error result."""
        return cls(value=None, error=error)


# ============================================================================
# Event Types
# ============================================================================

@dataclass(frozen=True)
class AlternativeSelectedEvent:
    """Event fired when an alternative is selected in the UI."""
    name: str
    group: "AlternativeGroup | None"


@dataclass(frozen=True)
class AlternativeChangedEvent:
    """Event fired when an alternative is modified."""
    name: str
    old_path: str | None
    new_path: str | None
    operation: str  # "set", "auto", "install", "remove"


@dataclass(frozen=True)
class SearchEvent:
    """Event fired when search query changes."""
    query: str
    result_count: int


# ============================================================================
# Configuration Types
# ============================================================================

@dataclass
class UIConfig:
    """UI-related configuration."""
    theme: str = "dark"
    show_clock: bool = True
    confirm_destructive: bool = True
    search_debounce_ms: int = 300


@dataclass
class ExecutorConfig:
    """Executor-related configuration."""
    timeout: int = 30
    use_sudo: bool = True
    max_retries: int = 3


@dataclass
class CacheConfig:
    """Cache-related configuration."""
    enabled: bool = True
    ttl_selections: int = 60
    ttl_details: int = 120
    max_size: int = 100
