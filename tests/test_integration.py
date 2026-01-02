"""Integration tests using real system update-alternatives data.

These tests verify that the parser correctly handles real-world
output from the system's update-alternatives command.

Note: These tests are marked with @pytest.mark.integration and
      require actual update-alternatives data from the system.
      They may be skipped in environments without alternatives.
"""

from __future__ import annotations

import subprocess
import pytest
from typing import TYPE_CHECKING

from update_alternatives_tui.parser import (
    OutputParser,
    parse_selections,
    parse_query,
    parse_display,
    extract_names,
)
from update_alternatives_tui.models import AlternativeStatus

if TYPE_CHECKING:
    from collections.abc import Generator


# ============================================================================
# Fixtures
# ============================================================================


def _run_update_alternatives(*args: str) -> tuple[int, str, str]:
    """Run update-alternatives command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["update-alternatives", *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        pytest.skip("update-alternatives command not found")
    except subprocess.TimeoutExpired:
        pytest.skip("update-alternatives command timed out")


@pytest.fixture(scope="module")
def system_selections() -> str:
    """Get real --get-selections output from system."""
    returncode, stdout, stderr = _run_update_alternatives("--get-selections")
    if returncode != 0 or not stdout.strip():
        pytest.skip("No alternatives available on this system")
    return stdout


@pytest.fixture(scope="module")
def system_alternative_names(system_selections: str) -> list[str]:
    """Get list of all alternative names from system."""
    names = extract_names(system_selections)
    if not names:
        pytest.skip("No alternatives available on this system")
    return names


@pytest.fixture(scope="module")
def system_query_outputs(system_alternative_names: list[str]) -> dict[str, str]:
    """Get --query output for each alternative."""
    outputs: dict[str, str] = {}
    for name in system_alternative_names:
        returncode, stdout, stderr = _run_update_alternatives("--query", name)
        if returncode == 0 and stdout.strip():
            outputs[name] = stdout
    return outputs


@pytest.fixture(scope="module")
def system_display_outputs(system_alternative_names: list[str]) -> dict[str, str]:
    """Get --display output for each alternative."""
    outputs: dict[str, str] = {}
    for name in system_alternative_names:
        returncode, stdout, stderr = _run_update_alternatives("--display", name)
        if returncode == 0 and stdout.strip():
            outputs[name] = stdout
    return outputs


# ============================================================================
# Integration Tests - Selections Parsing
# ============================================================================


@pytest.mark.integration
class TestSystemSelectionsParsing:
    """Test parsing of real --get-selections output."""

    def test_parse_all_selections(self, system_selections: str) -> None:
        """Test that all selections from system can be parsed."""
        selections = parse_selections(system_selections)
        
        # Should get at least one selection
        assert len(selections) > 0, "Should parse at least one selection"
        
        # Each selection should have required fields
        for sel in selections:
            assert sel.name, f"Selection should have name"
            assert sel.current_path, f"{sel.name} should have current_path"
            assert sel.mode in (AlternativeStatus.AUTO, AlternativeStatus.MANUAL), \
                f"{sel.name} should have valid mode"

    def test_selection_names_match_extract(
        self, system_selections: str, system_alternative_names: list[str]
    ) -> None:
        """Test that parsed selections match extracted names."""
        selections = parse_selections(system_selections)
        selection_names = {s.name for s in selections}
        extracted_names = set(system_alternative_names)
        
        assert selection_names == extracted_names, \
            "Selection names should match extracted names"

    def test_all_paths_are_absolute(self, system_selections: str) -> None:
        """Test that all parsed paths are absolute."""
        selections = parse_selections(system_selections)
        
        for sel in selections:
            assert sel.current_path.startswith("/"), \
                f"{sel.name}: path '{sel.current_path}' should be absolute"

    def test_selections_as_dict(self, system_selections: str) -> None:
        """Test parse_selections_as_dict with real data."""
        parser = OutputParser()
        selections_dict = parser.parse_selections_as_dict(system_selections)
        
        assert isinstance(selections_dict, dict)
        assert len(selections_dict) > 0
        
        for name, info in selections_dict.items():
            assert info.name == name


# ============================================================================
# Integration Tests - Query Parsing
# ============================================================================


@pytest.mark.integration
class TestSystemQueryParsing:
    """Test parsing of real --query output."""

    def test_parse_all_queries(self, system_query_outputs: dict[str, str]) -> None:
        """Test that all --query outputs can be parsed without errors."""
        if not system_query_outputs:
            pytest.skip("No query outputs available")
        
        failed_names: list[str] = []
        
        for name, output in system_query_outputs.items():
            try:
                group = parse_query(output)
                if group is None:
                    failed_names.append(f"{name}: returned None")
                elif group.name != name:
                    failed_names.append(f"{name}: parsed name is '{group.name}'")
            except Exception as e:
                failed_names.append(f"{name}: {type(e).__name__}: {e}")
        
        assert not failed_names, \
            f"Failed to parse {len(failed_names)} alternatives:\n" + "\n".join(failed_names)

    def test_query_fields_populated(self, system_query_outputs: dict[str, str]) -> None:
        """Test that parsed queries have all expected fields populated."""
        if not system_query_outputs:
            pytest.skip("No query outputs available")
        
        for name, output in system_query_outputs.items():
            group = parse_query(output)
            assert group is not None, f"{name}: should not return None"
            
            # Required fields
            assert group.name == name, f"{name}: name mismatch"
            assert group.link, f"{name}: should have link"
            assert group.link.startswith("/"), f"{name}: link should be absolute"
            assert group.status in (
                AlternativeStatus.AUTO, 
                AlternativeStatus.MANUAL,
                AlternativeStatus.UNKNOWN
            ), f"{name}: invalid status"

    def test_query_alternatives_valid(self, system_query_outputs: dict[str, str]) -> None:
        """Test that each query has valid alternatives."""
        if not system_query_outputs:
            pytest.skip("No query outputs available")
        
        for name, output in system_query_outputs.items():
            group = parse_query(output)
            assert group is not None
            
            # Should have at least one alternative
            assert len(group.alternatives) >= 1, \
                f"{name}: should have at least one alternative"
            
            for alt in group.alternatives:
                # Each alternative should have valid path
                # Note: priority can be negative (e.g., /bin/ed has -100)
                assert alt.path, f"{name}: alternative should have path"
                assert alt.path.startswith("/"), \
                    f"{name}: alternative path '{alt.path}' should be absolute"

    def test_query_slaves_consistency(self, system_query_outputs: dict[str, str]) -> None:
        """Test that slave links and slave paths are consistent."""
        if not system_query_outputs:
            pytest.skip("No query outputs available")
        
        for name, output in system_query_outputs.items():
            group = parse_query(output)
            assert group is not None
            
            # If there are header slave_links, alternatives may have slaves
            if group.slave_links:
                # Verify slave_links are valid
                for slave_name, slave_link in group.slave_links.items():
                    assert slave_name, f"{name}: slave name should not be empty"
                    assert slave_link.startswith("/"), \
                        f"{name}: slave link '{slave_link}' should be absolute"
            
            # Verify alternative slaves are valid
            for alt in group.alternatives:
                for slave_name, slave_path in alt.slaves.items():
                    assert slave_name, f"{name}: slave name should not be empty"
                    assert slave_path.startswith("/"), \
                        f"{name}: slave path '{slave_path}' should be absolute"

    def test_query_current_matches_alternative(
        self, system_query_outputs: dict[str, str]
    ) -> None:
        """Test that current value matches one of the alternatives."""
        if not system_query_outputs:
            pytest.skip("No query outputs available")
        
        for name, output in system_query_outputs.items():
            group = parse_query(output)
            assert group is not None
            
            if group.current:
                alt_paths = {alt.path for alt in group.alternatives}
                assert group.current in alt_paths, \
                    f"{name}: current '{group.current}' not in alternatives {alt_paths}"


# ============================================================================
# Integration Tests - Display Parsing
# ============================================================================


@pytest.mark.integration
class TestSystemDisplayParsing:
    """Test parsing of real --display output."""

    def test_parse_all_displays(self, system_display_outputs: dict[str, str]) -> None:
        """Test that all --display outputs can be parsed without errors."""
        if not system_display_outputs:
            pytest.skip("No display outputs available")
        
        failed_names: list[str] = []
        
        for name, output in system_display_outputs.items():
            try:
                group = parse_display(output)
                if group is None:
                    failed_names.append(f"{name}: returned None")
            except Exception as e:
                failed_names.append(f"{name}: {type(e).__name__}: {e}")
        
        assert not failed_names, \
            f"Failed to parse {len(failed_names)} displays:\n" + "\n".join(failed_names)


# ============================================================================
# Integration Tests - Cross-Validation
# ============================================================================


@pytest.mark.integration
class TestCrossValidation:
    """Cross-validate parsing results between different output formats."""

    def test_query_vs_selections_consistency(
        self,
        system_selections: str,
        system_query_outputs: dict[str, str],
    ) -> None:
        """Test that --query and --get-selections produce consistent results."""
        selections = {s.name: s for s in parse_selections(system_selections)}
        
        for name, query_output in system_query_outputs.items():
            if name not in selections:
                continue
            
            sel = selections[name]
            group = parse_query(query_output)
            assert group is not None
            
            # Mode should match
            assert group.status == sel.mode, \
                f"{name}: query status '{group.status}' != selection mode '{sel.mode}'"
            
            # Current path should match
            if group.current:
                assert group.current == sel.current_path, \
                    f"{name}: query current '{group.current}' != selection path '{sel.current_path}'"

    def test_service_slave_links_match_parser(
        self, system_query_outputs: dict[str, str]
    ) -> None:
        """Test that Service.get_details returns same slave_links as parse_query.
        
        This is a regression test to ensure Service doesn't overwrite
        correctly parsed slave_links from --query output.
        """
        from update_alternatives_tui.service import AlternativesService
        from update_alternatives_tui.executor import SubprocessExecutor
        
        executor = SubprocessExecutor()
        service = AlternativesService(executor)
        
        # Test with a few alternatives that have slaves
        for name, query_output in list(system_query_outputs.items())[:10]:
            parser_group = parse_query(query_output)
            if parser_group is None or not parser_group.slave_links:
                continue
            
            service_group = service.get_details(name)
            assert service_group is not None, f"{name}: service returned None"
            
            # slave_links from service should match parser
            assert service_group.slave_links == parser_group.slave_links, \
                f"{name}: service slave_links {service_group.slave_links} != " \
                f"parser slave_links {parser_group.slave_links}"


# ============================================================================
# Integration Tests - Edge Cases from Real Data
# ============================================================================


@pytest.mark.integration
class TestRealWorldEdgeCases:
    """Test edge cases discovered from real system data."""

    def test_alternative_with_dots_in_name(
        self, system_query_outputs: dict[str, str]
    ) -> None:
        """Test alternatives with dots in name (e.g., builtins.7.gz)."""
        dotted_names = [n for n in system_query_outputs.keys() if "." in n]
        
        for name in dotted_names:
            output = system_query_outputs[name]
            group = parse_query(output)
            
            assert group is not None, f"{name}: should parse successfully"
            assert group.name == name, f"{name}: name should match exactly"

    def test_alternative_with_plus_in_name(
        self, system_query_outputs: dict[str, str]
    ) -> None:
        """Test alternatives with plus signs in name (e.g., c++, g++)."""
        plus_names = [n for n in system_query_outputs.keys() if "+" in n]
        
        for name in plus_names:
            output = system_query_outputs[name]
            group = parse_query(output)
            
            assert group is not None, f"{name}: should parse successfully"

    def test_alternative_with_long_paths(
        self, system_query_outputs: dict[str, str]
    ) -> None:
        """Test alternatives with long paths (e.g., Java)."""
        if not system_query_outputs:
            pytest.skip("No query outputs available")
        
        for name, output in system_query_outputs.items():
            group = parse_query(output)
            assert group is not None
            
            for alt in group.alternatives:
                # Very long paths should work (Java paths can be 50+ chars)
                if len(alt.path) > 50:
                    assert alt.path.startswith("/"), \
                        f"{name}: long path should still be absolute"

    def test_alternatives_with_many_slaves(
        self, system_query_outputs: dict[str, str]
    ) -> None:
        """Test alternatives with many slaves."""
        for name, output in system_query_outputs.items():
            group = parse_query(output)
            if group is None:
                continue
            
            # Count total slaves across all alternatives
            total_slaves = sum(len(alt.slaves) for alt in group.alternatives)
            total_header_slaves = len(group.slave_links)
            
            # If there are many slaves, verify all were parsed
            if total_slaves > 5 or total_header_slaves > 5:
                # Just verify structure is correct
                for alt in group.alternatives:
                    for slave_name, slave_path in alt.slaves.items():
                        assert slave_name
                        assert slave_path.startswith("/")


# ============================================================================
# Smoke Tests - Quick Validation
# ============================================================================


@pytest.mark.integration
class TestSmoke:
    """Quick smoke tests for basic functionality with real data."""

    def test_system_has_alternatives(self, system_alternative_names: list[str]) -> None:
        """Verify system has at least some alternatives for testing."""
        assert len(system_alternative_names) >= 1, \
            "System should have at least one alternative"

    def test_parser_instantiation(self) -> None:
        """Test that OutputParser can be instantiated."""
        parser = OutputParser()
        assert parser is not None

    def test_common_alternatives_parseable(self) -> None:
        """Test that common alternatives can be queried and parsed."""
        common_names = ["editor", "pager", "awk", "vi", "vim"]
        
        for name in common_names:
            returncode, stdout, stderr = _run_update_alternatives("--query", name)
            if returncode != 0:
                continue  # Skip if not installed
            
            group = parse_query(stdout)
            assert group is not None, f"{name}: should parse successfully"
            assert group.name == name, f"{name}: name should match"


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """Performance tests with real system data."""

    def test_parse_all_selections_performance(self, system_selections: str) -> None:
        """Test that parsing all selections is fast."""
        import time
        
        start = time.perf_counter()
        for _ in range(100):
            parse_selections(system_selections)
        elapsed = time.perf_counter() - start
        
        # Should complete 100 iterations in under 1 second
        assert elapsed < 1.0, f"Parsing took {elapsed:.2f}s for 100 iterations"

    def test_parse_all_queries_performance(
        self, system_query_outputs: dict[str, str]
    ) -> None:
        """Test that parsing all queries is reasonably fast."""
        import time
        
        if not system_query_outputs:
            pytest.skip("No query outputs available")
        
        start = time.perf_counter()
        for _ in range(10):
            for output in system_query_outputs.values():
                parse_query(output)
        elapsed = time.perf_counter() - start
        
        # Should complete 10 full iterations in under 5 seconds
        assert elapsed < 5.0, \
            f"Parsing {len(system_query_outputs)} queries x10 took {elapsed:.2f}s"
