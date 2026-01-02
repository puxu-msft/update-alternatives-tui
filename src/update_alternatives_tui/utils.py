"""Utility functions for update-alternatives-tui.

This module provides common utility functions used throughout
the application, including text processing and sanitization.
"""

from __future__ import annotations

import re
from typing import Final

from rich.markup import escape as escape_markup

__all__ = [
    "escape_markup",
    "safe_markup",
    "sanitize_widget_id",
    "truncate_text",
]


# ============================================================================
# Widget ID Sanitization
# ============================================================================

# Pattern for invalid widget ID characters
_INVALID_ID_CHARS: Final[re.Pattern[str]] = re.compile(r"[^a-zA-Z0-9_-]")


def sanitize_widget_id(value: str, prefix: str = "") -> str:
    """Sanitize a string to be a valid Textual widget ID.
    
    Textual widget IDs must be valid CSS identifiers. This function
    replaces invalid characters with underscores and optionally
    adds a prefix.
    
    Args:
        value: The string to sanitize
        prefix: Optional prefix to add (useful for namespacing)
        
    Returns:
        A sanitized string safe for use as a widget ID
        
    Examples:
        >>> sanitize_widget_id("builtins.7.gz")
        'builtins_7_gz'
        >>> sanitize_widget_id("/usr/bin/vim", prefix="opt")
        'opt-_usr_bin_vim'
    """
    sanitized = _INVALID_ID_CHARS.sub("_", value)
    
    # Ensure it doesn't start with a digit
    if sanitized and sanitized[0].isdigit():
        sanitized = f"_{sanitized}"
    
    if prefix:
        return f"{prefix}-{sanitized}"
    return sanitized


# ============================================================================
# Rich Markup Helpers
# ============================================================================

def safe_markup(template: str, **kwargs: str) -> str:
    """Format a Rich markup template with safely escaped values.
    
    This function allows you to create Rich markup strings while
    ensuring that dynamic values are properly escaped to prevent
    markup injection.
    
    Args:
        template: A format string with Rich markup and {placeholders}
        **kwargs: Values to substitute, will be escaped automatically
        
    Returns:
        Formatted string safe for Rich rendering
        
    Examples:
        >>> safe_markup("[bold]Name:[/bold] {name}", name="test[0]")
        '[bold]Name:[/bold] test\\\\[0]'
        >>> safe_markup("[red]{error}[/red]", error="tag '[/]' invalid")
        "[red]tag '\\\\[/]' invalid[/red]"
    """
    escaped_kwargs = {key: escape_markup(value) for key, value in kwargs.items()}
    return template.format(**escaped_kwargs)


# ============================================================================
# Text Processing
# ============================================================================

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to a maximum length with optional suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to append when truncated
        
    Returns:
        Truncated text with suffix if needed
        
    Examples:
        >>> truncate_text("hello world", 8)
        'hello...'
        >>> truncate_text("hi", 10)
        'hi'
    """
    if len(text) <= max_length:
        return text
    
    truncate_at = max_length - len(suffix)
    if truncate_at <= 0:
        return suffix[:max_length]
    
    return text[:truncate_at] + suffix
