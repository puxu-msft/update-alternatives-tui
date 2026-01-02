"""Dialog widgets for update-alternatives TUI.

This module provides various dialog widgets including
ConfirmDialog, InputDialog, InstallDialog, SelectAlternativeDialog, and HelpDialog.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static
from rich.text import Text

from ..models import AlternativeGroup
from ..utils import escape_markup, sanitize_widget_id
from .messages import StatusIndicator
from .styles import DIALOG_CSS, HELP_DIALOG_CSS, INPUT_DIALOG_CSS, SELECT_DIALOG_CSS

if TYPE_CHECKING:
    from collections.abc import Callable


class ConfirmDialog(ModalScreen[bool]):
    """A confirmation dialog.
    
    Shows a yes/no dialog and returns True if confirmed.
    
    Example:
        def on_confirm(result: bool) -> None:
            if result:
                # do delete
        
        self.push_screen(ConfirmDialog("Delete?", "Are you sure?"), on_confirm)
    """
    
    DEFAULT_CSS = DIALOG_CSS
    
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(
        self,
        title: str,
        message: str,
        yes_label: str = "Yes (Y)",
        no_label: str = "No (N)",
        destructive: bool = False,
    ) -> None:
        """Initialize confirm dialog.
        
        Args:
            title: Dialog title
            message: Confirmation message
            yes_label: Label for yes button
            no_label: Label for no button
            destructive: If True, yes button is styled as error
        """
        super().__init__()
        self.title_text = title
        self.message_text = message
        self.yes_label = yes_label
        self.no_label = no_label
        self.destructive = destructive
    
    def compose(self) -> ComposeResult:
        with Container(classes="dialog-container"):
            # Escape dynamic text to prevent Rich markup injection
            yield Static(escape_markup(self.title_text), classes="dialog-title")
            yield Static(escape_markup(self.message_text), classes="dialog-message")
            with Horizontal(classes="dialog-buttons"):
                yield Button(
                    self.yes_label,
                    variant="error" if self.destructive else "primary",
                    id="yes"
                )
                yield Button(self.no_label, variant="default", id="no")
    
    @on(Button.Pressed, "#yes")
    def on_yes(self) -> None:
        """Handle yes button."""
        self.dismiss(True)
    
    @on(Button.Pressed, "#no")
    def on_no(self) -> None:
        """Handle no button."""
        self.dismiss(False)
    
    def action_confirm(self) -> None:
        """Handle y key."""
        self.dismiss(True)
    
    def action_cancel(self) -> None:
        """Handle n/escape key."""
        self.dismiss(False)


class InputDialog(ModalScreen[str | None]):
    """A dialog for text input.
    
    Shows an input field and returns the entered text.
    
    Example:
        def on_input(value: str | None) -> None:
            if value:
                # use value
        
        self.push_screen(InputDialog("Enter Name", "Name:"), on_input)
    """
    
    DEFAULT_CSS = DIALOG_CSS + INPUT_DIALOG_CSS
    
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(
        self,
        title: str,
        label: str,
        default: str = "",
        placeholder: str = "",
        validator: Callable[[str], str | None] | None = None,
    ) -> None:
        """Initialize input dialog.
        
        Args:
            title: Dialog title
            label: Input label
            default: Default value
            placeholder: Input placeholder
            validator: Optional validation function
        """
        super().__init__()
        self.title_text = title
        self.label_text = label
        self.default_value = default
        self.placeholder_text = placeholder
        self.validator = validator
    
    def compose(self) -> ComposeResult:
        with Container(classes="dialog-container"):
            # Escape dynamic text to prevent Rich markup injection
            yield Static(escape_markup(self.title_text), classes="dialog-title")
            with Vertical(classes="input-container"):
                yield Label(escape_markup(self.label_text))
                yield Input(
                    value=self.default_value,
                    placeholder=self.placeholder_text,
                    id="dialog-input"
                )
            with Horizontal(classes="dialog-buttons"):
                yield Button("OK", variant="primary", id="ok")
                yield Button("Cancel", variant="default", id="cancel")
    
    def on_mount(self) -> None:
        """Focus input on mount."""
        self.query_one("#dialog-input", Input).focus()
    
    @on(Button.Pressed, "#ok")
    def on_ok(self) -> None:
        """Handle OK button."""
        self._submit()
    
    @on(Button.Pressed, "#cancel")
    def on_cancel_button(self) -> None:
        """Handle cancel button."""
        self.dismiss(None)
    
    @on(Input.Submitted)
    def on_input_submitted(self) -> None:
        """Handle enter in input."""
        self._submit()
    
    def _submit(self) -> None:
        """Validate and submit input."""
        value = self.query_one("#dialog-input", Input).value.strip()
        
        if self.validator:
            error = self.validator(value)
            if error:
                self.notify(error, severity="error")
                return
        
        self.dismiss(value if value else None)
    
    def action_cancel(self) -> None:
        """Handle escape key."""
        self.dismiss(None)


class InstallDialog(ModalScreen[dict | None]):
    """Dialog for installing a new alternative.
    
    Collects name, link, path, and priority for a new alternative.
    
    Example:
        def on_install(result: dict | None) -> None:
            if result:
                request = InstallRequest(**result)
        
        self.push_screen(InstallDialog(name="editor", link="/usr/bin/editor"), on_install)
    """
    
    DEFAULT_CSS = DIALOG_CSS + INPUT_DIALOG_CSS
    
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+enter", "submit", "Install", show=False),
    ]
    
    def __init__(self, name: str = "", link: str = "") -> None:
        """Initialize install dialog.
        
        Args:
            name: Pre-filled alternative name
            link: Pre-filled link path
        """
        super().__init__()
        self.alt_name = name
        self.alt_link = link
    
    def compose(self) -> ComposeResult:
        with Container(classes="dialog-container"):
            yield Static("Install New Alternative", classes="dialog-title")
            yield Static(
                "[dim]Provide details for the new alternative entry[/dim]",
                classes="dialog-subtitle"
            )
            with Vertical(classes="input-container"):
                with Horizontal(classes="input-row"):
                    yield Label("Name:", classes="input-label")
                    yield Input(
                        value=self.alt_name,
                        id="name-input",
                        placeholder="e.g., python, editor"
                    )
                with Horizontal(classes="input-row"):
                    yield Label("Link:", classes="input-label")
                    yield Input(
                        value=self.alt_link,
                        id="link-input",
                        placeholder="symlink path, e.g., /usr/bin/python"
                    )
                with Horizontal(classes="input-row"):
                    yield Label("Path:", classes="input-label")
                    yield Input(
                        id="path-input",
                        placeholder="target binary, e.g., /usr/bin/python3.11"
                    )
                with Horizontal(classes="input-row"):
                    yield Label("Priority:", classes="input-label")
                    yield Input(
                        value="50",
                        id="priority-input",
                        placeholder="integer (higher = preferred in auto)"
                    )
                yield Static(
                    "[dim]Tip: Higher priority alternatives are selected in auto mode. "
                    "Use negative values for low-priority fallbacks.[/dim]",
                    id="install-tip"
                )
            with Horizontal(classes="dialog-buttons"):
                yield Button("Install", variant="success", id="install")
                yield Button("Cancel", variant="default", id="cancel")
    
    def on_mount(self) -> None:
        """Focus appropriate input on mount."""
        if not self.alt_name:
            self.query_one("#name-input", Input).focus()
        else:
            self.query_one("#path-input", Input).focus()
    
    @on(Button.Pressed, "#install")
    def on_install(self) -> None:
        """Handle install button."""
        self._submit()
    
    @on(Button.Pressed, "#cancel")
    def on_cancel_button(self) -> None:
        """Handle cancel button."""
        self.dismiss(None)
    
    def action_submit(self) -> None:
        """Handle Ctrl+Enter shortcut."""
        self._submit()
    
    def _submit(self) -> None:
        """Validate and submit form."""
        name = self.query_one("#name-input", Input).value.strip()
        link = self.query_one("#link-input", Input).value.strip()
        path = self.query_one("#path-input", Input).value.strip()
        priority_str = self.query_one("#priority-input", Input).value.strip()
        
        # Validate required fields with helpful messages
        if not name:
            self.notify("Name is required (e.g., 'python', 'editor')", severity="error")
            self.query_one("#name-input", Input).focus()
            return
        if not link:
            self.notify("Link path is required (the symlink location)", severity="error")
            self.query_one("#link-input", Input).focus()
            return
        if not path:
            self.notify("Target path is required (the actual binary)", severity="error")
            self.query_one("#path-input", Input).focus()
            return
        if not priority_str:
            self.notify("Priority is required (an integer value)", severity="error")
            self.query_one("#priority-input", Input).focus()
            return
        
        # Validate paths are absolute
        if not link.startswith("/"):
            self.notify("Link must be an absolute path (start with /)", severity="error")
            self.query_one("#link-input", Input).focus()
            return
        if not path.startswith("/"):
            self.notify("Path must be an absolute path (start with /)", severity="error")
            self.query_one("#path-input", Input).focus()
            return
        
        # Validate priority (negative values are allowed, e.g., /bin/ed uses -100)
        try:
            priority = int(priority_str)
        except ValueError:
            self.notify("Priority must be an integer (e.g., 50, 100, -10)", severity="error")
            self.query_one("#priority-input", Input).focus()
            return
        
        self.dismiss({
            "name": name,
            "link": link,
            "path": path,
            "priority": priority
        })
    
    def action_cancel(self) -> None:
        """Handle escape key."""
        self.dismiss(None)

class HelpDialog(ModalScreen[None]):
    """Dialog showing keyboard shortcuts and help information.
    
    Example:
        self.push_screen(HelpDialog())
    """
    
    DEFAULT_CSS = DIALOG_CSS + HELP_DIALOG_CSS
    
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
    ]
    
    HELP_TEXT = """
