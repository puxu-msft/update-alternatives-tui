"""Comprehensive tests for update_alternatives_tui widgets and UI components.

These tests cover:
- Widget creation, initialization, and configuration
- Widget behavior with various inputs (normal, edge cases, special characters)
- Dialog interactions (keyboard, mouse, callbacks)
- CSS styling verification
- Layout and scrolling behavior
- Integration with app context
- Error handling and edge cases
"""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Button, Static

from update_alternatives_tui.widgets import (
    StatusWidget,
    StatusMessage,
    AlternativeSelected,
    DialogClosed,
    AlternativeDetailPanel,
    ConfirmDialog,
    InputDialog,
    InstallDialog,
    SelectAlternativeDialog,
    HelpDialog,
    StatusColor,
    StatusIndicator,
    STATUS_WIDGET_CSS,
    DIALOG_CSS,
    INPUT_DIALOG_CSS,
    DETAIL_PANEL_CSS,
    SELECT_DIALOG_CSS,
    HELP_DIALOG_CSS,
)
from update_alternatives_tui.models import (
    Alternative,
    AlternativeGroup,
    AlternativeStatus,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def simple_group() -> AlternativeGroup:
    """Provide a simple alternative group with 2 alternatives."""
    return AlternativeGroup(
        name="editor",
        link="/usr/bin/editor",
        status=AlternativeStatus.AUTO,
        alternatives=[
            Alternative("/usr/bin/vim", 50),
            Alternative("/usr/bin/nano", 40),
        ],
        best="/usr/bin/vim",
        current="/usr/bin/vim",
    )


@pytest.fixture
def complex_group() -> AlternativeGroup:
    """Provide a complex alternative group with slaves and many alternatives."""
    return AlternativeGroup(
        name="java",
        link="/usr/bin/java",
        status=AlternativeStatus.MANUAL,
        alternatives=[
            Alternative("/usr/lib/jvm/java-17/bin/java", 1700, {
                "javac": "/usr/lib/jvm/java-17/bin/javac",
                "jar": "/usr/lib/jvm/java-17/bin/jar",
            }),
            Alternative("/usr/lib/jvm/java-11/bin/java", 1100, {
                "javac": "/usr/lib/jvm/java-11/bin/javac",
                "jar": "/usr/lib/jvm/java-11/bin/jar",
            }),
            Alternative("/usr/lib/jvm/java-8/bin/java", 800),
        ],
        best="/usr/lib/jvm/java-17/bin/java",
        current="/usr/lib/jvm/java-11/bin/java",
        slave_links={
            "javac": "/usr/bin/javac",
            "jar": "/usr/bin/jar",
        },
    )


@pytest.fixture
def special_chars_group() -> AlternativeGroup:
    """Provide a group with special characters that could break Rich markup."""
    return AlternativeGroup(
        name="builtins.7.gz",
        link="/usr/share/man/man7/builtins.7.gz",
        status=AlternativeStatus.AUTO,
        alternatives=[
            Alternative("/path/with/[brackets]/file", 50),
            Alternative("/path/with/<angle>/file", 40),
            Alternative("/path/test[0].so", 30),
        ],
        best="/path/with/[brackets]/file",
        current="/path/with/[brackets]/file",
    )


@pytest.fixture
def many_alternatives_group() -> AlternativeGroup:
    """Provide a group with many alternatives for scroll testing."""
    alternatives = [
        Alternative(f"/usr/bin/python3.{i}", 100 - i)
        for i in range(20)
    ]
    return AlternativeGroup(
        name="python",
        link="/usr/bin/python",
        status=AlternativeStatus.AUTO,
        alternatives=alternatives,
        best="/usr/bin/python3.0",
        current="/usr/bin/python3.0",
    )


# ============================================================================
# Message Dataclass Tests
# ============================================================================

class TestStatusMessage:
    """Tests for StatusMessage dataclass."""

    def test_creation_default(self) -> None:
        """Test creating message with defaults."""
        msg = StatusMessage(text="Test message")
        assert msg.text == "Test message"
        assert msg.is_error is False

    def test_creation_with_error(self) -> None:
        """Test creating error message."""
        msg = StatusMessage(text="Error occurred", is_error=True)
        assert msg.text == "Error occurred"
        assert msg.is_error is True

    def test_empty_text(self) -> None:
        """Test creating message with empty text."""
        msg = StatusMessage(text="")
        assert msg.text == ""

    def test_special_characters_in_text(self) -> None:
        """Test message with special characters."""
        msg = StatusMessage(text="[bold]Test[/bold] with <brackets>")
        assert "[bold]" in msg.text


class TestAlternativeSelected:
    """Tests for AlternativeSelected message."""

    def test_creation_name_only(self) -> None:
        """Test creating message with name only."""
        msg = AlternativeSelected(name="editor")
        assert msg.name == "editor"
        assert msg.path is None

    def test_creation_with_path(self) -> None:
        """Test creating message with path."""
        msg = AlternativeSelected(name="editor", path="/usr/bin/vim")
        assert msg.name == "editor"
        assert msg.path == "/usr/bin/vim"

    def test_special_name(self) -> None:
        """Test message with special characters in name."""
        msg = AlternativeSelected(name="python3.11", path="/usr/bin/python3.11")
        assert msg.name == "python3.11"


class TestDialogClosed:
    """Tests for DialogClosed message."""

    def test_creation_result_only(self) -> None:
        """Test creating message with result only."""
        msg = DialogClosed(result=True)
        assert msg.result is True
        assert msg.data is None

    def test_creation_with_data(self) -> None:
        """Test creating message with data."""
        data = {"name": "editor", "path": "/usr/bin/vim"}
        msg = DialogClosed(result=True, data=data)
        assert msg.result is True
        assert msg.data == data

    def test_false_result(self) -> None:
        """Test message with False result (cancelled)."""
        msg = DialogClosed(result=False)
        assert msg.result is False


# ============================================================================
# StatusWidget Tests
# ============================================================================

class TestStatusWidgetCreation:
    """Tests for StatusWidget creation and configuration."""

    def test_creation_default(self) -> None:
        """Test widget creation with defaults."""
        widget = StatusWidget()
        assert widget is not None
        assert widget.auto_clear == 5.0

    def test_auto_clear_custom(self) -> None:
        """Test custom auto_clear value."""
        widget = StatusWidget(auto_clear=10.0)
        assert widget.auto_clear == 10.0

    def test_auto_clear_disabled(self) -> None:
        """Test disabled auto_clear."""
        widget = StatusWidget(auto_clear=None)
        assert widget.auto_clear is None

    def test_auto_clear_zero(self) -> None:
        """Test zero auto_clear (immediate clear)."""
        widget = StatusWidget(auto_clear=0)
        assert widget.auto_clear == 0


class TestStatusWidgetBehavior:
    """Tests for StatusWidget behavior."""

    @pytest.mark.asyncio
    async def test_show_message_success(self) -> None:
        """Test showing success message."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield StatusWidget(id="status", auto_clear=None)

        async with TestApp().run_test() as pilot:
            status = pilot.app.query_one("#status", StatusWidget)
            status.show_message("Operation successful")
            assert "success" in status.classes
            assert "error" not in status.classes

    @pytest.mark.asyncio
    async def test_show_message_error(self) -> None:
        """Test showing error message."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield StatusWidget(id="status", auto_clear=None)

        async with TestApp().run_test() as pilot:
            status = pilot.app.query_one("#status", StatusWidget)
            status.show_message("Operation failed", is_error=True)
            assert "error" in status.classes
            assert "success" not in status.classes

    @pytest.mark.asyncio
    async def test_show_info(self) -> None:
        """Test showing info message."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield StatusWidget(id="status", auto_clear=None)

        async with TestApp().run_test() as pilot:
            status = pilot.app.query_one("#status", StatusWidget)
            status.show_info("Loading...")
            assert "error" not in status.classes
            assert "success" not in status.classes

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        """Test clearing status."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield StatusWidget(id="status", auto_clear=None)

        async with TestApp().run_test() as pilot:
            status = pilot.app.query_one("#status", StatusWidget)
            status.show_message("Test")
            status.clear()
            assert "success" not in status.classes
            assert "error" not in status.classes

    @pytest.mark.asyncio
    async def test_message_override(self) -> None:
        """Test that new message overrides old one."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield StatusWidget(id="status", auto_clear=None)

        async with TestApp().run_test() as pilot:
            status = pilot.app.query_one("#status", StatusWidget)
            status.show_message("First", is_error=True)
            assert "error" in status.classes
            
            status.show_message("Second", is_error=False)
            assert "success" in status.classes
            assert "error" not in status.classes

    @pytest.mark.asyncio
    async def test_special_characters_escaped(self) -> None:
        """Test that special characters are escaped in messages."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield StatusWidget(id="status", auto_clear=None)

        async with TestApp().run_test() as pilot:
            status = pilot.app.query_one("#status", StatusWidget)
            # This should not cause a Rich markup error
            status.show_message("[bold]Test[/bold] <test>")
            # If we get here without exception, escaping worked


# ============================================================================
# AlternativeDetailPanel Tests
# ============================================================================

class TestDetailPanelCreation:
    """Tests for AlternativeDetailPanel creation."""

    def test_creation_empty(self) -> None:
        """Test creating panel without group."""
        panel = AlternativeDetailPanel()
        assert panel is not None
        assert panel.current_group is None

    def test_get_current_group_empty(self) -> None:
        """Test get_current_group when empty."""
        panel = AlternativeDetailPanel()
        assert panel.get_current_group() is None


class TestDetailPanelDisplay:
    """Tests for AlternativeDetailPanel display functionality."""

    @pytest.mark.asyncio
    async def test_update_with_simple_group(self, simple_group: AlternativeGroup) -> None:
        """Test updating panel with simple group."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield AlternativeDetailPanel(id="panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#panel", AlternativeDetailPanel)
            panel.update_details(simple_group)
            assert panel.current_group == simple_group
            assert panel.get_current_group() == simple_group

    @pytest.mark.asyncio
    async def test_update_with_complex_group(self, complex_group: AlternativeGroup) -> None:
        """Test updating panel with complex group (slaves, manual mode)."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield AlternativeDetailPanel(id="panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#panel", AlternativeDetailPanel)
            panel.update_details(complex_group)
            assert panel.current_group == complex_group

    @pytest.mark.asyncio
    async def test_update_with_special_chars(self, special_chars_group: AlternativeGroup) -> None:
        """Test updating panel with special characters (Rich markup injection)."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield AlternativeDetailPanel(id="panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#panel", AlternativeDetailPanel)
            # This should not raise a Rich markup error
            panel.update_details(special_chars_group)
            assert panel.current_group == special_chars_group

    @pytest.mark.asyncio
    async def test_clear_details(self, simple_group: AlternativeGroup) -> None:
        """Test clearing panel by setting None."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield AlternativeDetailPanel(id="panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#panel", AlternativeDetailPanel)
            panel.update_details(simple_group)
            assert panel.current_group is not None
            
            panel.update_details(None)
            assert panel.current_group is None


class TestDetailPanelFormatting:
    """Tests for AlternativeDetailPanel internal formatting."""

    def test_format_group_contains_name(self, simple_group: AlternativeGroup) -> None:
        """Test that formatted output contains group name."""
        panel = AlternativeDetailPanel()
        output = panel._format_group(simple_group)
        assert "editor" in output

    def test_format_group_contains_alternatives(self, simple_group: AlternativeGroup) -> None:
        """Test that formatted output contains all alternatives."""
        panel = AlternativeDetailPanel()
        output = panel._format_group(simple_group)
        assert "/usr/bin/vim" in output
        assert "/usr/bin/nano" in output

    def test_format_group_contains_priority(self, simple_group: AlternativeGroup) -> None:
        """Test that formatted output contains priorities."""
        panel = AlternativeDetailPanel()
        output = panel._format_group(simple_group)
        assert "50" in output
        assert "40" in output

    def test_format_group_shows_current_indicator(self, simple_group: AlternativeGroup) -> None:
        """Test that current alternative is indicated."""
        panel = AlternativeDetailPanel()
        output = panel._format_group(simple_group)
        assert StatusIndicator.CURRENT in output

    def test_format_group_shows_best_indicator(self, simple_group: AlternativeGroup) -> None:
        """Test that best alternative is indicated."""
        panel = AlternativeDetailPanel()
        output = panel._format_group(simple_group)
        # Best and current are the same in simple_group
        assert StatusIndicator.BEST in output or StatusIndicator.CURRENT in output

    def test_format_group_with_slaves(self, complex_group: AlternativeGroup) -> None:
        """Test that slaves are shown."""
        panel = AlternativeDetailPanel()
        output = panel._format_group(complex_group)
        assert "javac" in output
        assert "jar" in output

    def test_format_group_with_slave_links(self, complex_group: AlternativeGroup) -> None:
        """Test that slave links section is shown."""
        panel = AlternativeDetailPanel()
        output = panel._format_group(complex_group)
        assert "Slave Links" in output

    def test_format_group_escapes_special_chars(self, special_chars_group: AlternativeGroup) -> None:
        """Test that special characters are escaped."""
        panel = AlternativeDetailPanel()
        # This should not raise an exception
        output = panel._format_group(special_chars_group)
        assert output is not None


# ============================================================================
# ConfirmDialog Tests
# ============================================================================

class TestConfirmDialogCreation:
    """Tests for ConfirmDialog creation."""

    def test_creation_basic(self) -> None:
        """Test basic dialog creation."""
        dialog = ConfirmDialog("Title", "Message")
        assert dialog.title_text == "Title"
        assert dialog.message_text == "Message"
        assert dialog.destructive is False

    def test_creation_destructive(self) -> None:
        """Test destructive dialog."""
        dialog = ConfirmDialog("Delete", "Are you sure?", destructive=True)
        assert dialog.destructive is True

    def test_custom_labels(self) -> None:
        """Test custom button labels."""
        dialog = ConfirmDialog("Title", "Message", yes_label="OK", no_label="Cancel")
        assert dialog.yes_label == "OK"
        assert dialog.no_label == "Cancel"


class TestConfirmDialogBehavior:
    """Tests for ConfirmDialog behavior."""

    @pytest.mark.asyncio
    async def test_yes_button_dismisses_with_true(self) -> None:
        """Test that yes button dismisses with True."""
        class TestApp(App):
            result = None
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: bool) -> None:
                    self.result = result
                self.push_screen(ConfirmDialog("Test", "Confirm?"), callback)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            # Click yes button - must query on screen, not app
            yes_btn = pilot.app.screen.query_one("#yes", Button)
            await pilot.click(yes_btn)
            await pilot.pause()
            assert pilot.app.result is True

    @pytest.mark.asyncio
    async def test_no_button_dismisses_with_false(self) -> None:
        """Test that no button dismisses with False."""
        class TestApp(App):
            result = None
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: bool) -> None:
                    self.result = result
                self.push_screen(ConfirmDialog("Test", "Confirm?"), callback)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            no_btn = pilot.app.screen.query_one("#no", Button)
            await pilot.click(no_btn)
            await pilot.pause()
            assert pilot.app.result is False

    @pytest.mark.asyncio
    async def test_escape_key_dismisses_with_false(self) -> None:
        """Test that escape key dismisses with False."""
        class TestApp(App):
            result = None
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: bool) -> None:
                    self.result = result
                self.push_screen(ConfirmDialog("Test", "Confirm?"), callback)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert pilot.app.result is False

    @pytest.mark.asyncio
    async def test_y_key_confirms(self) -> None:
        """Test that y key confirms."""
        class TestApp(App):
            result = None
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: bool) -> None:
                    self.result = result
                self.push_screen(ConfirmDialog("Test", "Confirm?"), callback)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            await pilot.press("y")
            await pilot.pause()
            assert pilot.app.result is True

    @pytest.mark.asyncio
    async def test_n_key_cancels(self) -> None:
        """Test that n key cancels."""
        class TestApp(App):
            result = None
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: bool) -> None:
                    self.result = result
                self.push_screen(ConfirmDialog("Test", "Confirm?"), callback)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            await pilot.press("n")
            await pilot.pause()
            assert pilot.app.result is False


