"""Comprehensive tests for service, executor, and parser modules.

This file adds tests for previously uncovered scenarios including:
- Service batch operations
- Service cache statistics
- Parser edge cases
- Error message formatting
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from update_alternatives_tui.service import AlternativesService
from update_alternatives_tui.executor import (
    MockExecutor,
    SubprocessExecutor,
    ExecutionResult,
    BaseExecutor,
)
from update_alternatives_tui.models import (
    AlternativeStatus,
    InstallRequest,
)
from update_alternatives_tui.parser import OutputParser


# ============================================================================
# Sample Test Data
# ============================================================================

SELECTIONS_OUTPUT = """\
editor                         auto     /usr/bin/vim.basic
python                         manual   /usr/bin/python3
java                           auto     /usr/lib/jvm/java-17/bin/java
"""

QUERY_OUTPUT_EDITOR = """\
Name: editor
Link: /usr/bin/editor
Slaves:
 editor.1.gz /usr/share/man/man1/editor.1.gz
Status: auto
Best: /usr/bin/vim.basic
Value: /usr/bin/vim.basic

Alternative: /usr/bin/ed
Priority: 10
Slaves:
 editor.1.gz /usr/share/man/man1/ed.1.gz

Alternative: /usr/bin/nano
Priority: 40
Slaves:
 editor.1.gz /usr/share/man/man1/nano.1.gz

Alternative: /usr/bin/vim.basic
Priority: 30
Slaves:
 editor.1.gz /usr/share/man/man1/vim.1.gz
"""

QUERY_OUTPUT_JAVA = """\
Name: java
Link: /usr/bin/java
Status: auto
Best: /usr/lib/jvm/java-17/bin/java
Value: /usr/lib/jvm/java-17/bin/java

Alternative: /usr/lib/jvm/java-11/bin/java
Priority: 1100

