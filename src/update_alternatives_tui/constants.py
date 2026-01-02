"""Constants and configuration values for update-alternatives-tui.

This module centralizes all magic numbers, strings, and configuration
defaults used throughout the application. Modification of behavior
should be done here rather than scattered throughout the codebase.
"""

from enum import Enum, auto
from pathlib import Path
from typing import Final


# ============================================================================
# Application Metadata
# ============================================================================

APP_NAME: Final[str] = "update-alternatives-tui"
APP_VERSION: Final[str] = "0.3.0"
APP_DESCRIPTION: Final[str] = "TUI for managing Linux update-alternatives"
APP_AUTHOR: Final[str] = "Update Alternatives TUI Contributors"


# ============================================================================
# Command Configuration
# ============================================================================

# Base command for alternatives management
UPDATE_ALTERNATIVES_CMD: Final[str] = "update-alternatives"

# Command-line arguments
class CommandArgs:
    """Command-line arguments for update-alternatives."""
    GET_SELECTIONS: Final[str] = "--get-selections"
    QUERY: Final[str] = "--query"
    DISPLAY: Final[str] = "--display"
    SET: Final[str] = "--set"
    AUTO: Final[str] = "--auto"
    INSTALL: Final[str] = "--install"
    REMOVE: Final[str] = "--remove"
    REMOVE_ALL: Final[str] = "--remove-all"
    SLAVE: Final[str] = "--slave"
    CONFIG: Final[str] = "--config"
    LIST: Final[str] = "--list"
    ALL: Final[str] = "--all"


# ============================================================================
# Execution Configuration
# ============================================================================

# Default timeout for command execution (seconds)
DEFAULT_TIMEOUT: Final[int] = 30

# Maximum retries for transient failures
DEFAULT_MAX_RETRIES: Final[int] = 3

# Retry delay base (seconds) - exponential backoff
RETRY_DELAY_BASE: Final[float] = 0.5

# Maximum output buffer size (bytes)
MAX_OUTPUT_SIZE: Final[int] = 1024 * 1024  # 1MB


# ============================================================================
# Cache Configuration
# ============================================================================

# Cache time-to-live (seconds)
CACHE_TTL_SELECTIONS: Final[int] = 60  # 1 minute
CACHE_TTL_DETAILS: Final[int] = 120  # 2 minutes

# Maximum number of cached items
CACHE_MAX_SIZE: Final[int] = 100


# ============================================================================
# UI Configuration
# ============================================================================

# UI refresh intervals (seconds)
UI_REFRESH_INTERVAL: Final[float] = 0.1
STATUS_MESSAGE_TIMEOUT: Final[float] = 5.0

# List view configuration
LIST_PAGE_SIZE: Final[int] = 50
SEARCH_DEBOUNCE_MS: Final[int] = 300

# Dialog dimensions
DIALOG_WIDTH: Final[int] = 60
DIALOG_MAX_HEIGHT_PERCENT: Final[int] = 80

# Output preview truncation
OUTPUT_PREVIEW_MAX_LENGTH: Final[int] = 200
FORMAT_ERROR_PREVIEW_MAX_LENGTH: Final[int] = 100


# ============================================================================
# Status and Mode Indicators
# ============================================================================

class StatusIndicator:
    """Unicode indicators for status display."""
    CURRENT: Final[str] = "●"
    BEST: Final[str] = "★"
    AUTO: Final[str] = "A"
    MANUAL: Final[str] = "M"
    UNKNOWN: Final[str] = "?"
    CHECK: Final[str] = "✓"
    CROSS: Final[str] = "✗"
    ARROW: Final[str] = "→"
    SLAVE: Final[str] = "└─"


class StatusColor:
    """Color names for status display in Rich markup."""
    SUCCESS: Final[str] = "green"
    ERROR: Final[str] = "red"
    WARNING: Final[str] = "yellow"
    INFO: Final[str] = "cyan"
    MUTED: Final[str] = "dim"
    AUTO_MODE: Final[str] = "green"
    MANUAL_MODE: Final[str] = "yellow"


# ============================================================================
# Keyboard Shortcuts
# ============================================================================

class KeyBinding:
    """Default keyboard bindings."""
    QUIT: Final[str] = "q"
    REFRESH: Final[str] = "r"
    SET: Final[str] = "s"
    AUTO: Final[str] = "a"
    INSTALL: Final[str] = "i"
    DELETE: Final[str] = "d"
    SEARCH: Final[str] = "/"
    HELP: Final[str] = "?"
    CONFIRM_YES: Final[str] = "y"
    CONFIRM_NO: Final[str] = "n"
    CANCEL: Final[str] = "escape"
    UP: Final[str] = "up"
    DOWN: Final[str] = "down"
    ENTER: Final[str] = "enter"
    TAB: Final[str] = "tab"


