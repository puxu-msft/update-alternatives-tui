"""Tests for update_alternatives_tui.widgets module.

Tests cover:
- Widget creation and initialization
- Message classes
- CSS application
- Widget behavior
"""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from update_alternatives_tui.widgets import (
    StatusWidget,
    StatusMessage,
    AlternativeSelected,
    DialogClosed,
    AlternativeDetailPanel,
    ConfirmDialog,
    STATUS_WIDGET_CSS,
    DIALOG_CSS,
    DETAIL_PANEL_CSS,
)
from update_alternatives_tui.models import (
    Alternative,
    AlternativeGroup,
    AlternativeStatus,
)


class TestStatusMessage:
    """Tests for StatusMessage dataclass."""

    def test_creation(self) -> None:
        """Test creating message."""
        msg = StatusMessage(text="Test message")
        assert msg.text == "Test message"
        assert msg.is_error is False

    def test_creation_with_error(self) -> None:
        """Test creating error message."""
        msg = StatusMessage(text="Error", is_error=True)
        assert msg.is_error is True


class TestAlternativeSelected:
    """Tests for AlternativeSelected message."""

    def test_creation(self) -> None:
        """Test creating message."""
        msg = AlternativeSelected(name="editor")
        assert msg.name == "editor"
        assert msg.path is None

    def test_creation_with_path(self) -> None:
        """Test creating message with path."""
        msg = AlternativeSelected(name="editor", path="/usr/bin/vim")
        assert msg.path == "/usr/bin/vim"


class TestDialogClosed:
    """Tests for DialogClosed message."""

    def test_creation(self) -> None:
        """Test creating message."""
        msg = DialogClosed(result=True)
        assert msg.result is True
        assert msg.data is None

    def test_creation_with_data(self) -> None:
        """Test creating message with data."""
        msg = DialogClosed(result=True, data={"key": "value"})
        assert msg.data == {"key": "value"}


class TestStatusWidget:
    """Tests for StatusWidget class."""

    def test_creation(self) -> None:
        """Test widget creation."""
        widget = StatusWidget()
        assert widget is not None

    def test_auto_clear_default(self) -> None:
        """Test default auto_clear value."""
        widget = StatusWidget()
        assert widget.auto_clear == 5.0

    def test_auto_clear_custom(self) -> None:
        """Test custom auto_clear value."""
        widget = StatusWidget(auto_clear=10.0)
        assert widget.auto_clear == 10.0

    def test_auto_clear_disabled(self) -> None:
        """Test disabled auto_clear."""
        widget = StatusWidget(auto_clear=None)
        assert widget.auto_clear is None

    @pytest.mark.asyncio
    async def test_show_message(self) -> None:
        """Test show_message method."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield StatusWidget(id="status", auto_clear=None)

        async with TestApp().run_test() as pilot:
            status = pilot.app.query_one("#status", StatusWidget)
            status.show_message("Test message")
            # Widget should have success class
            assert "success" in status.classes

    @pytest.mark.asyncio
    async def test_show_error_message(self) -> None:
        """Test show_message with error."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield StatusWidget(id="status", auto_clear=None)

        async with TestApp().run_test() as pilot:
            status = pilot.app.query_one("#status", StatusWidget)
            status.show_message("Error", is_error=True)
            assert "error" in status.classes

    @pytest.mark.asyncio
    async def test_show_info(self) -> None:
        """Test show_info method."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield StatusWidget(id="status", auto_clear=None)

        async with TestApp().run_test() as pilot:
            status = pilot.app.query_one("#status", StatusWidget)
            status.show_info("Info message")
            # Should not have error or success class
            assert "error" not in status.classes
            assert "success" not in status.classes

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        """Test clear method."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield StatusWidget(id="status", auto_clear=None)

        async with TestApp().run_test() as pilot:
            status = pilot.app.query_one("#status", StatusWidget)
            status.show_message("Test")
            status.clear()
            assert "success" not in status.classes
            assert "error" not in status.classes


class TestAlternativeDetailPanel:
    """Tests for AlternativeDetailPanel class."""

    @pytest.fixture
    def sample_group(self) -> AlternativeGroup:
        """Provide sample alternative group."""
        alternatives = [
            Alternative("/usr/bin/vim", 50),
            Alternative("/usr/bin/nano", 40),
            Alternative("/usr/bin/ed", 10),
        ]
        return AlternativeGroup(
            name="editor",
            link="/usr/bin/editor",
            status=AlternativeStatus.AUTO,
            alternatives=alternatives,
            best="/usr/bin/vim",
            current="/usr/bin/vim",
        )

    def test_creation_without_group(self) -> None:
        """Test creating panel without group."""
        panel = AlternativeDetailPanel()
        assert panel.current_group is None

    def test_get_current_group(self, sample_group: AlternativeGroup) -> None:
        """Test get_current_group method."""
        panel = AlternativeDetailPanel()
        panel.current_group = sample_group
        assert panel.get_current_group() == sample_group


class TestConfirmDialog:
    """Tests for ConfirmDialog class."""

    def test_creation(self) -> None:
        """Test dialog creation."""
        dialog = ConfirmDialog(title="Test", message="Are you sure?")
        assert dialog.title_text == "Test"
        assert dialog.message_text == "Are you sure?"

    def test_destructive_flag(self) -> None:
        """Test destructive flag."""
        dialog = ConfirmDialog("Delete", "Delete this?", destructive=True)
        assert dialog.destructive is True

    def test_custom_labels(self) -> None:
        """Test custom button labels."""
        dialog = ConfirmDialog(
            "Test",
            "Message",
            yes_label="Confirm",
            no_label="Cancel",
        )
        assert dialog.yes_label == "Confirm"
        assert dialog.no_label == "Cancel"


class TestWidgetCSS:
    """Tests for widget CSS constants."""

    def test_status_widget_css_exists(self) -> None:
        """Test StatusWidget CSS exists."""
        assert STATUS_WIDGET_CSS is not None
        assert len(STATUS_WIDGET_CSS) > 0
        assert "StatusWidget" in STATUS_WIDGET_CSS

    def test_dialog_css_exists(self) -> None:
        """Test dialog CSS exists."""
        assert DIALOG_CSS is not None
        assert len(DIALOG_CSS) > 0
        assert ".dialog-container" in DIALOG_CSS

    def test_detail_panel_css_exists(self) -> None:
        """Test detail panel CSS exists."""
        assert DETAIL_PANEL_CSS is not None
        assert len(DETAIL_PANEL_CSS) > 0
        assert "AlternativeDetailPanel" in DETAIL_PANEL_CSS


class TestWidgetIntegration:
    """Integration tests for widgets in an app context."""

    @pytest.mark.asyncio
    async def test_status_widget_in_app(self) -> None:
        """Test StatusWidget in app context."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield StatusWidget(id="status", auto_clear=None)

        async with TestApp().run_test() as pilot:
            app = pilot.app
            status = app.query_one("#status", StatusWidget)
            
            status.show_message("Test")
            assert "success" in status.classes