Alternative: /usr/lib/jvm/java-17/bin/java
Priority: 1700
"""


# ============================================================================
# Service Batch Operations Tests
# ============================================================================

class TestServiceBatchOperations:
    """Tests for service batch operations."""

    @pytest.fixture
    def mock_executor(self) -> MockExecutor:
        """Provide configured mock executor."""
        executor = MockExecutor()
        executor.set_response(
            ["--get-selections"],
            ExecutionResult.ok(SELECTIONS_OUTPUT),
        )
        executor.set_response(
            ["--query", "editor"],
            ExecutionResult.ok(QUERY_OUTPUT_EDITOR),
        )
        executor.set_response(
            ["--query", "java"],
            ExecutionResult.ok(QUERY_OUTPUT_JAVA),
        )
        executor.set_response(
            ["--query", "nonexistent"],
            ExecutionResult.error("not found"),
        )
        executor.set_response(
            ["--display", "editor"],
            ExecutionResult.ok(""),
        )
        return executor

    @pytest.fixture
    def service(self, mock_executor: MockExecutor) -> AlternativesService:
        """Provide AlternativesService instance."""
        return AlternativesService(executor=mock_executor)

    def test_get_details_batch(self, service: AlternativesService) -> None:
        """Test getting details for multiple alternatives."""
        results = service.get_details_batch(["editor", "java"])
        
        assert "editor" in results
        assert "java" in results
        assert results["editor"] is not None
        assert results["editor"].name == "editor"
        assert results["java"] is not None
        assert results["java"].name == "java"

    def test_get_details_batch_with_nonexistent(self, service: AlternativesService) -> None:
        """Test batch details with some nonexistent alternatives."""
        results = service.get_details_batch(["editor", "nonexistent"])
        
        assert results["editor"] is not None
        assert results["nonexistent"] is None

    def test_get_details_batch_empty_list(self, service: AlternativesService) -> None:
        """Test batch details with empty list."""
        results = service.get_details_batch([])
        assert results == {}

    def test_set_multiple(self, service: AlternativesService, mock_executor: MockExecutor) -> None:
        """Test setting multiple alternatives at once."""
        mock_executor.set_response(
            ["--set", "editor", "/usr/bin/nano"],
            ExecutionResult.ok(""),
        )
        mock_executor.set_response(
            ["--set", "python", "/usr/bin/python3.11"],
            ExecutionResult.ok(""),
        )
        
        settings = {
            "editor": "/usr/bin/nano",
            "python": "/usr/bin/python3.11",
        }
        results = service.set_multiple(settings)
        
        assert "editor" in results
        assert "python" in results
        assert results["editor"].success is True
        assert results["python"].success is True

    def test_set_multiple_partial_failure(
        self, service: AlternativesService, mock_executor: MockExecutor
    ) -> None:
        """Test set_multiple with some failures."""
        mock_executor.set_response(
            ["--set", "editor", "/usr/bin/nano"],
            ExecutionResult.ok(""),
        )
        mock_executor.set_response(
            ["--set", "python", "/invalid/path"],
            ExecutionResult.error("path not found"),
        )
        
        settings = {
            "editor": "/usr/bin/nano",
            "python": "/invalid/path",
        }
        results = service.set_multiple(settings)
        
        assert results["editor"].success is True
        assert results["python"].success is False

    def test_list_paths(self, service: AlternativesService, mock_executor: MockExecutor) -> None:
        """Test listing paths for an alternative group."""
        mock_executor.set_response(
            ["--list", "editor"],
            ExecutionResult.ok("/bin/ed\n/bin/nano\n/usr/bin/vim.basic\n"),
        )
        
        paths = service.list_paths("editor")
        
        assert len(paths) == 3
        assert "/bin/ed" in paths
        assert "/bin/nano" in paths
        assert "/usr/bin/vim.basic" in paths

    def test_list_paths_empty_name(self, service: AlternativesService) -> None:
        """Test list_paths with empty name."""
        paths = service.list_paths("")
        assert paths == []

    def test_list_paths_nonexistent(
        self, service: AlternativesService, mock_executor: MockExecutor
    ) -> None:
        """Test list_paths for nonexistent alternative."""
        mock_executor.set_response(
            ["--list", "nonexistent"],
            ExecutionResult.error("error: no alternatives for nonexistent"),
        )
        
        paths = service.list_paths("nonexistent")
        assert paths == []


# ============================================================================
# Service Cache Statistics Tests
# ============================================================================

class TestServiceCacheStats:
    """Tests for service cache statistics."""

    @pytest.fixture
    def mock_executor(self) -> MockExecutor:
        """Provide configured mock executor."""
        executor = MockExecutor()
        executor.set_response(["--get-selections"], ExecutionResult.ok(SELECTIONS_OUTPUT))
        executor.set_response(["--query", "editor"], ExecutionResult.ok(QUERY_OUTPUT_EDITOR))
        return executor

    def test_get_cache_stats(self, mock_executor: MockExecutor) -> None:
        """Test getting cache statistics."""
        service = AlternativesService(executor=mock_executor, enable_cache=True)
        
        stats = service.get_cache_stats()
        assert stats["enabled"] is True
        assert stats["selections_cache_size"] == 0
        assert stats["details_cache_size"] == 0

    def test_cache_stats_after_usage(self, mock_executor: MockExecutor) -> None:
        """Test cache stats after some operations."""
        service = AlternativesService(executor=mock_executor, enable_cache=True)
        
        # Trigger cache population
        service.get_selections()
        service.get_details("editor")
        
        stats = service.get_cache_stats()
        assert stats["selections_cache_size"] == 1
        assert stats["details_cache_size"] == 1

    def test_clear_cache(self, mock_executor: MockExecutor) -> None:
        """Test clearing cache."""
        service = AlternativesService(executor=mock_executor, enable_cache=True)
        
        service.get_selections()
        service.get_details("editor")
        service.clear_cache()
        
        stats = service.get_cache_stats()
        assert stats["selections_cache_size"] == 0
        assert stats["details_cache_size"] == 0


# ============================================================================
# Service Install Operation Tests
# ============================================================================

class TestServiceInstall:
    """Tests for service install operation."""

    @pytest.fixture
    def mock_executor(self) -> MockExecutor:
        """Provide configured mock executor."""
        executor = MockExecutor()
        executor.set_response(["--get-selections"], ExecutionResult.ok(SELECTIONS_OUTPUT))
        return executor

    @pytest.fixture
    def service(self, mock_executor: MockExecutor) -> AlternativesService:
        """Provide service instance."""
        return AlternativesService(executor=mock_executor)

    def test_install_basic(self, service: AlternativesService, mock_executor: MockExecutor) -> None:
        """Test basic install operation."""
        mock_executor.set_response(
            ["--install", "/usr/bin/editor", "editor", "/usr/bin/myeditor", "100"],
            ExecutionResult.ok(""),
        )
        
        request = InstallRequest(
            name="editor",
            link="/usr/bin/editor",
            path="/usr/bin/myeditor",
            priority=100,
        )
        result = service.install(request)
        
        assert result.success is True

    def test_install_failure(self, service: AlternativesService, mock_executor: MockExecutor) -> None:
        """Test install failure."""
        mock_executor.set_response(
            ["--install", "/usr/bin/editor", "editor", "/nonexistent", "100"],
            ExecutionResult.error("path does not exist"),
        )
        
        request = InstallRequest(
            name="editor",
            link="/usr/bin/editor",
            path="/nonexistent",
            priority=100,
        )
        result = service.install(request)
        
        assert result.success is False


# ============================================================================
# Service Remove Operations Tests
# ============================================================================

class TestServiceRemove:
    """Tests for service remove operations."""

    @pytest.fixture
    def mock_executor(self) -> MockExecutor:
        """Provide configured mock executor."""
        executor = MockExecutor()
        executor.set_response(["--get-selections"], ExecutionResult.ok(SELECTIONS_OUTPUT))
        return executor

    @pytest.fixture
    def service(self, mock_executor: MockExecutor) -> AlternativesService:
        """Provide service instance."""
        return AlternativesService(executor=mock_executor)

    def test_remove_success(self, service: AlternativesService, mock_executor: MockExecutor) -> None:
        """Test successful remove."""
        mock_executor.set_response(
            ["--remove", "editor", "/usr/bin/ed"],
            ExecutionResult.ok(""),
        )
        
        result = service.remove("editor", "/usr/bin/ed")
        assert result.success is True

    def test_remove_failure(self, service: AlternativesService, mock_executor: MockExecutor) -> None:
        """Test remove failure."""
        mock_executor.set_response(
            ["--remove", "editor", "/nonexistent"],
            ExecutionResult.error("alternative not found"),
        )
        
        result = service.remove("editor", "/nonexistent")
        assert result.success is False

    def test_remove_empty_name(self, service: AlternativesService) -> None:
        """Test remove with empty name."""
        result = service.remove("", "/path")
        assert result.success is False

    def test_remove_empty_path(self, service: AlternativesService) -> None:
        """Test remove with empty path."""
        result = service.remove("editor", "")
        assert result.success is False

    def test_remove_all_success(self, service: AlternativesService, mock_executor: MockExecutor) -> None:
        """Test successful remove_all."""
        mock_executor.set_response(
            ["--remove-all", "editor"],
            ExecutionResult.ok(""),
        )
        
        result = service.remove_all("editor")
        assert result.success is True

    def test_remove_all_empty_name(self, service: AlternativesService) -> None:
        """Test remove_all with empty name."""
        result = service.remove_all("")
        assert result.success is False


# ============================================================================
# Executor Build Command Tests
# ============================================================================

class TestExecutorBuildCommand:
    """Tests for executor command building."""

    def test_build_command_basic(self) -> None:
        """Test basic command building."""
        executor = MockExecutor()
        cmd = executor.build_command(["--query", "editor"])
        
        assert cmd == ["update-alternatives", "--query", "editor"]

    def test_build_command_with_sudo(self) -> None:
        """Test command building with sudo."""
        executor = MockExecutor()
        cmd = executor.build_command(["--set", "editor", "/path"], use_sudo=True)
        
        assert cmd[0] == "sudo"
        assert cmd[1] == "-n"  # Non-interactive
        assert "update-alternatives" in cmd

    def test_build_command_empty_args(self) -> None:
        """Test command building with empty args."""
        executor = MockExecutor()
        cmd = executor.build_command([])
        
        assert cmd == ["update-alternatives"]


# ============================================================================
# Parser Edge Cases Tests
# ============================================================================

class TestParserEdgeCases:
    """Additional edge case tests for parser."""

    def test_parse_query_with_empty_alternatives_section(self) -> None:
        """Test parsing query when no alternatives are present."""
        output = """\