# ============================================================================
# InputDialog Tests
# ============================================================================

class TestInputDialogCreation:
    """Tests for InputDialog creation."""

    def test_creation_basic(self) -> None:
        """Test basic dialog creation."""
        dialog = InputDialog("Title", "Label:")
        assert dialog.title_text == "Title"
        assert dialog.label_text == "Label:"
        assert dialog.default_value == ""

    def test_creation_with_default(self) -> None:
        """Test dialog with default value."""
        dialog = InputDialog("Title", "Name:", default="test")
        assert dialog.default_value == "test"

    def test_creation_with_placeholder(self) -> None:
        """Test dialog with placeholder."""
        dialog = InputDialog("Title", "Name:", placeholder="Enter name")
        assert dialog.placeholder_text == "Enter name"


class TestInputDialogBehavior:
    """Tests for InputDialog behavior."""

    @pytest.mark.asyncio
    async def test_ok_button_returns_value(self) -> None:
        """Test OK button returns input value."""
        class TestApp(App):
            result = "NOT_SET"
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: str | None) -> None:
                    self.result = result
                self.push_screen(InputDialog("Test", "Name:", default="test_value"), callback)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            ok_btn = pilot.app.screen.query_one("#ok", Button)
            await pilot.click(ok_btn)
            await pilot.pause()
            assert pilot.app.result == "test_value"

    @pytest.mark.asyncio
    async def test_cancel_button_returns_none(self) -> None:
        """Test cancel button returns None."""
        class TestApp(App):
            result = "NOT_SET"
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: str | None) -> None:
                    self.result = result
                self.push_screen(InputDialog("Test", "Name:"), callback)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            cancel_btn = pilot.app.screen.query_one("#cancel", Button)
            await pilot.click(cancel_btn)
            await pilot.pause()
            assert pilot.app.result is None

    @pytest.mark.asyncio
    async def test_escape_key_returns_none(self) -> None:
        """Test escape key returns None."""
        class TestApp(App):
            result = "NOT_SET"
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: str | None) -> None:
                    self.result = result
                self.push_screen(InputDialog("Test", "Name:"), callback)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert pilot.app.result is None


