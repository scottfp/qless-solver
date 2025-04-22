#!/usr/bin/env python3
"""
Command-line interface for qless-solver.
"""
import argparse
import sys
from typing import List, Optional

from qless_solver import __version__
from qless_solver.generator import generate_random_roll
from qless_solver.solver import solve_qless


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
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

    # Create a mutually exclusive group for input options
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
        "--all-words",
        "-a",
        action="store_true",
        help="Show all possible words, not just complete solutions",
    )

    return parser.parse_args(args)


def main() -> int:
    """Main entry point for the qless-solver CLI."""
    args = parse_args()

    # Handle random roll generation
    if args.generate:
        letters = generate_random_roll()
        print(f"Generated random roll: {letters.upper()}")
        print("To solve this roll, run:")
        print(f"  qless-solver --letters {letters}")
        return 0

    # Get letters from command line argument
    letters = args.letters.strip().lower()

    # Validate input
    if len(letters) != 12:
        print(
            f"Error: Expected exactly 12 letters, got {len(letters)}", file=sys.stderr
        )
        return 1

    if not letters.isalpha():
        print("Error: Input must contain only letters", file=sys.stderr)
        return 1

    # Solve the Q-Less game
    solutions = solve_qless(
        letters=letters,
        min_word_length=args.min_word_length,
        all_words=args.all_words,
    )

    # Display results
    if not solutions:
        print("No solutions found.")
        return 0

    print(f"Found {len(solutions)} solution(s):")
    for i, solution in enumerate(solutions, 1):
        print(f"\nSolution {i}:")
        for word in solution:
            print(f"- {word}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
