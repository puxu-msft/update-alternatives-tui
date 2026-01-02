"""Domain models for update-alternatives management.

This module defines the core data structures used throughout the application.
All models use dataclasses with proper validation, type hints, and immutability
where appropriate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from functools import total_ordering
from typing import TYPE_CHECKING, Any, Iterator, Self

from .exceptions import EmptyValueError, InvalidValueError, ValidationError

if TYPE_CHECKING:
    pass


# ============================================================================
# Enumerations
# ============================================================================

class AlternativeStatus(Enum):
    """Status of an alternative group.
    
    Alternatives can be in one of three states:
    - AUTO: System automatically selects the highest priority alternative
    - MANUAL: Administrator has manually selected an alternative
    - UNKNOWN: Status could not be determined
    """
    AUTO = "auto"
    MANUAL = "manual"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_string(cls, value: str) -> AlternativeStatus:
        """Parse status from string representation.
        
        Args:
            value: String to parse (case-insensitive, strips whitespace)
            
        Returns:
            Corresponding AlternativeStatus
            
        Examples:
            >>> AlternativeStatus.from_string("auto")
            AlternativeStatus.AUTO
            >>> AlternativeStatus.from_string("  MANUAL  ")
            AlternativeStatus.MANUAL
            >>> AlternativeStatus.from_string("invalid")
            AlternativeStatus.UNKNOWN
        """
        value_lower = value.lower().strip()
        for status in cls:
            if status.value == value_lower:
                return status
        return cls.UNKNOWN
    
    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        return self.value.capitalize()
    
    def __str__(self) -> str:
        return self.value


class OperationType(Enum):
    """Types of operations that can be performed on alternatives."""
    SET = auto()
    AUTO = auto()
    INSTALL = auto()
    REMOVE = auto()
    REMOVE_ALL = auto()
    QUERY = auto()
    LIST = auto()


# ============================================================================
# Value Objects (Immutable)
# ============================================================================

@dataclass(frozen=True, slots=True)
class SlaveLink:
    """Represents a slave link in an alternative.
    
    Slave links are secondary symlinks that are managed alongside
    the main alternative. For example, an editor alternative might
    have a slave link for its man page.
    
    This is an immutable value object.
    
    Attributes:
        name: Name identifier for the slave (e.g., "editor.1.gz")
        link: Symlink path (e.g., "/usr/share/man/man1/editor.1.gz")
        path: Target path (e.g., "/usr/share/man/man1/vim.1.gz")
    """
    name: str
    link: str
    path: str
    
    def __post_init__(self) -> None:
        """Validate slave link data."""
        if not self.name:
            raise EmptyValueError("slave name")
        if not self.link:
            raise EmptyValueError("slave link")
        if not self.path:
            raise EmptyValueError("slave path")
    
    def __str__(self) -> str:
        return f"{self.name}: {self.link} → {self.path}"
    
    def to_tuple(self) -> tuple[str, str, str]:
        """Convert to tuple for command line arguments."""
        return (self.name, self.link, self.path)


@dataclass(frozen=True, slots=True)
class SelectionInfo:
    """Information about a selection from --get-selections.
    
    This represents a single line from the selections output,
    containing the essential information about an alternative's
    current state.
    
    Attributes:
        name: Alternative name
        mode: Current mode (auto/manual)
        current_path: Path to currently selected alternative
    """
    name: str
    mode: AlternativeStatus
    current_path: str
    
    def __post_init__(self) -> None:
        """Validate selection info."""
        if not self.name:
            raise EmptyValueError("selection name")
        if not self.current_path:
            raise EmptyValueError("current path")
    
    @classmethod
    def from_line(cls, line: str) -> SelectionInfo | None:
        """Parse a line from --get-selections output.
        
        Args:
            line: Single line from get-selections output
            
        Returns:
            SelectionInfo if parsing succeeds, None otherwise
            
        Example:
            >>> info = SelectionInfo.from_line("editor auto /usr/bin/vim")
            >>> info.name
            'editor'
        """
        parts = line.split()
        if len(parts) >= 3:
            try:
                return cls(
                    name=parts[0],
                    mode=AlternativeStatus.from_string(parts[1]),
                    current_path=parts[2]
                )
            except (EmptyValueError, ValidationError):
                return None
        return None
    
    @property
    def is_auto(self) -> bool:
        """Check if selection is in auto mode."""
        return self.mode == AlternativeStatus.AUTO
    
    @property
    def is_manual(self) -> bool:
        """Check if selection is in manual mode."""
        return self.mode == AlternativeStatus.MANUAL
    
    def __str__(self) -> str:
        return f"{self.name} ({self.mode.value}) → {self.current_path}"


# ============================================================================
# Entity Objects (Mutable)
# ============================================================================

@total_ordering
@dataclass(slots=True)
class Alternative:
    """Represents a single alternative option.
    
    An alternative is a specific implementation that can be selected
    for an alternative group. For example, /usr/bin/vim.basic might
    be an alternative for the "editor" group.
    
    Attributes:
        path: Absolute path to the alternative binary
        priority: Numeric priority (higher = preferred in auto mode)
        slaves: Mapping of slave name to slave path
    """
    path: str
    priority: int
    slaves: dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate alternative data."""
        if not self.path:
            raise EmptyValueError("alternative path")
        # Note: update-alternatives allows negative priorities (e.g., -100 for /bin/ed)
    
    def __hash__(self) -> int:
        """Hash based on path (unique identifier)."""
        return hash(self.path)
    
    def __eq__(self, other: object) -> bool:
        """Compare by path and priority."""
        if not isinstance(other, Alternative):
            return NotImplemented
        return self.path == other.path and self.priority == other.priority
    
    def __lt__(self, other: Alternative) -> bool:
        """Compare by priority for sorting."""
        if not isinstance(other, Alternative):
            return NotImplemented
        return self.priority < other.priority
    
    def __str__(self) -> str:
        return f"{self.path} (priority: {self.priority})"
    
    def __repr__(self) -> str:
        return f"Alternative(path={self.path!r}, priority={self.priority}, slaves={len(self.slaves)})"
    
    def has_slaves(self) -> bool:
        """Check if this alternative has slave links."""
        return len(self.slaves) > 0
    
    @property
    def slave_count(self) -> int:
        """Get number of slave links."""
        return len(self.slaves)
    
    def get_slave_paths(self) -> list[str]:
        """Get list of slave paths."""
        return list(self.slaves.values())
    
    @property
    def slave_names(self) -> list[str]:
        """Get list of slave names."""
        return list(self.slaves.keys())
    
    def get_slave_path(self, name: str) -> str | None:
        """Get slave path by name."""
        return self.slaves.get(name)
    
    def add_slave(self, name: str, path: str) -> None:
        """Add or update a slave link."""
        if not name:
            raise EmptyValueError("slave name")
        if not path:
            raise EmptyValueError("slave path")
        self.slaves[name] = path
    
    def remove_slave(self, name: str) -> bool:
        """Remove a slave link by name.
        
        Returns:
            True if slave was removed, False if not found
        """
        if name in self.slaves:
            del self.slaves[name]
            return True
        return False
    
    def copy(self) -> Alternative:
        """Create a copy of this alternative."""
        return Alternative(
            path=self.path,
            priority=self.priority,
            slaves=dict(self.slaves)
        )


