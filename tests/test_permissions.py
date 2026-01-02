"""Comprehensive tests for permission handling.

This module tests all permission-related scenarios:
- Operations without sudo
- Operations with sudo but password required
- Operations with permission denied errors
- Permission check methods
- User-friendly error messages
"""

from __future__ import annotations

import os
import pytest
from unittest.mock import patch, MagicMock

from update_alternatives_tui.service import AlternativesService
from update_alternatives_tui.executor import MockExecutor, ExecutionResult
from update_alternatives_tui.models import InstallRequest


# ============================================================================
# Test Data
# ============================================================================

SELECTIONS_OUTPUT = """\
editor auto /bin/nano
python auto /usr/bin/python3
"""

QUERY_OUTPUT = """\
Name: editor
Link: /usr/bin/editor
Status: auto
Best: /bin/nano
Value: /bin/nano

Alternative: /bin/nano
Priority: 40
"""


# ============================================================================
# Permission Error Detection Tests
# ============================================================================

class TestPermissionErrorDetection:
    """Tests for detecting permission-related errors."""

    @pytest.fixture
    def service(self) -> AlternativesService:
        """Provide a service with mock executor."""
        return AlternativesService(executor=MockExecutor(), use_sudo=False)

    def test_detect_permission_denied_lowercase(self, service: AlternativesService) -> None:
        """Test detection of lowercase permission denied."""
        assert service._is_permission_denied_error("permission denied")

    def test_detect_permission_denied_uppercase(self, service: AlternativesService) -> None:
        """Test detection of uppercase permission denied."""
        assert service._is_permission_denied_error("PERMISSION DENIED")

    def test_detect_permission_denied_mixed_case(self, service: AlternativesService) -> None:
        """Test detection of mixed case permission denied."""
        assert service._is_permission_denied_error("Permission Denied")

    def test_detect_permission_denied_in_message(self, service: AlternativesService) -> None:
        """Test detection when permission denied is part of longer message."""
        error = "update-alternatives: error: error creating symbolic link: Permission denied"
        assert service._is_permission_denied_error(error)

    def test_detect_operation_not_permitted(self, service: AlternativesService) -> None:
        """Test detection of 'operation not permitted' error."""
        assert service._is_permission_denied_error("operation not permitted")

    def test_detect_access_denied(self, service: AlternativesService) -> None:
        """Test detection of 'access denied' error."""
        assert service._is_permission_denied_error("access denied")

    def test_detect_eacces(self, service: AlternativesService) -> None:
        """Test detection of EACCES error code."""
        assert service._is_permission_denied_error("EACCES: permission denied")

    def test_not_permission_error(self, service: AlternativesService) -> None:
        """Test that unrelated errors are not flagged."""
        assert not service._is_permission_denied_error("file not found")
        assert not service._is_permission_denied_error("invalid argument")
        assert not service._is_permission_denied_error("")


class TestSudoPasswordErrorDetection:
    """Tests for detecting sudo password errors."""

    @pytest.fixture
    def service(self) -> AlternativesService:
        """Provide a service with mock executor."""
        return AlternativesService(executor=MockExecutor(), use_sudo=True)

    def test_detect_password_required(self, service: AlternativesService) -> None:
        """Test detection of password required message."""
        assert service._is_sudo_password_error("sudo: a password is required")

    def test_detect_terminal_required(self, service: AlternativesService) -> None:
        """Test detection of terminal required message."""
        assert service._is_sudo_password_error("sudo: a terminal is required to read the password")

    def test_detect_no_tty(self, service: AlternativesService) -> None:
        """Test detection of no tty message."""
        assert service._is_sudo_password_error("no tty present and no askpass program specified")

    def test_detect_must_have_tty(self, service: AlternativesService) -> None:
        """Test detection of must have tty message."""
        assert service._is_sudo_password_error("sorry, you must have a tty to run sudo")

    def test_not_sudo_error(self, service: AlternativesService) -> None:
        """Test that unrelated errors are not flagged."""
        assert not service._is_sudo_password_error("permission denied")
        assert not service._is_sudo_password_error("command not found")