# ============================================================================
# SelectAlternativeDialog Tests
# ============================================================================

class TestSelectDialogCreation:
    """Tests for SelectAlternativeDialog creation."""

    def test_creation(self, simple_group: AlternativeGroup) -> None:
        """Test basic dialog creation."""
        dialog = SelectAlternativeDialog("Select", simple_group)
        assert dialog.title_text == "Select"
        assert dialog.group == simple_group


class TestSelectDialogBehavior:
    """Tests for SelectAlternativeDialog behavior."""

    @pytest.mark.asyncio
    async def test_cancel_returns_none(self, simple_group: AlternativeGroup) -> None:
        """Test cancel button returns None."""
        class TestApp(App):
            result = "NOT_SET"
            
            def __init__(self, group: AlternativeGroup):
                super().__init__()
                self.group = group
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: str | None) -> None:
                    self.result = result
                self.push_screen(SelectAlternativeDialog("Select", self.group), callback)

        async with TestApp(simple_group).run_test() as pilot:
            await pilot.pause()
            cancel_btn = pilot.app.screen.query_one("#cancel", Button)
            await pilot.click(cancel_btn)
            await pilot.pause()
            assert pilot.app.result is None

    @pytest.mark.asyncio
    async def test_escape_returns_none(self, simple_group: AlternativeGroup) -> None:
        """Test escape key returns None."""
        class TestApp(App):
            result = "NOT_SET"
            
            def __init__(self, group: AlternativeGroup):
                super().__init__()
                self.group = group
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: str | None) -> None:
                    self.result = result
                self.push_screen(SelectAlternativeDialog("Select", self.group), callback)

        async with TestApp(simple_group).run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert pilot.app.result is None

    @pytest.mark.asyncio
    async def test_number_key_selects(self, simple_group: AlternativeGroup) -> None:
        """Test number key selects alternative."""
        class TestApp(App):
            result = "NOT_SET"
            
            def __init__(self, group: AlternativeGroup):
                super().__init__()
                self.group = group
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: str | None) -> None:
                    self.result = result
                self.push_screen(SelectAlternativeDialog("Select", self.group), callback)

        async with TestApp(simple_group).run_test() as pilot:
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()
            # First alternative is the highest priority one
            assert pilot.app.result == "/usr/bin/vim"

    @pytest.mark.asyncio
    async def test_enter_selects_focused(self, simple_group: AlternativeGroup) -> None:
        """Test enter key selects focused option."""
        class TestApp(App):
            result = "NOT_SET"
            
            def __init__(self, group: AlternativeGroup):
                super().__init__()
                self.group = group
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: str | None) -> None:
                    self.result = result
                self.push_screen(SelectAlternativeDialog("Select", self.group), callback)

        async with TestApp(simple_group).run_test() as pilot:
            await pilot.pause()
            # First button should be focused by default
            await pilot.press("enter")
            await pilot.pause()
            assert pilot.app.result == "/usr/bin/vim"


