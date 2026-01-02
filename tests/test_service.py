"""Tests for update_alternatives_tui.service module.

Tests cover:
- Service initialization
- Cache behavior
- Alternative operations
- History tracking
- Error handling
"""

from __future__ import annotations

import pytest

from update_alternatives_tui.service import (
    AlternativesService,
    Cache,
)
from update_alternatives_tui.executor import MockExecutor, ExecutionResult
from update_alternatives_tui.models import (
    AlternativeStatus,
    CommandResult,
)


# Sample outputs for testing
SELECTIONS_OUTPUT = """\
editor                         auto     /usr/bin/vim.basic
python                         manual   /usr/bin/python3
"""

QUERY_OUTPUT = """\
Name: editor
Link: /usr/bin/editor
Status: auto
Best: /usr/bin/vim.basic
Value: /usr/bin/vim.basic

Alternative: /usr/bin/ed
Priority: 10

Alternative: /usr/bin/nano
Priority: 40

Alternative: /usr/bin/vim.basic
Priority: 30
"""


class TestCache:
    """Tests for Cache class."""

    def test_cache_set_and_get(self) -> None:
        """Test basic cache set and get."""
        cache: Cache[str] = Cache()
        cache.set("key", "value", ttl=60)
        
        assert cache.get("key") == "value"

    def test_cache_miss(self) -> None:
        """Test cache miss returns None."""
        cache: Cache[str] = Cache()
        
        assert cache.get("nonexistent") is None

    def test_cache_delete(self) -> None:
        """Test cache delete."""
        cache: Cache[str] = Cache()
        cache.set("key", "value", ttl=60)
        cache.delete("key")
        
        assert cache.get("key") is None

    def test_cache_clear(self) -> None:
        """Test cache clear."""
        cache: Cache[str] = Cache()
        cache.set("key1", "value1", ttl=60)
        cache.set("key2", "value2", ttl=60)
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_size(self) -> None:
        """Test cache size property."""
        cache: Cache[str] = Cache()
        
        assert cache.size == 0
        cache.set("key1", "value1", ttl=60)
        assert cache.size == 1
        cache.set("key2", "value2", ttl=60)
        assert cache.size == 2

    def test_cache_hit_rate(self) -> None:
        """Test cache hit rate."""
        cache: Cache[str] = Cache()
        cache.set("key", "value", ttl=60)
        
        # Hit
        cache.get("key")
        # Miss
        cache.get("nonexistent")
        
        # 1 hit, 1 miss = 50%
        assert cache.hit_rate == 50.0


class TestAlternativesService:
    """Tests for AlternativesService class."""

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
            ExecutionResult.ok(QUERY_OUTPUT),
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

    def test_service_creation(self, service: AlternativesService) -> None:
        """Test service can be created."""
        assert service is not None

    def test_list_all(self, service: AlternativesService) -> None:
        """Test listing all alternatives."""
        names = service.list_all()
        
        assert "editor" in names
        assert "python" in names

    def test_get_selections(self, service: AlternativesService) -> None:
        """Test getting all selections."""
        selections = service.get_selections()
        
        assert "editor" in selections
        assert "python" in selections
        assert selections["editor"].mode == AlternativeStatus.AUTO
        assert selections["python"].mode == AlternativeStatus.MANUAL

    def test_get_details(self, service: AlternativesService) -> None:
        """Test getting details for an alternative."""
        group = service.get_details("editor")
        
        assert group is not None
        assert group.name == "editor"
        assert group.status == AlternativeStatus.AUTO
        assert len(group.alternatives) == 3

    def test_get_details_not_found(self, service: AlternativesService, mock_executor: MockExecutor) -> None:
        """Test getting details for nonexistent alternative."""
        mock_executor.set_response(
            ["--query", "nonexistent"],
            ExecutionResult.error("not found"),
        )
        
        result = service.get_details("nonexistent")
        assert result is None

    def test_caching(self, service: AlternativesService, mock_executor: MockExecutor) -> None:
        """Test that results are cached."""
        # First call
        service.get_selections()
        call_count_1 = mock_executor.call_count
        
        # Second call should use cache
        service.get_selections()
        call_count_2 = mock_executor.call_count
        
        assert call_count_1 == call_count_2  # No additional calls

    def test_search(self, service: AlternativesService) -> None:
        """Test searching alternatives."""
        results = service.search("edit")
        
        assert "editor" in results

    def test_exists(self, service: AlternativesService) -> None:
        """Test exists method."""
        assert service.exists("editor") is True
        assert service.exists("nonexistent") is False

    def test_get_current_path(self, service: AlternativesService) -> None:
        """Test get_current_path method."""
        path = service.get_current_path("editor")
        assert path == "/usr/bin/vim.basic"

    def test_get_status(self, service: AlternativesService) -> None:
        """Test get_status method."""
        status = service.get_status("editor")
        assert status == AlternativeStatus.AUTO
        
        status = service.get_status("python")
        assert status == AlternativeStatus.MANUAL

    def test_is_auto(self, service: AlternativesService) -> None:
        """Test is_auto method."""
        assert service.is_auto("editor") is True
        assert service.is_auto("python") is False

    def test_is_manual(self, service: AlternativesService) -> None:
        """Test is_manual method."""
        assert service.is_manual("python") is True
        assert service.is_manual("editor") is False


