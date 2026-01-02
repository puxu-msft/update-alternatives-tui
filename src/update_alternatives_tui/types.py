"""Type definitions for update-alternatives-tui.

This module defines essential type aliases used throughout the application.
Keep this module minimal - only add types that are used in multiple places.
"""

from typing import TYPE_CHECKING, Any, Callable, TypeAlias

if TYPE_CHECKING:
    from .models import Alternative, AlternativeGroup, SelectionInfo


# ============================================================================
# Command Execution Types
# ============================================================================

CommandArgs: TypeAlias = list[str]


# ============================================================================
# Slave Types
# ============================================================================

SlaveDefinition: TypeAlias = tuple[str, str, str]  # (name, link, path)


# ============================================================================
# Selection Types
# ============================================================================

SelectionsMap: TypeAlias = dict[str, "SelectionInfo"]


# ============================================================================
# Callback Types (for future use)
# ============================================================================

Callback: TypeAlias = Callable[[], None]
ErrorHandler: TypeAlias = Callable[[Exception], None]


# ============================================================================
# Filter Types
# ============================================================================

FilterPredicate: TypeAlias = Callable[["AlternativeGroup"], bool]
SortKey: TypeAlias = Callable[["Alternative"], Any]
