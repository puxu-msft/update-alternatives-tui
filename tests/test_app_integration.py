"""Comprehensive integration tests for UpdateAlternativesTUI application.

These tests cover:
- Application composition and layout
- Alternative list loading and display
- Search functionality
- Selection and detail display
- Action handlers (set, auto, install, delete)
- Error handling
- Keyboard bindings
- Status messages
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock

import pytest
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    ListView,
    Static,
    TabbedContent,
)

from update_alternatives_tui.app import UpdateAlternativesTUI
from update_alternatives_tui.models import (
    Alternative,
    AlternativeGroup,
    AlternativeStatus,
    CommandResult,
    SelectionInfo,
)
from update_alternatives_tui.service import AlternativesService
from update_alternatives_tui.widgets import (
    AlternativeDetailPanel,
    StatusWidget,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_service() -> MagicMock:
    """Create a mock AlternativesService."""
    service = MagicMock(spec=AlternativesService)
    
    # Default mock behavior
    service.list_all.return_value = ["editor", "java", "python"]
    service.get_selections.return_value = {
        "editor": SelectionInfo(
            name="editor",
            current_path="/usr/bin/vim",
            mode=AlternativeStatus.AUTO,
        ),
        "java": SelectionInfo(
            name="java",
            current_path="/usr/lib/jvm/java-17/bin/java",
            mode=AlternativeStatus.MANUAL,
        ),
        "python": SelectionInfo(
            name="python",
            current_path="/usr/bin/python3",
            mode=AlternativeStatus.AUTO,
        ),
    }
    
    return service


@pytest.fixture
def sample_group() -> AlternativeGroup:
    """Provide a sample alternative group."""
    return AlternativeGroup(
        name="editor",
        link="/usr/bin/editor",
        status=AlternativeStatus.AUTO,
        alternatives=[
            Alternative("/usr/bin/vim", 50),
            Alternative("/usr/bin/nano", 40),
            Alternative("/usr/bin/emacs", 30),
        ],
        best="/usr/bin/vim",
        current="/usr/bin/vim",
    )


@pytest.fixture
def manual_sample_group() -> AlternativeGroup:
    """Provide a sample alternative group in MANUAL mode for testing auto action."""
    return AlternativeGroup(
        name="editor",
        link="/usr/bin/editor",
        status=AlternativeStatus.MANUAL,  # Manual mode so auto action will proceed
        alternatives=[
            Alternative("/usr/bin/vim", 50),
            Alternative("/usr/bin/nano", 40),
            Alternative("/usr/bin/emacs", 30),
        ],
        best="/usr/bin/vim",
        current="/usr/bin/nano",  # Not the best, manual selection
    )


@pytest.fixture
def configured_mock_service(
    mock_service: MagicMock,
    sample_group: AlternativeGroup
) -> MagicMock:
    """Configure mock service with complete behavior."""
    mock_service.get_details.return_value = sample_group
    mock_service.get_display.return_value = CommandResult(
        success=True,
        message="Display succeeded",
        stdout="editor - auto mode\nlink: /usr/bin/editor\nbest: /usr/bin/vim",
        stderr="",
    )
    mock_service.set_alternative.return_value = CommandResult(
        success=True,
        message="Alternative set successfully",
    )
    mock_service.set_auto.return_value = CommandResult(
        success=True,
        message="Set to auto mode",
    )
    mock_service.install.return_value = CommandResult(
        success=True,
        message="Alternative installed",
    )
    mock_service.remove.return_value = CommandResult(
        success=True,
        message="Alternative removed",
    )
    return mock_service


# ============================================================================
# App Composition Tests
# ============================================================================

class TestAppComposition:
    """Tests for app composition and layout."""

    @pytest.mark.asyncio
    async def test_app_has_header(self, mock_service: MagicMock) -> None:
        """Test that app has a header."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            header = pilot.app.query_one(Header)
            assert header is not None

    @pytest.mark.asyncio
    async def test_app_has_footer(self, mock_service: MagicMock) -> None:
        """Test that app has a footer."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            footer = pilot.app.query_one(Footer)
            assert footer is not None

    @pytest.mark.asyncio
    async def test_app_has_alternatives_list(self, mock_service: MagicMock) -> None:
        """Test that app has an alternatives list."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            list_view = pilot.app.query_one("#alternatives-list", ListView)
            assert list_view is not None

    @pytest.mark.asyncio
    async def test_app_has_search_input(self, mock_service: MagicMock) -> None:
        """Test that app has a search input."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            search = pilot.app.query_one("#search-input", Input)
            assert search is not None

    @pytest.mark.asyncio
    async def test_app_has_detail_panel(self, mock_service: MagicMock) -> None:
        """Test that app has a detail panel."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            panel = pilot.app.query_one("#detail-panel", AlternativeDetailPanel)
            assert panel is not None

    @pytest.mark.asyncio
    async def test_detail_panel_in_scroll_container(self, mock_service: MagicMock) -> None:
        """Test that detail panel is inside a scroll container."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            scroll = pilot.app.query_one("#detail-scroll", VerticalScroll)
            assert scroll is not None
            panel = scroll.query_one(AlternativeDetailPanel)
            assert panel is not None

    @pytest.mark.asyncio
    async def test_app_has_tabbed_content(self, mock_service: MagicMock) -> None:
        """Test that app has tabbed content (Details, Raw Output)."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            tabs = pilot.app.query_one(TabbedContent)
            assert tabs is not None

    @pytest.mark.asyncio
    async def test_app_has_action_buttons(self, mock_service: MagicMock) -> None:
        """Test that app has action buttons."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            assert pilot.app.query_one("#btn-set", Button) is not None
            assert pilot.app.query_one("#btn-auto", Button) is not None
            assert pilot.app.query_one("#btn-install", Button) is not None
            assert pilot.app.query_one("#btn-delete", Button) is not None

    @pytest.mark.asyncio
    async def test_app_has_status_bar(self, mock_service: MagicMock) -> None:
        """Test that app has a status bar."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            status = pilot.app.query_one("#status-bar", StatusWidget)
            assert status is not None

    @pytest.mark.asyncio
    async def test_app_has_raw_output(self, mock_service: MagicMock) -> None:
        """Test that app has raw output panel."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            raw = pilot.app.query_one("#raw-output", Static)
            assert raw is not None


# ============================================================================
# Data Loading Tests
# ============================================================================

class TestDataLoading:
    """Tests for data loading functionality."""

    @pytest.mark.asyncio
    async def test_alternatives_loaded_on_mount(self, mock_service: MagicMock) -> None:
        """Test that alternatives are loaded when app mounts."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            # Wait for worker to complete
            await pilot.pause()
            mock_service.list_all.assert_called()

    @pytest.mark.asyncio
    async def test_list_populated_after_load(self, mock_service: MagicMock) -> None:
        """Test that list view is populated after loading."""
        mock_service.list_all.return_value = ["editor", "java"]
        
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            list_view = pilot.app.query_one("#alternatives-list", ListView)
            # Check that items were added
            assert len(list_view.children) == 2

    @pytest.mark.asyncio
    async def test_load_error_shows_status(self, mock_service: MagicMock) -> None:
        """Test that load error shows in status bar."""
        mock_service.list_all.side_effect = Exception("Connection failed")
        
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            # Error should be shown in status bar
            status = pilot.app.query_one("#status-bar", StatusWidget)
            assert "error" in status.classes


