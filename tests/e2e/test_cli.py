"""End-to-end tests for the CLI interface."""

from __future__ import annotations

import subprocess
import sys

import pytest


def test_cli_version() -> None:
    """Test that the CLI returns a version number."""
    pytest.importorskip("qless_solver")

    result = subprocess.run(
        [sys.executable, "-m", "qless_solver.cli", "--version"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "qless-solver" in result.stdout


def test_cli_help() -> None:
    """Test that the CLI help works and documents --max-solutions."""
    pytest.importorskip("qless_solver")

    result = subprocess.run(
        [sys.executable, "-m", "qless_solver.cli", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
    assert "--letters" in result.stdout
    assert "--max-solutions" in result.stdout
    assert "--dictionary" in result.stdout


def test_cli_generate_roll() -> None:
    """Test generating a random 12-letter roll via --generate."""
    pytest.importorskip("qless_solver")

    result = subprocess.run(
        [sys.executable, "-m", "qless_solver.cli", "--generate"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Generated random roll:" in result.stdout
    assert "qless-solver --letters " in result.stdout


def test_cli_solve_grid_with_letters() -> None:
    """Test solving a real 12-letter roll and rendering ASCII grids."""
    pytest.importorskip("qless_solver")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "qless_solver.cli",
            "--letters",
            "rmtoepngtnxc",
            "--max-solutions",
            "2",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Found 2 solution(s):" in result.stdout
    assert "Solution 1 (" in result.stdout
    assert "Solution 2 (" in result.stdout
    assert "words:" in result.stdout


def test_cli_all_words() -> None:
    """Test listing all valid words with --all-words."""
    pytest.importorskip("qless_solver")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "qless_solver.cli",
            "--letters",
            "rmtoepngtnxc",
            "--all-words",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "valid word(s):" in result.stdout
    assert "- comet" in result.stdout
    assert "- prong" in result.stdout
    assert "- next" in result.stdout


def test_cli_unsolvable_roll() -> None:
    """Test that an unsolvable 12-letter roll exits cleanly with no solutions."""
    pytest.importorskip("qless_solver")

    result = subprocess.run(
        [sys.executable, "-m", "qless_solver.cli", "--letters", "bcdfghjklmnp"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "No solutions found." in result.stdout


def test_cli_invalid_input() -> None:
    """Test CLI validation error messages and non-zero exit codes."""
    pytest.importorskip("qless_solver")

    short = subprocess.run(
        [sys.executable, "-m", "qless_solver.cli", "--letters", "abc"],
        capture_output=True,
        text=True,
    )
    assert short.returncode != 0
    assert "Expected exactly 12 letters" in short.stderr

    non_alpha = subprocess.run(
        [sys.executable, "-m", "qless_solver.cli", "--letters", "abc123defghi"],
        capture_output=True,
        text=True,
    )
    assert non_alpha.returncode != 0
    assert "Input must contain only letters" in non_alpha.stderr

    bad_min_len = subprocess.run(
        [
            sys.executable,
            "-m",
            "qless_solver.cli",
            "--letters",
            "rmtoepngtnxc",
            "--min-word-length",
            "1",
        ],
        capture_output=True,
        text=True,
    )
    assert bad_min_len.returncode != 0
    assert "Minimum word length must be at least 2" in bad_min_len.stderr


def test_cli_exclude_words() -> None:
    """Test --exclude filters solved boards and --all-words output."""
    pytest.importorskip("qless_solver")

    solved = subprocess.run(
        [
            sys.executable,
            "-m",
            "qless_solver.cli",
            "--letters",
            "rmtoepngtnxc",
            "--max-solutions",
            "2",
            "--exclude",
            "context",
        ],
        capture_output=True,
        text=True,
    )
    assert solved.returncode == 0
    assert "Found " in solved.stdout
    assert "CONTEXT" not in solved.stdout

    listed = subprocess.run(
        [
            sys.executable,
            "-m",
            "qless_solver.cli",
            "--letters",
            "rmtoepngtnxc",
            "--all-words",
            "--exclude",
            "comet,prong",
        ],
        capture_output=True,
        text=True,
    )
    assert listed.returncode == 0
    assert "valid word(s):" in listed.stdout
    assert "- comet" not in listed.stdout
    assert "- prong" not in listed.stdout
    assert "- next" in listed.stdout


def test_cli_dictionary_selection() -> None:
    """Test --dictionary common vs full and invalid dictionary rejection."""
    pytest.importorskip("qless_solver")

    common_words = subprocess.run(
        [
            sys.executable,
            "-m",
            "qless_solver.cli",
            "--letters",
            "rmtoepngtnxc",
            "--all-words",
            "--dictionary",
            "common",
        ],
        capture_output=True,
        text=True,
    )
    assert common_words.returncode == 0
    assert "- comet" in common_words.stdout
    assert "- gorm" not in common_words.stdout
    assert "- mong" not in common_words.stdout

    full_words = subprocess.run(
        [
            sys.executable,
            "-m",
            "qless_solver.cli",
            "--letters",
            "rmtoepngtnxc",
            "--all-words",
            "--dictionary",
            "full",
        ],
        capture_output=True,
        text=True,
    )
    assert full_words.returncode == 0
    assert "- comet" in full_words.stdout
    assert "- gorm" in full_words.stdout
    assert "- mong" in full_words.stdout

    common_solve = subprocess.run(
        [
            sys.executable,
            "-m",
            "qless_solver.cli",
            "--letters",
            "rmtoepngtnxc",
            "--dictionary",
            "common",
            "--max-solutions",
            "2",
        ],
        capture_output=True,
        text=True,
    )
    assert common_solve.returncode == 0
    assert "Found " in common_solve.stdout

    invalid = subprocess.run(
        [
            sys.executable,
            "-m",
            "qless_solver.cli",
            "--letters",
            "rmtoepngtnxc",
            "--dictionary",
            "nope",
        ],
        capture_output=True,
        text=True,
    )
    assert invalid.returncode != 0


if __name__ == "__main__":
    pytest.main()