class TestSelectDialogWithManyAlternatives:
    """Tests for SelectAlternativeDialog with many alternatives."""

    @pytest.mark.asyncio
    async def test_handles_many_alternatives(self, many_alternatives_group: AlternativeGroup) -> None:
        """Test dialog handles groups with many alternatives."""
        class TestApp(App):
            result = "NOT_SET"
            
            def __init__(self, group: AlternativeGroup):
                super().__init__()
                self.group = group
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: str | None) -> None:
                    self.result = result
                self.push_screen(SelectAlternativeDialog("Select", self.group), callback)

        async with TestApp(many_alternatives_group).run_test() as pilot:
            await pilot.pause()
            # Should render without error
            await pilot.press("escape")
            await pilot.pause()
            assert pilot.app.result is None

    @pytest.mark.asyncio
    async def test_arrow_keys_navigate(self, simple_group: AlternativeGroup) -> None:
        """Test arrow keys navigate options."""
        class TestApp(App):
            result = "NOT_SET"
            
            def __init__(self, group: AlternativeGroup):
                super().__init__()
                self.group = group
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: str | None) -> None:
                    self.result = result
                self.push_screen(SelectAlternativeDialog("Select", self.group), callback)

        async with TestApp(simple_group).run_test() as pilot:
            await pilot.pause()
            # Navigate down then select
            await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()
            # Second alternative
            assert pilot.app.result == "/usr/bin/nano"