@dataclass(slots=True)
class AlternativeGroup:
    """Represents an alternative group with all its options.
    
    An alternative group is a collection of alternatives that can
    provide a particular functionality. For example, the "editor"
    group might contain vim, nano, and emacs as alternatives.
    
    Attributes:
        name: Group name (e.g., "editor")
        link: Symlink path (e.g., "/usr/bin/editor")
        status: Current mode (auto/manual)
        best: Path to highest-priority alternative
        current: Path to currently selected alternative
        alternatives: List of available alternatives
        slave_links: Global slave link definitions
    """
    name: str
    link: str
    status: AlternativeStatus = AlternativeStatus.AUTO
    best: str = ""
    current: str = ""
    alternatives: list[Alternative] = field(default_factory=list)
    slave_links: dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate group data."""
        if not self.name:
            raise EmptyValueError("group name")
    
    def __hash__(self) -> int:
        """Hash based on name (unique identifier)."""
        return hash(self.name)
    
    def __eq__(self, other: object) -> bool:
        """Compare by name."""
        if not isinstance(other, AlternativeGroup):
            return NotImplemented
        return self.name == other.name
    
    def __str__(self) -> str:
        return f"{self.name} ({self.status.value}) → {self.current}"
    
    def __repr__(self) -> str:
        return (
            f"AlternativeGroup(name={self.name!r}, status={self.status.value!r}, "
            f"alternatives={len(self.alternatives)})"
        )
    
    def __iter__(self) -> Iterator[Alternative]:
        """Iterate over alternatives."""
        return iter(self.alternatives)
    
    def __len__(self) -> int:
        """Get number of alternatives."""
        return len(self.alternatives)
    
    def __contains__(self, path: str) -> bool:
        """Check if path exists in alternatives."""
        return any(alt.path == path for alt in self.alternatives)
    
    def is_auto(self) -> bool:
        """Check if group is in auto mode."""
        return self.status == AlternativeStatus.AUTO
    
    def is_manual(self) -> bool:
        """Check if group is in manual mode."""
        return self.status == AlternativeStatus.MANUAL
    
    @property
    def is_synchronized(self) -> bool:
        """Check if current equals best (expected in auto mode)."""
        return self.current == self.best
    
    @property
    def has_alternatives(self) -> bool:
        """Check if there are any alternatives."""
        return len(self.alternatives) > 0
    
    def count_alternatives(self) -> int:
        """Get number of alternatives."""
        return len(self.alternatives)
    
    def get_current_alternative(self) -> Alternative | None:
        """Get the currently selected alternative."""
        return self.get_alternative_by_path(self.current)
    
    def get_best_alternative(self) -> Alternative | None:
        """Get the best (highest priority) alternative."""
        return self.get_alternative_by_path(self.best)
    
    def get_alternative_by_path(self, path: str) -> Alternative | None:
        """Find alternative by path."""
        for alt in self.alternatives:
            if alt.path == path:
                return alt
        return None
    
    def get_by_priority(self, priority: int) -> Alternative | None:
        """Find alternative by priority."""
        for alt in self.alternatives:
            if alt.priority == priority:
                return alt
        return None
    
    def get_alternatives_sorted_by_priority(self, descending: bool = True) -> list[Alternative]:
        """Get alternatives sorted by priority.
        
        Args:
            descending: If True (default), highest priority first
            
        Returns:
            Sorted list of alternatives
        """
        return sorted(self.alternatives, reverse=descending)
    
    def has_alternative(self, path: str) -> bool:
        """Check if path exists in alternatives."""
        return path in self
    
    def add_alternative(self, alternative: Alternative) -> None:
        """Add an alternative to the group.
        
        Args:
            alternative: Alternative to add
            
        Raises:
            ValidationError: If alternative with same path already exists
        """
        if alternative.path in self:
            raise ValidationError(
                f"Alternative already exists: {alternative.path}",
                field="path",
                value=alternative.path
            )
        self.alternatives.append(alternative)
    
    def remove_alternative(self, path: str) -> Alternative | None:
        """Remove an alternative by path.
        
        Args:
            path: Path of alternative to remove
            
        Returns:
            Removed alternative or None if not found
        """
        for i, alt in enumerate(self.alternatives):
            if alt.path == path:
                return self.alternatives.pop(i)
        return None
    
    def update_current(self, path: str) -> bool:
        """Update the current selection.
        
        Args:
            path: Path to set as current
            
        Returns:
            True if path exists in alternatives, False otherwise
        """
        if path in self:
            self.current = path
            self.status = AlternativeStatus.MANUAL
            return True
        return False
    
    def set_auto(self) -> None:
        """Set to auto mode and update current to best."""
        self.status = AlternativeStatus.AUTO
        if self.best:
            self.current = self.best
    
    def recalculate_best(self) -> None:
        """Recalculate the best alternative based on priority."""
        if self.alternatives:
            best_alt = max(self.alternatives)
            self.best = best_alt.path


# ============================================================================
# Result Types
# ============================================================================

@dataclass(slots=True)
class CommandResult:
    """Result of a command execution.
    
    This provides a structured way to return command execution results,
    including success status, messages, and raw output.
    
    Attributes:
        success: Whether the command succeeded
        message: Human-readable result message
        return_code: Process return code
        stdout: Standard output content
        stderr: Standard error content
    """
    success: bool
    message: str
    return_code: int = 0
    stdout: str = ""
    stderr: str = ""
    
    def __bool__(self) -> bool:
        """Allow using result in boolean context."""
        return self.success
    
    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"[{status}] {self.message}"
    
    @classmethod
    def ok(cls, message: str, stdout: str = "") -> CommandResult:
        """Create a successful result.
        
        Args:
            message: Success message
            stdout: Optional stdout content
            
        Returns:
            Successful CommandResult
        """
        return cls(success=True, message=message, return_code=0, stdout=stdout)
    
    @classmethod
    def error(
        cls,
        message: str,
        return_code: int = 1,
        stderr: str = ""
    ) -> CommandResult:
        """Create an error result.
        
        Args:
            message: Error message
            return_code: Process return code (default 1)
            stderr: Optional stderr content
            
        Returns:
            Error CommandResult
        """
        return cls(
            success=False,
            message=message,
            return_code=return_code,
            stderr=stderr
        )
    
    @property
    def output(self) -> str:
        """Get the primary output (stdout if available, else stderr)."""
        return self.stdout or self.stderr


# ============================================================================
# Request Types
# ============================================================================

@dataclass(slots=True)
class InstallRequest:
    """Request to install a new alternative.
    
    This encapsulates all the information needed to install
    a new alternative, including optional slave links.
    
    Attributes:
        name: Alternative group name
        link: Symlink path
        path: Alternative binary path
        priority: Numeric priority
        slaves: List of slave definitions (name, link, path)
    """
    name: str
    link: str
    path: str
    priority: int
    slaves: list[tuple[str, str, str]] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate install request."""
        if not self.name:
            raise EmptyValueError("name")
        if not self.link:
            raise EmptyValueError("link")
        if not self.path:
            raise EmptyValueError("path")
        # Note: update-alternatives allows negative priorities
        
        # Validate slave entries
        for slave in self.slaves:
            if len(slave) != 3:
                raise InvalidValueError(
                    "slaves",
                    slave,
                    "each slave must be (name, link, path)"
                )
    
    def to_args(self) -> list[str]:
        """Convert to command line arguments.
        
        Returns:
            List of arguments for update-alternatives --install
        """
        args = ["--install", self.link, self.name, self.path, str(self.priority)]
        for slave_name, slave_link, slave_path in self.slaves:
            args.extend(["--slave", slave_link, slave_name, slave_path])
        return args
    
    def add_slave(self, name: str, link: str, path: str) -> Self:
        """Add a slave link to the request.
        
        Args:
            name: Slave name
            link: Slave symlink path
            path: Slave target path
            
        Returns:
            Self for method chaining
        """
        if not name or not link or not path:
            raise EmptyValueError("slave definition")
        self.slaves.append((name, link, path))
        return self
    
    @classmethod
    def create(
        cls,
        name: str,
        link: str,
        path: str,
        priority: int
    ) -> InstallRequest:
        """Create a new install request.
        
        This is a factory method that provides a cleaner API
        than direct instantiation.
        
        Args:
            name: Alternative group name
            link: Symlink path
            path: Alternative binary path
            priority: Numeric priority
            
        Returns:
            New InstallRequest instance
        """
        return cls(name=name, link=link, path=path, priority=priority)


# ============================================================================
# History Types (for undo support)
# ============================================================================

@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """A single entry in the operation history.
    
    Used for tracking changes and potentially implementing undo.
    """
    timestamp: float
    operation: OperationType
    name: str
    old_value: str | None
    new_value: str | None
    success: bool
    
    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"[{status}] {self.operation.name} {self.name}: {self.old_value} → {self.new_value}"
