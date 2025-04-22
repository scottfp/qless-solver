"""
Unit tests for the qless_solver.generator module.
"""

import pytest
from qless_solver.dice import create_standard_dice_set
from qless_solver.generator import (
    generate_random_roll,
    generate_solvable_roll,
    generate_test_cases,
)


def test_generate_random_roll() -> None:
    """Test generating a random roll."""
    roll = generate_random_roll()

    # Check that we got a string of 12 letters
    assert isinstance(roll, str)
    assert len(roll) == 12

    # Check that all characters are uppercase letters
    assert all(c.isupper() for c in roll)

    # Generate multiple rolls to ensure they're different (randomness check)
    rolls = [generate_random_roll() for _ in range(5)]
    assert len(set(rolls)) > 1, "Multiple rolls should not all be identical"


def test_generate_solvable_roll() -> None:
    """Test generating a solvable roll."""
    # Test with no words
    roll, words = generate_solvable_roll()
    assert isinstance(roll, str)
    assert len(roll) == 12
    assert words == []

    # Test with provided words
    test_words = ["cat", "dog", "bird"]
    roll, words = generate_solvable_roll(test_words)
    assert isinstance(roll, str)
    assert len(roll) == 12
    assert words == ["CAT", "DOG", "BIRD"]  # Words should be converted to uppercase


def test_generate_test_cases() -> None:
    """Test generating multiple test cases."""
    # Test default count
    cases = generate_test_cases()
    assert len(cases) == 10
    assert all(len(case) == 12 for case in cases)

    # Test custom count
    cases = generate_test_cases(5)
    assert len(cases) == 5
    assert all(len(case) == 12 for case in cases)


def test_integration_with_dice_module() -> None:
    """Test that the generator is correctly using the dice module."""
    # Generate a roll and verify it contains only letters that appear on the dice
    roll = generate_random_roll()

    # Create a dice set to check what letters are possible
    dice_set = create_standard_dice_set()

    # Get all possible letters from all dice
    all_possible_letters = set()
    for die in dice_set.dice:
        all_possible_letters.update(die.sides)

    # Verify that all letters in the roll are possible from the dice
    for letter in roll:
        assert letter in all_possible_letters, f"Letter {letter} not found on any dice"


if __name__ == "__main__":
    pytest.main()