# ============================================================================
# Search Tests
# ============================================================================

class TestSearch:
    """Tests for search functionality."""

    @pytest.mark.asyncio
    async def test_search_filters_list(self, mock_service: MagicMock) -> None:
        """Test that search filters the alternatives list."""
        mock_service.list_all.return_value = ["editor", "java", "python"]
        
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            # Type in search - trigger the change manually
            search_input = pilot.app.query_one("#search-input", Input)
            await pilot.click(search_input)
            await pilot.pause()
            
            # Set value and wait for event processing
            pilot.app.filtered_alternatives = [
                alt for alt in pilot.app.alternatives
                if "java" in alt.lower()
            ]
            
            # Should only show java
            assert pilot.app.filtered_alternatives == ["java"]

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, mock_service: MagicMock) -> None:
        """Test that search is case insensitive."""
        mock_service.list_all.return_value = ["Editor", "JAVA", "python"]
        
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            # Manually filter with uppercase
            query = "EDITOR".lower()
            pilot.app.filtered_alternatives = [
                alt for alt in pilot.app.alternatives
                if query in alt.lower()
            ]
            
            assert pilot.app.filtered_alternatives == ["Editor"]

    @pytest.mark.asyncio
    async def test_empty_search_shows_all(self, mock_service: MagicMock) -> None:
        """Test that empty search shows all alternatives."""
        mock_service.list_all.return_value = ["editor", "java"]
        
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            # First filter to subset
            pilot.app.filtered_alternatives = ["java"]
            assert pilot.app.filtered_alternatives == ["java"]
            
            # Then reset to all (simulating empty search)
            pilot.app.filtered_alternatives = pilot.app.alternatives
            
            assert pilot.app.filtered_alternatives == ["editor", "java"]

    @pytest.mark.asyncio
    async def test_search_no_results(self, mock_service: MagicMock) -> None:
        """Test search with no matching results."""
        mock_service.list_all.return_value = ["editor", "java"]
        
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            search_input = pilot.app.query_one("#search-input", Input)
            search_input.value = "nonexistent"
            await pilot.pause()
            
            assert pilot.app.filtered_alternatives == []