# ============================================================================
# Error Message Formatting Tests
# ============================================================================

class TestErrorMessageFormatting:
    """Tests for user-friendly error message formatting."""

    @pytest.fixture
    def service_with_sudo(self) -> AlternativesService:
        """Provide a service with sudo enabled."""
        return AlternativesService(executor=MockExecutor(), use_sudo=True)

    @pytest.fixture
    def service_without_sudo(self) -> AlternativesService:
        """Provide a service without sudo."""
        return AlternativesService(executor=MockExecutor(), use_sudo=False)

    def test_format_sudo_password_error(self, service_with_sudo: AlternativesService) -> None:
        """Test formatting of sudo password error."""
        error = "sudo: a password is required"
        message = service_with_sudo._format_error_message(error, "default")
        
        assert "Permission denied" in message
        assert "sudo requires authentication" in message
        assert "sudo -v" in message

    def test_format_permission_denied_with_sudo(
        self, service_with_sudo: AlternativesService
    ) -> None:
        """Test formatting of permission denied when sudo is enabled."""
        error = "error creating symbolic link: Permission denied"
        message = service_with_sudo._format_error_message(error, "default")
        
        assert "Permission denied" in message
        assert "even with sudo" in message
        assert "sudo configuration" in message

    def test_format_permission_denied_without_sudo(
        self, service_without_sudo: AlternativesService
    ) -> None:
        """Test formatting of permission denied when sudo is disabled."""
        error = "error creating symbolic link: Permission denied"
        message = service_without_sudo._format_error_message(error, "default")
        
        assert "Permission denied" in message
        assert "requires root privileges" in message
        assert "sudo" in message

    def test_format_empty_error_uses_default(
        self, service_with_sudo: AlternativesService
    ) -> None:
        """Test that empty error returns default message."""
        message = service_with_sudo._format_error_message("", "default message")
        assert message == "default message"

    def test_format_other_error_unchanged(
        self, service_with_sudo: AlternativesService
    ) -> None:
        """Test that non-permission errors are unchanged."""
        error = "alternative not found"
        message = service_with_sudo._format_error_message(error, "default")
        assert message == error


# ============================================================================
# Permission Check Tests
# ============================================================================

class TestPermissionCheck:
    """Tests for permission checking methods."""

    def test_can_modify_with_sudo_enabled(self) -> None:
        """Test that can_modify returns True when sudo is enabled."""
        service = AlternativesService(executor=MockExecutor(), use_sudo=True)
        assert service.can_modify() is True

    def test_can_modify_without_sudo_no_permission(self) -> None:
        """Test can_modify without sudo and no write permission."""
        service = AlternativesService(executor=MockExecutor(), use_sudo=False)
        
        with patch("os.access", return_value=False):
            assert service.can_modify() is False

    def test_can_modify_without_sudo_with_permission(self) -> None:
        """Test can_modify without sudo but with write permission (root user)."""
        service = AlternativesService(executor=MockExecutor(), use_sudo=False)
        
        with patch("os.access", return_value=True):
            assert service.can_modify() is True

    def test_check_permission_success(self) -> None:
        """Test check_permission when modifications allowed."""
        service = AlternativesService(executor=MockExecutor(), use_sudo=True)
        
        result = service.check_permission()
        assert result.success is True
        assert "Permission check passed" in result.message

    def test_check_permission_failure(self) -> None:
        """Test check_permission when modifications not allowed."""
        service = AlternativesService(executor=MockExecutor(), use_sudo=False)
        
        with patch("os.access", return_value=False):
            result = service.check_permission()
            assert result.success is False
            assert "Permission denied" in result.message
            assert "root privileges" in result.message


# ============================================================================
# Operation Permission Tests
# ============================================================================

