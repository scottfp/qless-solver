from pydantic import BaseModel, Field
from typing import List, Dict, Tuple, Set
from collections import Counter

# Ensure this import path is correct based on your project structure
from cli.qless_solver.dictionary import Dictionary

class GridPosition(BaseModel):
    x: int
    y: int
    direction: str = "across"  # "across" or "down"

class PlacedWord(BaseModel):
    word: str
    position: GridPosition

class Grid(BaseModel):
    cells: Dict[Tuple[int, int], str] = Field(default_factory=dict)
    words: List[PlacedWord] = Field(default_factory=list)

    def place_word(self, word: str, position: GridPosition) -> bool:
        # Simulate cell updates based on word and position
        if position.direction == "across":
            for i, char in enumerate(word):
                self.cells[(position.x + i, position.y)] = char
        else: # down
            for i, char in enumerate(word):
                self.cells[(position.x, position.y + i)] = char
        self.words.append(PlacedWord(word=word, position=position))
        return True

    def validate_placement(self, word: str, position: GridPosition) -> bool:
        # Placeholder: Needs full implementation
        # - Check board boundaries (if any)
        # - Check if word connects correctly with existing letters on the grid
        # - Check if all newly formed words (by intersection) are valid dictionary words
        # - Check for no isolated letters or invalid short words are formed
        return True

    def get_anchor_points(self) -> List[GridPosition]:
        # Placeholder: Needs more sophisticated logic
        if not self.cells: # If grid is empty, anchor at origin for the first word
            return [GridPosition(x=0, y=0, direction="across"), GridPosition(x=0, y=0, direction="down")]

        anchors: Set[GridPosition] = set() # Use a set to avoid duplicate anchors
        # A more robust approach would be to find all cells adjacent to existing letters
        # where a new word could potentially start.
        for (r, c) in self.cells.keys():
            # Try to place words starting one cell away in all 4 directions
            # For "across" words
            anchors.add(GridPosition(x=r, y=c + 1, direction="across")) # Right of existing letter
            anchors.add(GridPosition(x=r, y=c - 1, direction="across")) # Left of existing letter (if word extends left)
            # For "down" words
            anchors.add(GridPosition(x=r + 1, y=c, direction="down"))   # Below existing letter
            anchors.add(GridPosition(x=r - 1, y=c, direction="down"))   # Above existing letter (if word extends up)

        # Also, consider starting a word overlaying an existing letter if it forms a valid new word.
        # This requires checking if the letter at (r,c) can be part of a new word.
        for (r_cell, c_cell) in self.cells.keys():
            anchors.add(GridPosition(x=r_cell, y=c_cell, direction="across"))
            anchors.add(GridPosition(x=r_cell, y=c_cell, direction="down"))

        return list(anchors)


    def remove_word(self, word_to_remove: PlacedWord):
        # Remove word from self.words
        self.words = [pw for pw in self.words if pw != word_to_remove]

        # Recalculate cells based on remaining words
        # This is safer than trying to selectively remove letters, especially with overlaps.
        self.cells.clear()
        for pw in self.words:
            if pw.position.direction == "across":
                for i, char in enumerate(pw.word):
                    self.cells[(pw.position.x + i, pw.position.y)] = char
            else: # down
                for i, char in enumerate(pw.word):
                    self.cells[(pw.position.x, pw.position.y + i)] = char


class GridSolution(BaseModel):
    grid: Grid
    used_letters: Counter

def get_valid_words(letters: str, dictionary: Dictionary, min_length: int = 3) -> List[str]:
    # Placeholder: Extremely inefficient. Replace with Trie/DAWG-based generation.
    possible_words = set()
    from itertools import permutations
    letter_list = list(letters.lower())
    for i in range(min_length, len(letter_list) + 1):
        for p in permutations(letter_list, i):
            word = "".join(p)
            if dictionary.is_valid_word(word):
                possible_words.add(word)
    return list(possible_words)


def sort_words_by_potential(words: List[str]) -> List[str]:
    # Sort by length (longer first), then alphabetically
    return sorted(words, key=lambda x: (-len(x), x))

def solve_qless_grid(
    letters: str,
    min_word_length: int = 3,
) -> List[GridSolution]:
    dictionary = Dictionary() # Assumes Dictionary() loads the default dictionary
    # Generate candidate words
    candidate_words = get_valid_words(letters, dictionary, min_word_length)

    # Find grid-valid solutions
    solutions = find_grid_solutions(
        candidate_words,
        Counter(letters.lower()),
        min_word_length,
        dictionary
    )

    return solutions


def find_grid_solutions(
    possible_words: List[str],
    original_available_letters: Counter,
    min_word_length: int,
    dictionary: Dictionary # Pass dictionary for validation if needed by deeper logic
) -> List[GridSolution]:
    solutions: List[GridSolution] = []

    # Sort words to try, e.g., longer words first as a heuristic
    sorted_candidate_words = sort_words_by_potential(possible_words)

    def backtrack(
        current_grid: Grid,
        current_remaining_letters: Counter,
        used_words_set: Set[str],
    ) -> None:
        # Base case for recursion
        if sum(current_remaining_letters.values()) < min_word_length:
            if current_grid.words: # Ensure at least one word is placed
                solution_used_letters = original_available_letters - current_remaining_letters
                # Ensure solutions are deep copies
                solutions.append(GridSolution(grid=current_grid.copy(deep=True), used_letters=solution_used_letters))
            return

        anchor_points = current_grid.get_anchor_points()
        if not current_grid.words and not anchor_points: # Special case for first word on empty grid
             anchor_points = [GridPosition(x=0,y=0,direction="across"), GridPosition(x=0,y=0,direction="down")]


        for point in anchor_points:
            for word_to_try in sorted_candidate_words:
                if word_to_try in used_words_set:
                    continue

                word_counter = Counter(word_to_try.lower())

                can_form_word = True
                for char, count in word_counter.items():
                    if current_remaining_letters[char] < count:
                        can_form_word = False
                        break
                if not can_form_word:
                    continue

                potential_next_grid = current_grid.copy(deep=True)
                # Correctly create PlacedWord instance before passing to place_word
                # place_word expects word (str) and position (GridPosition)
                potential_next_grid.place_word(word_to_try, point)

                # The validate_placement method is a stub and needs full implementation.
                # It should ideally check the state of potential_next_grid.
                if potential_next_grid.validate_placement(word_to_try, point):

                    next_remaining_letters = current_remaining_letters.copy()
                    for char, count in word_counter.items():
                        next_remaining_letters[char] -= count

                    next_used_words_set = used_words_set.copy()
                    next_used_words_set.add(word_to_try)

                    backtrack(potential_next_grid, next_remaining_letters, next_used_words_set)

    initial_grid = Grid()
    backtrack(initial_grid, original_available_letters.copy(), set())

    return solutions