# ============================================================================
# HelpDialog Tests
# ============================================================================

class TestHelpDialog:
    """Tests for HelpDialog."""

    @pytest.mark.asyncio
    async def test_close_button_dismisses(self) -> None:
        """Test close button dismisses dialog."""
        class TestApp(App):
            closed = False
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result) -> None:
                    self.closed = True
                self.push_screen(HelpDialog(), callback)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            # Focus button and press Enter (reliable keyboard activation)
            btn = pilot.app.screen.query_one("#close", Button)
            btn.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert pilot.app.closed is True

    @pytest.mark.asyncio
    async def test_escape_dismisses(self) -> None:
        """Test escape key dismisses dialog."""
        class TestApp(App):
            closed = False
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result) -> None:
                    self.closed = True
                self.push_screen(HelpDialog(), callback)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert pilot.app.closed is True

    @pytest.mark.asyncio
    async def test_q_key_dismisses(self) -> None:
        """Test q key dismisses dialog."""
        class TestApp(App):
            closed = False
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result) -> None:
                    self.closed = True
                self.push_screen(HelpDialog(), callback)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            await pilot.press("q")
            await pilot.pause()
            assert pilot.app.closed is True


# ============================================================================
# InstallDialog Tests
# ============================================================================

class TestInstallDialogCreation:
    """Tests for InstallDialog creation."""

    def test_creation_empty(self) -> None:
        """Test creating empty dialog."""
        dialog = InstallDialog()
        assert dialog.alt_name == ""
        assert dialog.alt_link == ""

    def test_creation_with_name(self) -> None:
        """Test creating with pre-filled name."""
        dialog = InstallDialog(name="editor")
        assert dialog.alt_name == "editor"

    def test_creation_with_link(self) -> None:
        """Test creating with pre-filled link."""
        dialog = InstallDialog(name="editor", link="/usr/bin/editor")
        assert dialog.alt_link == "/usr/bin/editor"


