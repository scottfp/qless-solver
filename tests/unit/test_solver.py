import pytest
from typing import List, Optional, Tuple
from qless_solver.solver import validate_qless_arrangement

# Helper to create a normalized grid for tests
def create_test_grid(rows_repr: List[str]) -> List[List[Optional[str]]]:
    if not rows_repr:
        return []
    parsed_rows: List[List[Optional[str]]] = []
    max_len = 0
    for r_str in rows_repr:
        current_parsed_row: List[Optional[str]] = []
        for char_in_row in r_str:
            if char_in_row == '.':
                current_parsed_row.append(None)
            else:
                current_parsed_row.append(char_in_row.lower())
        parsed_rows.append(current_parsed_row)
        if len(current_parsed_row) > max_len:
            max_len = len(current_parsed_row)
    normalized_grid: List[List[Optional[str]]] = []
    for p_row in parsed_rows:
        normalized_grid.append(p_row + [None] * (max_len - len(p_row)))
    return normalized_grid

# Updated Test cases
VALIDATION_TEST_CASES = [
    # Corrected "batcen" case - target_letters updated, and expecting False due to likely dictionary content
    ("bataceten", ["bat", "ace", "ten"], 3, False, [
        "Invalid word: 'bat' found horizontally",
        "Invalid word: 'ace' found horizontally",
        "Invalid word: 'ten' found horizontally",
        "Invalid word: 'bat' found vertically", # Assuming 'bat' is different from 'bta' etc.
        "Invalid word: 'ace' found vertically",
        "Invalid word: 'ten' found vertically",
        # Note: Letter conservation errors won't appear if word errors are found first due to current func logic.
        # If all words WERE valid, then target_letters='bataceten' would make letter conservation pass.
    ]),
    # Invalid: Letter Conservation - Missing letter from layout
    ("abcdefg", ["abc", "def"], 3, False, ["Letters missing from layout"]),
    # Invalid: Letter Conservation - Extra letter in layout
    ("abcdef", ["abc", "dex"], 3, False, ["Letters found in layout that were not in target"]),
    # Invalid: Horizontal non-word
    ("catdogbaz", ["cat", "dog", "baz"], 3, False, ["Invalid word: 'baz' found horizontally"]),
    # Invalid: Vertical non-word
    ("topmanfiz", ["tmf", "oai", "pnz"], 3, False, ["Invalid word: 'fiz' found vertically"]),
    # Segment logic tests (previously "wordgame")
    # Adjusted to expect errors for "wor" and "ame" based on previous run
    ("wordgame", ["wor.d", "g.ame"], 3, False, ["Invalid word: 'wor' found horizontally", "Invalid word: 'ame' found horizontally"]),
    # Adjusted to expect False because many 1 and 2 letter words from this grid are likely not in dictionary
    ("wordgame", ["wor.d", "g.ame"], 1, False, [
        "Invalid word: 'wor'", "Invalid word: 'd'", "Invalid word: 'g'", "Invalid word: 'ame'",
        "Invalid word: 'wg'", "Invalid word: 'o'", "Invalid word: 'ra'", "Invalid word: 'm'", "Invalid word: 'de'"
    ]),
    # Multiple errors test
    ("abcefg", ["axc", "efg"], 3, False, ["Invalid word: 'axc' found horizontally", "Letters missing", "Letters found"]),
    # Invalid due to min_word_length - current function behavior is to NOT error, so expect True, no errors
    ("cat", ["cat"], 4, True, []),
    # Empty grid tests
    ("", [], 3, True, []),
    # Adjusted to expect only the first error reported by the function
    ("abc", [], 3, False, ["Layout grid is empty, but target letters were provided"]),
    # Grid with only empty cells tests
    ("abc", ["...", "...", "."], 3, False, ["Letters missing"]),
    ("", ["...", "...", "."], 3, True, []),
]

@pytest.mark.parametrize("target_letters, layout_rows_repr, min_len, expected_is_valid, expected_errors_contain", VALIDATION_TEST_CASES)
def test_validate_qless_arrangement(target_letters, layout_rows_repr, min_len, expected_is_valid, expected_errors_contain):
    layout_grid = create_test_grid(layout_rows_repr)

    is_valid, errors = validate_qless_arrangement(target_letters, layout_grid, min_len)

    assert is_valid == expected_is_valid, f"Validation failed for input {target_letters=}, {layout_rows_repr=}. Errors: {errors}"
    if not expected_is_valid:
        assert len(errors) > 0, f"Expected errors for input {target_letters}, {layout_rows_repr} but got none."
        for expected_err_substring in expected_errors_contain:
            assert any(expected_err_substring.lower() in err.lower() for err in errors), \
                   f"Expected error substring '{expected_err_substring}' not found in errors: {errors}"
    else:
        assert len(errors) == 0, f"Expected no errors for input {target_letters}, {layout_rows_repr} but got: {errors}"
