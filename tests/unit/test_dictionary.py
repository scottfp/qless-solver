"""
Unit tests for the qless_solver.dictionary module.
"""

from collections import Counter

import pytest
from qless_solver.dictionary import (
    add_custom_words,
    can_form_word,
    get_valid_words,
    is_valid_word,
    load_dictionary,
)


def test_load_dictionary() -> None:
    """Test that the dictionary loads correctly."""
    dictionary = load_dictionary()
    assert isinstance(dictionary, set)
    assert len(dictionary) > 0
    assert all(isinstance(word, str) for word in dictionary)


def test_is_valid_word() -> None:
    """Test the is_valid_word function."""
    # Test with a word that should be in the dictionary
    assert is_valid_word("eat") is True

    # Test with a word that's too short
    assert is_valid_word("at", min_length=3) is False

    # Test with a word that shouldn't be in the dictionary
    assert is_valid_word("xyzzy") is False

    # Add a custom word and test it
    add_custom_words({"xyzzy"})
    assert is_valid_word("xyzzy") is True


def test_can_form_word() -> None:
    """Test the can_form_word function."""
    # Test a word that can be formed
    assert can_form_word("eat", Counter("eatxyz")) is True

    # Test a word that can't be formed (missing letter)
    assert can_form_word("eat", Counter("etxyz")) is False

    # Test a word that can't be formed (not enough of a letter)
    assert can_form_word("tee", Counter("etxyz")) is False

    # Test case insensitivity
    assert can_form_word("EaT", Counter("eatxyz")) is True


def test_get_valid_words() -> None:
    """Test the get_valid_words function."""
    # Add test words to the dictionary
    add_custom_words({"cat", "at", "hat"})

    # Test with letters that can form "cat" and "hat"
    valid_words = get_valid_words("cathat", min_length=3)
    assert "cat" in valid_words
    assert "hat" in valid_words
    assert "at" not in valid_words  # too short with min_length=3

    # Test with min_length=2
    valid_words = get_valid_words("cathat", min_length=2)
    assert "at" in valid_words


def test_add_custom_words() -> None:
    """Test the add_custom_words function."""
    # Add custom words
    add_custom_words({"customword", "anotherword"})

    # Check that they were added
    dictionary = load_dictionary()
    assert "customword" in dictionary
    assert "anotherword" in dictionary


if __name__ == "__main__":
    pytest.main()
