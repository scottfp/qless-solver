"""
Core solving logic for the Q-Less game.
"""

from collections import Counter
from typing import Dict, Iterator, List, Set

from pydantic import BaseModel, Field
from qless_solver.dictionary import get_valid_words


class Solution(BaseModel):
    """A solution for the Q-Less game, consisting of interlocking words."""

    words: List[str] = Field(description="List of words that form the solution")
    used_letters: Dict[str, int] = Field(
        description="Count of letters used in the solution"
    )

    def get_words(self) -> Iterator[str]:
        """Get an iterator over the solution's words."""
        return iter(self.words)


def solve_qless(
    letters: str,
    min_word_length: int = 3,
    all_words: bool = False,
) -> List[Solution]:
    """
    Solve the Q-Less game with the given letters.

    Args:
        letters: String of letters from the dice roll (expected to be 12 letters)
        min_word_length: Minimum word length to consider
        all_words: If True, return all valid words that can be formed, not just complete solutions

    Returns:
        A list of possible solutions, where each solution is a list of words
    """
    # Convert input to lowercase and create a counter of available letters
    letters = letters.lower()
    available_letters = Counter(letters)

    # Get all valid words that can be formed from these letters
    possible_words = get_valid_words(letters, min_length=min_word_length)

    if all_words:
        # If all_words is True, return all valid words as individual "solutions"
        return [
            Solution(words=[word], used_letters=Counter(word))
            for word in possible_words
        ]

    # Find solutions that use all letters
    solutions = find_complete_solutions(
        possible_words, available_letters, min_word_length
    )

    return solutions


def find_complete_solutions(
    possible_words: Set[str], available_letters: Counter, min_word_length: int
) -> List[Solution]:
    """
    Find solutions that use all available letters.

    Args:
        possible_words: Set of valid words that can be formed
        available_letters: Counter of available letters
        min_word_length: Minimum word length

    Returns:
        List of solutions
    """
    solutions: List[Solution] = []

    # Store the original letters counter for reference
    original_letters = available_letters.copy()

    # A recursive helper function to build solutions
    def backtrack(
        remaining_letters: Counter,
        current_solution: List[str],
    ) -> None:
        # If no letters remain, we have a complete solution
        if sum(remaining_letters.values()) == 0:
            # Create a solution with the words and the used letters
            solution = Solution(
                words=current_solution.copy(),
                used_letters=original_letters - remaining_letters,
            )
            solutions.append(solution)
            return

        # Try each possible word
        for word in possible_words:
            word_counter = Counter(word)

            # Check if this word can be formed with remaining letters
            if all(
                word_counter[letter] <= remaining_letters[letter]
                for letter in word_counter
            ):
                # Use this word
                current_solution.append(word)
                # Remove its letters from remaining_letters
                for letter, count in word_counter.items():
                    remaining_letters[letter] -= count

                # Recursively try to complete the solution
                backtrack(remaining_letters, current_solution)

                # Backtrack
                current_solution.pop()
                for letter, count in word_counter.items():
                    remaining_letters[letter] += count

    backtrack(available_letters.copy(), [])
    return solutions
