"""CSS styles for TUI widgets.

This module centralizes all CSS styles for widgets,
making them easier to maintain and modify.
"""

# ============================================================================
# Status Widget Styles
# ============================================================================

STATUS_WIDGET_CSS = """
StatusWidget {
    height: 1;
    width: 100%;
    background: $surface-darken-1;
    padding: 0 1;
}

StatusWidget.error {
    color: $error;
}

StatusWidget.success {
    color: $success;
}
"""

# ============================================================================
# Dialog Base Styles
# ============================================================================

DIALOG_CSS = """
.dialog-container {
    width: 60%;
    min-width: 40;
    max-width: 80;
    height: auto;
    max-height: 80%;
    border: thick $primary;
    background: $surface;
    padding: 1 1;
}

.dialog-title {
    text-align: center;
    padding: 0;
    text-style: bold;
    color: $primary;
}

.dialog-message {
    padding: 0 1;
    text-align: center;
}

.dialog-buttons {
    align: center middle;
    padding: 1 0 0 0;
    height: auto;
}

.dialog-buttons Button {
    margin: 0 1;
}
"""

# ============================================================================
# Input Dialog Styles
# ============================================================================

INPUT_DIALOG_CSS = """
.input-container {
    padding: 1;
}

.input-row {
    height: 3;
    margin: 1 0;
}

.input-label {
    width: 12;
    padding: 0 1;
}

.input-row Input {
    width: 1fr;
}

#install-tip {
    margin-top: 1;
    padding: 0 1;
}
"""

# ============================================================================
# Detail Panel Styles
# ============================================================================

DETAIL_PANEL_CSS = """
AlternativeDetailPanel {
    height: 1fr;
    overflow-y: auto;
    padding: 1;
}

.detail-header {
    text-style: bold;
    color: $primary;
    margin-bottom: 1;
}

.detail-row {
    margin-bottom: 0;
}

.detail-label {
    color: $text-muted;
    width: 12;
}

.detail-value {
    color: $text;
}

.alternatives-list {
    margin-top: 1;
}

.alternative-item {
    padding: 0 1;
}

.alternative-item.current {
    color: $success;
}

.slave-item {
    color: $text-muted;
    padding-left: 4;
}
"""

# ============================================================================
# Select Dialog Styles
# ============================================================================

SELECT_DIALOG_CSS = """
.select-dialog {
    width: 80%;
    min-width: 50;
    max-width: 100;
}

.dialog-subtitle {
    text-align: center;
    padding: 0;
    color: $text-muted;
}

.options-container {
    padding: 0;
    max-height: 60%;
    overflow-y: auto;
}

.option-button {
    width: 100%;
    height: auto;
    min-height: 1;
    margin: 0;
    padding: 0 1;
    content-align: left middle;
}

.option-button.current {
    background: $success 20%;
}
"""

# ============================================================================
# Help Dialog Styles
# ============================================================================

HELP_DIALOG_CSS = """
HelpDialog .dialog-container {
    width: 85%;
    min-width: 50;
    max-width: 90;
    max-height: 90%;
}

.help-content {
    padding: 1;
}

.help-section {
    margin-bottom: 1;
}

.help-section-title {
    text-style: bold;
    color: $primary;
}
"""
