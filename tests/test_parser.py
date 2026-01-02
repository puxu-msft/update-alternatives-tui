"""Tests for update_alternatives_tui.parser module.

Tests cover:
- Parsing of --get-selections output
- Parsing of --query output  
- Parsing of --display output
- Error handling for malformed input
- Edge cases and boundary conditions
"""

from __future__ import annotations

import pytest

from update_alternatives_tui.parser import (
    OutputParser,
    parse_selections,
    parse_query,
    parse_display,
    extract_names,
    PATTERNS,
)
from update_alternatives_tui.models import AlternativeStatus


# ============================================================================
# Sample Data
# ============================================================================

SAMPLE_SELECTIONS_OUTPUT = """\
editor                         auto     /usr/bin/vim.basic
python                         manual   /usr/bin/python3
java                           auto     /usr/lib/jvm/java-17/bin/java
"""

SAMPLE_QUERY_OUTPUT = """\
Name: editor
Link: /usr/bin/editor
Slaves:
 editor.1.gz /usr/share/man/man1/editor.1.gz
 editor.da.1.gz /usr/share/man/da/man1/editor.1.gz
Status: auto
Best: /usr/bin/vim.basic
Value: /usr/bin/vim.basic

Alternative: /usr/bin/ed
Priority: 10
Slaves:
 editor.1.gz /usr/share/man/man1/ed.1.gz

Alternative: /usr/bin/nano
Priority: 40
Slaves:
 editor.1.gz /usr/share/man/man1/nano.1.gz

Alternative: /usr/bin/vim.basic
Priority: 30
Slaves:
 editor.1.gz /usr/share/man/man1/vim.1.gz
"""

SAMPLE_DISPLAY_OUTPUT = """\
editor - auto mode
  link best version is /usr/bin/vim.basic
  link currently points to /usr/bin/vim.basic
  link editor is /usr/bin/editor
  slave editor.1.gz is /usr/share/man/man1/editor.1.gz
/usr/bin/ed - priority 10
  slave editor.1.gz: /usr/share/man/man1/ed.1.gz
/usr/bin/nano - priority 40
  slave editor.1.gz: /usr/share/man/man1/nano.1.gz
"""


class TestCompiledPatterns:
    """Tests for compiled regex patterns."""

    def test_name_pattern(self) -> None:
        """Test Name field pattern."""
        match = PATTERNS.NAME.match("Name: editor")
        assert match is not None
        assert match.group(1) == "editor"

    def test_link_pattern(self) -> None:
        """Test Link field pattern."""
        match = PATTERNS.LINK.match("Link: /usr/bin/editor")
        assert match is not None
        assert match.group(1) == "/usr/bin/editor"

    def test_status_pattern(self) -> None:
        """Test Status field pattern."""
        match = PATTERNS.STATUS.match("Status: auto")
        assert match is not None
        assert match.group(1) == "auto"

    def test_selection_pattern(self) -> None:
        """Test selection line pattern."""
        match = PATTERNS.SELECTION.match("editor auto /usr/bin/vim")
        assert match is not None
        assert match.groups() == ("editor", "auto", "/usr/bin/vim")

    def test_alternative_pattern(self) -> None:
        """Test Alternative field pattern."""
        match = PATTERNS.ALTERNATIVE.match("Alternative: /usr/bin/vim")
        assert match is not None
        assert match.group(1) == "/usr/bin/vim"

    def test_priority_pattern(self) -> None:
        """Test Priority field pattern."""
        match = PATTERNS.PRIORITY.match("Priority: 50")
        assert match is not None
        assert match.group(1) == "50"


class TestParseSelections:
    """Tests for parsing --get-selections output."""

    def test_parse_single_selection(self) -> None:
        """Test parsing a single selection line."""
        output = "editor                         auto     /usr/bin/vim.basic"
        selections = parse_selections(output)

        assert len(selections) == 1
        assert selections[0].name == "editor"
        assert selections[0].mode == AlternativeStatus.AUTO
        assert selections[0].current_path == "/usr/bin/vim.basic"

    def test_parse_multiple_selections(self) -> None:
        """Test parsing multiple selection lines."""
        selections = parse_selections(SAMPLE_SELECTIONS_OUTPUT)

        assert len(selections) == 3
        
        # Check editor (auto)
        editor = next(s for s in selections if s.name == "editor")
        assert editor.mode == AlternativeStatus.AUTO
        assert editor.current_path == "/usr/bin/vim.basic"

        # Check python (manual)
        python = next(s for s in selections if s.name == "python")
        assert python.mode == AlternativeStatus.MANUAL
        assert python.current_path == "/usr/bin/python3"

    def test_parse_empty_output(self) -> None:
        """Test parsing empty output."""
        selections = parse_selections("")
        assert selections == []

    def test_parse_whitespace_only(self) -> None:
        """Test parsing whitespace-only output."""
        selections = parse_selections("   \n\t\n   ")
        assert selections == []

    def test_parse_status_case_insensitive(self) -> None:
        """Test that status parsing is case insensitive."""
        output = "editor                         AUTO     /usr/bin/vim"
        selections = parse_selections(output)
        assert selections[0].mode == AlternativeStatus.AUTO

    def test_class_method(self) -> None:
        """Test OutputParser class method."""
        parser = OutputParser()
        selections = parser.parse_selections(SAMPLE_SELECTIONS_OUTPUT)
        assert len(selections) == 3

    def test_parse_selections_as_dict(self) -> None:
        """Test parse_selections_as_dict method."""
        parser = OutputParser()
        result = parser.parse_selections_as_dict(SAMPLE_SELECTIONS_OUTPUT)
        
        assert "editor" in result
        assert "python" in result
        assert result["editor"].mode == AlternativeStatus.AUTO