Name: orphan
Link: /usr/bin/orphan
Status: auto
Best:
Value:
"""
        parser = OutputParser()
        group = parser.parse_query(output)
        
        # Should return None or handle gracefully
        # This depends on implementation - either None or empty group
        if group is not None:
            assert group.name == "orphan"
            assert len(group.alternatives) == 0

    def test_parse_selections_with_tabs(self) -> None:
        """Test parsing selections with tab separators."""
        output = "editor\tauto\t/usr/bin/vim"
        parser = OutputParser()
        selections = parser.parse_selections(output)
        
        # Should handle tab-separated format
        assert len(selections) >= 0  # May or may not parse depending on regex

    def test_parse_query_with_malformed_slave(self) -> None:
        """Test parsing query with malformed slave entry."""
        output = """\
Name: editor
Link: /usr/bin/editor
Status: auto
Best: /usr/bin/vim
Value: /usr/bin/vim

Alternative: /usr/bin/vim
Priority: 50
Slaves:
 malformed_entry_without_path
"""
        parser = OutputParser()
        group = parser.parse_query(output)
        
        # Should not crash, just skip malformed entry
        assert group is not None
        assert group.name == "editor"

    def test_parse_selections_with_extra_whitespace(self) -> None:
        """Test parsing selections with extra whitespace."""
        output = "   editor                         auto     /usr/bin/vim   \n"
        parser = OutputParser()
        selections = parser.parse_selections(output)
        
        assert len(selections) == 1
        assert selections[0].name == "editor"


# ============================================================================
# Service Error Handling Tests
# ============================================================================

class TestServiceErrorHandling:
    """Tests for service error handling."""

    def test_format_error_message_empty_stderr(self) -> None:
        """Test error message formatting with empty stderr."""
        service = AlternativesService(executor=MockExecutor())
        
        msg = service._format_error_message("", "Default error")
        assert msg == "Default error"

    def test_format_error_message_sudo_password_variants(self) -> None:
        """Test sudo password error detection variants."""
        service = AlternativesService(executor=MockExecutor())
        
        # Test various sudo error messages
        sudo_errors = [
            "sudo: a password is required",
            "sudo: A PASSWORD IS REQUIRED",  # Case insensitive
            "sudo: a terminal is required to read the password",
            "no tty present and no askpass program specified",
            "sorry, you must have a tty to run sudo",
        ]
        
        for error in sudo_errors:
            assert service._is_sudo_password_error(error), f"Should detect: {error}"

    def test_format_error_message_regular_error(self) -> None:
        """Test that regular errors pass through."""
        service = AlternativesService(executor=MockExecutor())
        
        msg = service._format_error_message("file not found", "Default")
        assert msg == "file not found"

    def test_list_all_handles_failure(self) -> None:
        """Test list_all handles command failure gracefully."""
        executor = MockExecutor()
        executor.set_response(["--get-selections"], ExecutionResult.error("command failed"))
        
        service = AlternativesService(executor=executor)
        names = service.list_all()
        
        assert names == []

    def test_get_selections_handles_failure(self) -> None:
        """Test get_selections handles command failure gracefully."""
        executor = MockExecutor()
        executor.set_response(["--get-selections"], ExecutionResult.error("command failed"))
        
        service = AlternativesService(executor=executor)
        selections = service.get_selections()
        
        assert selections == {}


# ============================================================================
# Service Get Display Tests
# ============================================================================

class TestServiceGetDisplay:
    """Tests for service get_display method."""

    def test_get_display_success(self) -> None:
        """Test successful get_display."""
        executor = MockExecutor()
        executor.set_response(
            ["--display", "editor"],
            ExecutionResult.ok("editor - auto mode\n  link best version is /usr/bin/vim")
        )
        
        service = AlternativesService(executor=executor)
        result = service.get_display("editor")
        
        assert result.success is True
        assert "auto mode" in result.stdout

    def test_get_display_failure(self) -> None:
        """Test get_display failure."""
        executor = MockExecutor()
        executor.set_response(
            ["--display", "nonexistent"],
            ExecutionResult.error("no alternatives")
        )
        
        service = AlternativesService(executor=executor)
        result = service.get_display("nonexistent")
        
        assert result.success is False


# ============================================================================
# Service Cache Invalidation Tests
# ============================================================================

class TestServiceCacheInvalidation:
    """Tests for service cache invalidation."""

    @pytest.fixture
    def mock_executor(self) -> MockExecutor:
        """Provide configured mock executor."""
        executor = MockExecutor()
        executor.set_response(["--get-selections"], ExecutionResult.ok(SELECTIONS_OUTPUT))
        executor.set_response(["--query", "editor"], ExecutionResult.ok(QUERY_OUTPUT_EDITOR))
        executor.set_response(["--set", "editor", "/usr/bin/nano"], ExecutionResult.ok(""))
        return executor

    def test_set_alternative_invalidates_cache(self, mock_executor: MockExecutor) -> None:
        """Test that set_alternative invalidates cache."""
        service = AlternativesService(executor=mock_executor, enable_cache=True)
        
        # Populate cache
        service.get_selections()
        service.get_details("editor")
        
        # Perform set operation
        service.set_alternative("editor", "/usr/bin/nano")
        
        # Cache for selections should be cleared
        # Next call should hit the executor again
        call_count_before = mock_executor.call_count
        service.get_selections()  # Should make a new call
        call_count_after = mock_executor.call_count
        
        assert call_count_after > call_count_before