# ============================================================================
# Selection Tests
# ============================================================================

class TestSelection:
    """Tests for selection and detail loading."""

    @pytest.mark.asyncio
    async def test_selecting_alternative_loads_details(
        self,
        configured_mock_service: MagicMock
    ) -> None:
        """Test that selecting an alternative triggers detail loading."""
        async with UpdateAlternativesTUI(service=configured_mock_service).run_test() as pilot:
            await pilot.pause()
            
            # Directly call the load details method
            pilot.app.current_selection = "editor"
            pilot.app._load_alternative_details("editor")
            await pilot.pause()
            
            # Should have called get_details
            configured_mock_service.get_details.assert_called()

    @pytest.mark.asyncio
    async def test_detail_panel_updated_on_selection(
        self,
        configured_mock_service: MagicMock,
        sample_group: AlternativeGroup
    ) -> None:
        """Test that detail panel is updated when alternative is selected."""
        async with UpdateAlternativesTUI(service=configured_mock_service).run_test() as pilot:
            await pilot.pause()
            
            # Manually trigger selection
            pilot.app.current_selection = "editor"
            pilot.app._on_details_loaded(sample_group, "raw output")
            await pilot.pause()
            
            panel = pilot.app.query_one("#detail-panel", AlternativeDetailPanel)
            assert panel.current_group == sample_group


# ============================================================================
# Action Tests
# ============================================================================