class TestParseQuery:
    """Tests for parsing --query output."""

    def test_parse_basic_query(self) -> None:
        """Test parsing basic query output."""
        group = parse_query(SAMPLE_QUERY_OUTPUT)

        assert group is not None
        assert group.name == "editor"
        assert group.status == AlternativeStatus.AUTO
        assert group.link == "/usr/bin/editor"

    def test_parse_alternatives(self) -> None:
        """Test that alternatives are parsed correctly."""
        group = parse_query(SAMPLE_QUERY_OUTPUT)
        assert group is not None

        assert len(group.alternatives) == 3

        # Check priorities
        paths = {alt.path: alt.priority for alt in group.alternatives}
        assert paths["/usr/bin/ed"] == 10
        assert paths["/usr/bin/nano"] == 40
        assert paths["/usr/bin/vim.basic"] == 30

    def test_parse_slave_links(self) -> None:
        """Test that slave links are parsed."""
        group = parse_query(SAMPLE_QUERY_OUTPUT)
        assert group is not None

        # Test header slave links
        assert "editor.1.gz" in group.slave_links
        assert group.slave_links["editor.1.gz"] == "/usr/share/man/man1/editor.1.gz"
        
        # Test alternative slaves
        for alt in group.alternatives:
            assert "editor.1.gz" in alt.slaves, f"{alt.path} should have editor.1.gz slave"
    
    def test_parse_multiple_slaves(self) -> None:
        """Test parsing alternatives with multiple slaves (like awk)."""
        # Format similar to real awk output with multiple slaves
        output = """\
Name: awk
Link: /usr/bin/awk
Slaves:
 awk.1.gz /usr/share/man/man1/awk.1.gz
 nawk /usr/bin/nawk
 nawk.1.gz /usr/share/man/man1/nawk.1.gz
Status: auto
Best: /usr/bin/gawk
Value: /usr/bin/gawk

Alternative: /usr/bin/gawk
Priority: 10
Slaves:
 awk.1.gz /usr/share/man/man1/gawk.1.gz
 nawk /usr/bin/gawk
 nawk.1.gz /usr/share/man/man1/gawk.1.gz

Alternative: /usr/bin/mawk
Priority: 5
Slaves:
 awk.1.gz /usr/share/man/man1/mawk.1.gz
 nawk /usr/bin/mawk
 nawk.1.gz /usr/share/man/man1/mawk.1.gz
"""
        group = parse_query(output)
        assert group is not None
        
        # Check header slave links
        assert len(group.slave_links) == 3
        assert group.slave_links["awk.1.gz"] == "/usr/share/man/man1/awk.1.gz"
        assert group.slave_links["nawk"] == "/usr/bin/nawk"
        assert group.slave_links["nawk.1.gz"] == "/usr/share/man/man1/nawk.1.gz"
        
        # Check alternative slaves
        gawk = next(a for a in group.alternatives if "gawk" in a.path)
        assert len(gawk.slaves) == 3
        assert gawk.slaves["awk.1.gz"] == "/usr/share/man/man1/gawk.1.gz"
        assert gawk.slaves["nawk"] == "/usr/bin/gawk"
        
        mawk = next(a for a in group.alternatives if "mawk" in a.path)
        assert len(mawk.slaves) == 3
        assert mawk.slaves["nawk"] == "/usr/bin/mawk"

    def test_parse_best_value(self) -> None:
        """Test that best value is extracted."""
        group = parse_query(SAMPLE_QUERY_OUTPUT)
        assert group is not None
        assert group.best == "/usr/bin/vim.basic"

    def test_parse_current_value(self) -> None:
        """Test that current value is extracted."""
        group = parse_query(SAMPLE_QUERY_OUTPUT)
        assert group is not None
        assert group.current == "/usr/bin/vim.basic"

    def test_parse_empty_returns_none(self) -> None:
        """Test that empty output returns None."""
        result = parse_query("")
        assert result is None

    def test_manual_status(self) -> None:
        """Test parsing query with manual status."""
        output = """\
Name: python
Link: /usr/bin/python
Status: manual
Best: /usr/bin/python3.12
Value: /usr/bin/python3.11

Alternative: /usr/bin/python3.11
Priority: 311

Alternative: /usr/bin/python3.12
Priority: 312
"""
        group = parse_query(output)
        assert group is not None
        assert group.status == AlternativeStatus.MANUAL
        assert group.name == "python"

    def test_class_method(self) -> None:
        """Test OutputParser class method."""
        parser = OutputParser()
        group = parser.parse_query(SAMPLE_QUERY_OUTPUT)
        assert group is not None
        assert group.name == "editor"


