"""Tests for utility functions.

This module tests the utility functions in utils.py,
particularly focusing on edge cases with special characters.
"""

from __future__ import annotations

import pytest

from update_alternatives_tui.utils import (
    escape_markup,
    safe_markup,
    sanitize_widget_id,
    truncate_text,
)


# ============================================================================
# sanitize_widget_id Tests
# ============================================================================

class TestSanitizeWidgetId:
    """Tests for sanitize_widget_id function."""
    
    def test_simple_string(self) -> None:
        """Test with simple alphanumeric string."""
        assert sanitize_widget_id("editor") == "editor"
        assert sanitize_widget_id("python3") == "python3"
    
    def test_periods_replaced(self) -> None:
        """Test that periods are replaced with underscores."""
        assert sanitize_widget_id("builtins.7.gz") == "builtins_7_gz"
        assert sanitize_widget_id("file.txt") == "file_txt"
    
    def test_slashes_replaced(self) -> None:
        """Test that slashes are replaced with underscores."""
        assert sanitize_widget_id("/usr/bin/vim") == "_usr_bin_vim"
        assert sanitize_widget_id("path/to/file") == "path_to_file"
    
    def test_with_prefix(self) -> None:
        """Test with prefix parameter."""
        assert sanitize_widget_id("editor", prefix="alt") == "alt-editor"
        assert sanitize_widget_id("builtins.7.gz", prefix="alt") == "alt-builtins_7_gz"
        assert sanitize_widget_id("/usr/bin/vim", prefix="opt") == "opt-_usr_bin_vim"
    
    def test_leading_digit_handled(self) -> None:
        """Test that leading digits are prefixed with underscore."""
        assert sanitize_widget_id("7zip") == "_7zip"
        assert sanitize_widget_id("123test") == "_123test"
    
    def test_special_characters_replaced(self) -> None:
        """Test various special characters are replaced."""
        # Brackets
        assert sanitize_widget_id("test[0]") == "test_0_"
        assert sanitize_widget_id("array[index]") == "array_index_"
        
        # Spaces and other chars
        assert sanitize_widget_id("hello world") == "hello_world"
        assert sanitize_widget_id("test@domain") == "test_domain"
        assert sanitize_widget_id("name=value") == "name_value"
    
    def test_rich_markup_characters(self) -> None:
        """Test that Rich markup characters are safely handled."""
        # These could cause MarkupError if used in Rich text
        assert sanitize_widget_id("[bold]text[/bold]") == "_bold_text__bold_"
        assert sanitize_widget_id("test[/]end") == "test___end"
    
    def test_empty_string(self) -> None:
        """Test with empty string."""
        assert sanitize_widget_id("") == ""
        assert sanitize_widget_id("", prefix="alt") == "alt-"
    
    def test_only_special_chars(self) -> None:
        """Test string with only special characters."""
        assert sanitize_widget_id("...") == "___"
        assert sanitize_widget_id("///") == "___"
    
    def test_hyphen_preserved(self) -> None:
        """Test that hyphens are preserved (valid in CSS IDs)."""
        assert sanitize_widget_id("my-name") == "my-name"
        assert sanitize_widget_id("test-123") == "test-123"
    
    def test_underscore_preserved(self) -> None:
        """Test that underscores are preserved."""
        assert sanitize_widget_id("my_name") == "my_name"
        assert sanitize_widget_id("test_123") == "test_123"


# ============================================================================
# escape_markup Tests
# ============================================================================

