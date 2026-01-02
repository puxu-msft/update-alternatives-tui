"""TUI Application for update-alternatives management.

This module provides the main application class that ties together
all components into a complete TUI experience.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
    TabbedContent,
    TabPane,
)
from textual.worker import get_current_worker

from .constants import APP_VERSION, KeyBinding, StatusColor
from .models import AlternativeGroup, InstallRequest
from .service import AlternativesService
from .utils import escape_markup, sanitize_widget_id
from .widgets import (
    AlternativeDetailPanel,
    ConfirmDialog,
    HelpDialog,
    InstallDialog,
    SelectAlternativeDialog,
    StatusWidget,
)
from .app_styles import APP_CSS

if TYPE_CHECKING:
    pass


# ============================================================================
# Main Application
# ============================================================================

class UpdateAlternativesTUI(App):
    """Main TUI Application for update-alternatives management.
    
    This is the main entry point for the TUI application. It manages
    the overall layout, state, and coordination between components.
    
    Features:
    - List and search alternatives
    - View detailed information
    - Set alternatives (manual mode)
    - Set to auto mode
    - Install new alternatives
    - Remove alternatives
    
    Example:
        app = UpdateAlternativesTUI()
        app.run()
    """
    
    TITLE = "Update-Alternatives Manager"
    SUB_TITLE = f"TUI for managing system alternatives v{APP_VERSION}"
    CSS = APP_CSS
    
    BINDINGS: ClassVar[list[Binding]] = [
        Binding(KeyBinding.QUIT, "quit", "Quit"),
        Binding(KeyBinding.REFRESH, "refresh", "Refresh"),
        Binding(KeyBinding.SET, "set_alternative", "Set"),
        Binding(KeyBinding.AUTO, "set_auto", "Auto"),
        Binding(KeyBinding.INSTALL, "install", "Install"),
        Binding(KeyBinding.DELETE, "delete", "Delete"),
        Binding(KeyBinding.SEARCH, "search", "Search"),
        Binding(KeyBinding.HELP, "help", "Help"),
        Binding("escape", "clear_search", "Clear", show=False),
        Binding("g", "goto_first", "First", show=False),
        Binding("G", "goto_last", "Last", show=False),
        Binding("enter", "select_current", "Select", show=False),
        Binding("tab", "focus_next_panel", "Next Panel", show=False),
    ]
    
    def __init__(
        self,
        service: AlternativesService | None = None,
        **kwargs
    ) -> None:
        """Initialize the TUI application.
        
        Args:
            service: AlternativesService instance (for dependency injection)
            **kwargs: Additional arguments for App
        """
        super().__init__(**kwargs)
        self.service = service or AlternativesService()
        
        # State
        self.alternatives: list[str] = []
        self.filtered_alternatives: list[str] = []
        self.current_selection: str | None = None
        self.current_group: AlternativeGroup | None = None
        self._is_loading = False
        self._pending_delete_path: str = ""  # For delete confirmation flow
    
    # ========================================================================
    # Compose UI
    # ========================================================================
    
    def compose(self) -> ComposeResult:
        """Compose the application UI."""
        yield Header(show_clock=True)
        
        with Container(id="main-container"):
            with Horizontal():
                # Left panel - alternatives list
                with Vertical(id="left-panel"):
                    yield Static("Alternatives", id="list-header")
                    yield Static("", id="list-stats")  # Statistics display
                    with Container(id="search-container"):
                        yield Input(
                            placeholder="Search (/ to focus, Esc to clear)...",
                            id="search-input"
                        )
                    yield ListView(id="alternatives-list")
                
                # Right panel - details
                with Vertical(id="right-panel"):
                    with TabbedContent():
                        with TabPane("Details", id="details-tab"):
                            with VerticalScroll(id="detail-scroll"):
                                yield AlternativeDetailPanel(id="detail-panel")
                        with TabPane("Raw Output", id="raw-tab"):
                            with VerticalScroll():
                                yield Static(id="raw-output")
                    
                    with Horizontal(id="action-buttons"):
                        yield Button("Set", variant="primary", id="btn-set")
                        yield Button("Auto", variant="success", id="btn-auto")
                        yield Button("Install", variant="warning", id="btn-install")
                        yield Button("Delete", variant="error", id="btn-delete")
        
        yield StatusWidget(id="status-bar")
        yield Footer()
    
    # ========================================================================
    # Lifecycle
    # ========================================================================
    
    # Minimum recommended terminal size
    MIN_WIDTH = 80
    MIN_HEIGHT = 24
    
    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.title = self.TITLE
        self.sub_title = self.SUB_TITLE
        self._is_loading = True  # Set loading flag during initial load
        self._check_terminal_size()
        self.load_alternatives()
    
    def on_resize(self) -> None:
        """Called when terminal is resized."""
        self._check_terminal_size()
    
    def _check_terminal_size(self) -> None:
        """Check if terminal size is sufficient and warn if too small."""
        size = self.screen.size
        if size.width < self.MIN_WIDTH or size.height < self.MIN_HEIGHT:
            self._show_status(
                f"Terminal too small ({size.width}x{size.height}). "
                f"Recommended: {self.MIN_WIDTH}x{self.MIN_HEIGHT}",
                is_error=True
            )
    
    # ========================================================================
    # Data Loading
    # ========================================================================
    
    @work(thread=True)
    def load_alternatives(self) -> None:
        """Load all alternatives in background."""
        worker = get_current_worker()
        
        # Mark loading state (set from main thread in action_refresh)
        try:
            alternatives = self.service.list_all()
            if not worker.is_cancelled:
                self.call_from_thread(self._on_alternatives_loaded, alternatives)
        except Exception as e:
            if not worker.is_cancelled:
                self.call_from_thread(self._on_load_failed, str(e))
    
    def _on_load_failed(self, error: str) -> None:
        """Handle alternatives load failure."""
        self._is_loading = False
        self._update_stats()
        self._show_status(f"Failed to load alternatives: {error}", is_error=True)
    
    def _on_alternatives_loaded(self, alternatives: list[str]) -> None:
        """Handle alternatives loaded.
        
        Args:
            alternatives: List of alternative names
        """
        self.alternatives = alternatives
        
        # Apply current search filter if any
        search_input = self.query_one("#search-input", Input)
        query = search_input.value.lower().strip()
        
        if query:
            self.filtered_alternatives = [
                alt for alt in self.alternatives
                if query in alt.lower()
            ]
        else:
            self.filtered_alternatives = alternatives
        
        self._refresh_list_view()
        self._update_stats()
        self._is_loading = False  # Clear loading flag after list is refreshed
        self._show_status(f"Loaded {len(alternatives)} alternatives")
    
    def _update_stats(self) -> None:
        """Update the statistics display."""
        stats = self.query_one("#list-stats", Static)
        total = len(self.alternatives)
        shown = len(self.filtered_alternatives)
        
        if total == 0:
            stats.update(f"[{StatusColor.MUTED}]No alternatives found[/{StatusColor.MUTED}]")
        elif shown == total:
            stats.update(f"[{StatusColor.MUTED}]{total} alternatives[/{StatusColor.MUTED}]")
        else:
            stats.update(f"[{StatusColor.INFO}]{shown}[/{StatusColor.INFO}][{StatusColor.MUTED}]/{total} shown[/{StatusColor.MUTED}]")
    
    def _refresh_list_view(self) -> None:
        """Schedule an async refresh of the ListView.
        
        This method triggers an async worker to properly await the removal
        of existing children before mounting new ones, avoiding race conditions.
        """
        self._do_refresh_list_view()
    
    @work(exclusive=True)
    async def _do_refresh_list_view(self) -> None:
        """Actually refresh the ListView with current filtered alternatives.
        
        Uses await remove_children() to ensure all existing items are removed
        before mounting new ones, preventing DuplicateIds errors.
        
        The exclusive=True ensures only one refresh runs at a time.
        
        After refreshing, restores the previous selection if it still exists
        in the filtered list, and reloads the details panel.
        """
        list_view = self.query_one("#alternatives-list", ListView)
        
        # Remember current selection before clearing
        previous_selection = self.current_selection
        
        # Await the removal to ensure it completes before mounting new items
        await list_view.remove_children()
        
        # Get selections for status indicators
        selections = self.service.get_selections()
        
        # Build all items first, tracking index of previous selection
        items: list[ListItem] = []
        restore_index: int | None = None
        
        for i, name in enumerate(self.filtered_alternatives):
            info = selections.get(name)
            if info:
                if info.is_auto:
                    mode_indicator = f"[{StatusColor.AUTO_MODE}]A[/{StatusColor.AUTO_MODE}]"
                else:
                    mode_indicator = f"[{StatusColor.MANUAL_MODE}]M[/{StatusColor.MANUAL_MODE}]"
            else:
                mode_indicator = f"[{StatusColor.MUTED}]?[/{StatusColor.MUTED}]"
            
            # Escape name to prevent Rich markup injection
            safe_name = escape_markup(name)
            item = ListItem(
                Label(f"{mode_indicator} {safe_name}"),
                id=sanitize_widget_id(name, prefix="alt")
            )
            item.data = name  # Store original name for lookup
            items.append(item)
            
            # Track position of previously selected item
            if name == previous_selection:
                restore_index = i
        
        # Mount all items at once
        if items:
            list_view.mount(*items)
            
            # Restore previous selection if it exists in current filtered list
            if restore_index is not None:
                list_view.index = restore_index
                # Setting index doesn't trigger Highlighted event, so manually reload details
                self._load_alternative_details(previous_selection)
    
    @work(thread=True)
    def _load_alternative_details(self, name: str) -> None:
        """Load details for selected alternative.
        
        Args:
            name: Alternative name to load
        """
        worker = get_current_worker()
        
        try:
            group = self.service.get_details(name)
            display_result = self.service.get_display(name)
            raw_output = display_result.stdout if display_result.success else display_result.message
            
            if not worker.is_cancelled:
                self.call_from_thread(self._on_details_loaded, group, raw_output)
        except Exception as e:
            if not worker.is_cancelled:
                self.call_from_thread(
                    self._show_status,
                    f"Failed to load details: {e}",
                    True
                )
    
    def _on_details_loaded(
        self,
        group: AlternativeGroup | None,
        raw_output: str
    ) -> None:
        """Handle details loaded.
        
        Args:
            group: Loaded alternative group
            raw_output: Raw display output
        """
        self.current_group = group
        
        # Update detail panel
        detail_panel = self.query_one("#detail-panel", AlternativeDetailPanel)
        detail_panel.update_details(group)
        
        # Update raw output (escape to prevent markup injection)
        raw_panel = self.query_one("#raw-output", Static)
        raw_panel.update(escape_markup(raw_output))
    
    # ========================================================================
    # Event Handlers - Using @on decorator with CSS selectors (Best Practice)
    # ========================================================================
    
    @on(ListView.Highlighted, "#alternatives-list")
    def on_alternative_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle highlighting (cursor movement) of an alternative."""
        if event.item:
            # Get original name from data attribute
            name = getattr(event.item, "data", None)
            if name:
                self.current_selection = name
                self._load_alternative_details(name)
    
    @on(Input.Changed, "#search-input")
    def on_search_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        # Skip if we're currently loading data to avoid race conditions
        if self._is_loading:
            return
        
        # Verify the event value matches the current input value
        # This guards against stale events that were queued before a refresh
        # but processed after the refresh cleared the input
        search_input = self.query_one("#search-input", Input)
        if event.value != search_input.value:
            return
        
        query = event.value.lower()
        
        if query:
            self.filtered_alternatives = [
                alt for alt in self.alternatives
                if query in alt.lower()
            ]
        else:
            self.filtered_alternatives = self.alternatives
        
        self._refresh_list_view()
        self._update_stats()
    
    # Individual button handlers using @on with CSS selector (Best Practice)
    @on(Button.Pressed, "#btn-set")
    def on_btn_set_pressed(self) -> None:
        """Handle Set button press."""
        self.action_set_alternative()
    
    @on(Button.Pressed, "#btn-auto")
    def on_btn_auto_pressed(self) -> None:
        """Handle Auto button press."""
        self.action_set_auto()
    
    @on(Button.Pressed, "#btn-install")
    def on_btn_install_pressed(self) -> None:
        """Handle Install button press."""
        self.action_install()
    
    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete_pressed(self) -> None:
        """Handle Delete button press."""
        self.action_delete()
    
    # ========================================================================
    # Actions
    # ========================================================================
    
    def action_refresh(self) -> None:
        """Refresh the alternatives list."""
        # Set loading flag BEFORE clearing search to prevent race conditions
        self._is_loading = True
        
        # Clear search input using prevent() to avoid triggering Input.Changed event
        # This is the Textual best practice for programmatic value changes
        search_input = self.query_one("#search-input", Input)
        with self.prevent(Input.Changed):
            search_input.value = ""
        
        # Clear current selection state
        self.current_selection = None
        self.current_group = None
        
        # Clear detail panel
        detail_panel = self.query_one("#detail-panel", AlternativeDetailPanel)
        detail_panel.update_details(None)
        
        # Clear cache and reload
        self.service.clear_cache()
        self.load_alternatives()
        self._show_status("Refreshing...")
    
    def action_search(self) -> None:
        """Focus the search input."""
        self.query_one("#search-input", Input).focus()
    
    def action_clear_search(self) -> None:
        """Clear the search input and reset filter."""
        search_input = self.query_one("#search-input", Input)
        if search_input.value:
            search_input.value = ""
            self.filtered_alternatives = self.alternatives
            self._refresh_list_view()
            self._update_stats()
        elif self.screen.focused == search_input:
            # If search is already empty and focused, blur it
            self.query_one("#alternatives-list", ListView).focus()
    
    def action_goto_first(self) -> None:
        """Jump to the first item in the list."""
        list_view = self.query_one("#alternatives-list", ListView)
        if list_view.children:
            list_view.index = 0
            list_view.focus()
    
    def action_goto_last(self) -> None:
        """Jump to the last item in the list."""
        list_view = self.query_one("#alternatives-list", ListView)
        if list_view.children:
            list_view.index = len(list_view.children) - 1
            list_view.focus()
    
    def action_select_current(self) -> None:
        """Trigger set_alternative for the current selection."""
        if self.current_group and self.current_group.has_alternatives:
            self.action_set_alternative()
    
    def action_focus_next_panel(self) -> None:
        """Toggle focus between list and detail panels."""
        list_view = self.query_one("#alternatives-list", ListView)
        if self.screen.focused == list_view or isinstance(self.screen.focused, Input):
            # Move to detail panel
            self.query_one("#detail-panel", AlternativeDetailPanel).focus()
        else:
            # Move back to list
            list_view.focus()
    
    def action_set_alternative(self) -> None:
        """Set a specific alternative."""
        if not self.current_group:
            self._show_status("No alternative selected - select one from the list first", is_error=True)
            return
        
        if not self.current_group.has_alternatives:
            self._show_status("No alternatives available for this group", is_error=True)
            return
        
        # Capture current group to avoid stale reference in callback
        group = self.current_group
        current_path = group.current
        
        # Show selection dialog with callback
        def on_select(result: str | None) -> None:
            if result:
                # Check if already set to this value
                if result == current_path:
                    self._show_status(f"Already set to {result}", is_error=False)
                    return
                
                cmd_result = self.service.set_alternative(group.name, result)
                self._show_status(cmd_result.message, is_error=not cmd_result.success)
                
                if cmd_result.success:
                    # Refresh list which will restore highlight and trigger detail reload
                    self.load_alternatives()
            else:
                # User cancelled
                self._show_status("Selection cancelled")
        
        self.push_screen(
            SelectAlternativeDialog(
                f"Select Alternative for {group.name}",
                group
            ),
            on_select
        )
    
    def action_set_auto(self) -> None:
        """Set alternative to auto mode."""
        if not self.current_group:
            self._show_status("No alternative selected - select one from the list first", is_error=True)
            return
        
        # Capture current group to avoid stale reference in callback
        group = self.current_group
        
        # Check if already in auto mode
        if group.is_auto():
            self._show_status(f"'{group.name}' is already in auto mode", is_error=False)
            return
        
        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                result = self.service.set_auto(group.name)
                self._show_status(result.message, is_error=not result.success)
                
                if result.success:
                    # Refresh list which will restore highlight and trigger detail reload
                    self.load_alternatives()
            else:
                self._show_status("Auto mode cancelled")
        
        self.push_screen(
            ConfirmDialog(
                "Set Auto Mode",
                f"Set '{group.name}' to automatic mode?"
            ),
            on_confirm
        )
    
    def action_install(self) -> None:
        """Install a new alternative."""
        # Pre-fill from current selection if available
        name = self.current_group.name if self.current_group else ""
        link = self.current_group.link if self.current_group else ""
        
        def on_install(result: dict | None) -> None:
            if result:
                try:
                    request = InstallRequest(
                        name=result["name"],
                        link=result["link"],
                        path=result["path"],
                        priority=result["priority"],
                        slaves=result.get("slaves", [])
                    )
                    cmd_result = self.service.install(request)
                    self._show_status(
                        cmd_result.message,
                        is_error=not cmd_result.success
                    )
                    
                    if cmd_result.success:
                        self.load_alternatives()
                except ValueError as e:
                    self._show_status(str(e), is_error=True)
            else:
                self._show_status("Installation cancelled")
        
        self.push_screen(
            InstallDialog(name=name, link=link),
            on_install
        )
    
    def action_delete(self) -> None:
        """Delete an alternative."""
        if not self.current_group:
            self._show_status("No alternative selected - select one from the list first", is_error=True)
            return
        
        # Check if there are alternatives to delete
        if not self.current_group.has_alternatives:
            self._show_status("No alternatives to delete in this group", is_error=True)
            return
        
        group = self.current_group  # Capture for closures
        
        def on_confirm_delete(confirmed: bool) -> None:
            if confirmed:
                cmd_result = self.service.remove(
                    group.name,
                    self._pending_delete_path
                )
                self._show_status(
                    cmd_result.message,
                    is_error=not cmd_result.success
                )
                
                if cmd_result.success:
                    # Refresh list which will restore highlight and trigger detail reload
                    self.load_alternatives()
            else:
                self._show_status("Delete cancelled")
        
        def on_select_delete(result: str | None) -> None:
            if result:
                self._pending_delete_path = result
                self.push_screen(
                    ConfirmDialog(
                        "Confirm Delete",
                        f"Remove '{result}' from '{group.name}'?",
                        destructive=True
                    ),
                    on_confirm_delete
                )
            else:
                self._show_status("Delete cancelled")
        
        # Select which alternative to delete
        self.push_screen(
            SelectAlternativeDialog(
                f"Select Alternative to Delete from {group.name}",
                group
            ),
            on_select_delete
        )
    
    def action_help(self) -> None:
        """Show help dialog."""
        self.push_screen(HelpDialog())
    
    # ========================================================================
    # Status Updates
    # ========================================================================
    
    def _show_status(self, message: str, is_error: bool = False) -> None:
        """Show a status message.
        
        Args:
            message: Message to show
            is_error: Whether this is an error message
        """
        status_bar = self.query_one("#status-bar", StatusWidget)
        status_bar.show_message(message, is_error)