class TestInstallDialogBehavior:
    """Tests for InstallDialog behavior."""

    @pytest.mark.asyncio
    async def test_cancel_returns_none(self) -> None:
        """Test cancel button returns None."""
        class TestApp(App):
            result = "NOT_SET"
            
            def compose(self) -> ComposeResult:
                yield Static("Main")
            
            def on_mount(self) -> None:
                def callback(result: dict | None) -> None:
                    self.result = result
                self.push_screen(InstallDialog(), callback)

        async with TestApp().run_test() as pilot:
            await pilot.pause()
            cancel_btn = pilot.app.screen.query_one("#cancel", Button)
            await pilot.click(cancel_btn)
            await pilot.pause()
            assert pilot.app.result is None


# ============================================================================
# CSS Tests
# ============================================================================

class TestWidgetCSS:
    """Tests for widget CSS constants."""

    def test_status_widget_css_exists(self) -> None:
        """Test StatusWidget CSS exists and has content."""
        assert STATUS_WIDGET_CSS is not None
        assert len(STATUS_WIDGET_CSS) > 0
        assert "StatusWidget" in STATUS_WIDGET_CSS

    def test_dialog_css_exists(self) -> None:
        """Test dialog CSS exists."""
        assert DIALOG_CSS is not None
        assert ".dialog-container" in DIALOG_CSS

    def test_input_dialog_css_exists(self) -> None:
        """Test input dialog CSS exists."""
        assert INPUT_DIALOG_CSS is not None
        assert ".input" in INPUT_DIALOG_CSS

    def test_detail_panel_css_exists(self) -> None:
        """Test detail panel CSS exists."""
        assert DETAIL_PANEL_CSS is not None
        assert "AlternativeDetailPanel" in DETAIL_PANEL_CSS

    def test_select_dialog_css_exists(self) -> None:
        """Test select dialog CSS exists."""
        assert SELECT_DIALOG_CSS is not None
        assert ".select-dialog" in SELECT_DIALOG_CSS

    def test_help_dialog_css_exists(self) -> None:
        """Test help dialog CSS exists."""
        assert HELP_DIALOG_CSS is not None