class TestEscapeMarkup:
    """Tests for escape_markup function (re-exported from rich.markup).
    
    Note: Rich only escapes brackets that look like valid markup tags.
    [0], [1], etc. are NOT escaped because they are not valid tag names.
    [bold], [/], [red], etc. ARE escaped because they could be markup.
    """
    
    def test_simple_string(self) -> None:
        """Test that simple strings pass through unchanged."""
        assert escape_markup("hello world") == "hello world"
        assert escape_markup("test123") == "test123"
    
    def test_valid_tags_escaped(self) -> None:
        """Test that valid-looking markup tags are escaped."""
        assert escape_markup("[bold]") == "\\[bold]"
        assert escape_markup("[/bold]") == "\\[/bold]"
        assert escape_markup("[red]text[/red]") == "\\[red]text\\[/red]"
    
    def test_numeric_brackets_not_escaped(self) -> None:
        """Test that numeric brackets are NOT escaped (not valid tags)."""
        # Rich doesn't escape [0], [1], etc. because they're not valid tags
        assert escape_markup("test[0]") == "test[0]"
        assert escape_markup("array[123]") == "array[123]"
    
    def test_auto_close_tag_escaped(self) -> None:
        """Test the specific case that caused the bug: [/] auto-close tag."""
        result = escape_markup("[/]")
        assert result == "\\[/]"
    
    def test_mixed_content(self) -> None:
        """Test strings with mixed content."""
        result = escape_markup("Error: tag '[/]' is invalid")
        assert "\\[/]" in result
    
    def test_real_world_error_message(self) -> None:
        """Test with real-world error message that caused the bug."""
        msg = "Failed to load details: auto closing tag ('[/]') has nothing to close"
        result = escape_markup(msg)
        assert "\\[/]" in result
    
    def test_nested_brackets(self) -> None:
        """Test nested brackets - only valid-looking tags escaped."""
        # [[nested]] -> [\[nested]] because [[ is not a valid tag start
        # but [nested] is
        result = escape_markup("[[nested]]")
        assert "\\[nested]" in result
    
    def test_empty_string(self) -> None:
        """Test empty string."""
        assert escape_markup("") == ""
    
    def test_backslash_handling(self) -> None:
        """Test backslash handling."""
        result = escape_markup("test\\nvalue")
        assert "test" in result and "value" in result


# ============================================================================
# safe_markup Tests
# ============================================================================

class TestSafeMarkup:
    """Tests for safe_markup function.
    
    Note: safe_markup uses escape_markup which only escapes valid-looking tags.
    """
    
    def test_simple_template(self) -> None:
        """Test simple template without special characters."""
        result = safe_markup("[bold]Name:[/bold] {name}", name="editor")
        assert result == "[bold]Name:[/bold] editor"
    
    def test_escapes_valid_tags_in_values(self) -> None:
        """Test that valid markup tags in values are escaped."""
        result = safe_markup("[bold]Name:[/bold] {name}", name="[red]test[/red]")
        assert "[bold]Name:[/bold]" in result
        assert "\\[red]" in result
    
    def test_escapes_rich_markup_in_values(self) -> None:
        """Test that Rich markup in values is escaped."""
        result = safe_markup("[red]{error}[/red]", error="[bold]injection[/bold]")
        assert "[red]" in result and "[/red]" in result
        assert "\\[bold]" in result
    
    def test_escapes_auto_close_tag(self) -> None:
        """Test the specific case that caused the original bug."""
        result = safe_markup("Error: {msg}", msg="tag '[/]' is invalid")
        assert "\\[/]" in result
    
    def test_multiple_placeholders(self) -> None:
        """Test with multiple placeholders."""
        result = safe_markup(
            "[cyan]{key}[/cyan]: {value}",
            key="name[bold]",  # [bold] is valid markup
            value="test[/]end"  # [/] is valid markup
        )
        assert "\\[bold]" in result
        assert "\\[/]" in result
    
    def test_preserves_markup_tags(self) -> None:
        """Test that markup tags in template are preserved."""
        result = safe_markup(
            "[bold cyan]Title[/bold cyan]: {title}",
            title="plain text"
        )
        assert "[bold cyan]" in result
        assert "[/bold cyan]" in result
        assert "plain text" in result
    
    def test_empty_value(self) -> None:
        """Test with empty value."""
        result = safe_markup("[info]{msg}[/info]", msg="")
        assert result == "[info][/info]"
    
    def test_real_world_alternative_display(self) -> None:
        """Test real-world scenario: displaying alternative info."""
        result = safe_markup(
            "[bold cyan]Name:[/bold cyan] {name}\n[bold cyan]Path:[/bold cyan] {path}",
            name="builtins.7.gz",
            path="/usr/share/man/man7/builtins.7.gz"
        )
        assert "builtins.7.gz" in result
        assert "/usr/share/man/man7/builtins.7.gz" in result


# ============================================================================
# truncate_text Tests
# ============================================================================