class TestOperationPermissions:
    """Tests for permission handling in actual operations."""

    @pytest.fixture
    def mock_executor(self) -> MockExecutor:
        """Provide configured mock executor."""
        executor = MockExecutor()
        executor.set_response(["--get-selections"], ExecutionResult.ok(SELECTIONS_OUTPUT))
        executor.set_response(["--query", "editor"], ExecutionResult.ok(QUERY_OUTPUT))
        return executor

    def test_set_alternative_permission_denied_without_sudo(
        self, mock_executor: MockExecutor
    ) -> None:
        """Test set_alternative fails gracefully without sudo."""
        mock_executor.set_response(
            ["--set", "editor", "/bin/nano"],
            ExecutionResult.error(
                "update-alternatives: error: error creating symbolic link "
                "'/etc/alternatives/editor.dpkg-tmp': Permission denied",
                return_code=2
            ),
        )
        
        service = AlternativesService(executor=mock_executor, use_sudo=False)
        result = service.set_alternative("editor", "/bin/nano")
        
        assert result.success is False
        assert "Permission denied" in result.message
        assert "root privileges" in result.message

    def test_set_alternative_sudo_password_required(
        self, mock_executor: MockExecutor
    ) -> None:
        """Test set_alternative handles sudo password requirement."""
        # MockExecutor uses args without sudo prefix, the use_sudo flag is separate
        mock_executor.set_response(
            ["--set", "editor", "/bin/nano"],
            ExecutionResult.error("sudo: a password is required", return_code=1),
        )
        
        service = AlternativesService(executor=mock_executor, use_sudo=True)
        result = service.set_alternative("editor", "/bin/nano")
        
        assert result.success is False
        assert "sudo requires authentication" in result.message

    def test_set_auto_permission_denied(self, mock_executor: MockExecutor) -> None:
        """Test set_auto handles permission denied."""
        mock_executor.set_response(
            ["--auto", "editor"],
            ExecutionResult.error("Permission denied", return_code=2),
        )
        
        service = AlternativesService(executor=mock_executor, use_sudo=False)
        result = service.set_auto("editor")
        
        assert result.success is False
        assert "Permission denied" in result.message

    def test_install_permission_denied(self, mock_executor: MockExecutor) -> None:
        """Test install handles permission denied."""
        mock_executor.set_response(
            ["--install", "/usr/bin/test", "test", "/bin/ls", "10"],
            ExecutionResult.error(
                "error creating symbolic link: Permission denied",
                return_code=2
            ),
        )
        
        service = AlternativesService(executor=mock_executor, use_sudo=False)
        request = InstallRequest(
            name="test",
            link="/usr/bin/test",
            path="/bin/ls",
            priority=10
        )
        result = service.install(request)
        
        assert result.success is False
        assert "Permission denied" in result.message

    def test_remove_permission_denied(self, mock_executor: MockExecutor) -> None:
        """Test remove handles permission denied."""
        mock_executor.set_response(
            ["--remove", "editor", "/bin/nano"],
            ExecutionResult.error("Permission denied", return_code=2),
        )
        
        service = AlternativesService(executor=mock_executor, use_sudo=False)
        result = service.remove("editor", "/bin/nano")
        
        assert result.success is False
        assert "Permission denied" in result.message

    def test_remove_all_permission_denied(self, mock_executor: MockExecutor) -> None:
        """Test remove_all handles permission denied."""
        mock_executor.set_response(
            ["--remove-all", "editor"],
            ExecutionResult.error("Permission denied", return_code=2),
        )
        
        service = AlternativesService(executor=mock_executor, use_sudo=False)
        result = service.remove_all("editor")
        
        assert result.success is False
        assert "Permission denied" in result.message


# ============================================================================
# Read-Only Operations (No Permission Required)
# ============================================================================

