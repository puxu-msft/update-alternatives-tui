"""CSS styles for the main TUI application.

This module contains all CSS styles used by the UpdateAlternativesTUI
application, separated from the main app logic for better maintainability.
"""

# ============================================================================
# Application CSS
# ============================================================================

APP_CSS = """
Screen {
    background: $surface;
}

#main-container {
    width: 100%;
    height: 1fr;
}

#left-panel {
    width: 35%;
    min-width: 25;
    height: 100%;
    border: solid $primary;
    padding: 0 1;
}

#right-panel {
    width: 65%;
    min-width: 40;
    height: 100%;
    border: solid $secondary;
    padding: 1;
}

#list-header {
    height: 1;
    padding: 0 1;
    text-style: bold;
    color: $primary;
}

#list-stats {
    height: 1;
    padding: 0 1;
    text-align: right;
}

#search-container {
    height: 3;
    padding: 0 1;
    margin: 0;
}

#search-input {
    width: 100%;
}

#alternatives-list {
    height: 1fr;
}

#detail-panel {
    height: 1fr;
    overflow-y: auto;
}

#raw-output {
    padding: 1;
}

#status-bar {
    height: 1;
    width: 100%;
    background: $surface-darken-1;
    padding: 0 1;
}

.list-item {
    padding: 0 1;
}

.list-item:hover {
    background: $primary-darken-1;
}

.list-item.-selected {
    background: $primary;
}

/* Note: Dialog styles are in widgets/styles.py */

ModalScreen {
    align: center middle;
}

#action-buttons {
    height: auto;
    min-height: 3;
    padding: 0;
    align: center middle;
}

#action-buttons Button {
    margin: 0 1;
    min-width: 8;
}

DataTable {
    height: 1fr;
}

TabPane {
    padding: 0;
}

/* Loading indicator */
.loading {
    color: $text-muted;
    text-style: italic;
}
"""