class TestTruncateText:
    """Tests for truncate_text function."""
    
    def test_short_string_unchanged(self) -> None:
        """Test that short strings are not modified."""
        assert truncate_text("hello", 10) == "hello"
        assert truncate_text("hi", 10) == "hi"
    
    def test_exact_length_unchanged(self) -> None:
        """Test string exactly at max length."""
        assert truncate_text("hello", 5) == "hello"
    
    def test_truncation_with_default_suffix(self) -> None:
        """Test truncation with default '...' suffix."""
        assert truncate_text("hello world", 8) == "hello..."
    
    def test_truncation_with_custom_suffix(self) -> None:
        """Test truncation with custom suffix."""
        assert truncate_text("hello world", 8, suffix="~") == "hello w~"
    
    def test_very_short_max_length(self) -> None:
        """Test with max_length shorter than suffix."""
        assert truncate_text("hello", 2) == ".."
        assert truncate_text("hello", 1) == "."
    
    def test_empty_suffix(self) -> None:
        """Test with empty suffix."""
        assert truncate_text("hello world", 5, suffix="") == "hello"
    
    def test_empty_string(self) -> None:
        """Test with empty string."""
        assert truncate_text("", 10) == ""
    
    def test_special_characters_preserved(self) -> None:
        """Test that special characters are preserved during truncation."""
        result = truncate_text("[bold]text[/bold]", 12)
        assert result.startswith("[bold]")


# ============================================================================
# Integration Tests - Real World Scenarios
# ============================================================================

class TestRealWorldScenarios:
    """Test real-world scenarios that could cause issues."""
    
    def test_alternative_name_with_version(self) -> None:
        """Test alternative names with version numbers and extensions."""
        names = [
            "builtins.7.gz",
            "python3.11",
            "gcc-12",
            "g++-12",
            "clang-format-15",
        ]
        for name in names:
            # Should produce valid widget ID
            widget_id = sanitize_widget_id(name, prefix="alt")
            assert widget_id.startswith("alt-")
            assert "." not in widget_id.split("-", 1)[1]  # No dots after prefix
            
            # Should be safe to display (no valid markup tags in these names)
            safe_name = escape_markup(name)
            assert safe_name  # Not empty
    
    def test_paths_as_content(self) -> None:
        """Test file paths that might be displayed."""
        paths = [
            "/usr/bin/vim",
            "/usr/lib/jvm/java-17-openjdk-amd64/bin/java",
            "/home/user/.local/bin/python",
            "/opt/program[1]/bin/run",  # Path with brackets (not valid tag)
        ]
        for path in paths:
            # Should produce valid widget ID
            widget_id = sanitize_widget_id(path, prefix="opt")
            assert widget_id.startswith("opt-")
            assert "/" not in widget_id
            
            # Should be safe to display
            safe_path = escape_markup(path)
            assert safe_path
    
    def test_error_messages_with_markup_tags(self) -> None:
        """Test error messages that contain valid markup-like content."""
        # These contain valid markup tags that should be escaped
        errors_with_valid_tags = [
            ("Parse error: unexpected '[/]' at line 5", "\\[/]"),
            ("Config error: section [default] missing", "\\[default]"),
            ("Invalid [bold] tag", "\\[bold]"),
        ]
        for error, expected_escaped in errors_with_valid_tags:
            safe_error = escape_markup(error)
            assert expected_escaped in safe_error
    
    def test_error_messages_with_numeric_brackets(self) -> None:
        """Test error messages with numeric brackets (not escaped)."""
        # [0], [1], etc. are NOT valid markup tags
        errors = [
            "Error in file[0]: syntax error",
            "Array index [123] out of bounds",
        ]
        for error in errors:
            safe_error = escape_markup(error)
            # Numeric brackets should remain unchanged
            assert safe_error == error
    
    def test_user_input_with_special_chars(self) -> None:
        """Test handling user input that might have special characters."""
        # Only valid markup tags get escaped
        test_cases = [
            ("test[1]", "test[1]"),  # [1] not a valid tag
            ("name=value", "name=value"),  # No brackets
            ("hello<world>", "hello<world>"),  # Angle brackets not escaped
            ("path/to/file.txt", "path/to/file.txt"),  # No markup
            ("[bold]injection[/bold]", "\\[bold]injection\\[/bold]"),  # Valid tags escaped
            ("[/]auto close", "\\[/]auto close"),  # [/] is valid
        ]
        for user_input, expected in test_cases:
            safe = escape_markup(user_input)
            assert safe == expected, f"Input {user_input!r}: expected {expected!r}, got {safe!r}"
