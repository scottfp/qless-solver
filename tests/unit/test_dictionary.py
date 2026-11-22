"""
Unit tests for the qless_solver.dictionary module.
"""

from collections import Counter
from pathlib import Path

import pytest
from qless_solver.dictionary import (
    Dictionary,
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


def test_load_custom_dictionary_not_polluted_by_default_cache(tmp_path: Path) -> None:
    """Loading a custom dictionary path must not return the cached default set."""
    default_dict = load_dictionary()
    assert "eat" in default_dict

    custom_file = tmp_path / "custom_words.txt"
    custom_file.write_text("ALPHA first\nBETA second\n", encoding="utf-8")

    custom_dict = load_dictionary(custom_file)
    assert custom_dict == {"alpha", "beta"}
    assert "eat" not in custom_dict
    # Default cache remains intact
    assert "eat" in load_dictionary()


def test_load_dictionary_force_reload(tmp_path: Path) -> None:
    """force_reload=True refreshes a previously cached custom dictionary."""
    custom_file = tmp_path / "reload_words.txt"
    custom_file.write_text("ONE\nTWO\n", encoding="utf-8")

    first = load_dictionary(custom_file)
    assert first == {"one", "two"}

    custom_file.write_text("ONE\nTHREE\n", encoding="utf-8")
    assert load_dictionary(custom_file) == {"one", "two"}

    reloaded = load_dictionary(custom_file, force_reload=True)
    assert reloaded == {"one", "three"}

    wrapper = Dictionary(path=custom_file)
    assert wrapper.is_valid_word("three")
    custom_file.write_text("FOUR\n", encoding="utf-8")
    wrapper.load_dictionary(custom_file, force_reload=True)
    assert wrapper.words == {"four"}


def test_load_missing_custom_dictionary_raises(tmp_path: Path) -> None:
    """Providing an explicit missing path raises FileNotFoundError."""
    missing = tmp_path / "does_not_exist.txt"
    with pytest.raises(FileNotFoundError):
        load_dictionary(missing)


def test_dictionary_in_memory_and_valid_words() -> None:
    """Dictionary(words=...) normalizes input and filters candidate words cleanly."""
    d = Dictionary(words=[" Cat ", "AT", "Cats", "cater", "123", "café", ""])
    assert d.words == {"cat", "at", "cats", "cater"}
    assert d.is_valid_word("CAT") is True
    assert d.is_valid_word("at", min_length=2) is True
    assert d.is_valid_word("at", min_length=3) is False

    # Respects multiplicities ("cats" only once, "cater" missing 'e'/'r', "at" < 3)
    assert d.get_valid_words("cats", min_length=3) == {"cat", "cats"}
    assert d.get_valid_words("cat", min_length=2) == {"at", "cat"}


def test_bitmask_index_invalidated_on_reload_and_custom_words(tmp_path: Path) -> None:
    """Bitmask-indexed get_valid_words refreshes on force_reload and add_custom_words."""
    custom_file = tmp_path / "idx_words.txt"
    custom_file.write_text("ZAP\n", encoding="utf-8")

    # Warm both caches for custom_file
    assert get_valid_words("zapzip", min_length=3, dictionary_path=custom_file) == {
        "zap"
    }

    custom_file.write_text("ZAP\nZIP\n", encoding="utf-8")
    # Without reload, cached index still has only "zap"
    assert get_valid_words("zapzip", min_length=3, dictionary_path=custom_file) == {
        "zap"
    }

    # Reload via load_dictionary(force_reload=True) invalidates the index cache
    load_dictionary(custom_file, force_reload=True)
    assert get_valid_words("zapzip", min_length=3, dictionary_path=custom_file) == {
        "zap",
        "zip",
    }

    # add_custom_words invalidates the default index cache
    assert "qqqqq" not in get_valid_words("qqqqq", min_length=3)
    add_custom_words({"qqqqq"})
    assert "qqqqq" in get_valid_words("qqqqq", min_length=3)


def test_qless_dictionary_path_env_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QLESS_DICTIONARY_PATH overrides default dictionary lookup cleanly."""
    env_dict = tmp_path / "env_words.txt"
    env_dict.write_text("MANGO\nPLUM\n", encoding="utf-8")

    monkeypatch.setenv("QLESS_DICTIONARY_PATH", str(env_dict))
    loaded = load_dictionary()
    assert loaded == {"mango", "plum"}

    wrapper = Dictionary()
    assert wrapper.words == {"mango", "plum"}
    assert wrapper.get_valid_words("mangos", min_length=3) == {"mango"}

    # After monkeypatch cleans up, default dictionary lookup still works
    monkeypatch.delenv("QLESS_DICTIONARY_PATH")
    assert "eat" in load_dictionary()


if __name__ == "__main__":
    pytest.main()
