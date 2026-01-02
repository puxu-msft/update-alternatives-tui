"""Tests for update_alternatives_tui.types module.

Tests cover:
- Type aliases verification
- Callable types
"""

from __future__ import annotations

from typing import Any

from update_alternatives_tui.types import (
    # Type aliases
    CommandArgs,
    SlaveDefinition,
    SelectionsMap,
    Callback,
    ErrorHandler,
    FilterPredicate,
    SortKey,
)


# ============================================================================
# Type Alias Tests
# ============================================================================


class TestTypeAliases:
    """Tests for type alias definitions."""

    def test_command_args_is_list_of_str(self) -> None:
        """Test CommandArgs is list[str]."""
        args: CommandArgs = ["update-alternatives", "--query", "editor"]
        assert isinstance(args, list)
        assert all(isinstance(a, str) for a in args)

    def test_slave_definition_is_tuple(self) -> None:
        """Test SlaveDefinition is tuple of 3 strings."""
        slave: SlaveDefinition = ("editor.1.gz", "/usr/share/man/man1/editor.1.gz", "/usr/share/man/man1/vim.1.gz")
        assert isinstance(slave, tuple)
        assert len(slave) == 3
        assert all(isinstance(s, str) for s in slave)

    def test_selections_map_is_dict(self) -> None:
        """Test SelectionsMap is dict[str, str]."""
        selections: SelectionsMap = {
            "editor": "/usr/bin/vim",
            "pager": "/usr/bin/less",
        }
        assert isinstance(selections, dict)
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in selections.items())


# ============================================================================
# Callable Type Tests
# ============================================================================


class TestCallableTypes:
    """Tests for callable type aliases."""

    def test_callback_type(self) -> None:
        """Test Callback is a callable with no args returning None."""
        call_count = 0
        
        def my_callback() -> None:
            nonlocal call_count
            call_count += 1
        
        callback: Callback = my_callback
        callback()
        assert call_count == 1

    def test_error_handler_type(self) -> None:
        """Test ErrorHandler is a callable taking Exception returning None."""
        handled_error: Exception | None = None
        
        def my_handler(error: Exception) -> None:
            nonlocal handled_error
            handled_error = error
        
        handler: ErrorHandler = my_handler
        test_error = ValueError("test error")
        handler(test_error)
        assert handled_error is test_error

    def test_filter_predicate_type(self) -> None:
        """Test FilterPredicate is a callable taking str returning bool."""
        def my_filter(name: str) -> bool:
            return name.startswith("edit")
        
        predicate: FilterPredicate = my_filter
        assert predicate("editor") is True
        assert predicate("pager") is False

    def test_sort_key_type(self) -> None:
        """Test SortKey is a callable taking str returning Any for sorting."""
        def my_sort_key(name: str) -> Any:
            return name.lower()
        
        sort_key: SortKey = my_sort_key
        names = ["Editor", "Pager", "awk"]
        sorted_names = sorted(names, key=sort_key)
        assert sorted_names == ["awk", "Editor", "Pager"]


# ============================================================================
# Integration Tests
# ============================================================================


class TestTypeIntegration:
    """Integration tests for type usage patterns."""

    def test_command_args_in_function(self) -> None:
        """Test using CommandArgs as function parameter."""
        def execute_command(args: CommandArgs) -> str:
            return " ".join(args)
        
        result = execute_command(["update-alternatives", "--display", "editor"])
        assert result == "update-alternatives --display editor"

    def test_selections_map_manipulation(self) -> None:
        """Test manipulating SelectionsMap."""
        selections: SelectionsMap = {}
        
        # Add entries
        selections["editor"] = "/usr/bin/vim"
        selections["pager"] = "/usr/bin/less"
        
        # Query
        assert selections.get("editor") == "/usr/bin/vim"
        assert selections.get("nonexistent") is None
        
        # Iterate
        for name, path in selections.items():
            assert isinstance(name, str)
            assert isinstance(path, str)
            assert path.startswith("/")

    def test_callback_in_higher_order_function(self) -> None:
        """Test using Callback in higher-order function."""
        def run_with_callback(operation: str, on_complete: Callback) -> str:
            # Simulate operation
            result = f"Completed: {operation}"
            on_complete()
            return result
        
        completed = False
        
        def mark_complete() -> None:
            nonlocal completed
            completed = True
        
        result = run_with_callback("test", mark_complete)
        assert result == "Completed: test"
        assert completed is True
