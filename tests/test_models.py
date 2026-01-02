"""Tests for update_alternatives_tui.models module.

Tests cover:
- Model creation and validation
- Dataclass properties and equality
- Ordering and comparison
- Edge cases and error handling
"""

from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

from update_alternatives_tui.models import (
    Alternative,
    AlternativeGroup,
    AlternativeStatus,
    CommandResult,
    HistoryEntry,
    InstallRequest,
    OperationType,
    SelectionInfo,
    SlaveLink,
)
from update_alternatives_tui.exceptions import (
    EmptyValueError,
    InvalidValueError,
)


class TestAlternativeStatus:
    """Tests for AlternativeStatus enum."""

    def test_auto_mode(self) -> None:
        """Test auto mode status."""
        assert AlternativeStatus.AUTO.value == "auto"
        assert str(AlternativeStatus.AUTO) == "auto"

    def test_manual_mode(self) -> None:
        """Test manual mode status."""
        assert AlternativeStatus.MANUAL.value == "manual"
        assert str(AlternativeStatus.MANUAL) == "manual"

    def test_unknown_mode(self) -> None:
        """Test unknown mode status."""
        assert AlternativeStatus.UNKNOWN.value == "unknown"
        assert str(AlternativeStatus.UNKNOWN) == "unknown"

    def test_from_string_auto(self) -> None:
        """Test creating status from 'auto' string."""
        assert AlternativeStatus.from_string("auto") == AlternativeStatus.AUTO

    def test_from_string_manual(self) -> None:
        """Test creating status from 'manual' string."""
        assert AlternativeStatus.from_string("manual") == AlternativeStatus.MANUAL

    def test_from_string_unknown(self) -> None:
        """Test creating status from unknown string."""
        assert AlternativeStatus.from_string("invalid") == AlternativeStatus.UNKNOWN
        assert AlternativeStatus.from_string("") == AlternativeStatus.UNKNOWN

    def test_from_string_case_insensitive(self) -> None:
        """Test that from_string is case insensitive."""
        assert AlternativeStatus.from_string("AUTO") == AlternativeStatus.AUTO
        assert AlternativeStatus.from_string("Manual") == AlternativeStatus.MANUAL
        assert AlternativeStatus.from_string("MANUAL") == AlternativeStatus.MANUAL

    def test_display_name(self) -> None:
        """Test display_name property."""
        assert AlternativeStatus.AUTO.display_name == "Auto"
        assert AlternativeStatus.MANUAL.display_name == "Manual"


class TestSlaveLink:
    """Tests for SlaveLink frozen dataclass."""

    def test_creation(self) -> None:
        """Test basic creation."""
        slave = SlaveLink(
            name="editor.1.gz",
            link="/usr/share/man/man1/editor.1.gz",
            path="/usr/share/man/man1/vim.1.gz",
        )
        assert slave.name == "editor.1.gz"
        assert slave.link == "/usr/share/man/man1/editor.1.gz"
        assert slave.path == "/usr/share/man/man1/vim.1.gz"

    def test_frozen(self) -> None:
        """Test that SlaveLink is immutable."""
        slave = SlaveLink(name="test", link="/test/link", path="/test/path")
        with pytest.raises(FrozenInstanceError):
            slave.name = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        """Test equality comparison."""
        slave1 = SlaveLink(name="test", link="/link", path="/path")
        slave2 = SlaveLink(name="test", link="/link", path="/path")
        slave3 = SlaveLink(name="other", link="/link", path="/path")

        assert slave1 == slave2
        assert slave1 != slave3

    def test_hash(self) -> None:
        """Test that SlaveLink is hashable."""
        slave1 = SlaveLink(name="test", link="/link", path="/path")
        slave2 = SlaveLink(name="test", link="/link", path="/path")

        assert hash(slave1) == hash(slave2)
        # Can be used in sets and dicts
        slave_set = {slave1, slave2}
        assert len(slave_set) == 1

    def test_validation_empty_name(self) -> None:
        """Test validation rejects empty name."""
        with pytest.raises(EmptyValueError):
            SlaveLink(name="", link="/link", path="/path")

    def test_to_tuple(self) -> None:
        """Test to_tuple method."""
        slave = SlaveLink(name="test", link="/link", path="/path")
        assert slave.to_tuple() == ("test", "/link", "/path")


