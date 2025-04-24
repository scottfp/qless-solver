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

    # Use the provided path or default to dictionary.txt in the root directory
    if dictionary_path is None:
        dictionary_path = Path(__file__).parent.parent.parent / "dictionary.txt"

    _DICTIONARY = set()

    try:
        with open(dictionary_path, "r", encoding="utf-8") as f:
            for line in f:
                # Each line has format "WORD definition..." or just "WORD"
                # Extract just the word part (before the first space)
                if line.strip():
                    word = line.split(" ", 1)[0].lower()
                    # Remove any non-alphabetic characters
                    word = "".join(c for c in word if c.isalpha())
                    if word:  # Only add non-empty words
                        _DICTIONARY.add(word)
    except FileNotFoundError:
        print(
            f"Dictionary file not found at {dictionary_path}. Using built-in fallback dictionary."
        )
        # Fallback to a small built-in dictionary for testing purposes
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
        }

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
