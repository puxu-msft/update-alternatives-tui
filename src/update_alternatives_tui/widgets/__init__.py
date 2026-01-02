"""Widget components for update-alternatives TUI.

This package provides reusable UI widgets including:
- StatusWidget: Display status messages
- AlternativeDetailPanel: Show alternative details
- ConfirmDialog, InputDialog, InstallDialog: User input dialogs
- SelectAlternativeDialog: Alternative selection dialog
- HelpDialog: Help information display

Example:
    from update_alternatives_tui.widgets import (
        StatusWidget,
        AlternativeDetailPanel,
        ConfirmDialog,
        SelectAlternativeDialog,
    )
"""

from .base import AlternativeDetailPanel, StatusWidget
from .dialogs import (
    ConfirmDialog,
    HelpDialog,
    InputDialog,
    InstallDialog,
    SelectAlternativeDialog,
)
from .messages import (
    AlternativeSelected,
    DialogClosed,
    StatusColor,
    StatusIndicator,
    StatusMessage,
)
from .styles import (
    DETAIL_PANEL_CSS,
    DIALOG_CSS,
    HELP_DIALOG_CSS,
    INPUT_DIALOG_CSS,
    SELECT_DIALOG_CSS,
    STATUS_WIDGET_CSS,
)

__all__ = [
    # Base widgets
    "StatusWidget",
    "AlternativeDetailPanel",
    # Dialogs
    "ConfirmDialog",
    "InputDialog",
    "InstallDialog",
    "SelectAlternativeDialog",
    "HelpDialog",
    # Messages
    "StatusMessage",
    "AlternativeSelected",
    "DialogClosed",
    "StatusColor",
    "StatusIndicator",
    # Styles
    "STATUS_WIDGET_CSS",
    "DIALOG_CSS",
    "INPUT_DIALOG_CSS",
    "DETAIL_PANEL_CSS",
    "SELECT_DIALOG_CSS",
    "HELP_DIALOG_CSS",
]