class TestSelectionInfo:
    """Tests for SelectionInfo frozen dataclass."""

    def test_creation(self) -> None:
        """Test basic creation."""
        info = SelectionInfo(
            name="editor",
            mode=AlternativeStatus.AUTO,
            current_path="/usr/bin/vim.basic",
        )
        assert info.name == "editor"
        assert info.mode == AlternativeStatus.AUTO
        assert info.current_path == "/usr/bin/vim.basic"

    def test_frozen(self) -> None:
        """Test that SelectionInfo is immutable."""
        info = SelectionInfo(
            name="test",
            mode=AlternativeStatus.AUTO,
            current_path="/path",
        )
        with pytest.raises(FrozenInstanceError):
            info.name = "changed"  # type: ignore[misc]

    def test_is_auto(self) -> None:
        """Test is_auto property."""
        auto_info = SelectionInfo("test", AlternativeStatus.AUTO, "/path")
        manual_info = SelectionInfo("test", AlternativeStatus.MANUAL, "/path")

        assert auto_info.is_auto is True
        assert manual_info.is_auto is False

    def test_is_manual(self) -> None:
        """Test is_manual property."""
        auto_info = SelectionInfo("test", AlternativeStatus.AUTO, "/path")
        manual_info = SelectionInfo("test", AlternativeStatus.MANUAL, "/path")

        assert auto_info.is_manual is False
        assert manual_info.is_manual is True

    def test_from_line(self) -> None:
        """Test from_line class method."""
        info = SelectionInfo.from_line("editor auto /usr/bin/vim")
        assert info is not None
        assert info.name == "editor"
        assert info.mode == AlternativeStatus.AUTO

    def test_from_line_invalid(self) -> None:
        """Test from_line with invalid input."""
        assert SelectionInfo.from_line("invalid") is None
        assert SelectionInfo.from_line("") is None


class TestAlternative:
    """Tests for Alternative dataclass."""

    def test_creation_minimal(self) -> None:
        """Test creation with minimal arguments."""
        alt = Alternative(path="/usr/bin/vim", priority=50)
        assert alt.path == "/usr/bin/vim"
        assert alt.priority == 50
        assert alt.slaves == {}

    def test_creation_with_slaves(self) -> None:
        """Test creation with slave links."""
        slaves = {"man.1.gz": "/usr/share/man/man1/vim.1.gz"}
        alt = Alternative(path="/usr/bin/vim", priority=50, slaves=slaves)
        assert len(alt.slaves) == 1

    def test_validation_empty_path(self) -> None:
        """Test validation rejects empty path."""
        with pytest.raises(EmptyValueError):
            Alternative(path="", priority=50)

    def test_negative_priority_allowed(self) -> None:
        """Test that negative priority is allowed (e.g., /bin/ed has -100)."""
        alt = Alternative(path="/usr/bin/test", priority=-100)
        assert alt.priority == -100

    def test_equality(self) -> None:
        """Test equality based on path and priority."""
        alt1 = Alternative(path="/usr/bin/vim", priority=50)
        alt2 = Alternative(path="/usr/bin/vim", priority=50)
        alt3 = Alternative(path="/usr/bin/vim", priority=60)

        assert alt1 == alt2
        assert alt1 != alt3

    def test_hash(self) -> None:
        """Test hashability."""
        alt1 = Alternative(path="/usr/bin/vim", priority=50)
        alt2 = Alternative(path="/usr/bin/vim", priority=50)

        assert hash(alt1) == hash(alt2)

    def test_ordering_by_priority(self) -> None:
        """Test ordering by priority (higher first)."""
        low = Alternative(path="/usr/bin/ed", priority=10)
        mid = Alternative(path="/usr/bin/nano", priority=40)
        high = Alternative(path="/usr/bin/vim", priority=50)

        assert high > mid > low
        assert low < mid < high

        # Sorting should give descending priority
        sorted_alts = sorted([low, high, mid], reverse=True)
        assert sorted_alts == [high, mid, low]

    def test_has_slaves(self) -> None:
        """Test has_slaves method."""
        alt1 = Alternative("/path", 10)
        alt2 = Alternative("/path", 10, slaves={"test": "/test"})
        
        assert alt1.has_slaves() is False
        assert alt2.has_slaves() is True

    def test_add_slave(self) -> None:
        """Test add_slave method."""
        alt = Alternative("/path", 10)
        alt.add_slave("test", "/test/path")
        
        assert "test" in alt.slaves
        assert alt.slaves["test"] == "/test/path"

    def test_remove_slave(self) -> None:
        """Test remove_slave method."""
        alt = Alternative("/path", 10, slaves={"test": "/test"})
        
        assert alt.remove_slave("test") is True
        assert alt.remove_slave("nonexistent") is False


