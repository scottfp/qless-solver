"""
Dictionary module for the qless-solver.
Provides functions for validating words and finding valid words.
"""

from collections import Counter
from pathlib import Path
from typing import Optional, Set

# Global cache for the dictionary
_DICTIONARY: Optional[Set[str]] = None


def load_dictionary(
    dictionary_path: Optional[Path] = None,
) -> Set[str]:
    """
    Load a dictionary of valid words.

    Args:
        dictionary_path: Path to the dictionary file. If None, uses a default dictionary.

    Returns:
        A set of valid words.
    """
    global _DICTIONARY

    # Use cached dictionary if available
    if _DICTIONARY is not None:
        return _DICTIONARY

    # For now, use a small built-in dictionary for testing purposes
    # In a production version, this would be replaced with a proper dictionary file
    # This is a placeholder - we'd want to use a file-based dictionary in the real implementation
    _DICTIONARY = {
        "apple",
        "banana",
        "cherry",
        "date",
        "fig",
        "grape",
        "are",
        "ran",
        "ear",
        "near",
        "gear",
        "ran",
        "eat",
        "tea",
        "ate",
        "seat",
        "rate",
        "tear",
        "gate",
        "art",
        "rat",
        "tar",
        "tare",
        "stare",
        "depart",
        # Add more words as needed or load from a file
    }

    # Convert all words to lowercase
    _DICTIONARY = {word.lower() for word in _DICTIONARY}

    return _DICTIONARY


def is_valid_word(word: str, min_length: int = 3) -> bool:
    """
    Check if a word is valid.

    Args:
        word: The word to check.
        min_length: Minimum word length.

    Returns:
        True if the word is valid, False otherwise.
    """
    if len(word) < min_length:
        return False

    dictionary = load_dictionary()
    return word.lower() in dictionary


def can_form_word(word: str, available_letters: Counter) -> bool:
    """
    Check if a word can be formed from the available letters.

    Args:
        word: The word to check.
        available_letters: Counter of available letters.

    Returns:
        True if the word can be formed, False otherwise.
    """
    word_counter = Counter(word.lower())

    for letter, count in word_counter.items():
        if available_letters[letter] < count:
            return False

    return True


def get_valid_words(
    letters: str,
    min_length: int = 3,
    dictionary_path: Optional[Path] = None,
) -> Set[str]:
    """
    Get all valid words that can be formed from the given letters.

    Args:
        letters: String of available letters.
        min_length: Minimum word length.
        dictionary_path: Path to the dictionary file.

    Returns:
        Set of valid words that can be formed.
    """
    dictionary = load_dictionary(dictionary_path)
    available_letters = Counter(letters.lower())

    # Filter the dictionary to find words that can be formed
    valid_words = set()
    for word in dictionary:
        if len(word) >= min_length and can_form_word(word, available_letters):
            valid_words.add(word)

    return valid_words


def add_custom_words(words: Set[str]) -> None:
    """
    Add custom words to the dictionary.

    Args:
        words: Set of words to add.
    """
    dictionary = load_dictionary()
    for word in words:
        dictionary.add(word.lower())
