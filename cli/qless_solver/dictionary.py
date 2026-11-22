"""
Dictionary module for the qless-solver.
Provides a unified bitmask word index across multiple dictionary tiers,
word validation helpers, and zero-RAM disk-backed definition lookup.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from collections.abc import Set as AbstractSet
from enum import IntFlag
from pathlib import Path
from typing import Dict, Iterable, Iterator, Literal, Optional, Set, Tuple


class DictionaryFlag(IntFlag):
    """Per-word dictionary membership bitflags."""

    FULL = 1 << 0
    COMMON = 1 << 1


DictionaryName = Literal["common", "full"]
AVAILABLE_DICTIONARIES: Tuple[DictionaryName, ...] = ("common", "full")
DEFAULT_DICTIONARY_NAME: DictionaryName = "full"
DICTIONARY_MODE_FLAGS: Dict[DictionaryName, DictionaryFlag] = {
    "common": DictionaryFlag.COMMON,
    "full": DictionaryFlag.FULL,
}

# (letter_mask, word_len, dict_mask, word)
WordIndexEntry = Tuple[int, int, int, str]
WordIndex = Tuple[WordIndexEntry, ...]

DEFAULT_DICTIONARY_PATH = (
    Path(__file__).parent.parent.parent / "dictionary.txt"
).resolve()
DEFAULT_COMMON_DICTIONARY_PATH = (
    Path(__file__).parent.parent.parent / "common_words.txt"
).resolve()


def normalize_dictionary_name(name: str) -> DictionaryName:
    """Validate and normalize a dictionary mode name."""
    cleaned = name.strip().lower()
    if cleaned == "common":
        return "common"
    if cleaned == "full":
        return "full"
    valid = ", ".join(AVAILABLE_DICTIONARIES)
    raise ValueError(f"Unknown dictionary '{name}'. Expected one of: {valid}.")


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


def _resolve_default_common_dictionary_path(
    base_dict_path: Optional[Path] = None,
) -> Optional[Path]:
    """Resolve the curated common word list path when available."""
    env_path = os.environ.get("QLESS_COMMON_DICTIONARY_PATH", "").strip()
    is_custom_base = (
        base_dict_path is not None and base_dict_path != DEFAULT_DICTIONARY_PATH
    )
    if env_path and (
        not is_custom_base or base_dict_path == _resolve_default_dictionary_path()
    ):
        return Path(env_path).resolve()
    if is_custom_base:
        assert base_dict_path is not None
        sibling = base_dict_path.with_name("common_words.txt")
        return sibling if sibling.is_file() else None
    if DEFAULT_COMMON_DICTIONARY_PATH.is_file():
        return DEFAULT_COMMON_DICTIONARY_PATH
    cwd_candidate = (Path.cwd() / "common_words.txt").resolve()
    if cwd_candidate.is_file():
        return cwd_candidate
    return None


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


def _normalize_ascii_word(raw_token: str) -> str:
    lowered = raw_token.strip().lower()
    if not lowered:
        return ""
    return "".join(c for c in lowered if c.isascii() and c.isalpha())


def _build_word_index(word_flags: Dict[str, int]) -> WordIndex:
    return tuple(
        (_word_mask(word), len(word), dict_mask, word)
        for word, dict_mask in word_flags.items()
        if word and word.isascii() and word.isalpha()
    )


def _filter_index(
    index: WordIndex,
    letters: str,
    min_length: int,
    required_mask: int = int(DictionaryFlag.FULL),
) -> Set[str]:
    letters_lower = letters.lower()
    if not letters_lower or not letters_lower.isascii() or not letters_lower.isalpha():
        return set()

    available_letters = Counter(letters_lower)
    available_mask = _word_mask(letters_lower)
    disallowed_mask = ~available_mask
    max_length = len(letters_lower)

    valid_words: Set[str] = set()
    for mask, word_len, dict_mask, word in index:
        if (
            word_len < min_length
            or word_len > max_length
            or not (dict_mask & required_mask)
            or (mask & disallowed_mask)
        ):
            continue
        if all(word.count(ch) <= available_letters[ch] for ch in set(word)):
            valid_words.add(word)
    return valid_words


class _UnifiedWordStore:
    """Single shared word-flag mapping and bitmask index across dictionary modes."""

    __slots__ = (
        "source_path",
        "common_path",
        "word_flags",
        "index",
        "indexed_word_count",
        "flag_counts",
    )

    def __init__(
        self,
        source_path: Optional[Path],
        common_path: Optional[Path],
        word_flags: Dict[str, int],
    ) -> None:
        self.source_path = source_path
        self.common_path = common_path
        self.word_flags = word_flags
        self.index: Optional[WordIndex] = None
        self.indexed_word_count: int = -1
        self.flag_counts: Dict[int, int] = {}
        self.recompute_flag_counts()

    def recompute_flag_counts(self) -> None:
        """Recompute cached word counts for each dictionary bitflag."""
        full_flag = int(DictionaryFlag.FULL)
        common_flag = int(DictionaryFlag.COMMON)
        full_count = 0
        common_count = 0
        for flags in self.word_flags.values():
            if flags & full_flag:
                full_count += 1
            if flags & common_flag:
                common_count += 1
        self.flag_counts = {
            full_flag: full_count,
            common_flag: common_count,
        }

    def count_for_mask(self, required_mask: int) -> int:
        """Return the number of words matching ``required_mask``."""
        cached = self.flag_counts.get(required_mask)
        if cached is not None:
            return cached
        count = sum(1 for flags in self.word_flags.values() if flags & required_mask)
        self.flag_counts[required_mask] = count
        return count

    def get_index(self) -> WordIndex:
        """Return the cached bitmask index, building it lazily on first use."""
        if self.index is None or self.indexed_word_count != len(self.word_flags):
            self.index = _build_word_index(self.word_flags)
            self.indexed_word_count = len(self.word_flags)
        return self.index


# Global cache of unified stores keyed by (resolved_dict_path, resolved_common_path)
_UNIFIED_STORE_CACHE: Dict[Tuple[Path, Optional[Path]], _UnifiedWordStore] = {}


def _load_word_flags_from_disk(
    resolved_path: Path,
    resolved_common_path: Optional[Path],
    *,
    explicit_path: bool,
    explicit_common_path: bool,
) -> _UnifiedWordStore:
    full_flag = int(DictionaryFlag.FULL)
    common_flag = int(DictionaryFlag.COMMON)
    word_flags: Dict[str, int] = {}
    used_fallback = False

    try:
        with open(resolved_path, "r", encoding="utf-8") as f:
            for line in f:
                # Each line has format "WORD definition..." or just "WORD"
                if line.strip():
                    word = _normalize_ascii_word(line.split(" ", 1)[0])
                    if word:
                        word_flags[word] = full_flag
    except FileNotFoundError:
        if explicit_path:
            raise FileNotFoundError(f"Dictionary file not found: {resolved_path}")
        print(
            f"Dictionary file not found at {resolved_path}. "
            "Using built-in fallback dictionary."
        )
        used_fallback = True
        word_flags = {word: (full_flag | common_flag) for word in _FALLBACK_WORDS}

    if not used_fallback:
        if resolved_common_path is None:
            # No separate common word list available: treat all loaded words as common.
            for word in word_flags:
                word_flags[word] |= common_flag
        else:
            try:
                with open(resolved_common_path, "r", encoding="utf-8") as cf:
                    for line in cf:
                        if line.strip():
                            word = _normalize_ascii_word(line.split(" ", 1)[0])
                            if word and word in word_flags:
                                word_flags[word] |= common_flag
            except FileNotFoundError:
                if explicit_common_path:
                    raise FileNotFoundError(
                        f"Common dictionary file not found: {resolved_common_path}"
                    )
                for word in word_flags:
                    word_flags[word] |= common_flag

    return _UnifiedWordStore(
        source_path=None if used_fallback else resolved_path,
        common_path=None if used_fallback else resolved_common_path,
        word_flags=word_flags,
    )


def _resolve_store_paths(
    dictionary_path: Optional[Path] = None,
    common_path: Optional[Path] = None,
) -> Tuple[Path, Optional[Path]]:
    resolved_path = (
        _resolve_default_dictionary_path()
        if dictionary_path is None
        else Path(dictionary_path).resolve()
    )
    resolved_common_path = (
        _resolve_default_common_dictionary_path(resolved_path)
        if common_path is None
        else Path(common_path).resolve()
    )
    return resolved_path, resolved_common_path


def _get_unified_store(
    dictionary_path: Optional[Path] = None,
    common_path: Optional[Path] = None,
    *,
    force_reload: bool = False,
) -> _UnifiedWordStore:
    resolved_path, resolved_common_path = _resolve_store_paths(
        dictionary_path, common_path
    )
    cache_key = (resolved_path, resolved_common_path)

    if force_reload:
        for key in [k for k in _UNIFIED_STORE_CACHE if k[0] == resolved_path]:
            if common_path is None or key == cache_key:
                _UNIFIED_STORE_CACHE.pop(key, None)
    elif cache_key in _UNIFIED_STORE_CACHE:
        return _UNIFIED_STORE_CACHE[cache_key]

    store = _load_word_flags_from_disk(
        resolved_path,
        resolved_common_path,
        explicit_path=(dictionary_path is not None),
        explicit_common_path=(common_path is not None),
    )
    _UNIFIED_STORE_CACHE[cache_key] = store
    return store


class _DictionaryWordView(AbstractSet[str]):
    """Zero-copy read-only ``Set`` view over a unified store for a given bitmask."""

    def __init__(self, store: _UnifiedWordStore, required_mask: int) -> None:
        self._store = store
        self._required_mask = required_mask

    def __contains__(self, item: object) -> bool:
        if not isinstance(item, str):
            return False
        return bool(self._store.word_flags.get(item, 0) & self._required_mask)

    def __iter__(self) -> Iterator[str]:
        required_mask = self._required_mask
        return (
            word
            for word, flags in self._store.word_flags.items()
            if flags & required_mask
        )

    def __len__(self) -> int:
        return self._store.count_for_mask(self._required_mask)


def load_dictionary(
    dictionary_path: Optional[Path] = None,
    force_reload: bool = False,
    mode: DictionaryName = DEFAULT_DICTIONARY_NAME,
    common_path: Optional[Path] = None,
) -> Set[str]:
    """
    Load a dictionary of valid words for the requested mode.

    Args:
        dictionary_path: Path to the full dictionary file. Defaults to ``dictionary.txt``.
        force_reload: If True, bypass the cache and reload from disk.
        mode: Dictionary mode (``"full"`` or ``"common"``).
        common_path: Optional path to the curated common word list.

    Returns:
        A set of valid lowercase words for the selected mode.
    """
    normalized_mode = normalize_dictionary_name(mode)
    required_mask = int(DICTIONARY_MODE_FLAGS[normalized_mode])
    store = _get_unified_store(
        dictionary_path=dictionary_path,
        common_path=common_path,
        force_reload=force_reload,
    )
    return {word for word, flags in store.word_flags.items() if flags & required_mask}


def is_valid_word(
    word: str,
    min_length: int = 3,
    mode: DictionaryName = DEFAULT_DICTIONARY_NAME,
) -> bool:
    """
    Check if a word is valid in the default dictionary for ``mode``.

    Args:
        word: The word to check.
        min_length: Minimum word length.
        mode: Dictionary mode (``"full"`` or ``"common"``).

    Returns:
        True if the word is valid, False otherwise.
    """
    if len(word) < min_length:
        return False
    normalized_mode = normalize_dictionary_name(mode)
    required_mask = int(DICTIONARY_MODE_FLAGS[normalized_mode])
    store = _get_unified_store()
    return bool(store.word_flags.get(word.lower(), 0) & required_mask)


def is_common_word(word: str) -> bool:
    """Return True if ``word`` belongs to the curated common word list."""
    if not word:
        return False
    store = _get_unified_store()
    return bool(store.word_flags.get(word.lower(), 0) & int(DictionaryFlag.COMMON))


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
    mode: DictionaryName = DEFAULT_DICTIONARY_NAME,
    common_path: Optional[Path] = None,
) -> Set[str]:
    """
    Get all valid words that can be formed from the given letters.

    Args:
        letters: String of available letters.
        min_length: Minimum word length.
        dictionary_path: Path to the dictionary file.
        mode: Dictionary mode (``"full"`` or ``"common"``).
        common_path: Optional path to the curated common word list.

    Returns:
        Set of valid words that can be formed.
    """
    normalized_mode = normalize_dictionary_name(mode)
    required_mask = int(DICTIONARY_MODE_FLAGS[normalized_mode])
    store = _get_unified_store(
        dictionary_path=dictionary_path,
        common_path=common_path,
    )
    return _filter_index(store.get_index(), letters, min_length, required_mask)


def add_custom_words(words: Set[str]) -> None:
    """
    Add custom words to the cached default unified dictionary store.

    Args:
        words: Set of words to add.
    """
    store = _get_unified_store()
    both_flags = int(DictionaryFlag.FULL | DictionaryFlag.COMMON)
    changed = False
    for raw_word in words:
        word = _normalize_ascii_word(raw_word)
        if word:
            if store.word_flags.get(word) != both_flags:
                store.word_flags[word] = both_flags
                changed = True
    if changed:
        store.index = None
        store.indexed_word_count = -1
        store.recompute_flag_counts()


# ---------------------------------------------------------------------------
# Definition lookup (zero extra RAM: binary search over the sorted file on disk)
# ---------------------------------------------------------------------------

# Matches cross-reference entries such as ``<aah=v> [v]``, ``{bun=n} [n]`` or
# ``<abye=v> (archaic) [v]``.
_REF_RE = re.compile(
    r"^([<{])([A-Za-z]+)(?:=([A-Za-z]+))?[>}]"
    r"(?:\s*(\([^)]+\)))?\s*(\[[A-Za-z]+\])?$"
)
_SMALL_FILE_THRESHOLD = 65536


def _clean_definition_text(raw_def: str) -> str:
    """Strip internal annotations (e.g. ``(not_family)``) and normalize whitespace."""
    return " ".join(raw_def.replace("(not_family)", "").split())


def _select_matching_pos_senses(raw_def: str, target_pos: Optional[str]) -> str:
    """Keep only the senses of ``raw_def`` whose part-of-speech tag matches."""
    cleaned = _clean_definition_text(raw_def)
    if not target_pos or " / " not in cleaned:
        return cleaned
    tag = f"[{target_pos}]"
    matching = [s for s in cleaned.split(" / ") if s.strip().endswith(tag)]
    return " / ".join(matching) if matching else cleaned


def _parse_line(raw: bytes) -> Tuple[bytes, str]:
    line = raw.rstrip(b"\r\n")
    word_bytes, _sep, rest = line.partition(b" ")
    return word_bytes.upper(), rest.decode("utf-8", errors="replace").strip()


def _binary_search_raw_definition(dict_path: Path, target_upper: str) -> Optional[str]:
    """Find the raw definition text for ``target_upper`` in a sorted dictionary file.

    Large files are binary searched by byte offset so nothing is loaded into
    memory. Small files (e.g. custom test dictionaries) are scanned linearly
    and need not be sorted.
    """
    target = target_upper.encode("ascii", errors="ignore")
    if not target or not dict_path.is_file():
        return None

    with open(dict_path, "rb") as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        if file_size == 0:
            return None

        if file_size <= _SMALL_FILE_THRESHOLD:
            f.seek(0)
            for raw in f:
                word, rest = _parse_line(raw)
                if word == target:
                    return rest
            return None

        # Invariant: ``lo`` is always the start of a line; the target (if
        # present) starts at a line whose offset is in [lo, hi).
        lo, hi = 0, file_size
        while lo < hi:
            mid = (lo + hi) // 2
            f.seek(mid)
            if mid > 0:
                f.readline()  # skip the partial line
            line_start = f.tell()

            if line_start >= hi:
                # No full line starts in (mid, hi): scan linearly from lo.
                f.seek(lo)
                while f.tell() < hi:
                    raw = f.readline()
                    if not raw:
                        break
                    word, rest = _parse_line(raw)
                    if word == target:
                        return rest
                    if word > target:
                        return None
                return None

            raw = f.readline()
            if not raw:
                hi = mid
                continue
            word, rest = _parse_line(raw)
            if word == target:
                return rest
            if word < target:
                lo = f.tell()
            else:
                hi = line_start
    return None


def lookup_raw_definition(
    word: str, dictionary_path: Optional[str | Path] = None
) -> Optional[str]:
    """Return the unprocessed definition text for ``word``, or None if absent."""
    word = word.strip()
    if not word or not word.isascii() or not word.isalpha():
        return None
    resolved = (
        Path(dictionary_path).expanduser().resolve()
        if dictionary_path is not None
        else _resolve_default_dictionary_path()
    )
    return _binary_search_raw_definition(resolved, word.upper())


def get_definition(
    word: str,
    dictionary_path: Optional[str | Path] = None,
    max_depth: int = 3,
) -> Optional[str]:
    """Return a human-readable definition for ``word``.

    Cross-references are resolved: ``<base=pos>`` becomes ``form of BASE`` and
    ``{base=pos}`` becomes ``variant of BASE``, followed by the base word's
    meaning (filtered to the referenced part of speech).
    """
    raw = lookup_raw_definition(word, dictionary_path)
    if raw is None:
        return None

    current_raw = raw
    prefix_chain: list[str] = []
    notes: list[str] = []
    target_pos: Optional[str] = None
    leaf_pos: Optional[str] = None

    def _header() -> str:
        note_str = f" {' '.join(notes)}" if notes else ""
        pos_str = f" {leaf_pos}" if leaf_pos else ""
        return f"{' -> '.join(prefix_chain)}{note_str}{pos_str}"

    for _ in range(max_depth):
        match = _REF_RE.match(_clean_definition_text(current_raw))
        if not match:
            break
        bracket, base_word, ref_pos, note, pos_tag = match.groups()
        if leaf_pos is None and pos_tag:
            leaf_pos = pos_tag
        if note and note not in notes:
            notes.append(note)
        rel = "form of" if bracket == "<" else "variant of"
        prefix_chain.append(f"{rel} {base_word.upper()}")
        target_pos = ref_pos
        next_raw = lookup_raw_definition(base_word, dictionary_path)
        if next_raw is None:
            return _header()
        current_raw = next_raw

    if not prefix_chain:
        return _clean_definition_text(current_raw)

    base_meaning = _select_matching_pos_senses(current_raw, target_pos)
    if _REF_RE.match(base_meaning):
        # Chain deeper than max_depth; report what was resolved.
        return _header()
    for note in notes:
        # Avoid repeating notes (e.g. "(archaic)") already shown in the header.
        base_meaning = " ".join(base_meaning.replace(note, "").split())
    return f"{_header()} — {base_meaning}"


def get_definitions(
    words: Iterable[str], dictionary_path: Optional[str | Path] = None
) -> Dict[str, Optional[str]]:
    """Batch :func:`get_definition`, keyed by uppercase word."""
    result: Dict[str, Optional[str]] = {}
    for w in words:
        key = w.strip().upper()
        if key not in result:
            result[key] = get_definition(key, dictionary_path=dictionary_path)
    return result


def _strict_ascii_alpha(raw_word: str) -> str:
    stripped = raw_word.strip().lower()
    if stripped and stripped.isascii() and stripped.isalpha():
        return stripped
    return ""


class Dictionary:
    """Zero-copy dictionary view backed by a unified bitmask word store."""

    def __init__(
        self,
        path: Optional[Path] = None,
        words: Optional[Iterable[str]] = None,
        *,
        mode: DictionaryName = DEFAULT_DICTIONARY_NAME,
        common_path: Optional[Path] = None,
        common_words: Optional[Iterable[str]] = None,
        _store: Optional[_UnifiedWordStore] = None,
    ) -> None:
        self._mode: DictionaryName = normalize_dictionary_name(mode)
        self._required_mask: int = int(DICTIONARY_MODE_FLAGS[self._mode])

        if _store is not None:
            self._store = _store
        elif words is not None:
            full_flag = int(DictionaryFlag.FULL)
            common_flag = int(DictionaryFlag.COMMON)
            base_flags = (
                full_flag if common_words is not None else (full_flag | common_flag)
            )
            word_flags: Dict[str, int] = {}
            for raw_word in words:
                cleaned = _strict_ascii_alpha(raw_word)
                if cleaned:
                    word_flags[cleaned] = base_flags
            if common_words is not None:
                for raw_common in common_words:
                    cleaned = _strict_ascii_alpha(raw_common)
                    if cleaned and cleaned in word_flags:
                        word_flags[cleaned] |= common_flag
            self._store = _UnifiedWordStore(
                source_path=None,
                common_path=None,
                word_flags=word_flags,
            )
        else:
            self._store = _get_unified_store(
                dictionary_path=path,
                common_path=common_path,
            )

        self._words_view: _DictionaryWordView = _DictionaryWordView(
            self._store, self._required_mask
        )

    @property
    def mode(self) -> DictionaryName:
        """Return the active dictionary mode (``"common"`` or ``"full"``)."""
        return self._mode

    @property
    def required_mask(self) -> int:
        """Return the bitmask required for word membership in this view."""
        return self._required_mask

    @property
    def words(self) -> AbstractSet[str]:
        """Return a zero-copy read-only ``Set`` view of words in the active mode."""
        return self._words_view

    def __len__(self) -> int:
        return len(self._words_view)

    def with_mode(self, mode: DictionaryName) -> Dictionary:
        """Return a zero-copy ``Dictionary`` view sharing the same underlying store."""
        normalized = normalize_dictionary_name(mode)
        if normalized == self._mode:
            return self
        return Dictionary(mode=normalized, _store=self._store)

    def is_valid_word(self, word: str, min_length: int = 1) -> bool:
        """Return True if ``word`` meets ``min_length`` and matches this view's bitmask."""
        if len(word) < min_length:
            return False
        return bool(self._store.word_flags.get(word.lower(), 0) & self._required_mask)

    def is_common_word(self, word: str) -> bool:
        """Return True if ``word`` carries the ``COMMON`` bitflag in this store."""
        if not word:
            return False
        return bool(
            self._store.word_flags.get(word.lower(), 0) & int(DictionaryFlag.COMMON)
        )

    def has_uncommon_words(self) -> bool:
        """Return True when this full view includes words outside the common subset."""
        return self._required_mask == int(
            DictionaryFlag.FULL
        ) and self._store.count_for_mask(
            int(DictionaryFlag.FULL)
        ) > self._store.count_for_mask(
            int(DictionaryFlag.COMMON)
        )

    def load_dictionary(
        self,
        path: Path,
        force_reload: bool = False,
        common_path: Optional[Path] = None,
    ) -> None:
        """Reload the underlying unified store from ``path``."""
        self._store = _get_unified_store(
            dictionary_path=path,
            common_path=common_path,
            force_reload=force_reload,
        )
        self._words_view = _DictionaryWordView(self._store, self._required_mask)

    def get_valid_words(
        self,
        letters: str,
        min_length: int = 3,
        *,
        required_mask: Optional[int] = None,
    ) -> Set[str]:
        """Return all dictionary words formable from ``letters`` with length >= ``min_length``."""
        mask = self._required_mask if required_mask is None else required_mask
        return _filter_index(self._store.get_index(), letters, min_length, mask)

    def get_definition(self, word: str) -> Optional[str]:
        """Return the definition of ``word`` from this store's source file.

        In-memory dictionaries (built from ``words=``) have no definitions.
        """
        cleaned = word.strip().lower()
        if (
            not cleaned
            or not self.is_valid_word(cleaned, min_length=1)
            or self._store.source_path is None
        ):
            return None
        return get_definition(cleaned, dictionary_path=self._store.source_path)

    def get_definitions(self, words: Iterable[str]) -> Dict[str, Optional[str]]:
        """Batch :meth:`get_definition`, keyed by uppercase word."""
        result: Dict[str, Optional[str]] = {}
        for w in words:
            key = w.strip().upper()
            if key not in result:
                result[key] = self.get_definition(key)
        return result


__all__ = [
    "AVAILABLE_DICTIONARIES",
    "DEFAULT_COMMON_DICTIONARY_PATH",
    "DEFAULT_DICTIONARY_NAME",
    "DEFAULT_DICTIONARY_PATH",
    "DICTIONARY_MODE_FLAGS",
    "Dictionary",
    "DictionaryFlag",
    "DictionaryName",
    "WordIndex",
    "WordIndexEntry",
    "add_custom_words",
    "can_form_word",
    "get_definition",
    "get_definitions",
    "get_valid_words",
    "is_common_word",
    "is_valid_word",
    "load_dictionary",
    "lookup_raw_definition",
    "normalize_dictionary_name",
]
