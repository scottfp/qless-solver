"""
Unit tests for the qless_solver.solver module.
"""

from collections import Counter

import pytest
from qless_solver.dictionary import add_custom_words
from qless_solver.solver import Solution, find_complete_solutions, solve_qless


def test_solution_model() -> None:
    """Test the Solution model."""
    solution = Solution(
        words=["hello", "world"],
        used_letters={"h": 1, "e": 1, "l": 3, "o": 2, "w": 1, "r": 1, "d": 1},
    )

    assert len(solution.words) == 2
    assert solution.words == ["hello", "world"]
    assert solution.used_letters["l"] == 3

    # Test word retrieval using get_words
    words = list(solution.get_words())
    assert words == ["hello", "world"]


def test_solve_qless_all_words() -> None:
    """Test the solve_qless function with all_words=True."""
    # Add test words to the dictionary
    add_custom_words({"cat", "dog", "bat"})

    # Test with letters that can form "cat", "dog", and "bat"
    letters = "catdogbatxyz"
    result = solve_qless(letters, min_word_length=3, all_words=True)

    # Check that all expected words are found
    words = [solution.words[0] for solution in result]
    assert "cat" in words
    assert "dog" in words
    assert "bat" in words


def test_find_complete_solutions() -> None:
    """Test the find_complete_solutions function."""
    # Create a simple test case
    possible_words = {"cat", "dog"}
    available_letters = Counter("catdog")
    min_word_length = 3

    # Find solutions
    solutions = find_complete_solutions(
        possible_words, available_letters, min_word_length
    )

    # The function may find solutions with the same words in different orders
    # So we check that at least one solution exists with the right words
    assert len(solutions) > 0

    # Check that one of the solutions contains both "cat" and "dog"
    found_solution = False
    for solution in solutions:
        if set(solution.words) == {"cat", "dog"}:
            found_solution = True
            assert len(solution.words) == 2
            assert sum(solution.used_letters.values()) == 6  # c+a+t+d+o+g = 6

    assert found_solution, "No solution found with both 'cat' and 'dog'"


def test_solve_qless_with_all_words() -> None:
    """Test that solve_qless returns valid solutions when all_words=True."""
    # Test with a simple input
    solutions = solve_qless("cathateatrat", min_word_length=3, all_words=True)

    # We expect individual solutions for valid words
    assert len(solutions) > 0

    # Each solution should have exactly one word
    for solution in solutions:
        assert len(solution.words) == 1


def test_solve_qless_complete() -> None:
    """Test that solve_qless finds complete solutions."""
    # Test with a carefully crafted input where we know a solution exists
    solutions = solve_qless("cathateatrat", min_word_length=3, all_words=False)

    # We should find at least one solution that uses all letters
    assert len(solutions) > 0

    # Each solution should use exactly the letters provided
    for solution in solutions:
        used_letters = "".join(solution.words)
        assert Counter(used_letters.lower()) == Counter("cathateatrat")


def test_solution_iteration() -> None:
    """Test that a Solution instance words can be retrieved via get_words."""
    solution = Solution(
        words=["one", "two"], used_letters={"o": 1, "n": 1, "e": 1, "t": 1, "w": 1}
    )
    words = list(solution.get_words())
    assert words == ["one", "two"]


if __name__ == "__main__":
    pytest.main()
