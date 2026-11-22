"""
Unit tests for the qless_solver.dictionary module.
"""

from collections import Counter
from pathlib import Path

import pytest
from qless_solver.dictionary import (
    Dictionary,
    DictionaryFlag,
    add_custom_words,
    can_form_word,
    get_definition,
    get_definitions,
    get_valid_words,
    is_common_word,
    is_valid_word,
    load_dictionary,
    normalize_dictionary_name,
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


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("aa", "volcanic rock [n]"),  # first line of the file
        ("AA", "volcanic rock [n]"),
        ("zzz", "informal word for sleep [n]"),
        ("gorm", "foolish person [n] / understand [v]"),
        ("context", "circumstances of an event or fact [n]"),
    ],
)
def test_get_definition_direct(word: str, expected: str) -> None:
    assert get_definition(word) == expected


def test_get_definition_resolves_inflections() -> None:
    assert get_definition("aahed") == "form of AAH [v] — exclaim in pleasure [v]"
    assert get_definition("zzzs") == "form of ZZZ [n] — informal word for sleep [n]"
    assert get_definition("cats") == (
        "form of CAT [n] — small domesticated furry mammal [n]"
    )


def test_get_definition_resolves_variants_with_pos_filter() -> None:
    assert get_definition("bunn") == (
        "variant of BUN [n] — small sweet bread roll or cake [n]"
    )
    # DWAM has [n] and [v] senses; DWALM references the noun only.
    assert get_definition("dwalm") == "variant of DWAM [n] — stupor or daydream [n]"


def test_get_definition_multi_hop_keeps_notes_once() -> None:
    assert get_definition("abyed") == (
        "form of ABYE -> variant of ABY (archaic) [v] — pay the penalty for [v]"
    )


def test_get_definition_strips_internal_annotations() -> None:
    defn = get_definition("aborticides")
    assert defn is not None
    assert "not_family" not in defn
    assert defn.startswith("form of ABORTICIDE")


@pytest.mark.parametrize("word", ["notarealwordxyz", "", "123", "ca t", "café"])
def test_get_definition_missing_or_invalid(word: str) -> None:
    assert get_definition(word) is None


def test_get_definitions_batch_dedupes_and_uppercases() -> None:
    result = get_definitions(["gorm", "GORM", "notarealwordxyz"])
    assert result == {
        "GORM": "foolish person [n] / understand [v]",
        "NOTAREALWORDXYZ": None,
    }


def test_dictionary_definitions_from_small_custom_file(tmp_path: Path) -> None:
    custom = tmp_path / "custom.txt"
    # Deliberately unsorted: small files are scanned linearly.
    custom.write_text("DOG loyal pet [n]\nCAT furry pet [n]\nCATS <cat=n> [n]\n")
    wrapper = Dictionary(path=custom)
    assert wrapper.get_definition("cat") == "furry pet [n]"
    assert wrapper.get_definition("cats") == "form of CAT [n] — furry pet [n]"
    assert wrapper.get_definitions(["cat", "dog", "missing"]) == {
        "CAT": "furry pet [n]",
        "DOG": "loyal pet [n]",
        "MISSING": None,
    }


def test_in_memory_dictionary_has_no_definitions() -> None:
    wrapper = Dictionary(words={"cat", "dog"})
    assert wrapper.get_definition("cat") is None


def test_dictionary_definition_requires_word_in_dictionary() -> None:
    wrapper = Dictionary()
    assert wrapper.get_definition("gorm") == "foolish person [n] / understand [v]"
    assert wrapper.get_definition("notarealwordxyz") is None


def test_unified_store_sharing_and_common_dictionary_subset() -> None:
    """Common and full views share one unified store without duplicating RAM."""
    full_dict = Dictionary(mode="full")
    common_dict = Dictionary(mode="common")
    zero_copy_common = full_dict.with_mode("common")

    assert full_dict._store is common_dict._store
    assert full_dict._store is zero_copy_common._store
    assert full_dict.required_mask == int(DictionaryFlag.FULL)
    assert common_dict.required_mask == int(DictionaryFlag.COMMON)

    assert 20_000 <= len(common_dict) <= 50_000
    assert len(common_dict) < len(full_dict)

    for everyday in ("comet", "prong", "next", "context", "apple"):
        assert common_dict.is_valid_word(everyday)
        assert full_dict.is_valid_word(everyday)
        assert full_dict.is_common_word(everyday)
        assert is_common_word(everyday)

    for obscure in ("gorm", "aa", "dwalm", "mong"):
        assert full_dict.is_valid_word(obscure)
        assert not common_dict.is_valid_word(obscure)
        assert not full_dict.is_common_word(obscure)
        assert not is_common_word(obscure)

    assert is_valid_word("gorm", mode="full") is True
    assert is_valid_word("gorm", mode="common") is False
    assert "gorm" in get_valid_words("rmtoepngtnxc", mode="full")
    assert "gorm" not in get_valid_words("rmtoepngtnxc", mode="common")
    assert "comet" in get_valid_words("rmtoepngtnxc", mode="common")


def test_definitions_work_across_dictionary_modes() -> None:
    """Disk-backed definition lookup works in both common and full modes."""
    full_dict = Dictionary(mode="full")
    common_dict = full_dict.with_mode("common")

    assert common_dict.get_definition("comet") is not None
    assert full_dict.get_definition("comet") == common_dict.get_definition("comet")
    assert common_dict.get_definition("gorm") is None
    assert full_dict.get_definition("gorm") == "foolish person [n] / understand [v]"


def test_dictionary_mode_validation_and_in_memory_common_words() -> None:
    """Invalid dictionary modes raise ValueError; in-memory common_words filters flags."""
    with pytest.raises(ValueError, match="Unknown dictionary"):
        normalize_dictionary_name("oxford")
    with pytest.raises(ValueError, match="Unknown dictionary"):
        Dictionary(mode="oxford")  # type: ignore[arg-type]

    mem = Dictionary(
        words=["cat", "gorm", "dog"],
        common_words=["cat", "extra_not_in_full"],
        mode="full",
    )
    assert mem.words == {"cat", "gorm", "dog"}
    assert mem.is_common_word("cat") is True
    assert mem.is_common_word("gorm") is False
    assert mem.is_common_word("extra_not_in_full") is False
    assert mem.has_uncommon_words() is True

    mem_common = mem.with_mode("common")
    assert mem_common._store is mem._store
    assert mem_common.words == {"cat"}
    assert mem_common.get_valid_words("catgorm") == {"cat"}
    assert mem_common.has_uncommon_words() is False


if __name__ == "__main__":
    pytest.main()
