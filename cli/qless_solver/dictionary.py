"""
Dictionary module for the qless-solver.
Provides functions for validating words and finding valid words.
"""

import os
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Tuple

WordIndexEntry = Tuple[int, int, str]
WordIndex = Tuple[WordIndexEntry, ...]

DEFAULT_DICTIONARY_PATH = (
    Path(__file__).parent.parent.parent / "dictionary.txt"
).resolve()


def _resolve_default_dictionary_path() -> Path:
    """Resolve the default dictionary path across local, installed, and container layouts."""
    env_path = os.environ.get("QLESS_DICTIONARY_PATH", "").strip()
    if env_path:
        return Path(env_path).resolve()
    if DEFAULT_DICTIONARY_PATH.exists():
        return DEFAULT_DICTIONARY_PATH
    cwd_candidate = (Path.cwd() / "dictionary.txt").resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return DEFAULT_DICTIONARY_PATH


# Global cache for dictionaries and precomputed bitmask indices keyed by resolved path
_DICTIONARY_CACHE: Dict[Path, Set[str]] = {}
_DICTIONARY_INDEX_CACHE: Dict[Path, WordIndex] = {}

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


def _word_mask(word: str) -> int:
    mask = 0
    for ch in word:
        mask |= 1 << (ord(ch) - 97)
    return mask


def _build_word_index(words: Iterable[str]) -> WordIndex:
    return tuple(
        (_word_mask(word), len(word), word)
        for word in words
        if word and word.isascii() and word.isalpha()
    )


def _filter_index(index: WordIndex, letters: str, min_length: int) -> Set[str]:
    letters_lower = letters.lower()
    if not letters_lower or not letters_lower.isascii() or not letters_lower.isalpha():
        return set()

    available_letters = Counter(letters_lower)
    available_mask = _word_mask(letters_lower)
    disallowed_mask = ~available_mask
    max_length = len(letters_lower)

    valid_words: Set[str] = set()
    for mask, word_len, word in index:
        if word_len < min_length or word_len > max_length or (mask & disallowed_mask):
            continue
        if all(word.count(ch) <= available_letters[ch] for ch in set(word)):
            valid_words.add(word)
    return valid_words


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
        _resolve_default_dictionary_path()
        if dictionary_path is None
        else Path(dictionary_path).resolve()
    )

    if force_reload:
        _DICTIONARY_INDEX_CACHE.pop(resolved_path, None)
    elif resolved_path in _DICTIONARY_CACHE:
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


def _get_cached_index(dictionary_path: Optional[Path] = None) -> WordIndex:
    resolved_path = (
        _resolve_default_dictionary_path()
        if dictionary_path is None
        else Path(dictionary_path).resolve()
    )
    dictionary = load_dictionary(dictionary_path)
    index = _DICTIONARY_INDEX_CACHE.get(resolved_path)
    if index is None or len(index) != len(dictionary):
        index = _build_word_index(dictionary)
        _DICTIONARY_INDEX_CACHE[resolved_path] = index
    return index


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
    index = _get_cached_index(dictionary_path)
    return _filter_index(index, letters, min_length)


def add_custom_words(words: Set[str]) -> None:
    """
    Add custom words to the cached default dictionary.

    Args:
        words: Set of words to add.
    """
    dictionary = load_dictionary()
    for word in words:
        dictionary.add(word.lower())
    _DICTIONARY_INDEX_CACHE.pop(_resolve_default_dictionary_path(), None)


class Dictionary:
    """Dictionary wrapper that loads and validates words."""

    def __init__(
        self,
        path: Optional[Path] = None,
        words: Optional[Iterable[str]] = None,
    ) -> None:
        self._source_path: Optional[Path] = None
        self._word_index: Optional[WordIndex] = None
        self._indexed_word_count: int = -1

        if words is not None:
            self.words: Set[str] = {
                stripped.lower()
                for w in words
                for stripped in (w.strip(),)
                if stripped and stripped.isascii() and stripped.isalpha()
            }
        else:
            self._source_path = (
                _resolve_default_dictionary_path()
                if path is None
                else Path(path).resolve()
            )
            self.words = set(load_dictionary(path))

    def is_valid_word(self, word: str, min_length: int = 1) -> bool:
        """Return True if ``word`` meets ``min_length`` and exists in this dictionary."""
        return len(word) >= min_length and word.lower() in self.words

    def load_dictionary(self, path: Path, force_reload: bool = False) -> None:
        """Reload the dictionary from ``path``."""
        self._source_path = Path(path).resolve()
        self._word_index = None
        self._indexed_word_count = -1
        self.words = set(load_dictionary(path, force_reload=force_reload))

    def _get_index(self) -> WordIndex:
        if self._source_path is not None:
            cached_words = _DICTIONARY_CACHE.get(self._source_path)
            if cached_words is not None and len(cached_words) == len(self.words):
                return _get_cached_index(self._source_path)
        if self._word_index is None or self._indexed_word_count != len(self.words):
            self._word_index = _build_word_index(self.words)
            self._indexed_word_count = len(self.words)
        return self._word_index

    def get_valid_words(self, letters: str, min_length: int = 3) -> Set[str]:
        """Return all dictionary words formable from ``letters`` with length >= ``min_length``."""
        return _filter_index(self._get_index(), letters, min_length)