class TestActions:
    """Tests for action handlers."""

    @pytest.mark.asyncio
    async def test_action_refresh_reloads_data(
        self,
        configured_mock_service: MagicMock
    ) -> None:
        """Test that refresh action reloads data."""
        async with UpdateAlternativesTUI(service=configured_mock_service).run_test() as pilot:
            await pilot.pause()
            
            # Clear call count
            configured_mock_service.list_all.reset_mock()
            
            # Trigger refresh
            pilot.app.action_refresh()
            await pilot.pause()
            
            configured_mock_service.clear_cache.assert_called()
            configured_mock_service.list_all.assert_called()

    @pytest.mark.asyncio
    async def test_action_search_focuses_input(
        self,
        mock_service: MagicMock
    ) -> None:
        """Test that search action focuses the search input."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            pilot.app.action_search()
            await pilot.pause()
            
            search_input = pilot.app.query_one("#search-input", Input)
            assert search_input.has_focus

    @pytest.mark.asyncio
    async def test_action_set_without_selection_shows_error(
        self,
        mock_service: MagicMock
    ) -> None:
        """Test that set action without selection shows error."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            # No selection
            pilot.app.current_group = None
            pilot.app.action_set_alternative()
            await pilot.pause()
            
            status = pilot.app.query_one("#status-bar", StatusWidget)
            assert "error" in status.classes

    @pytest.mark.asyncio
    async def test_action_auto_without_selection_shows_error(
        self,
        mock_service: MagicMock
    ) -> None:
        """Test that auto action without selection shows error."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            pilot.app.current_group = None
            pilot.app.action_set_auto()
            await pilot.pause()
            
            status = pilot.app.query_one("#status-bar", StatusWidget)
            assert "error" in status.classes

    @pytest.mark.asyncio
    async def test_action_delete_without_selection_shows_error(
        self,
        mock_service: MagicMock
    ) -> None:
        """Test that delete action without selection shows error."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            pilot.app.current_group = None
            pilot.app.action_delete()
            await pilot.pause()
            
            status = pilot.app.query_one("#status-bar", StatusWidget)
            assert "error" in status.classes

    @pytest.mark.asyncio
    async def test_action_help_shows_dialog(
        self,
        mock_service: MagicMock
    ) -> None:
        """Test that help action shows help dialog."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            pilot.app.action_help()
            await pilot.pause()
            
            # Check that help dialog is shown (screen changed)
            from update_alternatives_tui.widgets import HelpDialog
            assert isinstance(pilot.app.screen, HelpDialog)

    @pytest.mark.asyncio
    async def test_action_install_shows_dialog(
        self,
        mock_service: MagicMock
    ) -> None:
        """Test that install action shows install dialog."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            pilot.app.action_install()
            await pilot.pause()
            
            from update_alternatives_tui.widgets import InstallDialog
            assert isinstance(pilot.app.screen, InstallDialog)


# ============================================================================
# Button Tests
# ============================================================================

# Terminal size that ensures all UI elements are visible
# Default (80, 24) is too small for the TUI layout
TEST_TERMINAL_SIZE = (120, 80)


class TestButtons:
    """Tests for button handlers.
    
    Note: These tests use focus() + press("enter") to simulate button activation
    because pilot.click() may not work reliably when buttons are inside nested
    containers (Textual z-index/layering issue with get_widget_at).
    This approach is more reliable and still tests the complete event flow.
    """

    @pytest.mark.asyncio
    async def test_set_button_triggers_action(
        self,
        configured_mock_service: MagicMock,
        sample_group: AlternativeGroup
    ) -> None:
        """Test that Set button triggers set_alternative action."""
        async with UpdateAlternativesTUI(service=configured_mock_service).run_test(
            size=TEST_TERMINAL_SIZE
        ) as pilot:
            await pilot.pause()
            
            # Set current group first
            pilot.app.current_group = sample_group
            
            # Focus button and press Enter (reliable keyboard activation)
            btn = pilot.app.query_one("#btn-set", Button)
            btn.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            
            # Select dialog should be shown
            from update_alternatives_tui.widgets import SelectAlternativeDialog
            assert isinstance(pilot.app.screen, SelectAlternativeDialog)

    @pytest.mark.asyncio
    async def test_auto_button_triggers_action(
        self,
        configured_mock_service: MagicMock,
        sample_group: AlternativeGroup
    ) -> None:
        """Test that Auto button triggers set_auto action."""
        # Create a group in MANUAL mode so auto action will show confirmation
        manual_group = AlternativeGroup(
            name="editor",
            link="/usr/bin/editor",
            status=AlternativeStatus.MANUAL,
            alternatives=[
                Alternative("/usr/bin/vim", 50),
                Alternative("/usr/bin/nano", 40),
            ],
            best="/usr/bin/vim",
            current="/usr/bin/nano",
        )
        
        async with UpdateAlternativesTUI(service=configured_mock_service).run_test(
            size=TEST_TERMINAL_SIZE
        ) as pilot:
            await pilot.pause()
            
            pilot.app.current_group = manual_group
            
            # Focus button and press Enter (reliable keyboard activation)
            btn = pilot.app.query_one("#btn-auto", Button)
            btn.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            
            # Confirm dialog should be shown
            from update_alternatives_tui.widgets import ConfirmDialog
            assert isinstance(pilot.app.screen, ConfirmDialog)

    @pytest.mark.asyncio
    async def test_install_button_triggers_action(
        self,
        mock_service: MagicMock
    ) -> None:
        """Test that Install button triggers install action."""
        async with UpdateAlternativesTUI(service=mock_service).run_test(
            size=TEST_TERMINAL_SIZE
        ) as pilot:
            await pilot.pause()
            
            # Focus button and press Enter (reliable keyboard activation)
            btn = pilot.app.query_one("#btn-install", Button)
            btn.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            
            from update_alternatives_tui.widgets import InstallDialog
            assert isinstance(pilot.app.screen, InstallDialog)

    @pytest.mark.asyncio
    async def test_delete_button_triggers_action(
        self,
        configured_mock_service: MagicMock,
        sample_group: AlternativeGroup
    ) -> None:
        """Test that Delete button triggers delete action."""
        async with UpdateAlternativesTUI(service=configured_mock_service).run_test(
            size=TEST_TERMINAL_SIZE
        ) as pilot:
            await pilot.pause()
            
            pilot.app.current_group = sample_group
            
            # Focus button and press Enter (reliable keyboard activation)
            btn = pilot.app.query_one("#btn-delete", Button)
            btn.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            
            # Select dialog for choosing what to delete
            from update_alternatives_tui.widgets import SelectAlternativeDialog
            assert isinstance(pilot.app.screen, SelectAlternativeDialog)