# ============================================================================
# File Paths and Patterns
# ============================================================================

class Paths:
    """Standard paths used by the application."""
    # System paths
    ALTERNATIVES_DIR: Final[Path] = Path("/etc/alternatives")
    ADMIN_DIR: Final[Path] = Path("/var/lib/dpkg/alternatives")
    
    # User configuration
    @staticmethod
    def config_dir() -> Path:
        """Get user configuration directory."""
        return Path.home() / ".config" / APP_NAME
    
    @staticmethod
    def config_file() -> Path:
        """Get main configuration file path."""
        return Paths.config_dir() / "config.toml"
    
    @staticmethod
    def history_file() -> Path:
        """Get command history file path."""
        return Paths.config_dir() / "history.json"
    
    @staticmethod
    def cache_dir() -> Path:
        """Get cache directory."""
        return Path.home() / ".cache" / APP_NAME


# ============================================================================
# Parsing Patterns
# ============================================================================

class ParsePatterns:
    """Regex patterns for parsing command output."""
    # Query output field patterns
    NAME_FIELD: Final[str] = r"^Name:\s*(.+)$"
    LINK_FIELD: Final[str] = r"^Link:\s*(.+)$"
    STATUS_FIELD: Final[str] = r"^Status:\s*(.+)$"
    BEST_FIELD: Final[str] = r"^Best:\s*(.+)$"
    VALUE_FIELD: Final[str] = r"^Value:\s*(.+)$"
    
    # Alternative section patterns
    ALTERNATIVE_FIELD: Final[str] = r"^Alternative:\s*(.+)$"
    PRIORITY_FIELD: Final[str] = r"^Priority:\s*(\d+)$"
    
    # Slave patterns
    SLAVE_ENTRY: Final[str] = r"^\s*(\S+)\s+(\S+)\s+(\S+)$"
    SLAVE_LINK: Final[str] = r"^\s*slave\s+(\S+):\s+(\S+)$"
    
    # Selection line pattern
    SELECTION_LINE: Final[str] = r"^(\S+)\s+(auto|manual)\s+(\S+)$"


# ============================================================================
# Error Messages
# ============================================================================

class ErrorMessages:
    """Standard error messages."""
    # General errors
    COMMAND_NOT_FOUND: Final[str] = "update-alternatives command not found"
    PERMISSION_DENIED: Final[str] = "Permission denied. Try running with sudo."
    TIMEOUT: Final[str] = "Operation timed out"
    
    # Validation errors
    EMPTY_NAME: Final[str] = "Alternative name cannot be empty"
    EMPTY_PATH: Final[str] = "Path cannot be empty"
    EMPTY_LINK: Final[str] = "Link cannot be empty"
    INVALID_PRIORITY: Final[str] = "Priority must be an integer"
    
    # Service errors
    NOT_FOUND: Final[str] = "Alternative not found"
    ALREADY_EXISTS: Final[str] = "Alternative already exists"
    
    # UI errors
    NO_SELECTION: Final[str] = "No alternative selected"
    NO_ALTERNATIVES: Final[str] = "No alternatives available"


# ============================================================================
# Success Messages
# ============================================================================

class SuccessMessages:
    """Standard success messages."""
    SET_ALTERNATIVE: Final[str] = "Successfully set {name} to {path}"
    SET_AUTO: Final[str] = "Successfully set {name} to auto mode"
    INSTALLED: Final[str] = "Successfully installed {path} for {name}"
    REMOVED: Final[str] = "Successfully removed {path} from {name}"
    REMOVED_ALL: Final[str] = "Successfully removed all alternatives for {name}"
    LOADED: Final[str] = "Loaded {count} alternatives"


# ============================================================================
# Logging Configuration
# ============================================================================

class LogConfig:
    """Logging configuration."""
    FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
    DEFAULT_LEVEL: Final[str] = "INFO"
    
    @staticmethod
    def log_file() -> Path:
        """Get log file path."""
        return Paths.config_dir() / "app.log"


# ============================================================================
# Feature Flags
# ============================================================================

class Features:
    """Feature flags for enabling/disabling functionality."""
    ENABLE_CACHE: bool = True
    ENABLE_HISTORY: bool = True
    ENABLE_UNDO: bool = False  # Not yet implemented
    ENABLE_THEMES: bool = True
    ENABLE_ASYNC_EXECUTOR: bool = False  # Not yet implemented
    DEBUG_MODE: bool = False
