"""Base widgets for update-alternatives TUI.

This module provides foundational widgets like StatusWidget
and AlternativeDetailPanel.
"""

from __future__ import annotations

from textual.widgets import Static

from ..constants import StatusColor, StatusIndicator
from ..models import AlternativeGroup
from ..utils import escape_markup
from .styles import DETAIL_PANEL_CSS, STATUS_WIDGET_CSS


class StatusWidget(Static):
    """Widget to display status messages.
    
    This widget provides a status bar at the bottom of the screen
    for showing success/error messages to the user.
    
    Example:
        status = StatusWidget()
        status.show_message("Operation completed", is_error=False)
    """
    
    DEFAULT_CSS = STATUS_WIDGET_CSS
    
    def __init__(
        self,
        *args,
        auto_clear: float | None = 5.0,
        **kwargs
    ) -> None:
        """Initialize status widget.
        
        Args:
            auto_clear: Seconds after which to clear message (None to disable)
        """
        super().__init__(*args, **kwargs)
        self.auto_clear = auto_clear
        self._clear_timer: object | None = None
    
    def show_message(self, message: str, is_error: bool = False) -> None:
        """Display a status message.
        
        Args:
            message: Message to display
            is_error: Whether this is an error message
        """
        # Cancel any pending clear
        if self._clear_timer:
            self._clear_timer.stop()
            self._clear_timer = None
        
        # Update styling
        self.remove_class("error", "success")
        self.add_class("error" if is_error else "success")
        
        # Format message (escape to prevent markup injection)
        color = StatusColor.ERROR if is_error else StatusColor.SUCCESS
        indicator = StatusIndicator.CROSS if is_error else StatusIndicator.CHECK
        safe_message = escape_markup(message)
        self.update(f"[{color}]{indicator} {safe_message}[/{color}]")
        
        # Schedule auto-clear
        if self.auto_clear:
            self._clear_timer = self.set_timer(self.auto_clear, self.clear)
    
    def show_info(self, message: str) -> None:
        """Display an informational message.
        
        Args:
            message: Message to display
        """
        self.remove_class("error", "success")
        safe_message = escape_markup(message)
        self.update(f"[{StatusColor.INFO}]{safe_message}[/{StatusColor.INFO}]")
    
    def clear(self) -> None:
        """Clear the status message."""
        self.remove_class("error", "success")
        self.update("")