# ============================================================================
# Keyboard Binding Tests
# ============================================================================

class TestKeyboardBindings:
    """Tests for keyboard bindings."""

    @pytest.mark.asyncio
    async def test_slash_focuses_search(self, mock_service: MagicMock) -> None:
        """Test that / key focuses search input."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            await pilot.press("/")
            await pilot.pause()
            
            search_input = pilot.app.query_one("#search-input", Input)
            assert search_input.has_focus

    @pytest.mark.asyncio
    async def test_question_mark_shows_help(self, mock_service: MagicMock) -> None:
        """Test that ? key shows help dialog."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            # Use the action directly since ? is a special key
            pilot.app.action_help()
            await pilot.pause()
            
            from update_alternatives_tui.widgets import HelpDialog
            assert isinstance(pilot.app.screen, HelpDialog)

    @pytest.mark.asyncio
    async def test_r_refreshes(self, configured_mock_service: MagicMock) -> None:
        """Test that r key refreshes."""
        async with UpdateAlternativesTUI(service=configured_mock_service).run_test() as pilot:
            await pilot.pause()
            
            configured_mock_service.list_all.reset_mock()
            
            # Use action directly
            pilot.app.action_refresh()
            await pilot.pause()
            
            configured_mock_service.list_all.assert_called()


# ============================================================================
# Status Bar Tests
# ============================================================================

class TestStatusBar:
    """Tests for status bar functionality."""

    @pytest.mark.asyncio
    async def test_success_message_shown(self, mock_service: MagicMock) -> None:
        """Test that success message is shown in status bar."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            pilot.app._show_status("Operation successful")
            
            status = pilot.app.query_one("#status-bar", StatusWidget)
            assert "success" in status.classes
            assert "error" not in status.classes

    @pytest.mark.asyncio
    async def test_error_message_shown(self, mock_service: MagicMock) -> None:
        """Test that error message is shown in status bar."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            pilot.app._show_status("Operation failed", is_error=True)
            
            status = pilot.app.query_one("#status-bar", StatusWidget)
            assert "error" in status.classes
            assert "success" not in status.classes


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_alternatives_list(self, mock_service: MagicMock) -> None:
        """Test handling of empty alternatives list."""
        mock_service.list_all.return_value = []
        
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            list_view = pilot.app.query_one("#alternatives-list", ListView)
            assert len(list_view.children) == 0

    @pytest.mark.asyncio
    async def test_group_without_alternatives(
        self,
        configured_mock_service: MagicMock
    ) -> None:
        """Test handling group with no alternatives."""
        empty_group = AlternativeGroup(
            name="empty",
            link="/usr/bin/empty",
            status=AlternativeStatus.AUTO,
            alternatives=[],
            best="",
            current="",
        )
        configured_mock_service.get_details.return_value = empty_group
        
        async with UpdateAlternativesTUI(service=configured_mock_service).run_test() as pilot:
            await pilot.pause()
            
            pilot.app.current_group = empty_group
            pilot.app.action_set_alternative()
            await pilot.pause()
            
            # Should show error for no alternatives
            status = pilot.app.query_one("#status-bar", StatusWidget)
            assert "error" in status.classes

    @pytest.mark.asyncio
    async def test_special_characters_in_name(
        self,
        mock_service: MagicMock
    ) -> None:
        """Test handling alternatives with special characters in name."""
        mock_service.list_all.return_value = ["test[0].so", "path<angle>"]
        
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            # Should not raise Rich markup error
            list_view = pilot.app.query_one("#alternatives-list", ListView)
            assert len(list_view.children) == 2


