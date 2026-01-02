"""Parser for update-alternatives command output.

This module provides robust parsing of various update-alternatives
command outputs, with proper error handling and type safety.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Iterator, Pattern

from .exceptions import InvalidFormatError
from .logging import LoggerMixin
from .models import (
    Alternative,
    AlternativeGroup,
    AlternativeStatus,
    SelectionInfo,
)


# ============================================================================
# Parser State Machine
# ============================================================================

class ParserState(Enum):
    """State of the query output parser."""
    HEADER = auto()
    ALTERNATIVE = auto()
    SLAVES = auto()
    DONE = auto()


@dataclass
class ParseContext:
    """Context maintained during parsing.
    
    This helps track the current state and accumulated data
    while parsing multi-line output.
    """
    state: ParserState = ParserState.HEADER
    line_number: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    def add_error(self, message: str) -> None:
        """Add an error message with line number."""
        self.errors.append(f"Line {self.line_number}: {message}")
    
    def add_warning(self, message: str) -> None:
        """Add a warning message with line number."""
        self.warnings.append(f"Line {self.line_number}: {message}")
    
    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0


# ============================================================================
# Compiled Regex Patterns
# ============================================================================

class CompiledPatterns:
    """Pre-compiled regex patterns for better performance.
    
    Compiling patterns once and reusing them is more efficient
    than recompiling on each parse operation.
    """
    
    # Header field patterns (case-insensitive)
    NAME: Pattern[str] = re.compile(r"^Name:\s*(.+)$", re.IGNORECASE)
    LINK: Pattern[str] = re.compile(r"^Link:\s*(.+)$", re.IGNORECASE)
    STATUS: Pattern[str] = re.compile(r"^Status:\s*(.+)$", re.IGNORECASE)
    BEST: Pattern[str] = re.compile(r"^Best:\s*(.+)$", re.IGNORECASE)
    VALUE: Pattern[str] = re.compile(r"^Value:\s*(.+)$", re.IGNORECASE)
    
    # Alternative section patterns
    ALTERNATIVE: Pattern[str] = re.compile(r"^Alternative:\s*(.+)$", re.IGNORECASE)
    PRIORITY: Pattern[str] = re.compile(r"^Priority:\s*(-?\d+)$", re.IGNORECASE)
    SLAVES_HEADER: Pattern[str] = re.compile(r"^Slaves:\s*$", re.IGNORECASE)
    
    # Slave entry in --query output: "name path" (two space-separated fields)
    # Note: --query format uses 2 fields, not 3
    # Lines are stripped before matching, so leading whitespace is optional
    SLAVE_ENTRY: Pattern[str] = re.compile(r"^(\S+)\s+(\S+)$")
    
    # Display output slave link pattern
    SLAVE_LINK: Pattern[str] = re.compile(r"^\s*slave\s+(\S+):\s+(\S+)")
    
    # Selection line pattern
    SELECTION: Pattern[str] = re.compile(r"^(\S+)\s+(auto|manual)\s+(\S+)", re.IGNORECASE)


# Global compiled patterns instance
PATTERNS = CompiledPatterns()


# ============================================================================
# Output Parser
# ============================================================================

class OutputParser(LoggerMixin):
    """Parser for update-alternatives command output.
    
    This class provides methods to parse various output formats from
    the update-alternatives command, including --get-selections,
    --query, and --display.
    
    Features:
    - State machine-based parsing for complex outputs
    - Detailed error reporting
    - Recovery from malformed input
    - Type-safe return values
    
    Example:
        parser = OutputParser()
        selections = parser.parse_selections(output)
        group = parser.parse_query(output)
    """
    
    def __init__(self, strict: bool = False) -> None:
        """Initialize parser.
        
        Args:
            strict: If True, raise exceptions on parse errors.
                   If False (default), try to recover and log warnings.
        """
        self.strict = strict
    
    # ========================================================================
    # Selection Parsing
    # ========================================================================
    
    def parse_selections(self, output: str) -> list[SelectionInfo]:
        """Parse --get-selections output.
        
        Format: name mode path
        Example: editor auto /usr/bin/vim.basic
        
        Args:
            output: Raw output from --get-selections
            
        Returns:
            List of SelectionInfo objects
            
        Example:
            >>> parser.parse_selections("editor auto /usr/bin/vim")
            [SelectionInfo(name='editor', mode=AUTO, current_path='/usr/bin/vim')]
        """
        selections: list[SelectionInfo] = []
        
        for line_num, line in enumerate(self._iter_lines(output), 1):
            info = self._parse_selection_line(line, line_num)
            if info:
                selections.append(info)
        
        self.logger.debug(f"Parsed {len(selections)} selections")
        return selections
    
    def _parse_selection_line(
        self,
        line: str,
        line_num: int
    ) -> SelectionInfo | None:
        """Parse a single selection line.
        
        Args:
            line: Line to parse
            line_num: Line number for error reporting
            
        Returns:
            SelectionInfo or None if line is invalid
        """
        # Try regex pattern first for exact matching
        match = PATTERNS.SELECTION.match(line)
        if match:
            name, mode, path = match.groups()
            return SelectionInfo(
                name=name,
                mode=AlternativeStatus.from_string(mode),
                current_path=path
            )
        
        # Fallback to split-based parsing for wider compatibility
        return SelectionInfo.from_line(line)
    
    def parse_selections_as_dict(self, output: str) -> dict[str, SelectionInfo]:
        """Parse selections and return as dictionary.
        
        Args:
            output: Raw output from --get-selections
            
        Returns:
            Dictionary mapping name to SelectionInfo
        """
        selections = self.parse_selections(output)
        return {s.name: s for s in selections}
    
    # ========================================================================
    # Query Parsing
    # ========================================================================
    
    def parse_query(self, output: str) -> AlternativeGroup | None:
        """Parse --query output.
        
        This uses a state machine to parse the structured output,
        handling header fields, alternatives, and slave entries.
        
        Args:
            output: Raw output from --query
            
        Returns:
            AlternativeGroup or None if parsing fails
            
        Example:
            >>> parser.parse_query('''
            ... Name: editor
            ... Link: /usr/bin/editor
            ... Status: auto
            ... Best: /usr/bin/vim
            ... Value: /usr/bin/vim
            ... 
            ... Alternative: /usr/bin/vim
            ... Priority: 50
            ... ''')
            AlternativeGroup(name='editor', ...)
        """
        if not output or not output.strip():
            self.logger.debug("Empty output, returning None")
            return None
        
        ctx = ParseContext()
        
        # Header fields
        name = ""
        link = ""
        status = AlternativeStatus.UNKNOWN
        best = ""
        current = ""
        
        # Header slave links (slave name -> slave link path)
        header_slave_links: dict[str, str] = {}
        
        # Track if we're in header section (before any Alternative:)
        in_header = True
        
        # Alternatives being built
        alternatives: list[Alternative] = []
        current_alt: Alternative | None = None
        
        for line in self._iter_lines(output):
            ctx.line_number += 1
            
            # Handle empty lines (section separator)
            if not line:
                continue
            
            # Try to match header fields
            if match := PATTERNS.NAME.match(line):
                name = match.group(1).strip()
                continue
            
            if match := PATTERNS.LINK.match(line):
                link = match.group(1).strip()
                continue
            
            if match := PATTERNS.STATUS.match(line):
                status = AlternativeStatus.from_string(match.group(1).strip())
                continue
            
            if match := PATTERNS.BEST.match(line):
                best = match.group(1).strip()
                continue
            
            if match := PATTERNS.VALUE.match(line):
                current = match.group(1).strip()
                continue
            
            # Alternative section
            if match := PATTERNS.ALTERNATIVE.match(line):
                # No longer in header
                in_header = False
                
                # Save previous alternative
                if current_alt:
                    alternatives.append(current_alt)
                
                path = match.group(1).strip()
                current_alt = Alternative(path=path, priority=0)
                ctx.state = ParserState.ALTERNATIVE
                continue
            
            if match := PATTERNS.PRIORITY.match(line):
                if current_alt:
                    try:
                        current_alt.priority = int(match.group(1))
                    except ValueError:
                        ctx.add_warning(f"Invalid priority value: {match.group(1)}")
                continue
            
            if PATTERNS.SLAVES_HEADER.match(line):
                ctx.state = ParserState.SLAVES
                continue
            
            # Slave entry - format is "name path" (2 fields)
            if ctx.state == ParserState.SLAVES:
                if match := PATTERNS.SLAVE_ENTRY.match(line):
                    slave_name, slave_path = match.groups()
                    if in_header:
                        # Header slaves define slave links
                        header_slave_links[slave_name] = slave_path
                    elif current_alt:
                        # Alternative slaves define slave paths for this alternative
                        current_alt.slaves[slave_name] = slave_path
        
        # Don't forget the last alternative
        if current_alt:
            alternatives.append(current_alt)
        
        # Validate required fields
        if not name:
            if self.strict:
                raise InvalidFormatError("query output", "missing Name field")
            self.logger.warning("Missing Name field in query output")
            return None
        
        # Log any warnings
        for warning in ctx.warnings:
            self.logger.warning(warning)
        
        return AlternativeGroup(
            name=name,
            link=link,
            status=status,
            best=best,
            current=current,
            alternatives=alternatives,
            slave_links=header_slave_links
        )
    
    # ========================================================================
    # Display Parsing
    # ========================================================================
    
    def parse_display(self, output: str) -> dict[str, str]:
        """Parse --display output to extract slave links.
        
        The display output contains information about slave links
        in the format "slave name: link".
        
        Args:
            output: Raw output from --display
            
        Returns:
            Dict of slave_name -> slave_link
            
        Example:
            >>> parser.parse_display("  slave editor.1.gz: /usr/share/man/...")
            {'editor.1.gz': '/usr/share/man/...'}
        """
        slave_links: dict[str, str] = {}
        
        for line in self._iter_lines(output):
            if match := PATTERNS.SLAVE_LINK.match(line):
                slave_name, slave_link = match.groups()
                slave_links[slave_name] = slave_link
        
        self.logger.debug(f"Parsed {len(slave_links)} slave links")
        return slave_links
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def extract_alternative_names(self, output: str) -> list[str]:
        """Extract alternative names from --get-selections output.
        
        This is a convenience method that only extracts the names,
        useful when you only need a list of available alternatives.
        
        Args:
            output: Raw output from --get-selections
            
        Returns:
            Sorted list of alternative names
        """
        names: list[str] = []
        
        for line in self._iter_lines(output):
            parts = line.split()
            if parts:
                names.append(parts[0])
        
        return sorted(names)
    
    def _iter_lines(self, output: str) -> Iterator[str]:
        """Iterate over non-empty lines in output.
        
        Args:
            output: Multi-line string
            
        Yields:
            Stripped lines (empty lines are yielded as empty strings)
        """
        for line in output.split('\n'):
            stripped = line.strip()
            # Yield empty strings to preserve section boundaries
            yield stripped
    
    # ========================================================================
    # Validation Methods
    # ========================================================================
    
    @staticmethod
    def validate_path(path: str) -> bool:
        """Validate that a path looks reasonable.
        
        Args:
            path: Path to validate
            
        Returns:
            True if path appears valid
        """
        if not path:
            return False
        # Basic check: should start with / for absolute path
        return path.startswith('/')
    
    @staticmethod
    def validate_priority(priority: str) -> int | None:
        """Validate and parse a priority value.
        
        Note: update-alternatives allows negative priorities (e.g., -100 for /bin/ed).
        
        Args:
            priority: Priority string to validate
            
        Returns:
            Parsed integer or None if invalid
        """
        try:
            return int(priority)
        except ValueError:
            return None


# ============================================================================
# Standalone Parse Functions
# ============================================================================

def parse_selections(output: str) -> list[SelectionInfo]:
    """Parse --get-selections output.
    
    Convenience function that creates a parser and parses selections.
    
    Args:
        output: Raw output from --get-selections
        
    Returns:
        List of SelectionInfo objects
    """
    return OutputParser().parse_selections(output)


def parse_query(output: str) -> AlternativeGroup | None:
    """Parse --query output.
    
    Convenience function that creates a parser and parses query output.
    
    Args:
        output: Raw output from --query
        
    Returns:
        AlternativeGroup or None if parsing fails
    """
    return OutputParser().parse_query(output)


def parse_display(output: str) -> dict[str, str]:
    """Parse --display output.
    
    Convenience function that creates a parser and parses display output.
    
    Args:
        output: Raw output from --display
        
    Returns:
        Dict of slave_name -> slave_link
    """
    return OutputParser().parse_display(output)


def extract_names(output: str) -> list[str]:
    """Extract alternative names from selections output.
    
    Convenience function for extracting just the names.
    
    Args:
        output: Raw output from --get-selections
        
    Returns:
        Sorted list of alternative names
    """
    return OutputParser().extract_alternative_names(output)
