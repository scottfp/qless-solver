#!/usr/bin/env python3
"""Command-line interface for qless-solver."""

from __future__ import annotations

import argparse
import re
import sys
from typing import Optional

from qless_solver import __version__
from qless_solver.dictionary import (
    AVAILABLE_DICTIONARIES,
    DEFAULT_DICTIONARY_NAME,
    Dictionary,
)
from qless_solver.generator import generate_random_roll
from qless_solver.grid_solver import solve_board


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="qless-solver",
        description="Solve the Q-Less solitaire dice game.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"qless-solver {__version__}",
        help="Show version number and exit",
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--letters",
        "-l",
        type=str,
        help="A string of 12 letters from the dice roll",
    )
    input_group.add_argument(
        "--generate",
        "-g",
        action="store_true",
        help="Generate a random roll of the Q-Less dice",
    )

    parser.add_argument(
        "--min-word-length",
        "-m",
        type=int,
        default=3,
        help="Minimum word length (default: 3)",
    )
    parser.add_argument(
        "--max-solutions",
        "-n",
        type=int,
        default=5,
        help="Maximum number of grid solutions to display (default: 5)",
    )
    parser.add_argument(
        "--all-words",
        "-a",
        action="store_true",
        help="Show all valid dictionary words formable from the letters",
    )
    parser.add_argument(
        "--dictionary",
        "-d",
        choices=list(AVAILABLE_DICTIONARIES),
        default=DEFAULT_DICTIONARY_NAME,
        help=(
            "Dictionary mode: 'full' (all NWL words with common words ranked first, "
            "default) or 'common' (everyday English words only)"
        ),
    )
    parser.add_argument(
        "--exclude",
        "-x",
        action="append",
        default=[],
        help="Exclude word(s) from solutions (repeatable or comma-separated)",
    )

    return parser.parse_args(args)


def _parse_excluded_words(raw_values: list[str]) -> list[str]:
    """Normalize repeatable or comma/whitespace-separated excluded words."""
    excluded: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        for token in re.split(r"[,\s]+", raw.strip().lower()):
            if token and token.isascii() and token.isalpha() and token not in seen:
                seen.add(token)
                excluded.append(token)
    return excluded


def main() -> int:
    """Main entry point for the qless-solver CLI."""
    args = parse_args()

    if args.generate:
        letters = generate_random_roll()
        print(f"Generated random roll: {letters.upper()}")
        print("To solve this roll, run:")
        print(f"  qless-solver --letters {letters.lower()}")
        return 0

    letters = args.letters.strip().lower()

    if len(letters) != 12:
        print(
            f"Error: Expected exactly 12 letters, got {len(letters)}",
            file=sys.stderr,
        )
        return 1

    if not (letters.isascii() and letters.isalpha()):
        print("Error: Input must contain only letters", file=sys.stderr)
        return 1

    if args.min_word_length < 2:
        print("Error: Minimum word length must be at least 2", file=sys.stderr)
        return 1

    if args.max_solutions < 1:
        print("Error: Maximum solutions must be at least 1", file=sys.stderr)
        return 1

    excluded = _parse_excluded_words(args.exclude)
    active_dict = Dictionary(mode=args.dictionary)

    if args.all_words:
        words = sorted(
            active_dict.get_valid_words(letters, min_length=args.min_word_length)
            - set(excluded),
            key=lambda w: (-len(w), w),
        )
        if not words:
            print("No valid words found.")
            return 0
        print(f"Found {len(words)} valid word(s):")
        for word in words:
            print(f"- {word}")
        return 0

    boards = solve_board(
        letters=letters,
        dictionary=active_dict,
        min_word_length=args.min_word_length,
        max_solutions=args.max_solutions,
        excluded_words=excluded or None,
    )

    if not boards:
        print("No solutions found.")
        return 0

    print(f"Found {len(boards)} solution(s):")
    for i, board in enumerate(boards, 1):
        words = [bw.word.upper() for bw in board.extract_runs(min_length=2)]
        print(f"\nSolution {i} ({len(words)} words: {', '.join(words)}):")
        print(board.to_ascii(empty_char=".").upper())

    return 0


if __name__ == "__main__":
    sys.exit(main())
