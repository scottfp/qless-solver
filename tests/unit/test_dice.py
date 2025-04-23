"""
Unit tests for the qless_solver.dice module.
"""

import pytest
from pydantic import ValidationError
from qless_solver.dice import (
    QLESS_DICE,
    DiceSet,
    Die,
    create_standard_dice_set,
    roll_dice,
)


def test_die_init() -> None:
    """Test die initialization."""
    # Test with valid sides
    die = Die(sides=["A", "B", "C", "D", "E", "F"], current_face=None)
    assert die.sides == ["A", "B", "C", "D", "E", "F"]
    assert die.current_face is None

    # Test with invalid number of sides
    with pytest.raises(ValidationError):
        Die(sides=["A", "B", "C", "D", "E"], current_face=None)

    with pytest.raises(ValidationError):
        Die(sides=["A", "B", "C", "D", "E", "F", "G"], current_face=None)


def test_die_roll() -> None:
    """Test die rolling."""
    die = Die(sides=["A", "B", "C", "D", "E", "F"], current_face=None)

    # Test specific roll
    assert die.roll(use_face_index=0) == "A"
    assert die.current_face == "A"

    assert die.roll(use_face_index=5) == "F"
    assert die.current_face == "F"

    # Test random roll is one of the sides
    for _ in range(10):  # Roll multiple times to ensure randomness works
        letter = die.roll()
        assert letter in ["A", "B", "C", "D", "E", "F"]
        assert die.current_face == letter


def test_dice_set_init() -> None:
    """Test dice set initialization."""
    # Test with default dice via from_config
    dice_set = DiceSet.from_config()
    assert len(dice_set.dice) == 12  # Q-Less has 12 dice

    # Test with custom dice
    custom_dice = [["A", "B", "C", "D", "E", "F"], ["G", "H", "I", "J", "K", "L"]]
    dice_set = DiceSet.from_config(custom_dice)
    assert len(dice_set.dice) == 2
    assert dice_set.dice[0].sides == ["A", "B", "C", "D", "E", "F"]
    assert dice_set.dice[1].sides == ["G", "H", "I", "J", "K", "L"]


def test_dice_set_roll() -> None:
    """Test rolling a set of dice."""
    # Test with custom dice and specific roll
    custom_dice = [["A", "B", "C", "D", "E", "F"], ["G", "H", "I", "J", "K", "L"]]
    dice_set = DiceSet.from_config(custom_dice)

    # Roll with specific indices
    result = dice_set.roll(use_face_indices=[0, 1])
    assert result == ["A", "H"]
    assert dice_set.roll_result == ["A", "H"]
    assert dice_set.get_roll_string() == "AH"

    # Test random roll
    dice_set = DiceSet.from_config(custom_dice)
    result = dice_set.roll()
    assert len(result) == 2
    assert all(letter in "ABCDEFGHIJKL" for letter in result)


def test_get_letter_frequency() -> None:
    """Test getting letter frequencies from a roll."""
    dice_set = DiceSet.from_config(
        [["A", "A", "A", "B", "B", "C"], ["A", "D", "D", "E", "E", "F"]]
    )
    dice_set.roll(use_face_indices=[0, 0])  # Roll "A" and "A"

    freq = dice_set.get_letter_frequency()
    assert freq == {"A": 2}

    dice_set.roll(use_face_indices=[3, 2])  # Roll "B" and "D"
    freq = dice_set.get_letter_frequency()
    assert freq == {"B": 1, "D": 1}


def test_create_standard_dice_set() -> None:
    """Test creating a standard dice set."""
    dice_set = create_standard_dice_set()
    assert len(dice_set.dice) == 12

    # Check that the dice match the standard configuration
    for i, die in enumerate(dice_set.dice):
        assert die.sides == QLESS_DICE[i]


def test_roll_dice() -> None:
    """Test the roll_dice function."""
    # Test with a specific dice set
    custom_dice = [["A", "B", "C", "D", "E", "F"], ["G", "H", "I", "J", "K", "L"]]
    dice_set = DiceSet.from_config(custom_dice)

    # Roll the dice set
    letters, letters_str = roll_dice(dice_set)
    assert len(letters) == 2
    assert len(letters_str) == 2
    assert "".join(letters) == letters_str

    # Test with default dice set
    letters, letters_str = roll_dice()
    assert len(letters) == 12  # Q-Less has 12 dice
    assert len(letters_str) == 12
    assert "".join(letters) == letters_str


def test_qless_dice_distribution() -> None:
    """Test that the Q-Less dice distribution is accurate."""
    # Check that there are 12 dice
    assert len(QLESS_DICE) == 12

    # Check that each die has 6 sides
    for die_sides in QLESS_DICE:
        assert len(die_sides) == 6

    # Check specific dice based on the known distribution
    assert QLESS_DICE[0] == ["M", "M", "L", "L", "B", "Y"]  # Die 1
    assert QLESS_DICE[10] == ["A", "E", "I", "O", "U", "U"]  # Die 11 (vowels)
    assert QLESS_DICE[11] == ["A", "A", "E", "E", "O", "O"]  # Die 12 (vowels)

    # Verify that all letters from A to Z except Q are present
    all_letters = [letter for die in QLESS_DICE for letter in die]
    for letter in "ABCDEFGHIJKLMNOPRSTUVWXYZ":  # Excluding Q
        assert letter in all_letters

    # Q should not be present (it's "Q-less" after all!)
    assert "Q" not in all_letters


if __name__ == "__main__":
    pytest.main()