[bold cyan]━━━ Update-Alternatives TUI Help ━━━[/bold cyan]

[bold]Main Commands:[/bold]
  [yellow]s[/yellow]         Set alternative (select from list)
  [yellow]a[/yellow]         Set to auto mode (highest priority)
  [yellow]i[/yellow]         Install new alternative
  [yellow]d[/yellow]         Delete an alternative

[bold]Navigation:[/bold]
  [yellow]↑↓[/yellow] / [yellow]jk[/yellow]   Navigate list
  [yellow]g[/yellow]         Jump to first item
  [yellow]G[/yellow]         Jump to last item
  [yellow]Tab[/yellow]       Switch between panels
  [yellow]Enter[/yellow]     Select/confirm
  [yellow]/[/yellow]         Focus search input
  [yellow]Esc[/yellow]       Clear search / Cancel

[bold]General:[/bold]
  [yellow]r[/yellow]         Refresh alternatives list
  [yellow]?[/yellow]         Show this help
  [yellow]q[/yellow]         Quit application

[bold]Status Indicators:[/bold]
  [green]A[/green]  Auto mode   [yellow]M[/yellow]  Manual mode
  [green]●[/green]  Current     [cyan]★[/cyan]  Best (highest priority)

[bold]Selection Dialog:[/bold]
  [yellow]1-9[/yellow]       Quick select by number
  [yellow]↑↓[/yellow] / [yellow]jk[/yellow]   Navigate options
  [yellow]Enter[/yellow]     Confirm selection
  [yellow]Esc[/yellow]       Cancel

