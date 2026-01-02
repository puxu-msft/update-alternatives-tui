"""Update-Alternatives TUI - A terminal user interface for managing update-alternatives.

This package provides a comprehensive TUI (Terminal User Interface) for
managing Linux update-alternatives, built with Textual.

Quick Start:
    # As a command-line tool
    $ update-alternatives-tui
    
    # Or programmatically
    from update_alternatives_tui import AlternativesService
    
    service = AlternativesService()
    alternatives = service.list_all()
    details = service.get_details("editor")

Architecture:
    - models: Domain models and data classes
    - executor: Command execution abstraction
    - parser: Output parsing utilities
    - service: High-level service API
    - widgets: Reusable UI components
    - app: Main TUI application
    
For more information, see the README.md file.
"""

from .constants import APP_NAME, APP_VERSION

__version__ = APP_VERSION
__app_name__ = APP_NAME

# ============================================================================
# Models - Core data structures
# ============================================================================
from .models import (
    Alternative,
    AlternativeGroup,
    AlternativeStatus,
    CommandResult,
    InstallRequest,
    SelectionInfo,
    SlaveLink,
)

# ============================================================================
# Executor - Command execution
# ============================================================================
from .executor import (
    BaseExecutor,
    ExecutionResult,
    MockExecutor,
    SubprocessExecutor,
)

# ============================================================================
# Parser - Output parsing
# ============================================================================
from .parser import (
    OutputParser,
    extract_names,
    parse_display,
    parse_query,
    parse_selections,
)

# ============================================================================
# Service - Business logic
# ============================================================================
from .cache import Cache
from .service import AlternativesService

# ============================================================================
# Exceptions - Error types
# ============================================================================
from .exceptions import (
    CommandNotFoundError,
    CommandTimeoutError,
    EmptyValueError,
    ExecutionError,
    InvalidFormatError,
    InvalidValueError,
    ParseError,
    PermissionDeniedError,
    UpdateAlternativesError,
    ValidationError,
)

# ============================================================================
# Widgets - UI components
# ============================================================================
from .widgets import (
    AlternativeDetailPanel,
    ConfirmDialog,
    HelpDialog,
    InputDialog,
    InstallDialog,
    SelectAlternativeDialog,
    StatusWidget,
)

# ============================================================================
# Utils - Utility functions
# ============================================================================
from .utils import (
    escape_markup,
    safe_markup,
    sanitize_widget_id,
    truncate_text,
)

# ============================================================================
# Application - Main app
# ============================================================================
from .app import UpdateAlternativesTUI, main

# ============================================================================
# Public API
# ============================================================================
__all__ = [
    # Package metadata
    "__version__",
    "__app_name__",
    
    # Models
    "Alternative",
    "AlternativeGroup",
    "AlternativeStatus",
    "CommandResult",
    "InstallRequest",
    "SelectionInfo",
    "SlaveLink",
    
    # Executor
    "BaseExecutor",
    "ExecutionResult",
    "MockExecutor",
    "SubprocessExecutor",
    
    # Parser
    "OutputParser",
    "extract_names",
    "parse_display",
    "parse_query",
    "parse_selections",
    
    # Service
    "AlternativesService",
    "Cache",
    
    # Exceptions
    "CommandNotFoundError",
    "CommandTimeoutError",
    "EmptyValueError",
    "ExecutionError",
    "InvalidFormatError",
    "InvalidValueError",
    "ParseError",
    "PermissionDeniedError",
    "UpdateAlternativesError",
    "ValidationError",
    
    # Widgets
    "AlternativeDetailPanel",
    "ConfirmDialog",
    "HelpDialog",
    "InputDialog",
    "InstallDialog",
    "SelectAlternativeDialog",
    "StatusWidget",
    
    # Utils
    "escape_markup",
    "safe_markup",
    "sanitize_widget_id",
    "truncate_text",
    
    # Application
    "UpdateAlternativesTUI",
    "main",
]
