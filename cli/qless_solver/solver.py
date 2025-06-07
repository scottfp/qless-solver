"""
Core solving logic for the Q-Less game.
"""

from collections import Counter
from typing import Dict, Iterator, List, Optional, Set, Tuple # Added Optional, Tuple

from pydantic import BaseModel, Field
from qless_solver.dictionary import get_valid_words, is_valid_word # Added is_valid_word


class Solution(BaseModel):
    """A solution for the Q-Less game, consisting of interlocking words."""

    words: List[str] = Field(description="List of words that form the solution")
    used_letters: Dict[str, int] = Field(
        description="Count of letters used in the solution"
    )

    def get_words(self) -> Iterator[str]:
        """Get an iterator over the solution's words."""
        return iter(self.words)


def solve_qless(
    letters: str,
    min_word_length: int = 3,
    all_words: bool = False,
) -> List[Solution]:
    """
    Solve the Q-Less game with the given letters.

    Args:
        letters: String of letters from the dice roll (expected to be 12 letters)
        min_word_length: Minimum word length to consider
        all_words: If True, return all valid words that can be formed, not just complete solutions

    Returns:
        A list of possible solutions, where each solution is a list of words
    """
    # Convert input to lowercase and create a counter of available letters
    letters = letters.lower()
    available_letters = Counter(letters)

    # Get all valid words that can be formed from these letters
    possible_words = get_valid_words(letters, min_length=min_word_length)

    if all_words:
        # If all_words is True, return all valid words as individual "solutions"
        return [
            Solution(words=[word], used_letters=Counter(word))
            for word in possible_words
        ]

    # Find solutions that use all letters
    solutions = find_complete_solutions(
        possible_words, available_letters, min_word_length
    )

    return solutions


def find_complete_solutions(
    possible_words: Set[str], available_letters: Counter, min_word_length: int
) -> List[Solution]:
    """
    Find solutions that use all available letters.

    Args:
        possible_words: Set of valid words that can be formed
        available_letters: Counter of available letters
        min_word_length: Minimum word length

    Returns:
        List of solutions
    """
    solutions: List[Solution] = []

    # Store the original letters counter for reference
    original_letters = available_letters.copy()

    # A recursive helper function to build solutions
    def backtrack(
        remaining_letters: Counter,
        current_solution: List[str],
    ) -> None:
        # If no letters remain, we have a complete solution
        if sum(remaining_letters.values()) == 0:
            # Create a solution with the words and the used letters
            solution = Solution(
                words=current_solution.copy(),
                used_letters=original_letters - remaining_letters,
            )
            solutions.append(solution)
            return

        # Try each possible word
        for word in possible_words:
            word_counter = Counter(word)

            # Check if this word can be formed with remaining letters
            if all(
                word_counter[letter] <= remaining_letters[letter]
                for letter in word_counter
            ):
                # Use this word
                current_solution.append(word)
                # Remove its letters from remaining_letters
                for letter, count in word_counter.items():
                    remaining_letters[letter] -= count

                # Recursively try to complete the solution
                backtrack(remaining_letters, current_solution)

                # Backtrack
                current_solution.pop()
                for letter, count in word_counter.items():
                    remaining_letters[letter] += count

    backtrack(available_letters.copy(), [])
    return solutions


def validate_qless_arrangement(
    target_letters_str: str,
    layout_grid: List[List[Optional[str]]],
    min_word_length: int = 3,
) -> Tuple[bool, List[str]]:

    errors: List[str] = []

    # Removed local import of is_valid_word, as it's imported at module level.

    target_letters_str_lower = target_letters_str.lower()
    target_letter_counts = Counter(target_letters_str_lower)

    # Optional: Initial check for target_letters_str validity (e.g., 12 unique letters)
    # if len(target_letters_str_lower) != 12 or len(target_letter_counts) != 12:
    #     errors.append(f"Target letters string must contain exactly 12 unique letters. Provided: '{target_letters_str}'")
    # For now, this responsibility can be left to the caller or CLI.

    layout_letter_counts = Counter()
    grid_rows = len(layout_grid)

    if grid_rows == 0:
        if target_letter_counts:
             errors.append(f"Layout grid is empty, but target letters were provided: {sorted(list(target_letter_counts.keys()))}")
        # If no target letters and empty grid, it's technically valid (no errors)
        return not errors, errors

    grid_cols = len(layout_grid[0]) # Assumes all rows are of same length (normalized by CLI)

    for r in range(grid_rows):
        if len(layout_grid[r]) != grid_cols: # Should not happen if CLI normalizes
            errors.append(f"Internal Error: Grid normalization failed. Row {r+1} has length {len(layout_grid[r])}, expected {grid_cols}.")
            return False, errors # Malformed grid, critical error

        for c in range(grid_cols):
            letter = layout_grid[r][c]
            if letter:
                if not isinstance(letter, str) or not letter.isalpha() or len(letter) != 1:
                    errors.append(f"Invalid character '{letter}' in grid at row {r+1}, col {c+1}. Only single letters allowed.")
                    continue
                layout_letter_counts[letter.lower()] += 1

    if layout_letter_counts != target_letter_counts:
        missing_from_layout = target_letter_counts - layout_letter_counts
        extra_in_layout = layout_letter_counts - target_letter_counts

        if missing_from_layout:
            errors.append(f"Letters missing from layout that were in target: {sorted(list(missing_from_layout.keys()))}")
        if extra_in_layout:
            errors.append(f"Letters found in layout that were not in target: {sorted(list(extra_in_layout.keys()))}")

        # Check for incorrect counts if a letter is common to both but counts differ
        # (This is usually covered by the symmetric difference logic of Counter if elements are unique)
        for letter_key in target_letter_counts:
             if letter_key not in missing_from_layout and letter_key not in extra_in_layout:
                 if layout_letter_counts[letter_key] != target_letter_counts[letter_key]:
                      errors.append(f"Letter '{letter_key}' count mismatch: layout has {layout_letter_counts[letter_key]}, target expects {target_letter_counts[letter_key]}.")


    def _extract_and_validate_segments(line: List[Optional[str]], is_horizontal: bool, line_num: int, current_errors: List[str]) -> None:
        current_segment_letters: List[str] = []
        start_idx = -1
        processed_line = line + [None]

        for i, cell_content in enumerate(processed_line):
            if cell_content and cell_content.isalpha():
                if not current_segment_letters:
                    start_idx = i
                current_segment_letters.append(cell_content)
            else:
                if len(current_segment_letters) >= min_word_length:
                    word_str = "".join(current_segment_letters)
                    if not is_valid_word(word_str, min_word_length):
                        orientation = "horizontally" if is_horizontal else "vertically"
                        col_row_label = "row" if is_horizontal else "column"
                        start_pos_label = "column" if is_horizontal else "row"
                        current_errors.append(
                            f"Invalid word: '{word_str}' found {orientation} in {col_row_label} {line_num+1} starting at {start_pos_label} {start_idx+1}."
                        )
                # Optional: Add warnings for segments < min_word_length if needed by rules
                current_segment_letters = []
                start_idx = -1

    for r_idx, row_list in enumerate(layout_grid):
        _extract_and_validate_segments(row_list, is_horizontal=True, line_num=r_idx, current_errors=errors)

    if grid_rows > 0 and grid_cols > 0:
        for c_idx in range(grid_cols):
            column_list = [layout_grid[r_idx][c_idx] for r_idx in range(grid_rows)]
            _extract_and_validate_segments(column_list, is_horizontal=False, line_num=c_idx, current_errors=errors)

    return not errors, errors