class TestAlternativeGroup:
    """Tests for AlternativeGroup dataclass."""

    def test_creation_minimal(self) -> None:
        """Test creation with minimal arguments."""
        group = AlternativeGroup(
            name="editor",
            link="/usr/bin/editor",
        )
        assert group.name == "editor"
        assert group.link == "/usr/bin/editor"
        assert group.status == AlternativeStatus.AUTO
        assert group.alternatives == []
        assert group.best == ""
        assert group.current == ""

    def test_creation_full(self) -> None:
        """Test creation with all arguments."""
        alts = [
            Alternative("/usr/bin/vim", 50),
            Alternative("/usr/bin/nano", 40),
        ]
        group = AlternativeGroup(
            name="editor",
            link="/usr/bin/editor",
            status=AlternativeStatus.AUTO,
            alternatives=alts,
            best="/usr/bin/vim",
            current="/usr/bin/vim",
        )
        assert len(group.alternatives) == 2
        assert group.best == "/usr/bin/vim"
        assert group.current == "/usr/bin/vim"

    def test_validation_empty_name(self) -> None:
        """Test validation rejects empty name."""
        with pytest.raises(EmptyValueError):
            AlternativeGroup(name="", link="/usr/bin/editor")

    def test_is_auto(self) -> None:
        """Test is_auto method."""
        auto = AlternativeGroup("test", "/test", AlternativeStatus.AUTO)
        manual = AlternativeGroup("test", "/test", AlternativeStatus.MANUAL)

        assert auto.is_auto() is True
        assert manual.is_auto() is False

    def test_has_alternatives(self) -> None:
        """Test has_alternatives property."""
        empty = AlternativeGroup("test", "/test")
        with_alts = AlternativeGroup(
            "test",
            "/test",
            alternatives=[Alternative("/path", 10)],
        )

        assert empty.has_alternatives is False
        assert with_alts.has_alternatives is True

    def test_count_alternatives(self) -> None:
        """Test count_alternatives method."""
        alts = [Alternative(f"/path{i}", i) for i in range(5)]
        group = AlternativeGroup(
            "test",
            "/test",
            alternatives=alts,
        )
        assert group.count_alternatives() == 5

    def test_get_alternative_by_path_found(self) -> None:
        """Test finding alternative by path."""
        vim = Alternative("/usr/bin/vim", 50)
        nano = Alternative("/usr/bin/nano", 40)
        group = AlternativeGroup(
            "editor",
            "/usr/bin/editor",
            alternatives=[vim, nano],
        )

        found = group.get_alternative_by_path("/usr/bin/vim")
        assert found == vim

    def test_get_alternative_by_path_not_found(self) -> None:
        """Test get_alternative_by_path returns None when not found."""
        group = AlternativeGroup(
            "editor",
            "/usr/bin/editor",
            alternatives=[Alternative("/usr/bin/vim", 50)],
        )

        assert group.get_alternative_by_path("/nonexistent") is None

    def test_get_current_alternative(self) -> None:
        """Test get_current_alternative method."""
        vim = Alternative("/usr/bin/vim", 50)
        group = AlternativeGroup(
            "editor",
            "/usr/bin/editor",
            alternatives=[vim],
            current="/usr/bin/vim",
        )

        assert group.get_current_alternative() == vim

    def test_iteration(self) -> None:
        """Test iteration over alternatives."""
        alts = [Alternative(f"/path{i}", i) for i in range(3)]
        group = AlternativeGroup("test", "/test", alternatives=alts)
        
        assert list(group) == alts

    def test_len(self) -> None:
        """Test len() on group."""
        alts = [Alternative(f"/path{i}", i) for i in range(5)]
        group = AlternativeGroup("test", "/test", alternatives=alts)
        
        assert len(group) == 5

    def test_contains(self) -> None:
        """Test 'in' operator."""
        group = AlternativeGroup(
            "test",
            "/test",
            alternatives=[Alternative("/usr/bin/vim", 50)],
        )
        
        assert "/usr/bin/vim" in group
        assert "/nonexistent" not in group


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_success_result(self) -> None:
        """Test successful command result."""
        result = CommandResult(success=True, message="ok", return_code=0, stdout="output")
        assert result.success is True
        assert result.return_code == 0
        assert result.stdout == "output"

    def test_failure_result(self) -> None:
        """Test failed command result."""
        result = CommandResult(success=False, message="error", return_code=1, stderr="error message")
        assert result.success is False
        assert result.stderr == "error message"

    def test_output_property_prefers_stdout(self) -> None:
        """Test output property returns stdout when available."""
        result = CommandResult(success=True, message="ok", stdout="stdout content", stderr="stderr content")
        assert result.output == "stdout content"

    def test_output_property_fallback_to_stderr(self) -> None:
        """Test output property falls back to stderr."""
        result = CommandResult(success=False, message="err", return_code=1, stdout="", stderr="error content")
        assert result.output == "error content"

    def test_bool_context(self) -> None:
        """Test bool context returns success."""
        success = CommandResult(success=True, message="ok")
        failure = CommandResult(success=False, message="err")
        
        assert bool(success) is True
        assert bool(failure) is False

    def test_ok_factory(self) -> None:
        """Test ok factory method."""
        result = CommandResult.ok("success message", stdout="output")
        assert result.success is True
        assert result.message == "success message"

    def test_error_factory(self) -> None:
        """Test error factory method."""
        result = CommandResult.error("error message", return_code=2, stderr="details")
        assert result.success is False
        assert result.message == "error message"
        assert result.return_code == 2


