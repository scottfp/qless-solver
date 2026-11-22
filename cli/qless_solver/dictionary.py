"""
Dictionary module for the qless-solver.
Provides functions for validating words and finding valid words.
"""

from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, Optional, Set

DEFAULT_DICTIONARY_PATH = (
    Path(__file__).parent.parent.parent / "dictionary.txt"
).resolve()

# Global cache for dictionaries keyed by resolved path
_DICTIONARY_CACHE: Dict[Path, Set[str]] = {}

_FALLBACK_WORDS: Set[str] = {
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


def load_dictionary(
    dictionary_path: Optional[Path] = None,
    force_reload: bool = False,
) -> Set[str]:
    """
    Load a dictionary of valid words.

    Args:
        dictionary_path: Path to the dictionary file. If None, uses the default dictionary.
        force_reload: If True, bypass the cache and reload from disk.

    Returns:
        A set of valid lowercase words.
    """
    is_default = dictionary_path is None
    resolved_path = (
        DEFAULT_DICTIONARY_PATH
        if dictionary_path is None
        else Path(dictionary_path).resolve()
    )

    if not force_reload and resolved_path in _DICTIONARY_CACHE:
        return _DICTIONARY_CACHE[resolved_path]

    words: Set[str] = set()

    try:
        with open(resolved_path, "r", encoding="utf-8") as f:
            for line in f:
                # Each line has format "WORD definition..." or just "WORD"
                # Extract just the word part (before the first space)
                if line.strip():
                    word = line.split(" ", 1)[0].lower()
                    # Keep only ASCII alphabetic characters
                    word = "".join(c for c in word if c.isascii() and c.isalpha())
                    if word:
                        words.add(word)
    except FileNotFoundError:
        if not is_default:
            raise FileNotFoundError(f"Dictionary file not found: {resolved_path}")
        print(
            f"Dictionary file not found at {resolved_path}. Using built-in fallback dictionary."
        )
        words = set(_FALLBACK_WORDS)

    _DICTIONARY_CACHE[resolved_path] = words
    return words


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


def can_form_word(word: str, available_letters: Counter[str]) -> bool:
    """
    Check if a word can be formed from the available letters.

    Args:
        word: The word to check.
        available_letters: Counter of available lowercase letters.

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
    max_length = len(letters)

    valid_words: Set[str] = set()
    for word in dictionary:
        if min_length <= len(word) <= max_length and can_form_word(
            word, available_letters
        ):
            valid_words.add(word)

    return valid_words


def add_custom_words(words: Set[str]) -> None:
    """
    Add custom words to the cached default dictionary.

    Args:
        words: Set of words to add.
    """
    dictionary = load_dictionary()
    for word in words:
        dictionary.add(word.lower())


class Dictionary:
    """Dictionary wrapper that loads and validates words."""

    def __init__(
        self,
        path: Optional[Path] = None,
        words: Optional[Iterable[str]] = None,
    ) -> None:
        if words is not None:
            self.words: Set[str] = {
                stripped.lower()
                for w in words
                for stripped in (w.strip(),)
                if stripped and stripped.isascii() and stripped.isalpha()
            }
        else:
            self.words = set(load_dictionary(path))

    def is_valid_word(self, word: str, min_length: int = 1) -> bool:
        """Return True if ``word`` meets ``min_length`` and exists in this dictionary."""
        return len(word) >= min_length and word.lower() in self.words

    def load_dictionary(self, path: Path, force_reload: bool = False) -> None:
        """Reload the dictionary from ``path``."""
        self.words = set(load_dictionary(path, force_reload=force_reload))

    def get_valid_words(self, letters: str, min_length: int = 3) -> Set[str]:
        """Return all dictionary words formable from ``letters`` with length >= ``min_length``."""
        available_letters = Counter(letters.lower())
        max_length = len(letters)
        return {
            word
            for word in self.words
            if min_length <= len(word) <= max_length
            and can_form_word(word, available_letters)
        }