class AlternativeDetailPanel(Static):
    """Panel showing details of selected alternative.
    
    Displays comprehensive information about an alternative group,
    including alternatives and their priorities.
    
    Example:
        panel = AlternativeDetailPanel()
        panel.update_details(group)
    """
    
    DEFAULT_CSS = DETAIL_PANEL_CSS
    
    def __init__(self, *args, **kwargs) -> None:
        """Initialize detail panel."""
        super().__init__(*args, **kwargs)
        self.current_group: AlternativeGroup | None = None
    
    def update_details(self, group: AlternativeGroup | None) -> None:
        """Update panel with alternative group details.
        
        Args:
            group: Group to display (or None to clear)
        """
        self.current_group = group
        if not group:
            self.update(self._format_empty_state())
            return
        
        self.update(self._format_group(group))
    
    def _format_empty_state(self) -> str:
        """Format the empty state message with helpful tips."""
        lines = [
            f"[{StatusColor.MUTED}]Select an alternative from the list to view details[/{StatusColor.MUTED}]",
            "",
            f"[{StatusColor.INFO}]Quick Tips:[/{StatusColor.INFO}]",
            f"  [{StatusColor.MUTED}]• Use [bold]/[/bold] to search alternatives[/{StatusColor.MUTED}]",
            f"  [{StatusColor.MUTED}]• Press [bold]s[/bold] to set a specific alternative[/{StatusColor.MUTED}]",
            f"  [{StatusColor.MUTED}]• Press [bold]a[/bold] to switch to auto mode[/{StatusColor.MUTED}]",
            f"  [{StatusColor.MUTED}]• Press [bold]?[/bold] for help[/{StatusColor.MUTED}]",
        ]
        return "\n".join(lines)
    
    def _format_group(self, group: AlternativeGroup) -> str:
        """Format group details for display.
        
        Args:
            group: Group to format
            
        Returns:
            Formatted Rich markup string
        """
        lines: list[str] = []
        
        # Header with name prominently displayed
        lines.append(f"[bold cyan]━━━ {escape_markup(group.name)} ━━━[/bold cyan]")
        lines.append("")
        
        # Basic info in a structured layout
        lines.append(f"[bold]Link:[/bold]    {escape_markup(group.link)}")
        
        # Status with color and explanation
        if group.is_auto():
            status_display = f"[{StatusColor.AUTO_MODE}]auto[/{StatusColor.AUTO_MODE}] (highest priority is selected)"
        else:
            status_display = f"[{StatusColor.MANUAL_MODE}]manual[/{StatusColor.MANUAL_MODE}] (administrator selected)"
        lines.append(f"[bold]Status:[/bold]  {status_display}")
        
        lines.append(f"[bold]Current:[/bold] {escape_markup(group.current)}")
        lines.append(f"[bold]Best:[/bold]    {escape_markup(group.best)}")
        
        # Alternatives section with count
        alt_count = len(group.alternatives)
        lines.append("")
        lines.append(f"[bold]Alternatives ({alt_count}):[/bold]")
        lines.append("")
        
        for alt in group.get_alternatives_sorted_by_priority():
            is_current = alt.path == group.current
            is_best = alt.path == group.best
            
            # Build markers
            markers: list[str] = []
            if is_current:
                markers.append(f"[{StatusColor.SUCCESS}]{StatusIndicator.CURRENT}[/{StatusColor.SUCCESS}]")
            if is_best:
                markers.append(f"[{StatusColor.INFO}]{StatusIndicator.BEST}[/{StatusColor.INFO}]")
            marker_str = " ".join(markers) if markers else "  "
            
            # Format alternative line with index (escape path)
            escaped_path = escape_markup(alt.path)
            priority_color = StatusColor.SUCCESS if is_best else StatusColor.MUTED
            if is_current:
                lines.append(f"  {marker_str} [bold]{escaped_path}[/bold]")
                lines.append(f"       [{priority_color}]priority: {alt.priority}[/{priority_color}]")
            else:
                lines.append(f"  {marker_str} {escaped_path}")
                lines.append(f"       [{priority_color}]priority: {alt.priority}[/{priority_color}]")
            
            # Show slaves if any
            if alt.has_slaves():
                for slave_name, slave_path in alt.slaves.items():
                    lines.append(f"       {StatusIndicator.SLAVE} [{StatusColor.MUTED}]{escape_markup(slave_name)}: {escape_markup(slave_path)}[/{StatusColor.MUTED}]")
        
        # Slave links section
        if group.slave_links:
            lines.append("")
            lines.append(f"[bold]Slave Links ({len(group.slave_links)}):[/bold]")
            for slave_name, slave_link in group.slave_links.items():
                lines.append(f"  • {escape_markup(slave_name)} {StatusIndicator.ARROW} {escape_markup(slave_link)}")
        
        # Legend at the bottom
        lines.append("")
        lines.append(f"[{StatusColor.MUTED}]Legend: [{StatusColor.SUCCESS}]{StatusIndicator.CURRENT}[/{StatusColor.SUCCESS}]=current [{StatusColor.INFO}]{StatusIndicator.BEST}[/{StatusColor.INFO}]=best[/{StatusColor.MUTED}]")
        
        return "\n".join(lines)
    
    def get_current_group(self) -> AlternativeGroup | None:
        """Get the currently displayed group.
        
        Returns:
            Current AlternativeGroup or None
        """
        return self.current_group