class TestServiceOperations:
    """Tests for service modification operations."""

    @pytest.fixture
    def mock_executor(self) -> MockExecutor:
        """Provide mock executor for modification tests."""
        executor = MockExecutor()
        executor.set_response(
            ["--get-selections"],
            ExecutionResult.ok(SELECTIONS_OUTPUT),
        )
        executor.set_response(
            ["--query", "editor"],
            ExecutionResult.ok(QUERY_OUTPUT),
        )
        executor.set_response(
            ["--display", "editor"],
            ExecutionResult.ok(""),
        )
        return executor

    @pytest.fixture
    def service(self, mock_executor: MockExecutor) -> AlternativesService:
        """Provide service for testing."""
        return AlternativesService(executor=mock_executor)

    def test_set_alternative(self, service: AlternativesService, mock_executor: MockExecutor) -> None:
        """Test setting alternative."""
        mock_executor.set_response(
            ["--set", "editor", "/usr/bin/nano"],
            ExecutionResult.ok(""),
        )
        
        result = service.set_alternative("editor", "/usr/bin/nano")
        
        assert result.success is True
        assert mock_executor.was_called_with(["--set", "editor", "/usr/bin/nano"])

    def test_set_auto(self, service: AlternativesService, mock_executor: MockExecutor) -> None:
        """Test setting auto mode."""
        mock_executor.set_response(
            ["--auto", "editor"],
            ExecutionResult.ok(""),
        )
        
        result = service.set_auto("editor")
        
        assert result.success is True
        assert mock_executor.was_called_with(["--auto", "editor"])

    def test_remove(self, service: AlternativesService, mock_executor: MockExecutor) -> None:
        """Test removing alternative."""
        mock_executor.set_response(
            ["--remove", "editor", "/usr/bin/ed"],
            ExecutionResult.ok(""),
        )
        
        result = service.remove("editor", "/usr/bin/ed")
        
        assert result.success is True

    def test_remove_all(self, service: AlternativesService, mock_executor: MockExecutor) -> None:
        """Test removing all alternatives."""
        mock_executor.set_response(
            ["--remove-all", "editor"],
            ExecutionResult.ok(""),
        )
        
        result = service.remove_all("editor")
        
        assert result.success is True

    def test_operation_failure(self, service: AlternativesService, mock_executor: MockExecutor) -> None:
        """Test handling operation failure."""
        mock_executor.set_response(
            ["--set", "editor", "/invalid"],
            ExecutionResult.error("error: alternative /invalid doesn't exist"),
        )
        
        result = service.set_alternative("editor", "/invalid")
        assert result.success is False


class TestServiceEdgeCases:
    """Tests for edge cases in service."""

    def test_empty_selections(self) -> None:
        """Test handling empty selections."""
        executor = MockExecutor()
        executor.set_response(
            ["--get-selections"],
            ExecutionResult.ok(""),
        )
        
        service = AlternativesService(executor=executor)
        names = service.list_all()
        
        assert names == []

    def test_service_without_executor(self) -> None:
        """Test service can be created without explicit executor."""
        # Should use SubprocessExecutor by default
        service = AlternativesService()
        assert service is not None
        assert service.executor is not None

    def test_cache_disabled(self) -> None:
        """Test service with cache disabled."""
        executor = MockExecutor()
        executor.set_response(
            ["--get-selections"],
            ExecutionResult.ok(SELECTIONS_OUTPUT),
        )
        
        service = AlternativesService(executor=executor, enable_cache=False)
        
        # First call
        service.get_selections()
        call_count_1 = executor.call_count
        
        # Second call should NOT use cache
        service.get_selections()
        call_count_2 = executor.call_count
        
        assert call_count_2 > call_count_1

    def test_empty_name_validation(self) -> None:
        """Test validation for empty name."""
        service = AlternativesService(executor=MockExecutor())
        
        result = service.set_alternative("", "/path")
        assert result.success is False

    def test_empty_path_validation(self) -> None:
        """Test validation for empty path."""
        executor = MockExecutor()
        executor.set_response(
            ["--get-selections"],
            ExecutionResult.ok(SELECTIONS_OUTPUT),
        )
        service = AlternativesService(executor=executor)
        
        result = service.set_alternative("editor", "")
        assert result.success is False

    def test_sudo_password_error_handling(self) -> None:
        """Test that sudo password errors are handled with friendly message."""
        executor = MockExecutor()
        executor.set_response(
            ["--get-selections"],
            ExecutionResult.ok(SELECTIONS_OUTPUT),
        )
        # Simulate sudo password error
        executor.set_response(
            ["--set", "editor", "/usr/bin/nano"],
            ExecutionResult.error("sudo: a password is required", return_code=1),
        )
        
        service = AlternativesService(executor=executor)
        result = service.set_alternative("editor", "/usr/bin/nano")
        
        assert result.success is False
        assert "Permission denied" in result.message
        assert "sudo requires authentication" in result.message

    def test_sudo_password_error_set_auto(self) -> None:
        """Test sudo password error in set_auto."""
        executor = MockExecutor()
        executor.set_response(
            ["--get-selections"],
            ExecutionResult.ok(SELECTIONS_OUTPUT),
        )
        executor.set_response(
            ["--auto", "editor"],
            ExecutionResult.error("sudo: a password is required", return_code=1),
        )
        
        service = AlternativesService(executor=executor)
        result = service.set_auto("editor")
        
        assert result.success is False
        assert "Permission denied" in result.message

    def test_regular_error_not_affected(self) -> None:
        """Test that regular errors are not affected by sudo handling."""
        executor = MockExecutor()
        executor.set_response(
            ["--get-selections"],
            ExecutionResult.ok(SELECTIONS_OUTPUT),
        )
        executor.set_response(
            ["--set", "editor", "/invalid/path"],
            ExecutionResult.error("error: alternative /invalid/path doesn't exist", return_code=2),
        )
        
        service = AlternativesService(executor=executor)
        result = service.set_alternative("editor", "/invalid/path")
        
        assert result.success is False
        # Should show original error, not sudo message
        assert "Permission denied" not in result.message
        assert "doesn't exist" in result.message
