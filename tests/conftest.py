"""Pytest configuration and shared fixtures for update-alternatives-tui tests."""

from __future__ import annotations

import pytest
from typing import TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from collections.abc import Generator

# ============================================================================
# Sample Data Constants
# ============================================================================

# Real --query output format (NOT --display format)
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

SAMPLE_SELECTIONS_OUTPUT = """\
editor                         auto     /usr/bin/vim.basic
python                         manual   /usr/bin/python3
java                           auto     /usr/lib/jvm/java-17/bin/java
"""

# ============================================================================
# Special Characters Test Data
# ============================================================================

# Names with special characters that could cause Rich markup issues
SPECIAL_CHAR_NAMES = [
    "builtins.7.gz",           # Dots and extension
    "python3.11",              # Version with dot
    "g++-12",                  # Plus signs
    "test[0]",                 # Brackets (Rich markup)
    "[bold]injection",         # Rich markup attempt
    "config[default]",         # Brackets in name
    "error[/]test",            # Auto-close tag
]

# Sample output with special character names
SAMPLE_SELECTIONS_WITH_SPECIAL = """\
editor                         auto     /usr/bin/vim.basic
builtins.7.gz                  auto     /usr/share/man/man7/builtins.7.gz
python3.11                     manual   /usr/bin/python3.11
test[0]                        auto     /usr/bin/test0
"""

SAMPLE_QUERY_WITH_SPECIAL = """\
Name: builtins.7.gz
Link: /usr/share/man/man7/builtins.7.gz
Status: auto
Best: /usr/share/man/man7/builtins.7.gz
Value: /usr/share/man/man7/builtins.7.gz

Alternative: /usr/share/man/man7/builtins.7.gz
Priority: 10
"""

SAMPLE_DISPLAY_OUTPUT = """\
Name: editor
Link: /usr/bin/editor
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


@dataclass(frozen=True)
class CommandOutputs:
    """Container for sample command outputs."""

    query: str = SAMPLE_QUERY_OUTPUT
    selections: str = SAMPLE_SELECTIONS_OUTPUT
    display: str = SAMPLE_DISPLAY_OUTPUT


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_outputs() -> CommandOutputs:
    """Provide sample command outputs for testing."""
    return CommandOutputs()


@pytest.fixture
def query_output() -> str:
    """Provide sample query output."""
    return SAMPLE_QUERY_OUTPUT


@pytest.fixture
def selections_output() -> str:
    """Provide sample selections output."""
    return SAMPLE_SELECTIONS_OUTPUT


@pytest.fixture
def display_output() -> str:
    """Provide sample display output."""
    return SAMPLE_DISPLAY_OUTPUT


@pytest.fixture
def empty_output() -> str:
    """Provide empty output."""
    return ""


@pytest.fixture
def malformed_output() -> str:
    """Provide malformed output for error testing."""
    return "This is not valid update-alternatives output"


@pytest.fixture
def special_char_names() -> list[str]:
    """Provide names with special characters for edge case testing."""
    return SPECIAL_CHAR_NAMES.copy()


@pytest.fixture
def selections_with_special() -> str:
    """Provide selections output containing special character names."""
    return SAMPLE_SELECTIONS_WITH_SPECIAL


@pytest.fixture
def query_with_special() -> str:
    """Provide query output containing special character names."""
    return SAMPLE_QUERY_WITH_SPECIAL


# ============================================================================
# Mock Executor Fixtures
# ============================================================================


class MockCommandResult:
    """Mock command result for testing."""

    def __init__(
        self,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.success = returncode == 0


class ConfigurableMockExecutor:
    """Configurable mock executor for testing different scenarios."""

    def __init__(self) -> None:
        self._responses: dict[tuple[str, ...], MockCommandResult] = {}
        self._default_response = MockCommandResult()
        self._call_history: list[tuple[str, ...]] = []

    def set_response(
        self,
        command: tuple[str, ...],
        *,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        """Configure response for a specific command."""
        self._responses[command] = MockCommandResult(returncode, stdout, stderr)

    def set_default_response(
        self,
        *,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        """Configure default response for unmatched commands."""
        self._default_response = MockCommandResult(returncode, stdout, stderr)

    def run(self, *args: str) -> MockCommandResult:
        """Execute command and return configured response."""
        self._call_history.append(args)
        return self._responses.get(args, self._default_response)

    @property
    def call_history(self) -> list[tuple[str, ...]]:
        """Get history of commands executed."""
        return self._call_history.copy()

    def reset_history(self) -> None:
        """Clear call history."""
        self._call_history.clear()


@pytest.fixture
def mock_executor() -> ConfigurableMockExecutor:
    """Provide configurable mock executor."""
    return ConfigurableMockExecutor()


@pytest.fixture
def executor_with_query_response(query_output: str) -> ConfigurableMockExecutor:
    """Provide mock executor configured with query response."""
    executor = ConfigurableMockExecutor()
    executor.set_response(
        ("update-alternatives", "--query", "editor"),
        stdout=query_output,
    )
    return executor


@pytest.fixture
def executor_with_selections_response(
    selections_output: str,
) -> ConfigurableMockExecutor:
    """Provide mock executor configured with selections response."""
    executor = ConfigurableMockExecutor()
    executor.set_response(
        ("update-alternatives", "--get-selections"),
        stdout=selections_output,
    )
    return executor


# ============================================================================
# Test Markers Configuration
# ============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests",
    )
    config.addinivalue_line(
        "markers",
        "requires_sudo: marks tests that require sudo privileges",
    )