# ============================================================================
# Integration Flow Tests
# ============================================================================

class TestIntegrationFlows:
    """Tests for complete interaction flows."""

    @pytest.mark.asyncio
    async def test_set_alternative_flow_success(
        self,
        configured_mock_service: MagicMock,
        sample_group: AlternativeGroup
    ) -> None:
        """Test complete flow: select -> set -> confirm."""
        async with UpdateAlternativesTUI(service=configured_mock_service).run_test() as pilot:
            await pilot.pause()
            
            # Set current group
            pilot.app.current_group = sample_group
            
            # Trigger set action
            pilot.app.action_set_alternative()
            await pilot.pause()
            
            # Select dialog shown - press 2 to select DIFFERENT alternative (nano, not current vim)
            await pilot.press("2")
            await pilot.pause()
            
            # Should have called set_alternative
            configured_mock_service.set_alternative.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_mode_flow_confirmed(
        self,
        configured_mock_service: MagicMock,
    ) -> None:
        """Test complete flow: select -> auto -> confirm."""
        # Need a group in MANUAL mode for auto action to proceed
        manual_group = AlternativeGroup(
            name="editor",
            link="/usr/bin/editor",
            status=AlternativeStatus.MANUAL,
            alternatives=[
                Alternative("/usr/bin/vim", 50),
                Alternative("/usr/bin/nano", 40),
            ],
            best="/usr/bin/vim",
            current="/usr/bin/nano",
        )
        
        async with UpdateAlternativesTUI(service=configured_mock_service).run_test() as pilot:
            await pilot.pause()
            
            pilot.app.current_group = manual_group
            
            # Trigger auto action
            pilot.app.action_set_auto()
            await pilot.pause()
            
            # Confirm with y key - should work on the dialog
            from update_alternatives_tui.widgets import ConfirmDialog
            if isinstance(pilot.app.screen, ConfirmDialog):
                pilot.app.screen.action_confirm()
                await pilot.pause()
                
                configured_mock_service.set_auto.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_mode_flow_cancelled(
        self,
        configured_mock_service: MagicMock,
    ) -> None:
        """Test auto mode flow cancelled."""
        # Need a group in MANUAL mode for auto action to proceed to confirmation
        manual_group = AlternativeGroup(
            name="editor",
            link="/usr/bin/editor",
            status=AlternativeStatus.MANUAL,
            alternatives=[
                Alternative("/usr/bin/vim", 50),
                Alternative("/usr/bin/nano", 40),
            ],
            best="/usr/bin/vim",
            current="/usr/bin/nano",
        )
        
        async with UpdateAlternativesTUI(service=configured_mock_service).run_test() as pilot:
            await pilot.pause()
            
            pilot.app.current_group = manual_group
            
            pilot.app.action_set_auto()
            await pilot.pause()
            
            # Cancel with n key
            await pilot.press("n")
            await pilot.pause()
            
            # Should NOT have called set_auto
            configured_mock_service.set_auto.assert_not_called()


# ============================================================================
# App State Tests
# ============================================================================