[bold]Note:[/bold]
  Operations that modify alternatives require [bold]sudo[/bold] privileges.
  Run the application with: [cyan]sudo update-alternatives-tui[/cyan]
"""
    
    def compose(self) -> ComposeResult:
        with Container(classes="dialog-container"):
            yield Static(self.HELP_TEXT, classes="help-content")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Close", variant="primary", id="close")
    
    @on(Button.Pressed, "#close")
    def on_close(self) -> None:
        """Handle close button."""
        self.dismiss(None)
    
    def action_close(self) -> None:
        """Handle escape/q key."""
        self.dismiss(None)


class SelectAlternativeDialog(ModalScreen[str | None]):
    """Dialog for selecting an alternative from a list.
    
    Shows all alternatives in a group and allows selecting one.
    Supports keyboard navigation with up/down arrows and number keys.
    
    Example:
        def on_select(selected: str | None) -> None:
            if selected:
                # use selected path
        
        self.push_screen(SelectAlternativeDialog("Select Editor", group), on_select)
    """
    
    DEFAULT_CSS = DIALOG_CSS + SELECT_DIALOG_CSS
    
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("up,k", "focus_previous", "Previous", show=False),
        Binding("down,j", "focus_next", "Next", show=False),
        Binding("enter", "select", "Select", show=False),
        Binding("1", "select_1", "1", show=False),
        Binding("2", "select_2", "2", show=False),
        Binding("3", "select_3", "3", show=False),
        Binding("4", "select_4", "4", show=False),
        Binding("5", "select_5", "5", show=False),
        Binding("6", "select_6", "6", show=False),
        Binding("7", "select_7", "7", show=False),
        Binding("8", "select_8", "8", show=False),
        Binding("9", "select_9", "9", show=False),
    ]
    
    def __init__(self, title: str, group: AlternativeGroup) -> None:
        """Initialize select dialog.
        
        Args:
            title: Dialog title
            group: Alternative group to select from
        """
        super().__init__()
        self.title_text = title
        self.group = group
        self._option_paths: list[str] = []  # Store paths in order
    
    def compose(self) -> ComposeResult:
        with Container(classes="dialog-container select-dialog"):
            # Escape dynamic text to prevent Rich markup injection
            yield Static(escape_markup(self.title_text), classes="dialog-title")
            yield Static(
                f"[dim]Current: {escape_markup(self.group.current)}[/dim]",
                classes="dialog-subtitle"
            )
            with Vertical(classes="options-container"):
                for idx, alt in enumerate(self.group.get_alternatives_sorted_by_priority(), 1):
                    is_current = alt.path == self.group.current
                    is_best = alt.path == self.group.best
                    self._option_paths.append(alt.path)
                    
                    # Build label with indicators
                    indicator = ""
                    if is_current:
                        indicator = f"[green]{StatusIndicator.CURRENT}[/green] "
                    elif is_best:
                        indicator = f"[cyan]{StatusIndicator.BEST}[/cyan] "
                    else:
                        indicator = "  "  # Align spacing
                    
                    # Format: number + indicator + path + priority
                    num_hint = f"[dim]{idx}.[/dim] " if idx <= 9 else "   "
                    label_text = f"{num_hint}{indicator}{escape_markup(alt.path)} [dim](pri:{alt.priority})[/dim]"
                    
                    # Create button
                    button = Button(
                        variant="primary" if is_current else "default",
                        id=sanitize_widget_id(alt.path, prefix="opt"),
                        classes="option-button"
                    )
                    button.label = Text.from_markup(label_text)
                    button.data = alt.path  # Store original path
                    if is_current:
                        button.add_class("current")
                    yield button
            
            with Horizontal(classes="dialog-buttons"):
                yield Button("Cancel (Esc)", variant="default", id="cancel")
    
    def on_mount(self) -> None:
        """Focus first option button on mount."""
        buttons = self.query(".option-button")
        if buttons:
            buttons.first().focus()
    
    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id and event.button.id.startswith("opt-"):
            path = getattr(event.button, "data", None)
            if path:
                self.dismiss(path)
    
    def action_cancel(self) -> None:
        """Handle escape key."""
        self.dismiss(None)
    
    def action_focus_previous(self) -> None:
        """Move focus to previous option."""
        self.screen.focus_previous()
    
    def action_focus_next(self) -> None:
        """Move focus to next option."""
        self.screen.focus_next()
    
    def action_select(self) -> None:
        """Select the currently focused option."""
        focused = self.focused
        if focused and hasattr(focused, "data"):
            path = getattr(focused, "data", None)
            if path:
                self.dismiss(path)
    
    def _select_by_index(self, index: int) -> None:
        """Select option by index (1-based)."""
        if 0 < index <= len(self._option_paths):
            self.dismiss(self._option_paths[index - 1])
    
    def action_select_1(self) -> None:
        self._select_by_index(1)
    
    def action_select_2(self) -> None:
        self._select_by_index(2)
    
    def action_select_3(self) -> None:
        self._select_by_index(3)
    
    def action_select_4(self) -> None:
        self._select_by_index(4)
    
    def action_select_5(self) -> None:
        self._select_by_index(5)
    
    def action_select_6(self) -> None:
        self._select_by_index(6)
    
    def action_select_7(self) -> None:
        self._select_by_index(7)
    
    def action_select_8(self) -> None:
        self._select_by_index(8)
    
    def action_select_9(self) -> None:
        self._select_by_index(9)
