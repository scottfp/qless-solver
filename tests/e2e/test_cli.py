"""
End-to-end tests for the CLI interface.
"""

import subprocess
import sys

import pytest


def test_cli_version() -> None:
    """Test that the CLI returns a version number."""
    # Skip this test if we're not running in development mode
    pytest.importorskip("qless_solver")

    # Run the CLI with --version
    result = subprocess.run(
        [sys.executable, "-m", "qless_solver.cli", "--version"],
        capture_output=True,
        text=True,
    )

    # Check that it returned successfully
    assert result.returncode == 0
    # Check that it printed something that looks like a version
    assert "qless-solver" in result.stdout


def test_cli_help() -> None:
    """Test that the CLI help works."""
    # Skip this test if we're not running in development mode
    pytest.importorskip("qless_solver")

    # Run the CLI with --help
    result = subprocess.run(
        [sys.executable, "-m", "qless_solver.cli", "--help"],
        capture_output=True,
        text=True,
    )

    # Check that it returned successfully
    assert result.returncode == 0
    # Check that it printed help information
    assert "usage:" in result.stdout.lower()
    assert "--letters" in result.stdout


def test_cli_with_letters() -> None:
    """Test the CLI with a simple letter input."""
    # Skip this test if we're not running in development mode
    pytest.importorskip("qless_solver")

    # First, add some test words to the dictionary
    # This is a bit of a hack, but it works for testing
    from qless_solver.dictionary import add_custom_words

    add_custom_words({"eat", "tea", "ate"})

    # Run the CLI with a simple input that should match our test words
    # Make sure we have exactly 12 letters
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "qless_solver.cli",
            "--letters",
            "eatbcdfghijk",
            "--all-words",
        ],
        capture_output=True,
        text=True,
    )

    # Check that it returned successfully
    assert result.returncode == 0

    # Check that it found the expected words
    assert "eat" in result.stdout
    assert "tea" in result.stdout
    assert "ate" in result.stdout


def test_cli_invalid_input() -> None:
    """Test the CLI with invalid input."""
    # Skip this test if we're not running in development mode
    pytest.importorskip("qless_solver")

    # Run the CLI with too few letters
    result = subprocess.run(
        [sys.executable, "-m", "qless_solver.cli", "--letters", "abc"],
        capture_output=True,
        text=True,
    )

    # Check that it returned an error
    assert result.returncode != 0
    assert "Expected exactly 12 letters" in result.stderr

    # Run the CLI with non-letter characters
    result = subprocess.run(
        [sys.executable, "-m", "qless_solver.cli", "--letters", "abc123defghi"],
        capture_output=True,
        text=True,
    )

    # Check that it returned an error
    assert result.returncode != 0
    assert "Input must contain only letters" in result.stderr


if __name__ == "__main__":
    pytest.main()