class TestParseDisplay:
    """Tests for parsing --display output."""

    def test_parse_slave_links(self) -> None:
        """Test parsing slave links from display output."""
        result = parse_display(SAMPLE_DISPLAY_OUTPUT)

        assert "editor.1.gz" in result

    def test_parse_empty_output(self) -> None:
        """Test parsing empty output."""
        result = parse_display("")
        assert result == {}

    def test_class_method(self) -> None:
        """Test OutputParser class method."""
        parser = OutputParser()
        result = parser.parse_display(SAMPLE_DISPLAY_OUTPUT)
        assert isinstance(result, dict)


class TestExtractNames:
    """Tests for extracting alternative group names."""

    def test_extract_from_selections(self) -> None:
        """Test extracting names from selections output."""
        names = extract_names(SAMPLE_SELECTIONS_OUTPUT)

        assert "editor" in names
        assert "python" in names
        assert "java" in names

    def test_extract_empty_output(self) -> None:
        """Test extracting names from empty output."""
        names = extract_names("")
        assert names == []

    def test_extract_is_sorted(self) -> None:
        """Test that extraction returns sorted names."""
        output = """\
zebra                          auto     /path
alpha                          auto     /path
middle                         auto     /path
"""
        names = extract_names(output)
        assert names == sorted(names)

    def test_class_method(self) -> None:
        """Test OutputParser class method."""
        parser = OutputParser()
        names = parser.extract_alternative_names(SAMPLE_SELECTIONS_OUTPUT)
        assert "editor" in names


class TestOutputParser:
    """Tests for OutputParser class."""

    def test_parser_instantiation(self) -> None:
        """Test that OutputParser can be instantiated."""
        parser = OutputParser()
        assert parser is not None

    def test_parser_strict_mode(self) -> None:
        """Test strict mode initialization."""
        parser = OutputParser(strict=True)
        assert parser.strict is True

    def test_parser_has_all_methods(self) -> None:
        """Test that parser has all expected methods."""
        parser = OutputParser()
        
        assert hasattr(parser, "parse_selections")
        assert hasattr(parser, "parse_query")
        assert hasattr(parser, "parse_display")
        assert hasattr(parser, "extract_alternative_names")

    def test_validate_path(self) -> None:
        """Test validate_path static method."""
        assert OutputParser.validate_path("/usr/bin/vim") is True
        assert OutputParser.validate_path("") is False
        assert OutputParser.validate_path("relative/path") is False

    def test_validate_priority(self) -> None:
        """Test validate_priority static method.
        
        Note: update-alternatives allows negative priorities (e.g., -100 for /bin/ed).
        """
        assert OutputParser.validate_priority("50") == 50
        assert OutputParser.validate_priority("-100") == -100  # Negative priorities are valid
        assert OutputParser.validate_priority("0") == 0
        assert OutputParser.validate_priority("invalid") is None


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_parse_very_long_path(self) -> None:
        """Test parsing with very long path."""
        long_path = "/very" + "/long" * 50 + "/path"
        output = f"editor                         auto     {long_path}"
        selections = parse_selections(output)
        
        assert len(selections) == 1
        assert selections[0].current_path == long_path

    def test_parse_special_characters_in_name(self) -> None:
        """Test parsing names with special characters."""
        output = "c++                            auto     /usr/bin/g++"
        selections = parse_selections(output)
        
        assert len(selections) == 1
        assert selections[0].name == "c++"

    def test_parse_unicode_path(self) -> None:
        """Test parsing with unicode in path."""
        output = "editor                         auto     /usr/bin/编辑器"
        selections = parse_selections(output)
        
        assert len(selections) == 1
        assert "编辑器" in selections[0].current_path

    def test_query_minimal_output(self) -> None:
        """Test parsing minimal valid query output."""
        output = """\
Name: editor
Link: /usr/bin/editor
Status: auto
Best: /usr/bin/vim
Value: /usr/bin/vim

Alternative: /usr/bin/vim
Priority: 50
"""
        group = parse_query(output)
        
        assert group is not None
        assert group.name == "editor"
        assert len(group.alternatives) == 1

    def test_query_with_no_slaves(self) -> None:
        """Test parsing query with alternatives having no slaves."""
        output = """\
Name: simple
Link: /usr/bin/simple
Status: auto
Best: /usr/bin/simple
Value: /usr/bin/simple

Alternative: /usr/bin/simple
Priority: 10
"""
        group = parse_query(output)
        
        assert group is not None
        assert group.alternatives[0].slaves == {}
