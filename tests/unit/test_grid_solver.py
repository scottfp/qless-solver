import pytest
from collections import Counter
from qless_solver.grid_solver import (
    Grid,
    GridPosition,
    PlacedWord,
    GridSolution,
    solve_qless_grid,
    get_valid_words,
)
from qless_solver.dictionary import Dictionary

# Mock Dictionary for testing get_valid_words and solve_qless_grid
class MockDictionary(Dictionary):
    def __init__(self, words=None):
        self._words = set(words) if words else set()

    def is_valid_word(self, word: str) -> bool:
        return word in self._words

    def load_dictionary(self, filepath: str) -> None: # Add filepath argument
        pass # Don't load from file for mock


@pytest.fixture
def empty_grid():
    return Grid()

@pytest.fixture
def simple_dictionary():
    return MockDictionary(words=["cat", "at", "a", "act", "car", "rat"])

def test_grid_creation(empty_grid: Grid):
    assert empty_grid.cells == {}
    assert empty_grid.words == []

def test_place_word_across(empty_grid: Grid):
    grid = empty_grid
    position = GridPosition(x=0, y=0, direction="across")
    word = "cat"
    grid.place_word(word, position)

    assert len(grid.words) == 1
    assert grid.words[0] == PlacedWord(word=word, position=position)
    assert grid.cells.get((0,0)) == "c"
    assert grid.cells.get((1,0)) == "a"
    assert grid.cells.get((2,0)) == "t"
    assert grid.cells.get((3,0)) is None

def test_place_word_down(empty_grid: Grid):
    grid = empty_grid
    position = GridPosition(x=0, y=0, direction="down")
    word = "cat"
    grid.place_word(word, position)

    assert len(grid.words) == 1
    assert grid.words[0] == PlacedWord(word=word, position=position)
    assert grid.cells.get((0,0)) == "c"
    assert grid.cells.get((0,1)) == "a"
    assert grid.cells.get((0,2)) == "t"
    assert grid.cells.get((0,3)) is None

def test_remove_word(empty_grid: Grid):
    grid = empty_grid
    # Define the word and position for placement
    word_to_place = "cat"
    position_to_place_at = GridPosition(x=0, y=0, direction="across")

    grid.place_word(word_to_place, position_to_place_at)
    assert len(grid.words) == 1

    # The PlacedWord object to remove must be the one that's actually in grid.words
    placed_word_in_grid = grid.words[0]
    assert placed_word_in_grid.word == word_to_place # Sanity check

    grid.remove_word(placed_word_in_grid)
    assert len(grid.words) == 0
    assert len(grid.cells) == 0

def test_get_anchor_points_empty_grid(empty_grid: Grid):
    anchors = empty_grid.get_anchor_points()
    assert GridPosition(x=0, y=0, direction="across") in anchors
    assert GridPosition(x=0, y=0, direction="down") in anchors

def test_get_anchor_points_with_word(empty_grid: Grid):
    grid = empty_grid
    grid.place_word("cat", GridPosition(x=0, y=0, direction="across"))
    anchors = grid.get_anchor_points()
    # The current get_anchor_points is a placeholder, so this test is basic.
    assert len(anchors) > 0

def test_validate_placement_stub(empty_grid: Grid):
    # Current validate_placement is a stub, always returns True
    assert empty_grid.validate_placement("word", GridPosition(x=0,y=0)) == True

def test_get_valid_words_mock_dict(simple_dictionary: MockDictionary):
    letters = "atc"
    valid_words = get_valid_words(letters, simple_dictionary, min_length=2)
    # Using set for comparison to ignore order and duplicates from permutations if any
    assert set(valid_words) == {"at", "cat", "act"} # "act" is also a permutation of "atc"

    valid_words_len_1 = get_valid_words(letters, simple_dictionary, min_length=1)
    assert "a" in valid_words_len_1


# Tests for solve_qless_grid
def test_solve_qless_grid_simple_case(monkeypatch, simple_dictionary: MockDictionary):
    # Patch the Dictionary class instantiation within the grid_solver module
    monkeypatch.setattr("qless_solver.grid_solver.Dictionary", lambda: simple_dictionary)

    solutions = solve_qless_grid(letters="cat", min_word_length=3)

    # Depending on current stubs (validate_placement always True, basic anchors),
    # "cat" should be a solution.
    found_cat_solution = False
    for sol in solutions:
        if len(sol.grid.words) == 1 and sol.grid.words[0].word == "cat":
            found_cat_solution = True
            # Counter("cat") will be {'c': 1, 'a': 1, 't': 1}
            assert sol.used_letters == Counter("cat")
            break
    assert found_cat_solution, "Expected to find a solution with the word 'cat'"


def test_solve_qless_grid_no_solution(monkeypatch, simple_dictionary: MockDictionary):
    monkeypatch.setattr("qless_solver.grid_solver.Dictionary", lambda: simple_dictionary)
    solutions = solve_qless_grid(letters="xyz", min_word_length=3)
    assert len(solutions) == 0

# Add more tests for edge cases, complex scenarios, and specific behaviors of Grid methods later.
# Especially once validate_placement and get_anchor_points are fully implemented.
# Test remove_word with overlapping words once that logic is more robust.