# ============================================================================
# Entry Point
# ============================================================================

def _reset_terminal() -> None:
    """Reset terminal to a sane state.
    
    This is called on exit to ensure the terminal is usable even if
    the application crashed or was interrupted.
    """
    import sys
    import os
    
    # Only reset if we're connected to a real terminal
    if not sys.stdout.isatty():
        return
    
    try:
        # Use stty to reset terminal to sane defaults
        # This handles most cases of corrupted terminal state
        os.system("stty sane 2>/dev/null")
        
        # Show cursor (in case it was hidden)
        sys.stdout.write("\033[?25h")
        
        # Reset character attributes
        sys.stdout.write("\033[0m")
        
        # Clear any alternate screen buffer and switch back to main screen
        sys.stdout.write("\033[?1049l")
        
        sys.stdout.flush()
    except Exception:
        # Silently ignore errors during cleanup
        pass


def main() -> None:
    """Entry point for the TUI application."""
    import atexit
    import signal
    
    # Register terminal reset on normal exit
    atexit.register(_reset_terminal)
    
    # Handle signals that might terminate the process
    def signal_handler(signum: int, frame: object) -> None:
        _reset_terminal()
        raise SystemExit(128 + signum)
    
    # Register signal handlers for common termination signals
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, signal_handler)
        except (OSError, ValueError):
            # Signal not available on this platform
            pass
    
    try:
        app = UpdateAlternativesTUI()
        app.run()
    except Exception:
        # Ensure terminal is reset even on unhandled exceptions
        _reset_terminal()
        raise
    finally:
        # Final cleanup
        _reset_terminal()


if __name__ == "__main__":
    main()
