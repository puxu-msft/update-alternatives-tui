"""Service layer for update-alternatives management.

This module provides the main business logic for interacting with
update-alternatives, including caching and proper error handling.
"""

from __future__ import annotations

from typing import Any

from .cache import Cache
from .constants import (
    CACHE_TTL_DETAILS,
    CACHE_TTL_SELECTIONS,
    ErrorMessages,
    SuccessMessages,
)
from .executor import BaseExecutor, ExecutionResult, SubprocessExecutor
from .logging import LoggerMixin
from .models import (
    AlternativeGroup,
    AlternativeStatus,
    CommandResult,
    InstallRequest,
    SelectionInfo,
)
from .parser import OutputParser


# ============================================================================
# Service Class
# ============================================================================

class AlternativesService(LoggerMixin):
    """High-level service for managing update-alternatives.
    
    This class provides a clean, high-level interface for all
    alternatives operations, with features like:
    
    - Dependency injection for testability
    - Caching for performance
    - Batch operations
    - Operation history
    - Proper error handling
    
    Example:
        service = AlternativesService()
        
        # List all alternatives
        names = service.list_all()
        
        # Get details
        group = service.get_details("editor")
        
        # Set alternative
        result = service.set_alternative("editor", "/usr/bin/vim")
    """
    
    # Directories that require write permission for modifications
    ALTERNATIVES_DIR = "/etc/alternatives"
    ADMIN_DIR = "/var/lib/dpkg/alternatives"
    
    def __init__(
        self,
        executor: BaseExecutor | None = None,
        use_sudo: bool = True,
        enable_cache: bool = True,
    ) -> None:
        """Initialize the service.
        
        Args:
            executor: Command executor (defaults to SubprocessExecutor)
            use_sudo: Whether to use sudo for privileged operations
            enable_cache: Whether to enable caching
        """
        self.executor = executor or SubprocessExecutor()
        self.use_sudo = use_sudo
        self.parser = OutputParser()
        
        # Caching
        self._cache_enabled = enable_cache
        self._selections_cache: Cache[dict[str, SelectionInfo]] = Cache()
        self._details_cache: Cache[AlternativeGroup] = Cache()
    
    # ========================================================================
    # Internal Helpers
    # ========================================================================
    
    # Sudo password error messages
    SUDO_PASSWORD_ERRORS = (
        "a password is required",
        "sudo: a terminal is required",
        "no tty present",
        "sorry, you must have a tty",
    )
    
    # Permission denied error patterns
    PERMISSION_DENIED_ERRORS = (
        "permission denied",
        "operation not permitted",
        "access denied",
        "eacces",
    )
    
    def _execute(
        self,
        args: list[str],
        need_sudo: bool = False
    ) -> ExecutionResult:
        """Execute command and return result.
        
        Args:
            args: Command arguments
            need_sudo: Whether this operation needs sudo
            
        Returns:
            ExecutionResult
        """
        use_sudo = need_sudo and self.use_sudo
        return self.executor.execute(args, use_sudo=use_sudo)
    
    def _is_sudo_password_error(self, stderr: str) -> bool:
        """Check if error is due to sudo requiring password.
        
        Args:
            stderr: Error output from command
            
        Returns:
            True if sudo needs password
        """
        stderr_lower = stderr.lower()
        return any(msg in stderr_lower for msg in self.SUDO_PASSWORD_ERRORS)
    
    def _is_permission_denied_error(self, stderr: str) -> bool:
        """Check if error is due to permission denied.
        
        Args:
            stderr: Error output from command
            
        Returns:
            True if permission was denied
        """
        stderr_lower = stderr.lower()
        return any(msg in stderr_lower for msg in self.PERMISSION_DENIED_ERRORS)
    
    def _format_error_message(self, stderr: str, default_msg: str) -> str:
        """Format error message with user-friendly permission error handling.
        
        Args:
            stderr: Error output from command
            default_msg: Default message if stderr is empty
            
        Returns:
            User-friendly error message
        """
        if not stderr:
            return default_msg
        
        # Check for sudo password requirement (when using sudo but password needed)
        if self._is_sudo_password_error(stderr):
            return (
                "Permission denied: sudo requires authentication.\n"
                "Please run 'sudo -v' in a terminal first, or configure "
                "passwordless sudo for update-alternatives."
            )
        
        # Check for permission denied (when not using sudo or sudo failed)
        if self._is_permission_denied_error(stderr):
            if self.use_sudo:
                return (
                    "Permission denied: Operation failed even with sudo.\n"
                    "Please check your sudo configuration and try again."
                )
            else:
                return (
                    "Permission denied: This operation requires root privileges.\n"
                    "Please run the application with sudo, or enable sudo mode."
                )
        
        return stderr
    
    def can_modify(self) -> bool:
        """Check if the service can perform modification operations.
        
        This checks if we have write permission to the alternatives
        directories, either directly or via sudo.
        
        Returns:
            True if modifications are likely to succeed
        """
        import os
        
        # If using sudo, we assume it will work (actual errors handled at execution)
        if self.use_sudo:
            return True
        
        # Check direct write permission
        return (
            os.access(self.ALTERNATIVES_DIR, os.W_OK) and
            os.access(self.ADMIN_DIR, os.W_OK)
        )
    
    def check_permission(self) -> CommandResult:
        """Check if modification operations can be performed.
        
        Returns:
            CommandResult with success=True if can modify,
            or success=False with helpful error message
        """
        if self.can_modify():
            return CommandResult.ok("Permission check passed")
        
        return CommandResult.error(
            "Permission denied: Cannot modify alternatives.\n"
            "This operation requires root privileges.\n"
            "Please run with 'sudo' or enable sudo mode in settings.",
            return_code=1
        )
    
    def _invalidate_cache(self, name: str | None = None) -> None:
        """Invalidate cache entries.
        
        Args:
            name: If provided, only invalidate for this alternative.
                 If None, invalidate all caches.
        """
        if not self._cache_enabled:
            return
        
        self._selections_cache.clear()
        if name:
            self._details_cache.delete(name)
        else:
            self._details_cache.clear()
    
    # ========================================================================
    # Query Operations (no sudo needed)
    # ========================================================================
    
    def list_all(self) -> list[str]:
        """Get list of all alternative names.
        
        Returns:
            Sorted list of alternative names
        """
        result = self._execute(["--get-selections"])
        if not result.success:
            self.logger.warning(f"Failed to list alternatives: {result.stderr}")
            return []
        
        return self.parser.extract_alternative_names(result.stdout)
    
    def get_selections(self) -> dict[str, SelectionInfo]:
        """Get all selections.
        
        Returns:
            Dict mapping alternative name to SelectionInfo
        """
        # Check cache
        if self._cache_enabled:
            cached = self._selections_cache.get("all")
            if cached is not None:
                return cached
        
        result = self._execute(["--get-selections"])
        if not result.success:
            self.logger.warning(f"Failed to get selections: {result.stderr}")
            return {}
        
        selections = self.parser.parse_selections(result.stdout)
        selections_dict = {s.name: s for s in selections}
        
        # Cache result
        if self._cache_enabled:
            self._selections_cache.set("all", selections_dict, CACHE_TTL_SELECTIONS)
        
        return selections_dict
    
    def get_details(self, name: str) -> AlternativeGroup | None:
        """Get detailed information about an alternative.
        
        Args:
            name: Alternative name
            
        Returns:
            AlternativeGroup or None if not found
        """
        if not name:
            return None
        
        # Check cache
        if self._cache_enabled:
            cached = self._details_cache.get(name)
            if cached is not None:
                return cached
        
        result = self._execute(["--query", name])
        if not result.success:
            return None
        
        group = self.parser.parse_query(result.stdout)
        if group and self._cache_enabled:
            self._details_cache.set(name, group, CACHE_TTL_DETAILS)
        
        return group
    
    def get_display(self, name: str) -> CommandResult:
        """Get human-readable display of an alternative.
        
        Args:
            name: Alternative name
            
        Returns:
            CommandResult with display output
        """
        result = self._execute(["--display", name])
        if result.success:
            return CommandResult.ok(result.stdout, stdout=result.stdout)
        return CommandResult.error(
            result.stderr or "Failed to display alternative",
            result.return_code,
            result.stderr
        )
    
    def list_paths(self, name: str) -> list[str]:
        """List all available paths for an alternative group.
        
        This is a lightweight way to get just the paths without
        full details. Uses --list command.
        
        Args:
            name: Alternative group name
            
        Returns:
            List of available paths for this group
        """
        if not name:
            return []
        
        result = self._execute(["--list", name])
        if not result.success:
            return []
        
        # --list output is one path per line
        paths = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        return paths
    
    def search(self, query: str) -> list[str]:
        """Search alternatives by name.
        
        Args:
            query: Search query (case-insensitive substring match)
            
        Returns:
            List of matching alternative names
        """
        all_alternatives = self.list_all()
        query_lower = query.lower()
        return [alt for alt in all_alternatives if query_lower in alt.lower()]
    
    def exists(self, name: str) -> bool:
        """Check if an alternative exists.
        
        Args:
            name: Alternative name
            
        Returns:
            True if alternative exists
        """
        return name in self.list_all()
    
    def get_current_path(self, name: str) -> str | None:
        """Get current path for an alternative.
        
        Args:
            name: Alternative name
            
        Returns:
            Current path or None if not found
        """
        selections = self.get_selections()
        info = selections.get(name)
        return info.current_path if info else None
    
    def get_status(self, name: str) -> AlternativeStatus | None:
        """Get status (auto/manual) for an alternative.
        
        Args:
            name: Alternative name
            
        Returns:
            AlternativeStatus or None if not found
        """
        selections = self.get_selections()
        info = selections.get(name)
        return info.mode if info else None
    
    def is_auto(self, name: str) -> bool:
        """Check if alternative is in auto mode.
        
        Args:
            name: Alternative name
            
        Returns:
            True if in auto mode
        """
        status = self.get_status(name)
        return status == AlternativeStatus.AUTO if status else False
    
    def is_manual(self, name: str) -> bool:
        """Check if alternative is in manual mode.
        
        Args:
            name: Alternative name
            
        Returns:
            True if in manual mode
        """
        status = self.get_status(name)
        return status == AlternativeStatus.MANUAL if status else False
    
    # ========================================================================
    # Modification Operations (sudo needed)
    # ========================================================================
    
    def set_alternative(self, name: str, path: str) -> CommandResult:
        """Set a specific alternative (switches to manual mode).
        
        Args:
            name: Alternative group name
            path: Path to set as current
            
        Returns:
            CommandResult indicating success/failure
        """
        if not name:
            return CommandResult.error(ErrorMessages.EMPTY_NAME)
        if not path:
            return CommandResult.error(ErrorMessages.EMPTY_PATH)
        
        result = self._execute(["--set", name, path], need_sudo=True)
        
        if result.success:
            self._invalidate_cache(name)
            message = SuccessMessages.SET_ALTERNATIVE.format(name=name, path=path)
            return CommandResult.ok(message)
        
        error_msg = self._format_error_message(
            result.stderr,
            "Failed to set alternative"
        )
        return CommandResult.error(
            error_msg,
            result.return_code,
            result.stderr
        )
    
    def set_auto(self, name: str) -> CommandResult:
        """Set alternative to auto mode.
        
        Args:
            name: Alternative group name
            
        Returns:
            CommandResult indicating success/failure
        """
        if not name:
            return CommandResult.error(ErrorMessages.EMPTY_NAME)
        
        result = self._execute(["--auto", name], need_sudo=True)
        
        if result.success:
            self._invalidate_cache(name)
            message = SuccessMessages.SET_AUTO.format(name=name)
            return CommandResult.ok(message)
        
        error_msg = self._format_error_message(
            result.stderr,
            "Failed to set auto mode"
        )
        return CommandResult.error(
            error_msg,
            result.return_code,
            result.stderr
        )
    
    def install(self, request: InstallRequest) -> CommandResult:
        """Install a new alternative.
        
        Args:
            request: InstallRequest with installation details
            
        Returns:
            CommandResult indicating success/failure
        """
        args = request.to_args()
        result = self._execute(args, need_sudo=True)
        
        if result.success:
            self._invalidate_cache(request.name)
            message = SuccessMessages.INSTALLED.format(
                name=request.name,
                path=request.path
            )
            return CommandResult.ok(message)
        
        error_msg = self._format_error_message(
            result.stderr,
            "Failed to install alternative"
        )
        return CommandResult.error(
            error_msg,
            result.return_code,
            result.stderr
        )
    
    def remove(self, name: str, path: str) -> CommandResult:
        """Remove an alternative from a group.
        
        Args:
            name: Alternative group name
            path: Path to remove
            
        Returns:
            CommandResult indicating success/failure
        """
        if not name:
            return CommandResult.error(ErrorMessages.EMPTY_NAME)
        if not path:
            return CommandResult.error(ErrorMessages.EMPTY_PATH)
        
        result = self._execute(["--remove", name, path], need_sudo=True)
        
        if result.success:
            self._invalidate_cache(name)
            message = SuccessMessages.REMOVED.format(name=name, path=path)
            return CommandResult.ok(message)
        
        error_msg = self._format_error_message(
            result.stderr,
            "Failed to remove alternative"
        )
        return CommandResult.error(
            error_msg,
            result.return_code,
            result.stderr
        )
    
    def remove_all(self, name: str) -> CommandResult:
        """Remove all alternatives for a name.
        
        Args:
            name: Alternative group name
            
        Returns:
            CommandResult indicating success/failure
        """
        if not name:
            return CommandResult.error(ErrorMessages.EMPTY_NAME)
        
        result = self._execute(["--remove-all", name], need_sudo=True)
        
        if result.success:
            self._invalidate_cache(name)
            message = SuccessMessages.REMOVED_ALL.format(name=name)
            return CommandResult.ok(message)
        
        error_msg = self._format_error_message(
            result.stderr,
            "Failed to remove all alternatives"
        )
        return CommandResult.error(
            error_msg,
            result.return_code,
            result.stderr
        )
    
    # ========================================================================
    # Batch Operations
    # ========================================================================
    
    def get_details_batch(
        self,
        names: list[str]
    ) -> dict[str, AlternativeGroup | None]:
        """Get details for multiple alternatives.
        
        Args:
            names: List of alternative names
            
        Returns:
            Dict mapping name to AlternativeGroup (or None)
        """
        results: dict[str, AlternativeGroup | None] = {}
        for name in names:
            results[name] = self.get_details(name)
        return results
    
    def set_multiple(
        self,
        settings: dict[str, str]
    ) -> dict[str, CommandResult]:
        """Set multiple alternatives at once.
        
        Args:
            settings: Dict mapping alternative name to path
            
        Returns:
            Dict mapping name to CommandResult
        """
        results: dict[str, CommandResult] = {}
        for name, path in settings.items():
            results[name] = self.set_alternative(name, path)
        return results
    
    # ========================================================================
    # History and Statistics
    # ========================================================================
    # Cache Management
    # ========================================================================
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dict with cache statistics
        """
        return {
            "enabled": self._cache_enabled,
            "selections_cache_size": self._selections_cache.size,
            "selections_cache_hit_rate": self._selections_cache.hit_rate,
            "details_cache_size": self._details_cache.size,
            "details_cache_hit_rate": self._details_cache.hit_rate,
        }
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        self._selections_cache.clear()
        self._details_cache.clear()