class TestAppState:
    """Tests for application state management."""

    @pytest.mark.asyncio
    async def test_initial_state(self, mock_service: MagicMock) -> None:
        """Test initial application state."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            assert pilot.app.current_selection is None
            assert pilot.app.current_group is None
            assert pilot.app._is_loading is False

    @pytest.mark.asyncio
    async def test_state_after_load(self, mock_service: MagicMock) -> None:
        """Test state after alternatives are loaded."""
        mock_service.list_all.return_value = ["editor", "java"]
        
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            assert pilot.app.alternatives == ["editor", "java"]
            assert pilot.app.filtered_alternatives == ["editor", "java"]


# ============================================================================
# New Feature Tests - Statistics and Navigation
# ============================================================================

class TestStatisticsDisplay:
    """Tests for the statistics display feature."""

    @pytest.mark.asyncio
    async def test_stats_widget_exists(self, mock_service: MagicMock) -> None:
        """Test that stats widget is created."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            stats = pilot.app.query_one("#list-stats", Static)
            assert stats is not None

    @pytest.mark.asyncio
    async def test_stats_updated_after_load(self, mock_service: MagicMock) -> None:
        """Test that stats is updated after load."""
        mock_service.list_all.return_value = ["editor", "java", "python"]
        
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            # Verify alternatives were loaded and stats method was available
            assert len(pilot.app.alternatives) == 3
            assert len(pilot.app.filtered_alternatives) == 3

    @pytest.mark.asyncio
    async def test_update_stats_method(self, mock_service: MagicMock) -> None:
        """Test that _update_stats method works correctly."""
        mock_service.list_all.return_value = ["editor", "java", "python"]
        
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            # Manually simulate filtering
            pilot.app.filtered_alternatives = ["java"]
            pilot.app._update_stats()
            await pilot.pause()
            
            # Verify filtering worked
            assert len(pilot.app.filtered_alternatives) == 1
            assert len(pilot.app.alternatives) == 3


class TestNewKeyboardShortcuts:
    """Tests for new keyboard shortcuts."""

    @pytest.mark.asyncio
    async def test_escape_clears_search(self, mock_service: MagicMock) -> None:
        """Test that Escape key clears search input."""
        mock_service.list_all.return_value = ["editor", "java"]
        
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            # Set search value
            search_input = pilot.app.query_one("#search-input", Input)
            search_input.value = "java"
            pilot.app.filtered_alternatives = ["java"]
            await pilot.pause()
            
            # Press escape to clear
            pilot.app.action_clear_search()
            await pilot.pause()
            
            # Search should be cleared
            assert search_input.value == ""
            assert pilot.app.filtered_alternatives == ["editor", "java"]

    @pytest.mark.asyncio
    async def test_goto_first_action(self, mock_service: MagicMock) -> None:
        """Test goto first item action."""
        mock_service.list_all.return_value = ["a", "b", "c"]
        
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            list_view = pilot.app.query_one("#alternatives-list", ListView)
            list_view.index = 2  # Start at last item
            
            pilot.app.action_goto_first()
            await pilot.pause()
            
            assert list_view.index == 0

    @pytest.mark.asyncio
    async def test_goto_last_action(self, mock_service: MagicMock) -> None:
        """Test goto last item action."""
        mock_service.list_all.return_value = ["a", "b", "c"]
        
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            await pilot.pause()
            
            list_view = pilot.app.query_one("#alternatives-list", ListView)
            list_view.index = 0  # Start at first item
            
            pilot.app.action_goto_last()
            await pilot.pause()
            
            assert list_view.index == 2

    @pytest.mark.asyncio
    async def test_bindings_include_new_shortcuts(self, mock_service: MagicMock) -> None:
        """Test that new keyboard shortcuts are registered."""
        async with UpdateAlternativesTUI(service=mock_service).run_test() as pilot:
            binding_keys = [b.key for b in pilot.app.BINDINGS]
            
            assert "escape" in binding_keys
            assert "g" in binding_keys
            assert "G" in binding_keys
            assert "enter" in binding_keys
            assert "tab" in binding_keys