class TestReadOnlyOperations:
    """Tests verifying read-only operations don't require special permissions."""

    @pytest.fixture
    def mock_executor(self) -> MockExecutor:
        """Provide configured mock executor."""
        executor = MockExecutor()
        executor.set_response(["--get-selections"], ExecutionResult.ok(SELECTIONS_OUTPUT))
        executor.set_response(["--query", "editor"], ExecutionResult.ok(QUERY_OUTPUT))
        executor.set_response(["--display", "editor"], ExecutionResult.ok("display output"))
        executor.set_response(["--list", "editor"], ExecutionResult.ok("/bin/nano\n"))
        return executor

    @pytest.fixture
    def service(self, mock_executor: MockExecutor) -> AlternativesService:
        """Provide service without sudo to verify read-only works."""
        return AlternativesService(executor=mock_executor, use_sudo=False)

    def test_list_all_no_permission_needed(self, service: AlternativesService) -> None:
        """Test list_all works without sudo."""
        names = service.list_all()
        assert "editor" in names

    def test_get_selections_no_permission_needed(self, service: AlternativesService) -> None:
        """Test get_selections works without sudo."""
        selections = service.get_selections()
        assert "editor" in selections

    def test_get_details_no_permission_needed(self, service: AlternativesService) -> None:
        """Test get_details works without sudo."""
        group = service.get_details("editor")
        assert group is not None
        assert group.name == "editor"

    def test_get_display_no_permission_needed(self, service: AlternativesService) -> None:
        """Test get_display works without sudo."""
        result = service.get_display("editor")
        assert result.success is True

    def test_list_paths_no_permission_needed(self, service: AlternativesService) -> None:
        """Test list_paths works without sudo."""
        paths = service.list_paths("editor")
        assert "/bin/nano" in paths

    def test_search_no_permission_needed(self, service: AlternativesService) -> None:
        """Test search works without sudo."""
        results = service.search("edit")
        assert "editor" in results

    def test_exists_no_permission_needed(self, service: AlternativesService) -> None:
        """Test exists works without sudo."""
        assert service.exists("editor") is True

    def test_get_current_path_no_permission_needed(
        self, service: AlternativesService
    ) -> None:
        """Test get_current_path works without sudo."""
        path = service.get_current_path("editor")
        assert path == "/bin/nano"

    def test_get_status_no_permission_needed(self, service: AlternativesService) -> None:
        """Test get_status works without sudo."""
        from update_alternatives_tui.models import AlternativeStatus
        status = service.get_status("editor")
        assert status == AlternativeStatus.AUTO


# ============================================================================
# Real-World Error Message Tests
# ============================================================================

class TestRealWorldErrorMessages:
    """Tests using real error messages from update-alternatives."""

    @pytest.fixture
    def service_no_sudo(self) -> AlternativesService:
        """Service without sudo."""
        return AlternativesService(executor=MockExecutor(), use_sudo=False)

    def test_real_symlink_permission_error(
        self, service_no_sudo: AlternativesService
    ) -> None:
        """Test real symlink permission error from update-alternatives."""
        real_error = (
            "update-alternatives: error: error creating symbolic link "
            "'/etc/alternatives/editor.dpkg-tmp': Permission denied"
        )
        
        message = service_no_sudo._format_error_message(real_error, "default")
        assert "Permission denied" in message
        assert "root privileges" in message

    def test_real_admindir_permission_error(
        self, service_no_sudo: AlternativesService
    ) -> None:
        """Test real admindir permission error."""
        real_error = (
            "update-alternatives: error: unable to create "
            "'/var/lib/dpkg/alternatives/test': Permission denied"
        )
        
        message = service_no_sudo._format_error_message(real_error, "default")
        assert "Permission denied" in message

    def test_real_removal_permission_error(
        self, service_no_sudo: AlternativesService
    ) -> None:
        """Test real removal permission error."""
        real_error = "update-alternatives: error: cannot remove: Permission denied"
        
        message = service_no_sudo._format_error_message(real_error, "default")
        assert "Permission denied" in message


# ============================================================================
# Integration Tests with Real System (Marked as requires_sudo)
# ============================================================================

@pytest.mark.requires_sudo
class TestRealSystemPermissions:
    """Integration tests that verify real system permission handling.
    
    These tests are skipped by default. Run with:
        pytest -m requires_sudo
    """

    def test_real_permission_denied_without_sudo(self) -> None:
        """Test real command execution without sudo."""
        from update_alternatives_tui.executor import SubprocessExecutor
        
        executor = SubprocessExecutor()
        service = AlternativesService(executor=executor, use_sudo=False)
        
        # This should fail with permission denied
        result = service.set_alternative("editor", "/bin/nano")
        
        assert result.success is False
        assert "Permission denied" in result.message or "permission denied" in result.stderr.lower()