class TestStatusIndicators:
    """Tests for status indicator constants."""

    def test_current_indicator(self) -> None:
        """Test current indicator exists."""
        assert StatusIndicator.CURRENT is not None
        assert len(StatusIndicator.CURRENT) > 0

    def test_best_indicator(self) -> None:
        """Test best indicator exists."""
        assert StatusIndicator.BEST is not None

    def test_indicators_are_different(self) -> None:
        """Test that different indicators have different values."""
        assert StatusIndicator.CURRENT != StatusIndicator.BEST


class TestStatusColors:
    """Tests for status color constants."""

    def test_success_color(self) -> None:
        """Test success color exists."""
        assert StatusColor.SUCCESS is not None

    def test_error_color(self) -> None:
        """Test error color exists."""
        assert StatusColor.ERROR is not None

    def test_info_color(self) -> None:
        """Test info color exists."""
        assert StatusColor.INFO is not None


# ============================================================================
# Layout and Scrolling Tests
# ============================================================================

class TestDetailPanelScrolling:
    """Tests for detail panel scrolling behavior."""

    @pytest.mark.asyncio
    async def test_long_content_in_scroll_container(self, many_alternatives_group: AlternativeGroup) -> None:
        """Test that long content is scrollable when in VerticalScroll."""
        class TestApp(App):
            def compose(self) -> ComposeResult:
                with VerticalScroll(id="scroll"):
                    yield AlternativeDetailPanel(id="panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#panel", AlternativeDetailPanel)
            panel.update_details(many_alternatives_group)
            await pilot.pause()
            
            # Verify scroll container exists
            scroll = pilot.app.query_one("#scroll", VerticalScroll)
            assert scroll is not None


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_single_character_group_name(self) -> None:
        """Test handling group with single character name."""
        group = AlternativeGroup(
            name="x",
            link="/usr/bin/test",
            status=AlternativeStatus.AUTO,
            alternatives=[Alternative("/usr/bin/test", 50)],
            best="/usr/bin/test",
            current="/usr/bin/test",
        )
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield AlternativeDetailPanel(id="panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#panel", AlternativeDetailPanel)
            # Should not raise
            panel.update_details(group)

    @pytest.mark.asyncio
    async def test_group_with_no_alternatives(self) -> None:
        """Test handling group with no alternatives."""
        group = AlternativeGroup(
            name="test",
            link="/usr/bin/test",
            status=AlternativeStatus.AUTO,
            alternatives=[],
            best="",
            current="",
        )
        
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield AlternativeDetailPanel(id="panel")

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one("#panel", AlternativeDetailPanel)
            # Should not raise
            panel.update_details(group)

    def test_status_widget_rapid_updates(self) -> None:
        """Test rapid status updates don't cause issues."""
        widget = StatusWidget(auto_clear=None)
        for i in range(100):
            widget.show_message(f"Message {i}")
        # Should not raise