class TestInstallRequest:
    """Tests for InstallRequest dataclass."""

    def test_creation_minimal(self) -> None:
        """Test creation with minimal arguments."""
        request = InstallRequest(
            name="editor",
            link="/usr/bin/editor",
            path="/usr/bin/vim",
            priority=50,
        )
        assert request.name == "editor"
        assert request.slaves == []

    def test_validation_empty_fields(self) -> None:
        """Test validation for empty fields."""
        with pytest.raises(EmptyValueError):
            InstallRequest(name="", link="/link", path="/path", priority=50)

    def test_negative_priority_allowed(self) -> None:
        """Test that negative priority is allowed."""
        request = InstallRequest(name="test", link="/link", path="/path", priority=-10)
        assert request.priority == -10

    def test_to_args(self) -> None:
        """Test to_args method."""
        request = InstallRequest(
            name="editor",
            link="/usr/bin/editor",
            path="/usr/bin/vim",
            priority=50,
        )
        args = request.to_args()
        
        assert "--install" in args
        assert "/usr/bin/editor" in args
        assert "editor" in args

    def test_add_slave(self) -> None:
        """Test add_slave method."""
        request = InstallRequest(
            name="editor",
            link="/usr/bin/editor",
            path="/usr/bin/vim",
            priority=50,
        )
        request.add_slave("man", "/usr/share/man/man1/editor.1", "/usr/share/man/man1/vim.1")
        assert len(request.slaves) == 1


class TestHistoryEntry:
    """Tests for HistoryEntry dataclass."""

    def test_creation(self) -> None:
        """Test basic creation."""
        import time
        entry = HistoryEntry(
            timestamp=time.time(),
            operation=OperationType.SET,
            name="editor",
            old_value="/usr/bin/nano",
            new_value="/usr/bin/vim",
            success=True,
        )
        assert entry.operation == OperationType.SET
        assert entry.name == "editor"
        assert entry.old_value == "/usr/bin/nano"
        assert entry.new_value == "/usr/bin/vim"
        assert entry.success is True

    def test_frozen(self) -> None:
        """Test that HistoryEntry is immutable."""
        import time
        entry = HistoryEntry(
            timestamp=time.time(),
            operation=OperationType.AUTO,
            name="test",
            old_value=None,
            new_value="auto",
            success=True,
        )
        with pytest.raises(FrozenInstanceError):
            entry.name = "changed"  # type: ignore[misc]


class TestOperationType:
    """Tests for OperationType enum."""

    def test_all_operations_exist(self) -> None:
        """Test all expected operation types exist."""
        assert OperationType.SET
        assert OperationType.AUTO
        assert OperationType.INSTALL
        assert OperationType.REMOVE
        assert OperationType.REMOVE_ALL
