"""Messages for widget communication.

This module defines message types used for communication
between widgets and the main application.

Re-exports StatusColor and StatusIndicator from constants for convenience.
"""

from __future__ import annotations

from dataclasses import dataclass

from textual.message import Message

from ..constants import StatusColor, StatusIndicator

# Re-export for convenience
__all__ = [
    "StatusMessage",
    "AlternativeSelected",
    "DialogClosed",
    "StatusColor",
    "StatusIndicator",
]


@dataclass
class StatusMessage(Message):
    """Message for status updates."""
    text: str
    is_error: bool = False


@dataclass
class AlternativeSelected(Message):
    """Message when an alternative is selected."""
    name: str
    path: str | None = None


@dataclass
class DialogClosed(Message):
    """Message when a dialog is closed."""
    result: bool
    data: dict | None = None
